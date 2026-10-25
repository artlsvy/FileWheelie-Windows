# Immediate bounded task — resolve Windows G4 desktop startup failure

Latest Windows stage=match_qt_screen identifies the cause: Win32 device name
\\.\DISPLAY1 differs from Qt friendly name MAG 244F. The adapter now associates
by unique full monitor origin/dimensions + valid DPR, with rounding tolerance;
names/index/primary are not identity. See STATUS.md for actual evidence/tests.

After syncing, retry the same direct GUI command once. No shortcut reinstall or
repeat headless diagnostic. If successful, verify Back/Escape/confirmation and
GUI Send to; if unsuccessful inspect the new stage/geometry details and fix only
the evidenced issue. Keep native mixed-DPI/focus acceptance queued. Preserve
Mouse3 and the controller boundary. G5 follows a usable G4 popup.

## Following milestone — G5 PNG → JPEG conversion

G4-A is implemented and Linux/offscreen tested. Windows radial overlay acceptance
remains queued separately in STATUS.md/SEND_TO.md. Basic single-file headless
explicit CLI/Send to was user-verified on build26200/Python3.15.0; do not repeat
that diagnostic without a regression. Preserve Mouse3; no new mouse research.

1. Read STATUS.md, ROADMAP.md, UI_SPEC.md, CONVERSION_MATRIX.md and decisions.
2. Implement one real PNG→JPEG engine behind the registry/controller/UI boundary.
   Keep preview capabilities clearly distinct from actually executable engines.
3. Use a worker outside the GUI thread, preserve sources, allocate a collision-safe
   output path without overwriting existing files, and define alpha/background
   handling explicitly. Validate real output by decoding it and checking format.
4. Route the PNG→JPEG radial choice to the engine with progress/error/completion;
   all other edges remain honest dry-run previews. No broad engine framework,
   OCR, cloud, services or Mouse3 changes needed for this bounded task.
5. Test representative image pixels/transparency, collisions, failures and
   cancellation/resource cleanup. Review material changes; record actual Linux
   and Windows validation separately and update docs.

After the image smoke converter: PDF→editable DOCX, then MarkItDown integration
(DOCX/PDF/PPTX/XLSX/HTML→MD), with local dependency/capability checks.

## Independent Windows queue

Follow GUI instructions in SEND_TO.md: optional UI dependency on targetPython3.15,
stage/install --mode gui, one-file preview (AGENTS.md works; PNG exercises three
formats), confirmation with zero file changes, Escape/Back/outside/focus/exit,
mixed DPI and negative monitors. Also broader explicit-path Unicode/invalid/
multiple arguments and owned-shortcut removal. No claim of native GUI verification
from offscreen tests. Preserve headless diagnostics and experimental Mouse3.
