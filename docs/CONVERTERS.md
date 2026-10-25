# Local conversions and runtime setup

Format clicks in the normal GUI now perform real conversions. There is no cloud,
account, OCR, LLM client or conversion service. The experimental hover resolver
still emits no trusted targets. Headless path diagnostics remain metadata-only.

The UI extra uses PySide6-Essentials (Core/Gui/Widgets/Test), avoiding unused
WebEngine/Addons distributions. It retains the same PySide6 Python API.

## Engines and limits

| Engine | Working pairs when installed | Limits / fidelity |
| --- | --- | --- |
| Pillow | PNG/JPEG/WebP between different formats; HEIC/HEIF→JPEG/PNG with pillow-heif; images→PDF with PyMuPDF validation | 100MiB /40M pixels; single-frame only; EXIF orientation; JPEG quality90; white background for JPEG/PDF alpha; PNG/WebP retain alpha |
| PyMuPDF | PDF→PNG/JPEG, every page | 50MiB /100pages /40M pixels per page,144DPI; numbered outputs; rasterized, not editable |
| pdf2docx | PDF→editable DOCX | 50MiB /100pages; text-based PDF; reconstructed fonts/layout/tables may differ; scanned/blank PDFs rejected with OCR guidance |
| MarkItDown | DOCX/PDF/PPTX/XLSX/HTML→UTF-8 MD | Python<3.15; per-format dependency checks;50MiB input /200MiB expanded Office;100PDF pages; lossy extraction, no OCR |
| LibreOffice | DOCX→PDF | Installed LibreOffice + PyMuPDF required;50MiB /200MiB expanded;90s process deadline; isolated profile; external resources/macros rejected; installed fonts affect layout |

Unavailable engines/codecs are omitted from the live menu. Markdown/Text, Image
and Document categories contain only available real pairs. Audio/Video have no
engines yet and stay hidden. The explicit preview registry remains only a testing
seam; it is not the normal launcher registry. No extension renaming is a conversion.

Outputs are written beside the source: `name.jpg`, then `name (2).jpg`, etc.
Multi-page PDF images use `name-page-001.png` and so on. Private same-directory
staging is validated before atomic hardlink publication. This requires a filesystem
supporting hardlinks (e.g. NTFS/ext4); unsupported filesystems fail safely without
replacing files. Failure/cancellation cleans the stage and this job's partial
publications, preserving source and pre-existing outputs. Input metadata is
rechecked; a later action cannot reuse an old validation indefinitely.

Escape/outside/focus-loss can cancel and hide the popup while a worker is active.
Cancellation is cooperative: an in-progress Pillow/pdf2docx/MarkItDown call cannot
be forcibly interrupted; LibreOffice has its own process deadline. Cleanup and
application exit wait for that worker. A cancellation arriving after a completed
publication cannot undo a successful conversion. Success/error and warnings appear
inside the same popup; output/warning details are available through tooltips.

## Windows setup (existing Python3.15 venv)

From the synced checkout:

```powershell
.\.venv\Scripts\python.exe -m pip install -e ".[ui,images,pdf,heif,office,markdown]"
.\.venv\Scripts\python.exe -m filewheel.platforms.windows.sendto stage --mode gui
.\.venv\Scripts\python.exe -m filewheel.platforms.windows.sendto install --mode gui
```

Install LibreOffice separately if DOCX→PDF is needed; its command must be on PATH
or in the usual Program Files directory. The installer is not downloaded or run
by Filewheel. Optional Microsoft Word COM is not implemented or required.

The menu entry remains **Filewheel preview** to preserve ownership of existing
shortcuts; it now launches real converters. Existing owned shortcuts continue
working without reinstall when interpreter/checkout are unchanged. Diagnostic mode
is still separately named and never converts. Install/remove ownership checks
remain strict; no registry changes, admin requirement or background service.

MarkItDown0.1.9 declares Python>=3.10,<3.15; the markdown dependency marker skips
it on3.15, and those menu choices remain hidden. Do not force unsupported wheels.
For all Markdown pairs use a separate Python3.14 venv if installed:

```powershell
py -3.14 -m venv .venv314
.\.venv314\Scripts\python.exe -m pip install -e ".[ui,images,pdf,heif,office,markdown]"
```

To point Send to at it, first remove the GUI link using the old interpreter, then
install with the new one (keep the old environment intact):

```powershell
.\.venv\Scripts\python.exe -m filewheel.platforms.windows.sendto remove --mode gui
.\.venv314\Scripts\python.exe -m filewheel.platforms.windows.sendto install --mode gui
```

A differing staged shortcut also needs explicit removal in Explorer if switching
interpreters; staging never overwrites a different file. Live installation does
not require staging. Removal of the new owned link uses the same .venv314 command
with `remove --mode gui`.

## Windows manual smoke and acceptance (new conversions still unverified)

Create a new, uniquely named PNG and open the actual menu:

```powershell
$filewheelSmoke = Join-Path $env:TEMP ("filewheel-smoke-" + [guid]::NewGuid().ToString("N") + ".png")
.\.venv\Scripts\python.exe -c "from PIL import Image; import sys; Image.new('RGBA',(320,200),(70,130,210,128)).save(sys.argv[1])" $filewheelSmoke
$filewheelBefore = (Get-FileHash -LiteralPath $filewheelSmoke).Hash
.\.venv\Scripts\python.exe -m filewheel.platforms.windows.explicit_path_diagnostics --gui -- $filewheelSmoke
$LASTEXITCODE
(Get-FileHash -LiteralPath $filewheelSmoke).Hash -eq $filewheelBefore
```

If using .venv314 replace that interpreter consistently. Choose Image→JPEG:
expect progress then Converted, a readable320×200 JPEG, white alpha background
and unchanged source hash. Repeat to check `(2)` collision handling. Then test
Send to on that same PNG. Retain created test files for inspection; no automatic
cleanup of your source/output is performed by this guide.

Test text PDF→DOCX (editable text), image-only PDF→DOCX (OCR error), DOCX→PDF with
and without LibreOffice, and all5 MD fixtures on3.14. Test PNG/JPEG/WebP/HEIC and
multi-page PDF→images; inspect every page, warnings and filenames. Corrupt files
must show errors without output; cancel during work and check eventual cleanup.

Check240px size, configurable sizes, Escape/Back/Done, hover labels, outside/focus
loss, corner transparency and no rectangular shadow on real Windows. Test
100/150/200% mixed DPI and negative monitors. Basic G4 launch/render is already
user-verified; new polish, workers/native engines and detailed DPI acceptance are
not inferred from Linux tests. Headless basic Send to need not be repeated.

## Kubuntu development

```bash
python3 -m venv .venv-dev
.venv-dev/bin/python -m pip install -e '.[ui,images,pdf,heif,markdown,office,dev]'
QT_QPA_PLATFORM=offscreen .venv-dev/bin/python -m pytest -q
```

Use Python3.14 for the full currently tested dependency set. Real LibreOffice
fixtures require the installed binary and usable desktop runtime storage even in
headless mode. Tests report skips when optional dependencies are absent; fake and
Linux tests do not establish Windows integration.

## Primary API / compatibility sources

- [pdf2docx API](https://github.com/ArtifexSoftware/pdf2docx/blob/master/docs/quickstart.convert.rst): local layout reconstruction, upstream no longer actively maintained.
- [MarkItDown API and extras](https://github.com/microsoft/markitdown), [0.1.9 Python support](https://pypi.org/project/markitdown/0.1.9/).
- [LibreOffice command-line parameters](https://help.libreoffice.org/latest/en-GB/text/shared/guide/start_parameters.html).
- [Pillow documentation](https://pillow.readthedocs.io/en/stable/), [pillow-heif](https://pillow-heif.readthedocs.io/en/latest/).
- [PyMuPDF package/license](https://pypi.org/project/PyMuPDF/): AGPL/commercial licensing; private local use does not add redistribution infrastructure.
- [ONNX Runtime privacy](https://github.com/microsoft/onnxruntime/blob/main/docs/Privacy.md): Filewheel sets ORT_DISABLE_TELEMETRY before optional imports and also disables telemetry through the API. No MarkItDown plugins, remote/LLM adapters or HTTP input routes are enabled.
