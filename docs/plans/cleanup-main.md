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
1. Complete: cleanup/LFS EXE committed b9b77a3, main fast-forwarded and pushed;
   remote refs/heads/main verified equal to b9b77a3. Old native EXE preserved in Git.
2. Complete: bounded PPTX/XLSX-to-PDF, offline workbook guards and unrun regression
   cases added. EXE rebuilt successfully with --skip-tool-probes, no test runs.
3. Complete: report and rebuilt EXE committed1290458 and pushed to main; remote
   refs/heads/main verified at1290458 and LFS upload completed. No tests/probes,
   benchmarks or interactive automation ran.

Evidence: origin/main is an ancestor of HEAD; branch contains two later commits
(F5/OpenGL and Windows onefile). Git LFS3.3.0 available. Existing EXE668358672 bytes.
Current untracked report.pdf/report.txt/unicode.txt/tests/a.txt/tests/b.txt appear
manual fixtures; preserve via external backup instead of deleting personal files.
Cleanup removed77 files' obsolete material (4062 lines), retained current safety
contracts and useful tests/build tooling. Local backups are outside checkout;
the user's running artifacts/f5 instance is untouched. LFS upload completed.
Current artifact SHA256a0bf33614ee5eb24269add1b871a7c28c9470fcc7c2a293eccc41f77ef37feb1.
MarkItDown speech helper calls online Google recognition; excluded. C review finds
no need for a rewrite; no implementation started. No tests/benchmarks/UI automation.
Working tree is clean. Build intermediates were moved to the external backup;
the active build environment and user's running older install remain local.
Next: stop. Runtime acceptance requires a future request; do not restart the
interrupted UI test or begin a C implementation.
