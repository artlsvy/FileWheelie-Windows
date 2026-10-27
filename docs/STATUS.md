# Current Filewheel status

Updated2026-10-27. Windows11 amd64 only; Python3.14/PySide6 host with native
conversion libraries and embedded Pandoc/LibreOffice.

## Delivered baseline

- Family EXE: releases/Filewheel.exe, Git LFS tracked; share the EXE alone.
- Baseline SHA256:4a46099d87b9d67f65aefa956801dee0b682cfedff83f64c3d0bdc70b01b131c.
- Prior Windows suite:660 tests/407 subtests passed,4 skips. Six earlier Windows
  test failures were resolved. These are historical results, not a new test run.
- Prior relocated single-EXE checks:34 checks/26 pairs passed, both tools bundled,
  real frozen workers converted/cancelled/retried and extraction cleanup passed.
- User accepted OpenGL progress reliability and cancellation. The onefile UI
  trial completed46 cycles before user interruption;100-cycle acceptance remains
  incomplete. See standalone/verification.json and F5_RENDERER_RELIABILITY.md.

## Current authorized task

Priority1: clean source tree, preserve standalone EXE through Git LFS, commit and
integrate origin/main. Then bounded offline converter additions where appropriate.
C feasibility is a source/context review only. No tests or UI automation in this
pass. Do not restart interactive testing while the user needs the PC.

Obsolete prototype captures, superseded Linux setup and loose manual fixtures
were removed from the active checkout. Local copies are preserved outside the
repo in C:/Users/lsvy/fileconverter-local-backup-20261027; tracked history remains
in Git. Source, useful tests, build recipes, diagnostics and safety specifications
are retained. A running older Filewheel uses artifacts/f5, so that ignored local
folder is intentionally preserved rather than moving a live installation.

## Remaining limits

New changes require future Windows acceptance. Other GPUs/drivers, mixed DPI,
sleep/resume and a clean family PC remain unverified. Audio/video transcription
must stay offline; online MarkItDown speech recognition is not enabled.
See NEXT_TASK.md and plans/cleanup-main.md for the current handoff.

## Cleanup checkpoint

Obsolete prototype assets, three superseded render scripts, the unused glass_demo
entry point, remote-Linux setup prompt/docs and stale current-status prose were
removed. Source/build/test/safety contracts and current native evidence remain.
Manual files, duplicate inactive venvs, old distributions and obsolete assets
are backed up outside the checkout. Running artifacts/f5 remains untouched.
Stable EXE4a46099d87 is tracked through Git LFS in releases. No tests were run.
