"""Actual Windows Pandoc publishing/content checks."""
import hashlib
import importlib.util
import os
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from threading import Event
from unittest.mock import patch
from xml.etree import ElementTree
from zipfile import ZipFile

import pytest

from filewheel.converters import ConversionCancelled, ConversionError, ConversionManager, Registry
from filewheel.converters.base import DependencyUnavailable, EngineOutput
from filewheel.converters.office import LibreOfficeEngine
from filewheel.converters.pandoc import PandocEngine
from filewheel.pandoc_tool import find_pandoc

TOOL = os.getenv('FILEWHEEL_PANDOC')
AVAILABLE = find_pandoc(TOOL) is not None


@pytest.fixture
def engine():
    if not AVAILABLE:
        pytest.skip('Actual local Pandoc required; no wrapper assumption')
    return PandocEngine(executable=TOOL)


@pytest.fixture
def source(tmp_path):
    path = tmp_path / 'Résumé notes æøå.md'
    path.write_text('# Résumé heading\n\nUseful paragraph with [Reference](https://example.org).\n\n'
                    '- First item\n- Second item\n\n'
                    '| Name | Count |\n| --- | --- |\n| Widgets | 42 |\n', encoding='utf-8')
    return path


def xml_text(archive, member):
    return ' '.join(ElementTree.fromstring(archive.read(member)).itertext())


@pytest.mark.parametrize('extension', ['.docx', '.html', '.txt', '.rtf', '.odt', '.epub', '.pptx'])
def test_actual_seven_formats_preserve_content_and_source(engine, source, extension):
    before = hashlib.sha256(source.read_bytes()).digest()
    manager = ConversionManager(Registry((engine,)))
    result = manager.convert(source, extension)
    engine.validate(EngineOutput(result.path, result.path.name))
    assert hashlib.sha256(source.read_bytes()).digest() == before
    assert not list(source.parent.glob('.filewheel-*'))
    assert result.engine_id == 'pandoc' and result.warnings
    if extension in ('.docx', '.odt', '.pptx'):
        member = {'.docx': 'word/document.xml', '.odt': 'content.xml', '.pptx': 'ppt/slides/slide1.xml'}[extension]
        with ZipFile(result.path) as archive:
            content = xml_text(archive, member)
            # PPTX can distribute blocks across slides; inspect all slide XML.
            if extension == '.pptx':
                content = ' '.join(xml_text(archive, name) for name in archive.namelist()
                                   if name.startswith('ppt/slides/slide') and name.endswith('.xml'))
            assert 'Résumé heading' in content
            assert 'Useful paragraph' in content
            assert 'First item' in content
            assert 'Widgets' in content and '42' in content
    elif extension == '.epub':
        with ZipFile(result.path) as archive:
            content = ' '.join(xml_text(archive, name) for name in archive.namelist()
                               if name.endswith('.xhtml'))
            assert 'Résumé heading' in content and 'Widgets' in content and 'First item' in content
    elif extension == '.rtf':
        text = result.path.read_text(encoding='utf-8')
        assert 'Useful paragraph' in text and 'Widgets' in text and 'First item' in text
        assert r'\u233' in text  # Unicode escaped correctly rather than lost.
    else:
        text = result.path.read_text(encoding='utf-8')
        assert 'Résumé heading' in text and 'Widgets' in text and 'First item' in text
        if extension == '.html':
            assert '<!DOCTYPE html>' in text and '<html' in text and '<head>' in text and '<body>' in text
            assert '<table>' in text and 'https://example.org' in text
    if extension == '.docx':
        with ZipFile(result.path) as archive:
            xml = archive.read('word/document.xml').decode()
            assert 'Heading1' in xml and '<w:tbl>' in xml
            assert b'https://example.org' in archive.read('word/_rels/document.xml.rels')


def test_local_raster_images_embed_and_unsafe_resources_never_fetch(engine, source, tmp_path):
    from PIL import Image
    requests = []
    class Handler(BaseHTTPRequestHandler):
        def do_GET(self):
            requests.append(self.path)
            self.send_response(200)
            self.end_headers()
        def log_message(self, *_):
            pass
    server = ThreadingHTTPServer(('127.0.0.1', 0), Handler)
    worker = threading.Thread(target=server.serve_forever, daemon=True)
    worker.start()
    try:
        picture = tmp_path / 'image æøå.png'
        Image.new('RGBA', (24, 16), (30, 90, 40, 150)).save(picture)
        original_image = picture.read_bytes()
        source.write_text('# Safe heading\n\n![Local](image%20%C3%A6%C3%B8%C3%A5.png)\n\n'
                          f'![Remote](http://127.0.0.1:{server.server_port}/private.png)\n\n'
                          '![Outside](../secret.png)\n\n[Bad](javascript:alert(1))\n\n'
                          '<script>alert(1)</script>\n', encoding='utf-8')
        manager = ConversionManager(Registry((engine,)))
        result = manager.convert(source, '.docx')
        with ZipFile(result.path) as archive:
            media = [name for name in archive.namelist() if name.startswith('word/media/')]
            assert len(media) == 1
            assert archive.read(media[0]).startswith(b'\x89PNG\r\n\x1a\n')
        html = manager.convert(source, '.html').path.read_text(encoding='utf-8')
        assert 'data:image/png;base64,' in html
        assert 'src="http://' not in html
        assert 'href="javascript:' not in html
        assert '<script>' not in html
        assert requests == []
        assert picture.read_bytes() == original_image
        assert any('omitted' in warning for warning in result.warnings)
    finally:
        server.shutdown()
        server.server_close()
        worker.join(timeout=2)


def test_missing_tool_office_and_supported_writer_gates(source, tmp_path):
    engine = PandocEngine(executable=tmp_path / 'missing-pandoc')
    assert not engine.available()
    assert not Registry((engine,)).categories(source)
    with pytest.raises(DependencyUnavailable):
        ConversionManager(Registry((engine,))).convert(source, '.docx')
    with patch('filewheel.converters.pandoc.find_pandoc', return_value=None):
        assert not PandocEngine().available()


def test_office_absent_hides_pdf_only(engine):
    with patch.object(LibreOfficeEngine, 'available', return_value=False):
        minimal = PandocEngine(executable=TOOL)
    assert minimal.available()
    outputs = {c.output_extension for c in minimal.capabilities}
    assert '.pdf' not in outputs and '.docx' in outputs and '.html' in outputs


def test_invalid_utf8_empty_input_and_cancellation_leave_no_outputs(engine, tmp_path):
    manager = ConversionManager(Registry((engine,)))
    for payload in (b'\xffnot UTF-8', b'', b'\x00binary'):
        source = tmp_path / 'invalid.md'
        source.write_bytes(payload)
        with pytest.raises(ConversionError):
            manager.convert(source, '.docx')
        assert not source.with_suffix('.docx').exists()
        assert not list(tmp_path.glob('.filewheel-*'))
    event = Event()
    event.set()
    source.write_text('# Valid document', encoding='utf-8')
    with pytest.raises(ConversionCancelled):
        manager.convert(source, '.docx', cancel=event)
    assert not source.with_suffix('.docx').exists()


def test_unicode_collision_and_source_integrity(engine, source):
    original = source.read_bytes()
    first = source.with_suffix('.docx')
    first.write_bytes(b'Existing personal document')
    result = ConversionManager(Registry((engine,))).convert(source, '.docx')
    assert result.path.name == 'Résumé notes æøå (2).docx'
    assert first.read_bytes() == b'Existing personal document'
    assert source.read_bytes() == original


@pytest.mark.skipif(importlib.util.find_spec('pymupdf') is None, reason='PDF validation needs PyMuPDF')
def test_actual_md_docx_pdf_one_transaction_no_intermediate_publish(engine, source):
    import pymupdf
    if not engine.office.available():
        pytest.skip('Actual LibreOffice required for staged PDF')
    before = source.read_bytes()
    result = ConversionManager(Registry((engine,))).convert(source, '.pdf')
    with pymupdf.open(result.path) as document:
        text = ''.join(page.get_text() for page in document)
        assert 'Résumé heading' in text and 'Widgets' in text and 'First item' in text
    assert source.read_bytes() == before
    assert not source.with_suffix('.docx').exists()
    assert not list(source.parent.glob('.filewheel-*'))


def test_multistage_cancel_between_pandoc_and_office_cleans_stage(engine, source):
    if not engine.office.available():
        pytest.skip('LibreOffice pair must be available')
    event = Event()
    def progress(value, message):
        if 'Rendering Markdown PDF' in message:
            event.set()
    with pytest.raises(ConversionCancelled):
        ConversionManager(Registry((engine,))).convert(source, '.pdf', progress=progress, cancel=event)
    assert not source.with_suffix('.docx').exists() and not source.with_suffix('.pdf').exists()
    assert not list(source.parent.glob('.filewheel-*'))


def test_corrupt_local_image_and_symlink_resources_fail_safely(engine, source, tmp_path):
    bad = tmp_path / 'bad.png'
    bad.write_bytes(b'not an image')
    source.write_text('![Broken](bad.png)', encoding='utf-8')
    with pytest.raises(ConversionError, match='resource'):
        ConversionManager(Registry((engine,))).convert(source, '.docx')
    link = tmp_path / 'linked.png'
    try:
        link.symlink_to(bad)
    except (OSError, NotImplementedError):
        pytest.skip('Symlink creation unavailable')
    source.write_text('![Linked](linked.png)', encoding='utf-8')
    with pytest.raises(ConversionError, match='links|reparse'):
        ConversionManager(Registry((engine,))).convert(source, '.docx')
    assert not source.with_suffix('.docx').exists()
    assert not list(tmp_path.glob('.filewheel-*'))


def test_invalid_generated_structures_are_rejected(engine, tmp_path):
    for suffix, payload in (('.docx', b'not a document'), ('.html', b'<p>fragment</p>'),
                            ('.rtf', b'not rtf'), ('.txt', b'\x00')):
        path = tmp_path / ('invalid' + suffix)
        path.write_bytes(payload)
        with pytest.raises(ConversionError):
            engine.validate(EngineOutput(path, path.name))


def test_bom_text_supported_but_input_and_ast_budgets_fail_closed(engine, source, tmp_path):
    source.write_bytes('# Unicode æøå heading\n\nContent'.encode('utf-16'))
    result = ConversionManager(Registry((engine,))).convert(source, '.txt')
    assert 'Unicode æøå heading' in result.path.read_text(encoding='utf-8')
    source.write_text('x' * 50, encoding='utf-8')
    with (patch('filewheel.converters.pandoc.MAX_INPUT', 16),
          pytest.raises(ConversionError, match='size limit')):
        ConversionManager(Registry((engine,))).convert(source, '.docx')
    assert not source.with_suffix('.docx').exists()
    with patch('filewheel.converters.pandoc.run_pandoc') as run:
        def corrupt_ast(location, arguments, **kwargs):
            path = Path(next(item.split('=', 1)[1] for item in arguments if item.startswith('--output=')))
            path.write_bytes(b'{invalid JSON')
        run.side_effect = corrupt_ast
        with pytest.raises(ConversionError, match='invalid'):
            ConversionManager(Registry((engine,))).convert(source, '.docx')
    assert not source.with_suffix('.docx').exists()
    assert not list(tmp_path.glob('.filewheel-*'))


def test_actual_reader_writer_feature_gate_uses_tool_capabilities(engine):
    from dataclasses import replace
    location = replace(engine.location, writers=('json', 'plain', 'html5'))
    with patch('filewheel.converters.pandoc.find_pandoc', return_value=location):
        limited = PandocEngine(executable=TOOL)
    assert limited.available()
    assert {c.output_extension for c in limited.capabilities} == {'.txt', '.html'}
    location = replace(location, readers=('gfm',))
    with patch('filewheel.converters.pandoc.find_pandoc', return_value=location):
        unsupported = PandocEngine(executable=TOOL)
    assert not unsupported.available()


def test_ast_recursion_and_corrupt_package_content_limits(engine, source, tmp_path):
    from filewheel.converters.pandoc import _Assets, _sanitize_ast
    nested = []
    for _ in range(150):
        nested = [nested]
    with pytest.raises(ConversionError, match='depth|node'):
        _sanitize_ast({'blocks': nested, 'meta': {}}, _Assets(source, None, []), None, [])
    bad = tmp_path / 'empty.docx'
    with ZipFile(bad, 'w') as archive:
        archive.writestr('word/document.xml', '<w:document xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main"><w:body/></w:document>')
    with pytest.raises(ConversionError, match='no text'):
        engine.validate(EngineOutput(bad, bad.name))


def test_repeated_images_are_counted_and_cannot_expand_past_ast_budget(source, tmp_path, monkeypatch):
    from PIL import Image

    import filewheel.converters.pandoc as module
    image = tmp_path/'tiny.png'
    Image.new('RGB', (2, 2), 'green').save(image)
    assets = module._Assets(source, None, [])
    uri = assets.image('tiny.png')
    assets.image('tiny.png')
    assert assets.count == 2 and assets.referenced_bytes == len(uri) * 2
    monkeypatch.setattr(module, 'MAX_AST', len(uri) * 2)
    with pytest.raises(ConversionError, match='expanded structure'):
        assets.image('tiny.png')


def test_ast_serialization_checks_size_before_building_a_whole_json_string(tmp_path, monkeypatch):
    import filewheel.converters.pandoc as module
    monkeypatch.setattr(module, 'MAX_AST', 1024)
    with (patch.object(module.json, 'dumps', side_effect=AssertionError('unbounded serialization')),
          pytest.raises(ConversionError, match='size limit')):
        module._write_ast(tmp_path/'bounded.json', {'blocks': ['x'*200] * 10000})
    assert (tmp_path/'bounded.json').stat().st_size <= 1024


@pytest.mark.parametrize('extension', ['.docx', '.odt'])
def test_actual_office_outputs_keep_headings_lists_links_and_tables(engine, source, extension):
    output = ConversionManager(Registry((engine,))).convert(source, extension).path
    with ZipFile(output) as archive:
        member = 'word/document.xml' if extension == '.docx' else 'content.xml'
        root = ElementTree.fromstring(archive.read(member))
        if extension == '.docx':
            assert any(node.tag.endswith('}pStyle') and 'Heading1' in node.attrib.values() for node in root.iter())
            assert any(node.tag.endswith('}numPr') for node in root.iter())
            assert any(node.tag.endswith('}tbl') for node in root.iter())
            assert b'https://example.org' in archive.read('word/_rels/document.xml.rels')
        else:
            for tag in ('}h', '}list', '}table', '}a'):
                assert any(node.tag.endswith(tag) for node in root.iter())
            assert b'https://example.org' in archive.read(member)
