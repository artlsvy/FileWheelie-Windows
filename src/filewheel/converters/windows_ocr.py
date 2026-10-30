"""Bounded offline OCR fallback for image-only PDFs; no model downloads or cloud."""
import json
import os
from pathlib import Path

from filewheel.converters.base import ConversionError, check_cancel
from filewheel.converters.office import run_office


def recognize_image(image, workdir, cancel):
    if os.name != 'nt':
        raise ConversionError('Image-only PDF conversion requires Windows local OCR.')
    executable = Path(os.environ.get('SystemRoot', r'C:\Windows')) / 'System32/WindowsPowerShell/v1.0/powershell.exe'
    script = Path(__file__).parents[1] / 'platforms/windows/ocr_image.ps1'
    output = workdir / 'ocr-result.json'
    output.unlink(missing_ok=True)
    result = run_office(
        [str(executable), '-NoLogo', '-NoProfile', '-NonInteractive', '-ExecutionPolicy', 'Bypass',
         '-File', str(script), '-InputPath', str(image), '-OutputPath', str(output)],
        workdir=workdir, timeout=60, cancel=cancel, tool_name='Windows OCR',
    )
    if result:
        if 'NO_OCR_LANGUAGE' in result.stderr:
            raise ConversionError(
                'Windows OCR has no installed recognition language. Add OCR for your document '
                'language in Windows Settings > Time & language > Language & region > Language options.'
            )
        raise ConversionError('Windows local OCR failed. ' + result.stderr.strip()[:500])
    check_cancel(cancel)
    try:
        if output.stat().st_size > 2 * 1024 * 1024:
            raise ValueError('OCR response too large')
        payload = json.loads(output.read_text(encoding='utf-8-sig'))
        lines, language = payload['lines'], payload['language']
        if (not isinstance(lines, list) or not all(isinstance(line, str) for line in lines)
                or not isinstance(language, str) or not language):
            raise ValueError('Invalid OCR response')
    except (OSError, ValueError, KeyError, TypeError) as error:
        raise ConversionError('Windows OCR returned an invalid result') from error
    return lines, language


# Keep the existing import surface for callers; shared document assembly now
# dispatches recognition by platform, preserving Windows native OCR.
def ocr_pdf_pages(*args, **kwargs):
    from filewheel.converters.local_ocr import ocr_pdf_pages as pages

    return pages(*args, **kwargs)


def image_pdf_to_docx(*args, **kwargs):
    from filewheel.converters.local_ocr import image_pdf_to_docx as convert

    return convert(*args, **kwargs)
