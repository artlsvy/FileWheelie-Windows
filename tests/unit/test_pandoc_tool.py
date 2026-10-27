"""Actual tool discovery/process bounds; no Windows build is inferred."""
import sys
from pathlib import Path
from threading import Event, Timer
from unittest.mock import patch
from zipfile import BadZipFile

import pytest

from filewheel.converters.base import ConversionCancelled, ConversionError, DependencyUnavailable
from filewheel.pandoc_tool import (
    PUBLISH_WRITERS,
    _invoke,
    _probe,
    find_pandoc,
    run_pandoc,
    validate_bundle,
)

TOOL = Path('/tmp/filewheel-pandoc-3.12.1/pandoc')


def test_absent_and_relative_explicit_tool_do_not_fall_back(monkeypatch, tmp_path):
    monkeypatch.setenv('FILEWHEEL_PANDOC', str(tmp_path / 'absent'))
    assert find_pandoc() is None
    assert find_pandoc('pandoc') is None
    with pytest.raises(DependencyUnavailable):
        run_pandoc(None, [], workdir=tmp_path)


def test_portable_tree_requires_licenses_and_an_executable(tmp_path):
    with pytest.raises(ValueError):
        validate_bundle(tmp_path, platform='win32', execute=False)
    (tmp_path/'pandoc.exe').write_bytes(b'MZ fixture - not a native executable test')
    (tmp_path/'COPYRIGHT.txt').write_text('copyright')
    with pytest.raises(ValueError):
        validate_bundle(tmp_path, platform='win32', execute=False)
    (tmp_path/'COPYING.rtf').write_text('GPL')
    info = validate_bundle(tmp_path, platform='win32', execute=False)
    assert info.source == 'bundled' and info.version == 'not-executed'


@pytest.mark.skipif(not TOOL.is_file(), reason='Actual optional Pandoc absent')
def test_actual_writer_probes_cache_and_withhold_broken_templates(monkeypatch):
    _probe.cache_clear()
    from filewheel import pandoc_tool
    actual = pandoc_tool._writer_smoke
    def omit_pptx(executable, writer, extension, directory, invoke):
        if writer == 'pptx':
            raise BadZipFile('Reference template unavailable or corrupt')
        return actual(executable, writer, extension, directory, invoke)
    try:
        with patch.object(pandoc_tool, '_writer_smoke', side_effect=omit_pptx) as smoke:
            info = find_pandoc(TOOL)
            assert 'docx' in info.writers and 'pptx' not in info.writers
            count = smoke.call_count
            assert find_pandoc(TOOL) == info
            assert smoke.call_count == count
    finally:
        _probe.cache_clear()
    assert set(PUBLISH_WRITERS.values()) <= set(find_pandoc(TOOL).writers)


def test_real_process_timeout_cancel_failure_and_diagnostic_budget(tmp_path):
    with pytest.raises(ConversionError, match='timed out'):
        _invoke(sys.executable, ['-c', 'import time; time.sleep(10)'], workdir=tmp_path, timeout=.08)
    cancel = Event()
    timer = Timer(.08, cancel.set)
    timer.start()
    try:
        with pytest.raises(ConversionCancelled):
            _invoke(sys.executable, ['-c', 'import time; time.sleep(10)'], workdir=tmp_path,
                    timeout=5, cancel=cancel)
    finally:
        timer.join()
    with pytest.raises(ConversionError, match='could not convert'):
        _invoke(sys.executable, ['-c', 'import sys; sys.stderr.write("real failure");sys.exit(2)'],
                workdir=tmp_path, timeout=5)
    with pytest.raises(ConversionError, match='diagnostic'):
        _invoke(sys.executable, ['-c', 'print("x"*200000)'], workdir=tmp_path, timeout=5)
    with pytest.raises(DependencyUnavailable):
        _invoke(tmp_path/'absent', [], workdir=tmp_path, timeout=1)


def test_real_process_argv_and_cwd_preserve_spaces_unicode_without_shell(tmp_path):
    path = tmp_path/'Résumé space'
    path.mkdir()
    value = 'plain $(not-a-shell) `value` æøå'
    output = _invoke(sys.executable, ['-c', 'import sys;print(sys.argv[1])', value],
                     workdir=path, timeout=5)
    assert output.strip() == value


def test_invalid_timeouts_fail_before_start(tmp_path):
    for seconds in (0, -1, float('nan'), float('inf'), True):
        with pytest.raises(ValueError):
            _invoke(sys.executable, [], workdir=tmp_path, timeout=seconds)


def test_frozen_root_discovery_and_explicit_override_priority(monkeypatch, tmp_path):
    from filewheel import pandoc_tool
    monkeypatch.delenv('FILEWHEEL_PANDOC', raising=False)
    root = tmp_path/'frozen'
    portable = root/'tools/pandoc'
    portable.mkdir(parents=True)
    name = 'pandoc.exe' if sys.platform == 'win32' else 'pandoc'
    binary = portable/name
    binary.write_bytes(b'trusted native fixture; probe mocked')
    binary.chmod(0o755)
    (portable/'COPYRIGHT.txt').write_text('copyright')
    (portable/'COPYING.rtf').write_text('GPL')
    monkeypatch.setattr(pandoc_tool, 'application_root', lambda: root)
    with patch.object(pandoc_tool, '_probe', return_value=('3.12.1', ('gfm','json'), ('json','docx'))):
        found = find_pandoc()
        assert found.executable == binary.resolve()
        assert found.source == 'bundled'
        monkeypatch.setenv('FILEWHEEL_PANDOC', str(root/'missing.exe'))
        assert find_pandoc() is None  # Bad explicit choice is not silently replaced.
