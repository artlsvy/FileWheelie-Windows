# Current handoff

Implemented task: offline Windows installer and finalized tray. See
plans/installer-tray.md and INSTALLER.md. Setup reuses compatible installed
LibreOffice/Pandoc, includes private fallbacks and runtime, shows dependency choices
and installation progress, creates Start Menu/uninstall and optional login startup.
Tray: Enable wheel, Start on login, Quit. Both mouse/touchpad routes default on;
injected exact-path confirmation and target validation remain mandatory.

No tests, conversion/tool probes, installer execution or desktop automation while
the user needs the PC. Compilation/static payload review is allowed; do not
extend older native acceptance to the new installer. Do not stop the resident
older Filewheel from artifacts/f5. Do not push automatically.

Cleanup/main integration completed and was pushed in b9b77a3/1290458/9e64127.
The older portable Filewheel.exe remains at SHA256
a0bf33614ee5eb24269add1b871a7c28c9470fcc7c2a293eccc41f77ef37feb1;
it does not include the new installer/tray changes. New Office PDF routes are
compiled but runtime-unverified. Offline speech extraction/C rewrite remain out
of scope; there is no reason to start a C rewrite.

Built: releases/FilewheelSetup.exe, SHA256
e29f925ceb792335b1abfa11df2c668e624a41c1a738fceae2e70ed54a24b0f6.
Inno6.7.3 compilation succeeded. Packaged source/static inventory review succeeded;
runtime acceptance remains unrun. Metadata: releases/INSTALLER-BUILD-INFO.json.

Stop after committing this milestone. Only when user requests testing: native
install/reuse/fallback/login/upgrade/uninstall acceptance, Office-route regression
checks and the interrupted UI trial. Do not begin other feature development.
