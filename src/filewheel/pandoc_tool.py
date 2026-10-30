"""Optional local Pandoc discovery and bounded, frozen-safe process execution."""
import argparse
import json
import math
import os
import re
import shutil
import subprocess
import sys
import tempfile
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path
from time import monotonic
from zipfile import BadZipFile, ZipFile

from filewheel.converters.base import (
    ConversionError,
    DependencyUnavailable,
    check_cancel,
)
from filewheel.converters.office import _stop_office_tree
from filewheel.libreoffice_bundle import external_tool_environment
from filewheel.paths import bundled_tool_root, ensure_separate_tool_source

PUBLISH_WRITERS = {'.docx': 'docx', '.html': 'html5', '.txt': 'plain', '.rtf': 'rtf',
                   '.odt': 'odt', '.epub': 'epub3', '.pptx': 'pptx'}
_RTS = ['+RTS', '-M512M', '-RTS']


@dataclass(frozen=True)
class PandocLocation:
    executable: Path
    source: str
    version: str
    readers: tuple[str, ...]
    writers: tuple[str, ...]


def _invoke(executable, arguments, *, workdir, timeout, cancel=None):
    if type(timeout) not in (int, float) or not math.isfinite(timeout) or not 0 < timeout <= 600:
        raise ValueError('Tool timeout must be finite and between 0 and 600 seconds')
    check_cancel(cancel)
    process = environment = None
    # Files keep warnings/errors bounded in parent memory. No UI or pipe wait.
    with tempfile.TemporaryFile(dir=workdir) as stdout, tempfile.TemporaryFile(dir=workdir) as stderr:
        try:
            with external_tool_environment() as environment:
                process = subprocess.Popen([str(executable), *arguments], shell=False, cwd=workdir,
                                           stdout=stdout, stderr=stderr, env=environment,
                                           creationflags=getattr(subprocess, 'CREATE_NO_WINDOW', 0),
                                           **({'process_group': 0} if sys.platform == 'linux' else {}))
        except OSError as error:
            if process is not None:
                _stop_office_tree(process, environment)
            raise DependencyUnavailable('Could not start the local Pandoc executable') from error
        deadline = monotonic() + timeout
        try:
            while process.poll() is None:
                check_cancel(cancel)
                if os.fstat(stdout.fileno()).st_size > 131072 or os.fstat(stderr.fileno()).st_size > 131072:
                    raise ConversionError('Pandoc diagnostic output exceeds its limit')
                if monotonic() >= deadline:
                    raise ConversionError('Pandoc timed out before output publication')
                try:
                    process.wait(timeout=min(.05, max(.001, deadline - monotonic())))
                except subprocess.TimeoutExpired:
                    pass
            check_cancel(cancel)
        except BaseException:  # Reap an owned tool on interruption/unexpected IO errors too.
            _stop_office_tree(process, environment)
            raise
        stdout.seek(0)
        stderr.seek(0)
        out, err = stdout.read(131073), stderr.read(131073)
        if len(out) > 131072 or len(err) > 131072:
            raise ConversionError('Pandoc diagnostic output exceeds its limit')
        if process.returncode:
            cause = RuntimeError(f'Pandoc exit={process.returncode}: {err.decode("utf-8", errors="replace")[:8192]}')
            raise ConversionError('Pandoc could not convert this document; see the local log') from cause
        return out.decode('utf-8', errors='strict')


def _writer_smoke(executable, writer, extension, directory, invoke):
    """Listing a writer is insufficient when sandbox reference data is missing."""
    output = Path(directory) / ('probe' + extension)
    invoke([*_RTS, '--sandbox', '--data-dir=' + str(Path(directory) / 'data'),
            '--from=gfm-raw_html', '--to=' + writer, '--standalone',
            '--metadata=title:Filewheel probe', '--output=' + str(output),
            '--', str(Path(directory) / 'probe.md')])
    with output.open('rb') as stream:
        data = stream.read(2 * 1024 * 1024 + 1)
    if not data or len(data) > 2 * 1024 * 1024:
        return False
    if extension in ('.docx', '.odt', '.pptx', '.epub'):
        required = {'.docx': 'word/document.xml', '.odt': 'content.xml',
                    '.pptx': 'ppt/slides/slide1.xml', '.epub': 'META-INF/container.xml'}[extension]
        with ZipFile(output) as archive:
            text = archive.read(required)
            return b'Filewheel' in text if extension != '.epub' else b'rootfile' in text
    if extension == '.html':
        return all(tag in data.lower() for tag in (b'<html', b'<head', b'<body')) and b'Filewheel' in data
    if extension == '.rtf':
        return data.startswith(b'{\\rtf') and b'Filewheel' in data
    return b'Filewheel' in data and b'\x00' not in data


@lru_cache(maxsize=16)
def _probe(executable, device, inode, size, modified):
    # Identity-keyed startup cache; no recurring tool calls while hovering.
    try:
        with tempfile.TemporaryDirectory(prefix='filewheel-pandoc-probe-') as directory:
            deadline = monotonic() + 8
            def invoke(arguments):
                remaining = deadline - monotonic()
                if remaining <= 0:
                    raise ConversionError('Pandoc capability probe exceeded its startup budget')
                return _invoke(executable, arguments, workdir=directory, timeout=min(2, remaining))
            version_text = invoke(['--version'])
            match = re.match(r'pandoc (\d+)\.(\d+)(?:\.\d+)*', version_text)
            if not match or tuple(map(int, match.group(1, 2))) < (3, 1):
                return None
            readers = invoke(['--list-input-formats'])
            writers = invoke(['--list-output-formats'])
            read, write = tuple(readers.split()), tuple(writers.split())
            if not {'gfm', 'json'}.issubset(read) or 'json' not in write:
                return None
            (Path(directory) / 'data').mkdir()
            (Path(directory) / 'probe.md').write_text('# Filewheel probe\n\nUseful text.\n', encoding='utf-8')
            verified = ['json']
            for extension, writer in PUBLISH_WRITERS.items():
                if writer not in write:
                    continue
                try:
                    if _writer_smoke(executable, writer, extension, directory, invoke):
                        verified.append(writer)
                except (OSError, ValueError, KeyError, BadZipFile, ConversionError):
                    continue  # Missing reference templates hide this writer only.
            return match.group(0).removeprefix('pandoc '), read, tuple(verified)
    except (OSError, UnicodeError, ConversionError):
        return None


def _location(path, source):
    path = Path(path)
    if not path.is_absolute() or not path.is_file():
        return None
    if sys.platform == 'win32' and path.suffix.lower() != '.exe':
        return None
    path = path.resolve()
    info = path.stat()
    result = _probe(str(path), info.st_dev, info.st_ino, info.st_size, info.st_mtime_ns)
    return PandocLocation(path, source, *result) if result else None


def validate_bundle(directory, *, platform=None, execute=True, output_root=None):
    directory = Path(directory)
    if output_root is not None:
        # Resolve ancestor junctions/symlinks too, before executing or rebuilding.
        ensure_separate_tool_source(directory, output_root)
    if directory.is_dir():
        for member in directory.iterdir():
            if (member.is_symlink() or member.is_junction() or not member.is_file()):
                raise ValueError('Portable Pandoc must be a flat release without filesystem aliases')
    platform = sys.platform if platform is None else platform
    executable = directory / ('pandoc.exe' if platform == 'win32' else 'pandoc')
    licenses = ('COPYRIGHT.txt', 'COPYRIGHT')
    copying = ('COPYING.rtf', 'COPYING', 'LICENSE')
    if (not directory.is_dir() or directory.is_symlink() or directory.is_junction() or not executable.is_file()
            or executable.is_symlink() or not executable.stat().st_size
            or not any((directory / name).is_file() and (directory / name).stat().st_size for name in licenses)
            or not any((directory / name).is_file() and (directory / name).stat().st_size for name in copying)):
        raise ValueError('Keep the complete portable Pandoc executable and COPYRIGHT/COPYING files together')
    if not execute:
        return PandocLocation(executable.resolve(), 'bundled', 'not-executed', (), ())
    location = _location(executable.resolve(), 'bundled')
    if location is None or not set(PUBLISH_WRITERS.values()).intersection(location.writers):
        raise ValueError('Portable Pandoc 3.1+ with working gfm/json reader/writer probes is required')
    return location


def find_pandoc(executable=None, *, app_root=None):
    explicit = executable if executable is not None else os.getenv('FILEWHEEL_PANDOC')
    try:
        if explicit is not None:
            return _location(explicit, 'explicit')
        from filewheel.installation import selected_tool
        selected = selected_tool('Pandoc') if app_root is None else None
        if selected is not None:
            location = _location(selected, 'system')
            if location is not None:
                return location
        root = bundled_tool_root() if app_root is None else Path(app_root)
        try:
            return validate_bundle(root / 'tools/pandoc')
        except (ValueError, OSError):
            if os.getenv('FILEWHEEL_BUNDLED_TOOLS_ONLY') == '1':
                return None
        installed = shutil.which('pandoc')
        return _location(Path(installed).absolute(), 'system') if installed else None
    except (OSError, ValueError):
        return None


def run_pandoc(location, arguments, *, workdir, cancel=None, timeout=45):
    if location is None or not location.executable.is_file():
        raise DependencyUnavailable('Install Pandoc 3.1+ or configure FILEWHEEL_PANDOC')
    # The official binary supports RTS heap limits; no filter/PDF engine is run.
    _invoke(location.executable, [*_RTS, *arguments], workdir=workdir,
            cancel=cancel, timeout=timeout)


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--validate', type=Path, required=True)
    parser.add_argument('--output-root', type=Path, help='pre-build physical source/output separation check')
    args = parser.parse_args(argv)
    try:
        location = validate_bundle(args.validate, output_root=args.output_root)
    except (ValueError, OSError) as error:
        print(f'Pandoc bundle validation failed: {error}', file=sys.stderr)
        return 2
    print(json.dumps({'valid': True, 'executable': str(location.executable), 'version': location.version,
                      'writers': location.writers}))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
