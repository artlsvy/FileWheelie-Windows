# Clean main and offline converter review

Goal: prioritize a clean committed repository containing the standalone EXE,
merge with origin/main, then add bounded useful offline conversions if applicable.
Review C feasibility from code/context only; no C implementation.

Acceptance: current source/build/tests retained; obsolete reports/prototypes and
remote-Linux instructions removed; untracked personal files preserved outside
checkout; EXE versioned through Git LFS (normal Git limit100MiB); main integrated
and remote verified. Audio/video transcription requiring network remains absent.

Constraints: no tests, benchmarks or interactive UI automation this pass. Do not
claim new native validation. Preserve OpenGL, trusted-target boundaries, worker
cancellation and source/output transactions. No C rewrite.

Milestones:
1. Active: cleanup, include existing stable EXE with LFS, commit and integrate main.
2. Pending: bounded PPTX/XLSX-to-PDF using existing LibreOffice, rebuild EXE if changed.
3. Pending: document converter/audio/C findings, final commit/remote integration.

Evidence: origin/main is an ancestor of HEAD; branch contains two later commits
(F5/OpenGL and Windows onefile). Git LFS3.3.0 available. Existing EXE668358672 bytes.
Current untracked report.pdf/report.txt/unicode.txt/tests/a.txt/tests/b.txt appear
manual fixtures; preserve via external backup instead of deleting personal files.
Next: inventory references and remove obsolete tracked artifacts; stage LFS EXE.
