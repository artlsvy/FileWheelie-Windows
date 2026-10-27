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

Current: offline per-user Setup wizard with dependency inventory/reuse, optional
login startup, shortcuts/uninstall and finalized tray. Physical/touchpad routes
default enabled with existing input safeguards; shared persistent Enable wheel
switch, Start on login and Quit. State: plans/installer-tray.md. No tests or UI
automation while the user needs the PC. Build/static review only this pass.

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
See NEXT_TASK.md and plans/installer-tray.md for the current handoff.

## Installer/tray delivery

FilewheelSetup.exe0.1.0 compiled with Inno Setup6.7.3. SHA256:
e29f925ceb792335b1abfa11df2c668e624a41c1a738fceae2e70ed54a24b0f6.
Per-user offline wizard, dependency inventory/reuse, private fallbacks, shortcuts,
uninstall and optional login startup implemented. Tray exposes Enable wheel,
Start on login and Quit; physical/injected routes default enabled with mandatory
injected exact-path confirmation and unchanged provenance/path checks.

Static Python compilation80 files; nine packaged runtime sources match current
source. Full runtime/tool inventory and compiler record are in
releases/INSTALLER-BUILD-INFO.json. No tests, installer execution, conversion/tool
probes, login changes or UI automation ran. Native install/reuse/fallback and
upgrade/uninstall/sign-in acceptance remains deferred. Prior portable EXE is
unchanged and does not include these tray changes. See INSTALLER.md and the
installer-tray plan. No automatic push or unrelated development.

## Cleanup checkpoint

Obsolete prototype assets, three superseded render scripts, the unused glass_demo
entry point, remote-Linux setup prompt/docs and stale current-status prose were
removed. Source/build/test/safety contracts and current native evidence remain.
Manual files, duplicate inactive venvs, old distributions and obsolete assets
are backed up outside the checkout. Running artifacts/f5 remains untouched.
Stable EXE4a46099d87 is tracked through Git LFS in releases. No tests were run.

## Offline Office PDF additions and source review

Added PPTX/PDF and XLSX/PDF using existing LibreOffice filters; no new dependency
or approved UI change. Reused private input/profile, cancellation, output checks
and no-overwrite publication. Spreadsheet connections/external links/query tables,
macro sheets and active/network formulas reject before LO starts. Future regression
cases added in test_office_pdf_routes.py, not executed. Self-test coverage extended
for future native runs, but no self-test was run now.

MarkItDown0.1.9's speech helper calls recognize_google; its audio/MP4 transcription
therefore fails the offline requirement and stays absent. Popularity findings are
qualified converter-operator lists, not a global ranking. C review from code/context
finds no need for a rewrite: coordination is Python, expensive engines already native,
and preserving QML/MarkItDown would still need Qt C++/Python or major replacements.

Rebuilt releases/Filewheel.exe without native tool probes:668357057 bytes, SHA256
a0bf33614ee5eb24269add1b871a7c28c9470fcc7c2a293eccc41f77ef37feb1.
No tests, benchmarks or UI automation ran. Compilation is not runtime acceptance.
The last natively checked baseline4a46099d87 remains recoverable from b9b77a3 via
Git LFS. Current artifact metadata is in releases and standalone/cleanup-build.json.
Remaining runtime/family checks require a new user request. No C implementation.

## Final integration

Cleanup checkpoint b9b77a3 and converter/source/EXE commit1290458 were both pushed
to origin/main. Remote main was independently verified at1290458 and the complete
668MB LFS upload succeeded. Source working tree was clean at that checkpoint.
Build intermediates were preserved outside checkout; the running older Filewheel
install was not moved. No tests/probes/benchmarks/UI automation ran. Current EXE
and new Office routes still require future runtime acceptance; no C rewrite needed.
