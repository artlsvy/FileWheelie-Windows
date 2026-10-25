import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from filewheel.converters import ConversionError, ConversionManager, Registry
from filewheel.converters.base import DependencyUnavailable
from filewheel.converters.debugging import describe_conversion_error
from filewheel.converters.pdf_docx import PdfDocxEngine


class ConversionDebugTests(unittest.TestCase):
    def test_pdf_docx_failure_records_backend_operation_traceback(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            source = root / 'input.pdf'
            source.write_bytes(b'fixture')
            engine = PdfDocxEngine()
            with (patch.dict('os.environ', {'FILEWHEEL_LOG_DIR': str(root / 'logs')}),
                  patch.object(engine, 'available', return_value=True),
                  patch.object(engine, 'convert', side_effect=ValueError('real parser failure')),
                  self.assertRaises(ConversionError) as failure):
                ConversionManager(Registry((engine,))).convert(source, '.docx')
            error = failure.exception
            self.assertEqual(error.engine_id, 'pdf2docx')
            self.assertEqual(error.operation, 'convert')
            text = error.debug_log.read_text(encoding='utf-8')
            self.assertIn('ValueError: real parser failure', text)
            self.assertIn('engine=pdf2docx operation=convert', text)
            self.assertIn('pdf2docx', describe_conversion_error(error))
            self.assertNotIn('LibreOffice', describe_conversion_error(error))
            self.assertEqual(source.read_bytes(), b'fixture')

    def test_missing_pdf_docx_dependency_has_distinct_kind(self):
        with tempfile.TemporaryDirectory() as folder:
            source = Path(folder) / 'input.pdf'
            source.write_bytes(b'fixture')
            engine = PdfDocxEngine()
            with (patch.dict('os.environ', {'FILEWHEEL_LOG_DIR': folder}),
                  patch.object(engine, 'available', return_value=False),
                  self.assertRaises(DependencyUnavailable) as failure):
                ConversionManager(Registry((engine,))).convert(source, '.docx')
            self.assertEqual(failure.exception.engine_id, 'pdf2docx')
            self.assertEqual(failure.exception.kind, 'dependency_unavailable')

    def test_log_failure_does_not_replace_original_error(self):
        engine = PdfDocxEngine()
        with tempfile.TemporaryDirectory() as folder:
            source = Path(folder) / 'input.pdf'
            source.write_bytes(b'fixture')
            for error in (OSError('path unavailable'), RuntimeError('home unavailable')):
                with (patch.object(engine, 'available', return_value=True),
                      patch.object(engine, 'convert', side_effect=ConversionError('useful reason')),
                      patch('filewheel.converters.debugging.debug_log_path', side_effect=error),
                      self.assertRaisesRegex(ConversionError, 'useful reason') as failure):
                    ConversionManager(Registry((engine,))).convert(source, '.docx')
                self.assertIsNone(failure.exception.debug_log)

    def test_wrapped_dependency_error_is_classified(self):
        try:
            try:
                raise DependencyUnavailable('missing decoder')
            except DependencyUnavailable as cause:
                raise ConversionError('backend wrapper') from cause
        except ConversionError as wrapped:
            error = wrapped
        with tempfile.TemporaryDirectory() as folder:
            source = Path(folder) / 'input.pdf'
            source.write_bytes(b'fixture')
            engine = PdfDocxEngine()
            with (patch.dict('os.environ', {'FILEWHEEL_LOG_DIR': folder}),
                  patch.object(engine, 'available', return_value=True),
                  patch.object(engine, 'convert', side_effect=error),
                  self.assertRaises(DependencyUnavailable) as failure):
                ConversionManager(Registry((engine,))).convert(source, '.docx')
            self.assertEqual(failure.exception.kind, 'dependency_unavailable')
