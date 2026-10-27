"""Future regression coverage for Office PDF dispatch; not run in the review pass."""
from pathlib import Path
from unittest.mock import patch
from zipfile import ZipFile

import pytest

from filewheel.converters.base import ConversionError
from filewheel.converters.office import LibreOfficeEngine


@pytest.mark.parametrize(('suffix', 'part', 'filter_name'), [
    ('.docx', 'word/document.xml', 'writer_pdf_Export'),
    ('.pptx', 'ppt/presentation.xml', 'impress_pdf_Export'),
    ('.xlsx', 'xl/workbook.xml', 'calc_pdf_Export'),
])
def test_office_filter_dispatch_and_source_preservation(tmp_path, suffix, part, filter_name):
    source = tmp_path / ('input with spaces' + suffix)
    with ZipFile(source, 'w') as archive:
        archive.writestr(part, '<root/>')
    original = source.read_bytes()
    work = tmp_path / 'stage'
    work.mkdir()

    def render(arguments, *, workdir, timeout, cancel):
        assert arguments[arguments.index('--convert-to') + 1] == 'pdf:' + filter_name
        assert Path(arguments[-1]) == work / ('input' + suffix)
        assert Path(workdir) == work
        (work / 'rendered/input.pdf').write_bytes(b'validation happens separately')
        return 0

    engine = LibreOfficeEngine()
    with (patch.object(engine, 'executable', return_value='soffice.com'),
          patch('filewheel.converters.office.run_office', side_effect=render)):
        outputs = engine.convert(source, '.pdf', work, lambda *args: None, None)
    assert outputs[0].path == work / 'output.pdf'
    assert source.read_bytes() == original


@pytest.mark.parametrize('blocked', ['connection', 'formula', 'macro'])
def test_xlsx_rejects_active_content_before_starting_office(tmp_path, blocked):
    source = tmp_path / 'blocked.xlsx'
    with ZipFile(source, 'w') as archive:
        archive.writestr('xl/workbook.xml', '<root/>')
        if blocked == 'connection':
            archive.writestr('xl/connections.xml', '<connections/>')
        elif blocked == 'macro':
            archive.writestr('xl/VBAPROJECT.bin', b'blocked')
        else:
            archive.writestr('xl/worksheets/sheet1.xml',
                             '<worksheet><f>WEBSERVICE(A1)</f></worksheet>')
    engine = LibreOfficeEngine()
    with (patch.object(engine, 'executable', return_value='soffice.com'),
          patch('filewheel.converters.office.run_office') as spawn,
          pytest.raises(ConversionError)):
        engine.convert(source, '.pdf', tmp_path, lambda *args: None, None)
    spawn.assert_not_called()
