"""Real local text/EPUB/ZIP extraction and bounded archive rejection fixtures."""
import hashlib
import importlib.util
import struct
from pathlib import Path
from threading import Event
from unittest.mock import patch
from zipfile import ZIP_DEFLATED, ZIP_STORED, ZipFile, ZipInfo

import pytest

from filewheel.converters import (
    ConversionCancelled,
    ConversionError,
    ConversionManager,
    Registry,
    archive_markdown,
)
from filewheel.converters.archive_markdown import ArchiveMarkdownEngine
from filewheel.converters.archive_safety import ArchiveLimits, read_archive
from filewheel.converters.markdown import MarkItDownEngine
from filewheel.converters.structured_markdown import StructuredMarkdownEngine


@pytest.fixture
def manager():
    return ConversionManager(Registry((StructuredMarkdownEngine(), ArchiveMarkdownEngine(), MarkItDownEngine())))


def convert(manager, source):
    before = hashlib.sha256(source.read_bytes()).digest()
    with patch('socket.create_connection', side_effect=AssertionError('network attempted')):
        result = manager.convert(source, '.md')
    assert hashlib.sha256(source.read_bytes()).digest() == before
    assert not list(source.parent.glob('.filewheel-*'))
    assert result.warnings
    return result.path.read_text(encoding='utf-8')


@pytest.mark.parametrize(('extension', 'input_text', 'expected'), [
    ('.txt', 'Résumé plain text\nSecond line', ('```text', 'Résumé plain text', 'Second line')),
    ('.csv', 'Name,Count\nRésumé widgets,42\n"pipe|value","line\nvalue"', ('| Name | Count |', '| --- | --- |', 'pipe\\|value', 'line<br>value')),
    ('.json', '{"name":"Résumé","items":[1,{"count":42}]}', ('```json', '"name": "Résumé"', '"count": 42')),
    ('.xml', '<book lang="da"><title>Résumé</title><chapter id="1">Useful text</chapter></book>', ('# XML structure', '**book**', '@lang: da', '**title**: Résumé', '@id: 1: Useful text')),
])
def test_actual_structured_input_content_unicode_and_collisions(manager, tmp_path, extension, input_text, expected):
    source = tmp_path / ('Résumé source' + extension)
    source.write_text(input_text, encoding='utf-8')
    text = convert(manager, source)
    for needle in expected:
        assert needle in text
    previous = source.with_suffix('.md').read_bytes()
    result = manager.convert(source, '.md')
    assert result.path.name == 'Résumé source (2).md'
    assert source.with_suffix('.md').read_bytes() == previous


def test_bom_utf16_text_and_fence_escape(manager, tmp_path):
    source = tmp_path / 'BOM.txt'
    source.write_text('Résumé\n```danger\ncontent', encoding='utf-16')
    result = convert(manager, source)
    assert result.startswith('````text\n') and result.endswith('````\n')
    assert 'Résumé' in result


@pytest.mark.parametrize(('suffix', 'content'), [
    ('.txt', b'\x00binary'), ('.csv', b'A,B\n1'), ('.json', b'{bad'),
    ('.json', b'{"x":NaN}'), ('.json', b'{"x":1,"x":2}'),
    ('.xml', b'<broken>'),
    ('.xml', b'<!DOCTYPE a [<!ENTITY x "secret">]><a>&x;</a>'),
    ('.xml', b'<!DOCTYPE a SYSTEM "file:///etc/passwd"><a/>'),
])
def test_corrupt_structured_inputs_are_rejected_and_cleaned(manager, tmp_path, suffix, content):
    source = tmp_path / ('bad' + suffix)
    source.write_bytes(content)
    with pytest.raises(ConversionError):
        manager.convert(source, '.md')
    assert not source.with_suffix('.md').exists()
    assert not list(tmp_path.glob('.filewheel-*'))


def test_size_depth_and_cancellation_limits(manager, tmp_path):
    source = tmp_path / 'large.txt'
    source.write_text('abcdef')
    small = ConversionManager(Registry((StructuredMarkdownEngine(max_bytes=3),)))
    with pytest.raises(ConversionError, match='size limit'):
        small.convert(source, '.md')
    cancellation = Event()
    cancellation.set()
    with pytest.raises(ConversionCancelled):
        manager.convert(source, '.md', cancel=cancellation)
    for suffix, content in (('.json', '['*66+'0'+']'*66), ('.xml', '<a>'*66+'text'+'</a>'*66)):
        source = tmp_path / ('depth' + suffix)
        source.write_text(content)
        with pytest.raises(ConversionError, match='depth'):
            manager.convert(source, '.md')


def epub(path, *, spine=('two', 'one')):
    with ZipFile(path, 'w', compression=ZIP_STORED) as z:
        z.writestr('mimetype', 'application/epub+zip')
        z.writestr('META-INF/container.xml', '<container><rootfiles><rootfile full-path="OPS/book.opf"/></rootfiles></container>')
        z.writestr('OPS/book.opf', '<package xmlns:dc="http://purl.org/dc/elements/1.1/"><metadata><dc:title>Résumé book</dc:title></metadata><manifest><item id="one" href="one.xhtml" media-type="application/xhtml+xml"/><item id="two" href="two.xhtml" media-type="application/xhtml+xml"/></manifest><spine>'+''.join(f'<itemref idref="{name}"/>' for name in spine)+'</spine></package>')
        z.writestr('OPS/one.xhtml', '<html xmlns="http://www.w3.org/1999/xhtml"><body><h1>First chapter</h1><p>Useful text one</p></body></html>')
        z.writestr('OPS/two.xhtml', '<html xmlns="http://www.w3.org/1999/xhtml"><body><h1>Second chapter</h1><ul><li>Useful text two</li></ul></body></html>')


@pytest.mark.skipif(importlib.util.find_spec('markitdown') is None, reason='MarkItDown optional')
def test_actual_htm_and_epub_content_spine_order(manager, tmp_path):
    source = tmp_path / 'Résumé page.htm'
    source.write_text('<html><h1>Useful heading</h1><ul><li>Résumé entry</li></ul><img src="https://invalid.example/p.png"/></html>')
    text = convert(manager, source)
    assert '# Useful heading' in text and 'Résumé entry' in text
    source = tmp_path / 'Résumé book.epub'
    epub(source)
    text = convert(manager, source)
    assert 'Résumé book' in text and '# First chapter' in text and '# Second chapter' in text
    assert text.index('Second chapter') < text.index('First chapter')


def zip_fixture(path, members, compression=ZIP_STORED):
    with ZipFile(path, 'w', compression=compression) as z:
        for name, value in members:
            z.writestr(name, value)


def test_actual_text_archive_preserves_member_content_without_extraction(manager, tmp_path):
    source = tmp_path / 'Résumé collection.zip'
    zip_fixture(source, [('notes/plain.txt', 'Résumé words'), ('data.csv', 'Item,Count\nWidgets,42'),
                         ('values.json', '{"useful":true}'), ('book.xml', '<book>Content</book>'),
                         ('notes.md', '# Existing heading'), ('page.htm', '<h1>HTML heading</h1>')])
    text = convert(manager, source)
    for needle in ('# notes/plain.txt', 'Résumé words', 'Widgets', '"useful": true', '**book**: Content', '# Existing heading', '# HTML heading'):
        assert needle in text
    assert not (tmp_path/'notes').exists()


@pytest.mark.parametrize('name', ['../escape.txt', '/absolute.txt', 'C:/file.txt', 'folder\\file.txt', 'a/../b.txt', 'bad:stream.txt', 'trailing./file.txt'])
def test_zip_unsafe_paths_rejected_before_extraction(tmp_path, name):
    source = tmp_path/'unsafe.zip'
    zip_fixture(source, [(name, 'text')])
    with pytest.raises(ConversionError, match='Unsafe'):
        read_archive(source)
    assert list(tmp_path.iterdir()) == [source]


def test_zip_count_directory_ratio_expansion_links_duplicates_and_deadline(tmp_path):
    source = tmp_path/'bad.zip'
    zip_fixture(source, [(f'{i}.txt', 'a') for i in range(129)])
    with (patch('filewheel.converters.archive_safety.ZipFile', side_effect=AssertionError('allocated ZipInfo')),
          pytest.raises(ConversionError, match='directory')):
        read_archive(source)
    zip_fixture(source, [('huge.txt', 'a'*10000)], ZIP_DEFLATED)
    with pytest.raises(ConversionError, match='ratio'):
        read_archive(source)
    zip_fixture(source, [('a.txt', 'abc'), ('b.txt', 'def')])
    with pytest.raises(ConversionError, match='expanded'):
        read_archive(source, limits=ArchiveLimits(expanded_bytes=5))
    with pytest.raises(ConversionError, match='time'):
        read_archive(source, clock=iter((0., 11.)).__next__)
    with ZipFile(source, 'w') as z:
        info = ZipInfo('link.txt'); info.create_system=3; info.external_attr=0o120777 << 16
        z.writestr(info, 'target')
    with pytest.raises(ConversionError, match='links'):
        read_archive(source)
    zip_fixture(source, [('a.txt', 'a'), ('A.txt', 'b')])
    with pytest.raises(ConversionError, match='Duplicate'):
        read_archive(source)


def test_fake_eocd_count_rejected_before_zipfile(tmp_path):
    source = tmp_path/'eocd.zip'
    source.write_bytes(struct.pack('<4s4H2IH', b'PK\x05\x06', 0, 0, 1000, 1000, 0, 0, 0))
    with (patch('filewheel.converters.archive_safety.ZipFile', side_effect=AssertionError('allocated ZipInfo')),
          pytest.raises(ConversionError, match='directory')):
        read_archive(source)


@pytest.mark.parametrize('member', ['nested.zip', 'image.png', 'document.docx'])
def test_nested_and_binary_zip_members_are_not_advertised_as_extracted(manager, tmp_path, member):
    source = tmp_path/'unsupported.zip'
    zip_fixture(source, [(member, 'ignored?')])
    with pytest.raises(ConversionError, match='textual ZIP'):
        manager.convert(source, '.md')
    assert not source.with_suffix('.md').exists()
    assert not list(tmp_path.glob('.filewheel-*'))


def test_corrupt_epub_and_missing_spine_reject(manager, tmp_path):
    source = tmp_path/'bad.epub'
    source.write_bytes(b'not a zip')
    with pytest.raises(ConversionError):
        manager.convert(source, '.md')
    source.unlink()
    epub(source, spine=('missing',))
    with pytest.raises(ConversionError, match='EPUB'):
        manager.convert(source, '.md')


def test_archive_uses_one_bounded_immutable_source_read(tmp_path):
    import io
    source = tmp_path/'race.zip'
    zip_fixture(source, [('valid.txt', 'Validated snapshot')])
    snapshot = source.read_bytes()
    stream = io.BytesIO(snapshot)
    with patch.object(Path, 'open', return_value=stream) as opened:
        assert read_archive(source) == {'valid.txt': b'Validated snapshot'}
    assert opened.call_count == 1  # No reopening by ZipFile after preflight.


def test_epub_upstream_consumes_validated_stage_snapshot(manager, tmp_path):
    from markitdown import MarkItDown
    source = tmp_path/'snapshot.epub'
    epub(source)
    original = MarkItDown.convert_local
    observed = []
    def checked(converter, path, *args, **kwargs):
        path = Path(path)
        observed.append(path)
        assert path.name == 'validated.epub' and path.parent.name.startswith('.filewheel-')
        assert path != source
        with ZipFile(path) as archive:
            assert archive.infolist()[0].filename == 'mimetype'
        return original(converter, path, *args, **kwargs)
    with patch.object(MarkItDown, 'convert_local', checked):
        assert 'Useful text one' in convert(manager, source)
    assert len(observed) == 1


def test_archive_actual_central_record_count_and_bytes_are_bounded(tmp_path):
    source = tmp_path/'claims.zip'
    zip_fixture(source, [(f'{i}.txt', 'x') for i in range(3)])
    data = bytearray(source.read_bytes())
    eocd = data.rfind(b'PK\x05\x06')
    struct.pack_into('<HH', data, eocd+8, 1, 1)  # Claims one entry, actually three.
    source.write_bytes(data)
    with (patch('filewheel.converters.archive_safety.ZipFile', side_effect=AssertionError('allocated ZipInfo')),
          pytest.raises(ConversionError, match='directory')):
        read_archive(source, limits=ArchiveLimits(members=2))
    zip_fixture(source, [('one.txt', 'x')])
    with pytest.raises(ConversionError, match='directory'):
        read_archive(source, limits=ArchiveLimits(directory_bytes=1))


def test_archive_output_and_post_parse_time_limits(manager, tmp_path):
    source = tmp_path/'deadline.zip'
    zip_fixture(source, [('one.txt', 'Useful words')])
    engine = ArchiveMarkdownEngine(max_output=4)
    limited = ConversionManager(Registry((engine,)))
    with pytest.raises(ConversionError, match='size limit'):
        limited.convert(source, '.md')
    original = archive_markdown.render_markdown
    clock = iter((0., 0., 11.))
    with (patch('filewheel.converters.archive_markdown.monotonic', side_effect=clock.__next__),
          patch('filewheel.converters.archive_markdown.render_markdown', wraps=original),
          pytest.raises(ConversionError, match='time limit')):
        manager.convert(source, '.md')
    assert not source.with_suffix('.md').exists()
    assert not list(tmp_path.glob('.filewheel-*'))


def test_archive_cancellation_during_streaming_and_crc_failure(tmp_path):
    source = tmp_path/'cancel.zip'
    zip_fixture(source, [('one.txt', 'x'*100000)])
    cancellation = Event()
    def cancel_after_begin():
        cancellation.set()
        return 0.
    with pytest.raises(ConversionCancelled):
        read_archive(source, cancel=cancellation, clock=cancel_after_begin)
    zip_fixture(source, [('one.txt', 'Unique payload')])
    data = source.read_bytes().replace(b'Unique payload', b'Changedpayload', 1)
    source.write_bytes(data)
    with pytest.raises(ConversionError, match='corrupt'):
        read_archive(source)
