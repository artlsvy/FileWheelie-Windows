"""Small offline parsers for useful Markdown from bounded textual inputs."""
import csv
import html
import io
import json
import re
from importlib.util import find_spec
from pathlib import Path

from filewheel.converters.base import Capability, ConversionError, EngineOutput, check_cancel

EXTENSIONS = ('.txt', '.csv', '.json', '.xml')
MAX_BYTES = 8 * 1024 * 1024
MAX_OUTPUT = 16 * 1024 * 1024


def decode_text(data):
    try:
        encoding = 'utf-16' if data.startswith((b'\xff\xfe', b'\xfe\xff')) else 'utf-8-sig'
        text = data.decode(encoding)
    except UnicodeError as error:
        raise ConversionError('Text input must be UTF-8 or BOM-marked UTF-16') from error
    if not text.strip() or any(ord(c) < 32 and c not in '\t\n\r' for c in text):
        raise ConversionError('Text input is empty or contains binary/control data')
    return text


def fence(text, language):
    length = max((len(match.group()) for match in re.finditer(r'`+', text)), default=0)
    marker = '`' * max(3, length + 1)
    return f'{marker}{language}\n{text.rstrip()}\n{marker}\n'


def cell(text):
    return html.escape(str(text)).replace('\\', '\\\\').replace('|', r'\|').replace('\r\n', '<br>').replace('\n', '<br>').replace('\r', '<br>')


def _json_object(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            raise ValueError('Duplicate JSON keys are unsupported')
        result[key] = value
    return result


def render_markdown(text, extension, *, cancel=None, max_output=MAX_OUTPUT):
    check_cancel(cancel)
    if extension in ('.txt', '.md'):
        result = fence(text, 'text') if extension == '.txt' else text.rstrip() + '\n'
    elif extension == '.csv':
        rows, width = [], None
        try:
            for index, row in enumerate(csv.reader(io.StringIO(text), strict=True)):
                check_cancel(cancel)
                if index >= 20000 or len(row) > 128:
                    raise ConversionError('CSV row or column limit exceeded')
                if width is None:
                    width = len(row)
                    if not width:
                        raise ConversionError('CSV has no columns')
                if len(row) != width:
                    raise ConversionError('CSV rows have inconsistent column counts')
                rows.append('| ' + ' | '.join(cell(value) for value in row) + ' |')
        except csv.Error as error:
            raise ConversionError('CSV input is malformed or has an oversized field') from error
        if not rows:
            raise ConversionError('CSV has no rows')
        rows.insert(1, '| ' + ' | '.join('---' for _ in range(width)) + ' |')
        result = '\n'.join(rows) + '\n'
    elif extension == '.json':
        try:
            def bad_constant(value):
                raise ValueError('Non-finite JSON values are unsupported')
            value = json.loads(text, parse_constant=bad_constant, object_pairs_hook=_json_object)
            stack, count = [(value, 0)], 0
            while stack:
                check_cancel(cancel)
                value_item, depth = stack.pop()
                count += 1
                if depth > 64 or count > 100000:
                    raise ConversionError('JSON depth or item limit exceeded')
                if isinstance(value_item, dict):
                    stack.extend((item, depth + 1) for item in value_item.values())
                elif isinstance(value_item, list):
                    stack.extend((item, depth + 1) for item in value_item)
            result = fence(json.dumps(value, ensure_ascii=False, indent=2, allow_nan=False), 'json')
        except (ValueError, RecursionError) as error:
            raise ConversionError('JSON input is malformed, ambiguous or too deeply nested') from error
    elif extension == '.xml':
        from defusedxml import ElementTree
        from defusedxml.common import DefusedXmlException
        try:
            parser = ElementTree.iterparse(io.StringIO(text), events=('start', 'end'), forbid_dtd=True,
                                           forbid_entities=True, forbid_external=True)
            depth = count = 0
            for event, _ in parser:
                check_cancel(cancel)
                depth += 1 if event == 'start' else -1
                count += event == 'start'
                if depth > 64 or count > 100000:
                    raise ConversionError('XML depth or element limit exceeded')
            root = parser.root
        except (ElementTree.ParseError, DefusedXmlException, ValueError) as error:
            raise ConversionError('XML is malformed or contains forbidden DTD/entities') from error
        lines = ['# XML structure', '']
        stack = [(root, 0)]
        while stack:
            check_cancel(cancel)
            node, depth = stack.pop()
            line = '  ' * depth + '- **' + cell(node.tag) + '**'
            if node.attrib:
                line += ' — ' + '; '.join(f'@{cell(k)}: {cell(v)}' for k, v in node.attrib.items())
            if node.text and node.text.strip():
                line += ': ' + cell(node.text.strip())
            lines.append(line)
            if node.tail and node.tail.strip():
                lines.append('  ' * depth + '  ' + cell(node.tail.strip()))
            stack.extend((child, depth + 1) for child in reversed(list(node)))
        result = '\n'.join(lines) + '\n'
    else:
        raise ConversionError('Unsupported structured Markdown input')
    check_cancel(cancel)
    if len(result.encode('utf-8')) > max_output:
        raise ConversionError('Markdown output size limit exceeded')
    return result


class StructuredMarkdownEngine:
    engine_id = 'structured-markdown'

    def __init__(self, *, max_bytes=MAX_BYTES, max_output=MAX_OUTPUT):
        if type(max_bytes) is not int or max_bytes < 1 or type(max_output) is not int or max_output < 1:
            raise ValueError('Text limits must be positive integers')
        self.max_bytes, self.max_output = max_bytes, max_output
        self.capabilities = tuple(Capability(ext, 'Markdown/Text', '.md', 'Markdown', self.engine_id)
                                  for ext in EXTENSIONS if ext != '.xml' or find_spec('defusedxml') is not None)

    def available(self):
        return True

    def convert(self, source: Path, extension, workdir: Path, progress, cancel):
        check_cancel(cancel)
        suffix = source.suffix.lower()
        if extension != '.md' or suffix not in {c.input_extension for c in self.capabilities}:
            raise ConversionError('Unsupported structured Markdown conversion')
        if source.stat().st_size > self.max_bytes:
            raise ConversionError('Text input exceeds the size limit')
        progress(.1, 'Reading local text')
        with source.open('rb') as stream:
            data = stream.read(self.max_bytes + 1)
        if len(data) > self.max_bytes:
            raise ConversionError('Text input exceeds the size limit')
        text = render_markdown(decode_text(data), suffix, cancel=cancel, max_output=self.max_output)
        output = workdir / 'output.md'
        output.write_text(text, encoding='utf-8')
        progress(.8, 'Checking Markdown')
        return (EngineOutput(output, source.with_suffix('.md').name,
                             ('Local structured extraction; document layout is not preserved.',)),)

    def validate(self, output):
        text = output.path.read_text(encoding='utf-8')
        if not text.strip() or '\x00' in text or output.path.stat().st_size > self.max_output:
            raise ConversionError('Generated Markdown is empty, binary or oversized')
