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
| MarkItDown | DOCX/PDF/PPTX/XLSX/HTML→UTF-8 MD | Python3.14; per-format dependency checks;50MiB input /200MiB expanded Office;100PDF pages; lossy extraction, no OCR |
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

## One Python3.14 environment (development and builds)

Normal Filewheel now requires Python>=3.14,<3.15. This one runtime supports every
current Python converter, including MarkItDown0.1.9. Do not force packages into
3.15 or maintain separate application environments for Markdown.

From the synced Windows checkout:

```powershell
py -3.14 -m venv .venv-filewheel
.\.venv-filewheel\Scripts\python.exe -m pip install -e ".[desktop]"
.\.venv-filewheel\Scripts\python.exe -m filewheel.platforms.windows.sendto install --mode gui
```

Alternatively `powershell -File scripts/setup-windows.ps1` creates/checks the same
venv and installs the complete pinned desktop extra. It refuses to replace an
existing different runtime. Kubuntu uses Python3.14 with the same desktop extra.

If migrating an existing shortcut, first remove it using the interpreter that
originally installed it, for example the old .venv3.15 interpreter:

```powershell
.\.venv\Scripts\python.exe -m filewheel.platforms.windows.sendto remove --mode gui
```

This cleanup command remains importable on the old runtime; GUI conversion now
rejects unsupported runtime with a clear3.14 message. Keep old environments intact
until migration succeeds. A differing shortcut is never overwritten automatically.

LibreOffice is needed only for DOCX→PDF. PDF→DOCX uses pdf2docx/PyMuPDF and does
not depend on LibreOffice. G12's full portable bundle is documented separately;
a system LibreOffice installation may also be detected. Optional Word COM is not
implemented or required.

## Windows manual smoke and acceptance (new conversions still unverified)

Create a new, uniquely named PNG and open the actual menu:

```powershell
$filewheelSmoke = Join-Path $env:TEMP ("filewheel-smoke-" + [guid]::NewGuid().ToString("N") + ".png")
.\.venv-filewheel\Scripts\python.exe -c "from PIL import Image; import sys; Image.new('RGBA',(320,200),(70,130,210,128)).save(sys.argv[1])" $filewheelSmoke
$filewheelBefore = (Get-FileHash -LiteralPath $filewheelSmoke).Hash
.\.venv-filewheel\Scripts\python.exe -m filewheel.platforms.windows.explicit_path_diagnostics --gui -- $filewheelSmoke
$LASTEXITCODE
(Get-FileHash -LiteralPath $filewheelSmoke).Hash -eq $filewheelBefore
```

Use the unified .venv-filewheel interpreter consistently. Choose Image→JPEG:
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
.venv-dev/bin/python -m pip install -e '.[desktop,dev]'
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

## Local conversion debugging

Failures name the selected engine and operation in the popup/tooltip and write
actual exception chains to `%LOCALAPPDATA%/Filewheel/logs/conversion-debug.log`
(on Linux, `$XDG_STATE_HOME/filewheel/logs` or `~/.local/state/filewheel/logs`).
FILEWHEEL_LOG_DIR overrides the directory. Logs rotate2MB with3 backups and contain
local paths/tracebacks; they are never uploaded. Missing dependencies are distinct
from encoder/parser failures. PDF→DOCX errors must be diagnosed as pdf2docx errors,
not assumed to require LibreOffice. Preserve the source and inspect the named log.


Portable LibreOffice prefers a complete `tools/libreoffice` tree, then falls
back to a separate system installation. See [PORTABLE_LIBREOFFICE.md](PORTABLE_LIBREOFFICE.md)
for validation/build commands and the remaining Windows bundle acceptance.
