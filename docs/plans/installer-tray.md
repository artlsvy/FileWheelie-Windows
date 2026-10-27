# Installer and finalized tray

Goal: professional Windows per-user installer with welcome/Next/Cancel/progress,
dependency inventory, compatible installed-tool reuse, Start Menu/uninstall and
optional start at login. Tray: Enable wheel, Start on login, Quit. Mouse3 and
touchpad enabled by default, with existing evidence/injected-candidate consent.

Acceptance: Setup.exe compiles with all fallback dependencies; installed tool
selection persists; no global Python/tool reinstall; wheel preference persists;
login toggle reads/writes the same owned startup entry as installer; startup
does not block UI and failures remain recoverable. Preserve current OpenGL,
conversion cancellation and source/output safeguards. No forced termination of
running conversions during update/uninstall. No desktop automation this pass.

Milestones:
1. Implemented: persistent wheel preference, default physical/injected input,
   three-entry tray, shared owned startup registration, async hook cleanup.
2. Implemented: Inno wizard, compatible tool reuse/private fallbacks, installed
   path configuration, shortcuts/login/uninstall and running-app mutex.
3. Complete: FilewheelSetup.exe compiled, static review/build records and docs
   finalized for the local milestone commit. No automatic push.

Decisions: install private runtime, reuse compatible installed Pandoc/LibreOffice
by default, bundle fallbacks; do not depend on arbitrary system Python/Qt. Install
onedir files once (installer remains one EXE), avoiding portable EXE unpacking on
every launch. Startup at login is opt-in during setup and toggleable in tray.
Evidence: Inno6.7.3 bootstrap hash/signature verified; private portable compiler
under ignored build-tools. Script compiled against placeholders, never executed.
Full onedir build succeeded with tool probes disabled. Static EXE archive review
matches all eight changed/new runtime modules and runtime_hook to current source.
Static Python compilation covers80 files without executing their code.
No tests, conversion probes or desktop automation ran.

Build corrections: separate work/output directories; copy complete external tool
trees after PyInstaller Analysis so their DLLs are not scanned as Python deps.
Limit build PATH to venv/Windows to avoid accidental JDK/system-app DLL capture.
Final Setup compiled successfully (235.032 seconds). SHA256:
e29f925ceb792335b1abfa11df2c668e624a41c1a738fceae2e70ed54a24b0f6.
Nine packaged source files match current code; complete native tool trees and
Windows Qt plugin present. Full static inventory is in release build metadata.
Older portable release remains explicitly unchanged.
Artifact:415408242 bytes (396.2MiB); compiler included all17753 payload files
exactly once. Python/Qt runtime3921 files, LibreOffice13826, Pandoc4 plus app and
dependency list. Existing installed tools are skipped by conditional copy rules.
Automatic approval review blocked removal of generated staging folders with
"blocked by policy"; they remain ignored under build/, outside committed files.
Next: stop after this local milestone commit. Installer runtime/clean-machine
acceptance remains deferred by user; future checklist is in INSTALLER.md.
