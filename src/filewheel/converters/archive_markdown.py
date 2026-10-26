"""Conservative text-only ZIP to Markdown, without recursive conversion/extraction."""
import io
from importlib.util import find_spec
from pathlib import PurePosixPath
from time import monotonic

from filewheel.converters.archive_safety import DEFAULT_LIMITS, read_archive
from filewheel.converters.base import Capability, ConversionError, EngineOutput, check_cancel
from filewheel.converters.markdown import RejectRequestsSession
from filewheel.converters.structured_markdown import MAX_OUTPUT, cell, decode_text, render_markdown


class ArchiveMarkdownEngine:
    engine_id = 'archive-markdown'
    capabilities = (Capability('.zip', 'Markdown/Text', '.md', 'Markdown', engine_id),)

    def __init__(self, *, limits=DEFAULT_LIMITS, max_output=MAX_OUTPUT):
        if type(max_output) is not int or max_output < 1:
            raise ValueError('Output limit must be a positive integer')
        self.limits, self.max_output = limits, max_output
        self.execution_timeouts = {'.zip': limits.seconds}

    def available(self):
        return True

    def convert(self, source, extension, workdir, progress, cancel):
        if source.suffix.lower() != '.zip' or extension != '.md':
            raise ConversionError('Unsupported text archive conversion')
        started = monotonic()
        def check():
            check_cancel(cancel)
            if monotonic() - started > self.limits.seconds:
                raise ConversionError('Archive processing time limit exceeded')
        members = read_archive(source, limits=self.limits, cancel=cancel)
        if not members:
            raise ConversionError('Archive contains no textual documents')
        chunks, output_bytes = [], 0
        for name, data in members.items():
            check()
            suffix = PurePosixPath(name).suffix.lower()
            if suffix not in ('.txt', '.csv', '.json', '.xml', '.md', '.html', '.htm'):
                raise ConversionError('Only textual ZIP members are supported; nested archives and binaries are rejected')
            text = decode_text(data)
            if suffix in ('.html', '.htm'):
                if find_spec('markitdown') is None:
                    raise ConversionError('HTML archive members require the local MarkItDown dependency')
                import onnxruntime

                onnxruntime.disable_telemetry_events()
                from markitdown import MarkItDown
                from markitdown.converters import HtmlConverter
                session = RejectRequestsSession()
                try:
                    converter = MarkItDown(enable_builtins=False, enable_plugins=False, requests_session=session)
                    converter.register_converter(HtmlConverter())
                    markdown = converter.convert_stream(io.BytesIO(text.encode('utf-8')), file_extension='.html').markdown
                finally:
                    session.close()
                if not isinstance(markdown, str) or not markdown.strip():
                    raise ConversionError('HTML archive member has no extractable content')
            else:
                markdown = render_markdown(text, suffix, cancel=cancel, max_output=self.max_output)
            check()
            chunk = f'# {cell(name)}\n\n{markdown.rstrip()}\n\n'
            output_bytes += len(chunk.encode('utf-8'))
            if output_bytes > self.max_output:
                raise ConversionError('Combined archive Markdown size limit exceeded')
            chunks.append(chunk)
        output = workdir / 'output.md'
        output.write_text(''.join(chunks), encoding='utf-8')
        check()
        progress(.8, 'Checking combined Markdown')
        return (EngineOutput(output, source.with_suffix('.md').name,
                             ('Text-only ZIP extraction; no nested archives, attachments, OCR or cloud services.',)),)

    def validate(self, output):
        text = output.path.read_text(encoding='utf-8')
        if not text.strip() or '\x00' in text or output.path.stat().st_size > self.max_output:
            raise ConversionError('Generated archive Markdown is empty, binary or oversized')
