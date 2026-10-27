"""Optional offline Markdown publishing via a sandboxed local Pandoc executable."""
import base64
import io
import json
import math
import re
import stat
from pathlib import PurePosixPath
from urllib.parse import unquote, urlsplit
from xml.etree import ElementTree
from zipfile import BadZipFile, ZipFile

from filewheel.converters.base import (
    Capability,
    ConversionError,
    DependencyUnavailable,
    EngineOutput,
    check_cancel,
)
from filewheel.converters.office import LibreOfficeEngine
from filewheel.converters.structured_markdown import decode_text
from filewheel.pandoc_tool import PUBLISH_WRITERS as WRITERS
from filewheel.pandoc_tool import find_pandoc, run_pandoc

MAX_INPUT = 8 * 1024 * 1024
MAX_AST = 32 * 1024 * 1024
MAX_OUTPUT = 64 * 1024 * 1024
MAX_ASSET = 8 * 1024 * 1024
MAX_ASSETS = 32 * 1024 * 1024


def _read_bounded(path, limit):
    with path.open('rb') as stream:
        result = stream.read(limit + 1)
    if len(result) > limit:
        raise ConversionError('Markdown document or generated output exceeds the size limit')
    return result


class _Assets:
    """Only bounded local raster bytes become resources visible to the writer."""
    def __init__(self, source, cancel, warnings):
        self.root = source.parent.resolve()
        self.cancel, self.warnings = cancel, warnings
        self.count = self.total = self.referenced_bytes = 0
        self.cache = {}

    def image(self, target):
        check_cancel(self.cancel)
        self.count += 1
        if self.count > 32:
            raise ConversionError('Markdown image count limit exceeded')
        if target in self.cache:
            return self._reference(self.cache[target])
        parsed = urlsplit(target)
        name = unquote(parsed.path)
        # Do not let Pandoc resolve network URLs, drive/UNC paths, SVG or includes.
        if (parsed.scheme or parsed.netloc or parsed.query or parsed.fragment or not name
                or '\\' in name or ':' in name or '\x00' in name
                or PurePosixPath(name).is_absolute() or '..' in PurePosixPath(name).parts):
            self.warnings.append('Remote, absolute or unsafe image references were omitted; no resource was fetched.')
            self.cache[target] = None
            return None
        candidate = self.root / name
        if candidate.suffix.lower() not in ('.png', '.jpg', '.jpeg', '.webp'):
            self.warnings.append('Only local PNG, JPEG and WebP image resources are embedded; other resources were omitted.')
            self.cache[target] = None
            return None
        try:
            relative = candidate.relative_to(self.root)
            current = self.root
            for part in relative.parts:
                current = current / part
                info = current.lstat()
                if stat.S_ISLNK(info.st_mode) or getattr(info, 'st_file_attributes', 0) & 0x400:
                    raise ConversionError('Markdown image links/reparse points are unsupported')
            if not stat.S_ISREG(info.st_mode) or not candidate.resolve().is_relative_to(self.root):
                raise ConversionError('Markdown image must be a regular local file')
            data = _read_bounded(candidate, MAX_ASSET)
        except FileNotFoundError:
            self.warnings.append('A missing local image was omitted.')
            self.cache[target] = None
            return None
        from PIL import Image
        try:
            with Image.open(io.BytesIO(data)) as image:
                if image.format not in ('PNG', 'JPEG', 'WEBP') or image.width * image.height > 16_000_000:
                    raise ConversionError('Markdown image format or dimensions exceed the supported limits')
                image.seek(0)
                image.load()
                check_cancel(self.cancel)
                image = image.convert('RGBA' if 'A' in image.getbands() else 'RGB')
                encoded = io.BytesIO()
                image.save(encoded, format='PNG')
                data = encoded.getvalue()
        except (OSError, ValueError) as error:
            raise ConversionError('A Markdown image resource is unreadable or corrupt') from error
        self.total += len(data)
        if len(data) > MAX_ASSET or self.total > MAX_ASSETS:
            raise ConversionError('Markdown embedded image size limit exceeded')
        self.cache[target] = 'data:image/png;base64,' + base64.b64encode(data).decode('ascii')
        return self._reference(self.cache[target])

    def _reference(self, uri):
        # Repeated cached images expand again in the writer's JSON input.
        self.referenced_bytes += len(uri) if uri else 0
        if self.referenced_bytes > MAX_AST:
            raise ConversionError('Markdown image references exceed the expanded structure budget')
        return uri


def _write_ast(path, ast):
    total = 0
    encoder = json.JSONEncoder(ensure_ascii=False)
    with path.open('wb') as stream:
        for chunk in encoder.iterencode(ast):
            data = chunk.encode('utf-8')
            total += len(data)
            if total > MAX_AST:
                raise ConversionError('Prepared Markdown structure exceeds the size limit')
            stream.write(data)


def _sanitize_ast(value, assets, cancel, warnings):
    count = 0
    def visit(node, depth=0):
        nonlocal count
        check_cancel(cancel)
        count += 1
        if depth > 128 or count > 200000:
            raise ConversionError('Markdown structure exceeds depth or node limits')
        if isinstance(node, list):
            return [visit(child, depth + 1) for child in node]
        if not isinstance(node, dict):
            return node
        tag, content = node.get('t'), node.get('c')
        if tag in ('RawBlock', 'RawInline'):
            warnings.append('Raw HTML/TeX is omitted from Markdown publishing.')
            return {'t': 'Plain', 'c': []} if tag == 'RawBlock' else {'t': 'Str', 'c': ''}
        if tag == 'Image':
            if not isinstance(content, list) or len(content) != 3:
                raise ConversionError('Invalid Markdown image structure')
            alt = visit(content[1], depth + 1)
            uri = assets.image(content[2][0])
            if uri is None:
                return {'t': 'Span', 'c': [['', [], []], alt]}
            return {'t': 'Image', 'c': [['', [], []], alt, [uri, '']]}
        if tag == 'Link':
            if not isinstance(content, list) or len(content) != 3:
                raise ConversionError('Invalid Markdown link structure')
            label = visit(content[1], depth + 1)
            uri = content[2][0]
            parsed = urlsplit(uri)
            if (parsed.scheme.lower() not in ('', 'http', 'https', 'mailto')
                    or parsed.netloc and not parsed.scheme or '\\' in uri
                    or any(ord(char) < 32 for char in uri)
                    or not parsed.scheme and ':' in uri):
                warnings.append('Unsafe hyperlink targets were omitted.')
                return {'t': 'Span', 'c': [['', [], []], label]}
            return {'t': 'Link', 'c': [['', [], []], label, [uri, '']]}
        return {key: visit(child, depth + 1) for key, child in node.items()}
    result = visit(value)
    if not isinstance(result, dict) or not isinstance(result.get('blocks'), list):
        raise ConversionError('Pandoc did not produce a document structure')
    result['meta'] = {}  # No input metadata can select templates, filters or resources.
    return result


class PandocEngine:
    engine_id = 'pandoc'

    def __init__(self, *, executable=None, timeout=45, office=None):
        if type(timeout) not in (int, float) or not math.isfinite(timeout) or not 0 < timeout <= 600:
            raise ValueError('Pandoc timeout must be positive and bounded')
        self.timeout = timeout
        self.location = find_pandoc(executable)
        self.office = office if office is not None else LibreOfficeEngine()
        offered = WRITERS if self.location is None else {
            ext: writer for ext, writer in WRITERS.items() if writer in self.location.writers}
        self.capabilities = tuple(Capability('.md', 'Document', ext, ext[1:].upper(), self.engine_id)
                                  for ext in offered)
        if self.office.available() and (self.location is None or 'docx' in self.location.writers):
            self.capabilities += (Capability('.md', 'Document', '.pdf', 'PDF', self.engine_id),)

    def available(self):
        return (self.location is not None and self.location.executable.is_file()
                and {'gfm', 'json'} <= set(self.location.readers)
                and 'json' in self.location.writers and bool(self.capabilities))

    def convert(self, source, extension, workdir, progress, cancel):
        check_cancel(cancel)
        if not self.available():
            raise DependencyUnavailable('Install a compatible local Pandoc executable for Markdown publishing')
        if source.suffix.lower() != '.md' or extension not in {c.output_extension for c in self.capabilities}:
            raise ConversionError('Unsupported Markdown publishing format')
        text = decode_text(_read_bounded(source, MAX_INPUT))
        local = workdir / 'input.md'
        local.write_text(text, encoding='utf-8')
        data_dir = workdir / 'pandoc-data'
        data_dir.mkdir()
        common = ['--sandbox', '--data-dir=' + str(data_dir)]
        ast_path = workdir / 'document.json'
        progress(.1, 'Parsing Markdown locally')
        run_pandoc(self.location, [*common, '--from=gfm-raw_html', '--to=json',
                                  '--output=' + str(ast_path), '--', str(local)],
                   workdir=workdir, cancel=cancel, timeout=self.timeout)
        try:
            ast = json.loads(_read_bounded(ast_path, MAX_AST))
        except (ValueError, RecursionError) as error:
            raise ConversionError('Pandoc returned invalid or excessively nested Markdown structure') from error
        warnings = ['Markdown publishing preserves basic structure, not exact original layout or fonts.']
        assets = _Assets(source, cancel, warnings)
        ast = _sanitize_ast(ast, assets, cancel, warnings)
        _write_ast(ast_path, ast)
        check_cancel(cancel)
        intermediate = extension == '.pdf'
        writer = 'docx' if intermediate else WRITERS[extension]
        generated = workdir / ('intermediate.docx' if intermediate else 'output' + extension)
        progress(.35, 'Publishing with local Pandoc')
        run_pandoc(self.location, [*common, '--from=json', '--to=' + writer, '--standalone',
                                  '--metadata=title:Filewheel document', '--output=' + str(generated),
                                  '--', str(ast_path)], workdir=workdir, cancel=cancel, timeout=self.timeout)
        check_cancel(cancel)
        _read_bounded(generated, MAX_OUTPUT)
        if intermediate:
            if not self.office.available():
                raise DependencyUnavailable('LibreOffice is required for Markdown to PDF')
            office_dir = workdir / 'office'
            office_dir.mkdir()
            self.validate(EngineOutput(generated, 'intermediate.docx'))
            progress(.6, 'Rendering Markdown PDF with LibreOffice')
            outputs = self.office.convert(generated, '.pdf', office_dir,
                                          lambda value, message: progress(.6 + .2 * value, message), cancel)
            if len(outputs) != 1:
                raise ConversionError('LibreOffice produced unexpected Markdown PDF outputs')
            self.office.validate(outputs[0])
            check_cancel(cancel)
            final = workdir / 'output.pdf'
            outputs[0].path.replace(final)
            generated = final
            warnings.extend(outputs[0].warnings)
        if extension == '.pptx':
            warnings.append('Markdown-to-slides uses heading-based slide splitting; complex layout and notes may be lost.')
        progress(.85, 'Checking published document')
        return (EngineOutput(generated, source.with_suffix(extension).name, tuple(dict.fromkeys(warnings))),)

    def validate(self, output):
        path = output.path
        data = _read_bounded(path, MAX_OUTPUT)
        suffix = path.suffix.lower()
        if suffix == '.pdf':
            self.office.validate(output)
        elif suffix in ('.docx', '.odt', '.epub', '.pptx'):
            try:
                with ZipFile(path) as archive:
                    if sum(info.file_size for info in archive.infolist()) > 256 * 1024 * 1024 or archive.testzip():
                        raise ConversionError('Published document archive is corrupt or oversized')
                    required = {'.docx': 'word/document.xml', '.odt': 'content.xml',
                                '.pptx': 'ppt/presentation.xml', '.epub': 'META-INF/container.xml'}[suffix]
                    root = ElementTree.fromstring(archive.read(required))
                    if not list(root):
                        raise ConversionError('Published document has no structure')
                    if suffix == '.epub' and archive.read('mimetype') != b'application/epub+zip':
                        raise ConversionError('Published EPUB has an invalid media type')
                    names = archive.namelist()
                    if suffix == '.docx':
                        text = ''.join(node.text or '' for node in root.iter() if node.tag.endswith('}t'))
                        if not text.strip() and not any(name.startswith('word/media/') for name in names):
                            raise ConversionError('Published Word document has no text or images')
                    elif suffix == '.odt':
                        text = ''.join(root.itertext())
                        if not text.strip() and not any(name.startswith('Pictures/') for name in names):
                            raise ConversionError('Published ODT document has no content')
                    elif suffix == '.pptx':
                        slides = [name for name in names if re.fullmatch(r'ppt/slides/slide\d+\.xml', name)]
                        if not slides:
                            raise ConversionError('Published presentation has no slides')
                        for name in slides:
                            if not ElementTree.fromstring(archive.read(name)).tag.endswith('}sld'):
                                raise ConversionError('Published slide has an invalid structure')
                    elif suffix == '.epub':
                        packages = [node.get('full-path') for node in root.iter() if node.tag.endswith('}rootfile')]
                        if not packages:
                            raise ConversionError('Published EPUB has no package')
                        for name in packages:
                            package = ElementTree.fromstring(archive.read(name))
                            if not any(node.tag.endswith('}itemref') for node in package.iter()):
                                raise ConversionError('Published EPUB has no reading order')
            except (BadZipFile, KeyError, ElementTree.ParseError) as error:
                raise ConversionError('Published document has an invalid structure') from error
        elif suffix == '.html':
            text = data.decode('utf-8')
            if not all(re.search(r'<' + tag + r'(?:\s|>)', text, re.IGNORECASE) for tag in ('html', 'head', 'body')):
                raise ConversionError('Published HTML must be a complete standalone document')
        elif suffix == '.rtf':
            if not data.startswith(b'{\\rtf') or not data.rstrip().endswith(b'}') or b'\x00' in data:
                raise ConversionError('Published RTF is invalid')
        elif suffix == '.txt':
            if not data.decode('utf-8').strip() or b'\x00' in data:
                raise ConversionError('Published text is empty or binary')
        else:
            raise ConversionError('Unknown Markdown publishing output')
