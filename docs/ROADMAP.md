# Remaining work

Current priority: cleanup/main integration and bounded offline conversions. See
plans/cleanup-main.md for progress and NEXT_TASK.md for the immediate handoff.

Completed baseline: Windows-only onefile with embedded tools, OpenGL mitigation,
source/output safety, process cancellation and user acceptance of progress/cancel.

Potential additions are selected by utility and available offline engines, not by
advertising every format an upstream package mentions. Popular document/image
routes are already present. PPTX/XLSX-to-PDF can reuse bundled LibreOffice.
Audio/video transcription requiring network is excluded. A separate local speech
model or media transcoder would be a new dependency/milestone, not an implicit
MarkItDown feature. No C rewrite is justified by current code and accepted UX.

Still pending when explicitly requested: finish the interrupted onefile UI stress
trial, clean-family-PC acceptance, other GPUs, mixed DPI and sleep/resume.
No tests/desktop automation are authorized during the current review pass.
