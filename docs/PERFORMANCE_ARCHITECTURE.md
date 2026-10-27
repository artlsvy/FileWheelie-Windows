# Host language and performance assessment

## Current decision: keep Python; no C rewrite is needed

2026-10-27 source/context review, with no benchmarks or tests run for this review.
The user reports responsive, reliable OpenGL progress and working cancellation.
The previous backend comparison localized a presentation difference; it did not
establish an interpreter bottleneck. See F5_RENDERER_RELIABILITY.md.

- Python coordinates state, Explorer evidence, subprocesses and file transactions.
  Most expensive work already runs in compiled Pillow/PyMuPDF/ONNX libraries or
  external LibreOffice/Pandoc, in an isolated worker process.
- A C host can call Win32 hooks and COM, but preserving the present Qt Quick/QML
  UI normally requires a C++ Qt layer. Pure C would need a bridge or a new UI.
- MarkItDown and pdf2docx are Python tools. Keeping their behavior from C would
  retain Python workers, or require substantial replacements and new validation.
- Most bundle volume is conversion tooling, libraries and models. Rewriting the
  coordinator does not remove LibreOffice, Pandoc, Qt or those dependencies.
- Existing proven cancellation, no-overwrite transactions, provenance checks and
  UI lifetimes would all need reimplementation/bridging. That cost is not justified
  by current accepted behavior or by single-EXE packaging (already available).

A C implementation is technically feasible, but there is no demonstrated need.
No C implementation or migration plan is being started. If future evidence shows
a concrete host bottleneck, first isolate the specific operation and consider a
small native adapter while retaining the existing worker/conversion contracts.
Do not infer an improvement from the language name or rewrite the entire app to
address a graphics backend issue. New measurements require user authorization.

Existing optional benchmark helpers remain available for future diagnostics;
they were not executed in this pass. Earlier prototype captures and Linux baseline
files were removed from the active tree and remain recoverable through Git history.
