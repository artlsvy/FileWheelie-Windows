# Filewheel

Private, local Windows11 file converter with a cursor-centered two-stage radial
menu. Explorer **Send to → Filewheel preview** supplies an explicit file path;
choose an available category and format to convert in a background worker.
The historical shortcut label is retained for compatibility: it now converts.

Implemented: PNG/JPEG/WebP and optional HEIC, image/PDF rendering, editable
PDF→DOCX, MarkItDown document→Markdown, and LibreOffice DOCX→PDF. Only installed
engine/codec capabilities appear. Sources and existing outputs are preserved;
collisions get numbered filenames. No accounts, cloud uploads, OCR or LLM clients.

From the Windows checkout:

```powershell
.\.venv\Scripts\python.exe -m pip install -e ".[ui,images,pdf,heif,markdown,office]"
.\.venv\Scripts\python.exe -m filewheel.platforms.windows.sendto install --mode gui
```

MarkItDown0.1.9 excludes Python3.15, so its pairs are hidden there; use a separate
Python3.14 venv for all Markdown formats. LibreOffice must be installed separately
for DOCX→PDF. [Setup, exact smoke commands and engine limits](docs/CONVERTERS.md)
explain both environments, results, cancellation and collision handling.
[Send to management](docs/SEND_TO.md) covers staging/removal and ownership checks.

Basic explicit-path invocation and G4 rendering are user-verified on Windows.
New conversions and240px UI polish are Linux/Qt-offscreen tested; Windows engine,
worker, transparency, focus and mixed-DPI acceptance remain queued in
[STATUS](docs/STATUS.md). No live Windows test is inferred from Linux checks.

Experimental Mouse3 infrastructure is preserved, diagnostic-only and emits no
trusted hover target. [Diagnostic instructions](docs/DIAGNOSTIC_POC.md) and its
strict [identity gate](docs/EXPLORER_HIT_TEST.md) remain available. The conversion
UI consumes the same validated controller target as future trusted Mouse3.

For Kubuntu development use the optional extras and pytest commands in
[CONVERTERS.md](docs/CONVERTERS.md). Project checkpoints live in
[ROADMAP](docs/ROADMAP.md) and [NEXT_TASK](docs/NEXT_TASK.md).
