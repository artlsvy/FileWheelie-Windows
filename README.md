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
py -3.14 -m venv .venv-filewheel
.\.venv-filewheel\Scripts\python.exe -m pip install -e ".[desktop]"
.\.venv-filewheel\Scripts\python.exe -m filewheel.platforms.windows.sendto install --mode gui
```

The application/build runtime is Python3.14 for every converter; Python3.15
is not a supported application environment. LibreOffice must be installed separately
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


Current personal workflow (D-016): opt-in experimental Mouse3 opens the wheel
directly after evidence/path checks. The optional tray checkbox restores per-file
confirmation. Latest UI uses a 170px forest/ivory/brass wheel with a small Esc/Back
center and circular conversion feedback. See docs/NEXT_TASK.md for Windows checks.

During conversion the 170px circle shows a short status and percentage/ring.
Conversion/results stay visible above ordinary windows when clicking elsewhere;
Cancel/Escape waits visibly for cleanup, and Done closes the result. Technical
messages and file/output details remain available in tooltips and local logs.

Production conversion jobs now use a separate process to keep native converters
out of the mouse-hook/UI interpreter. Menu labels follow the ring, surfaces are
subtly translucent and empty state reads No formats. Windows cursor performance
still needs acceptance. To enable the existing DOCX → PDF route, follow
[the LibreOffice setup guide](docs/DOCX_TO_PDF.md).


Experimental native glass renderer: [GLASS_UI.md](docs/GLASS_UI.md) documents
`--ui-backend quick`, reduced effects, Windows acceptance and the Widget fallback.
The default remains Widget. [PERFORMANCE_ARCHITECTURE.md](docs/PERFORMANCE_ARCHITECTURE.md)
contains actual local measurements and the recommendation to keep the Python host.
