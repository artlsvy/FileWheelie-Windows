# Installing Filewheel

Give the recipient **releases/FilewheelSetup.exe**. Everything needed is inside
this one offline installer. It supports Windows 11 x64 and installs for the current
user without administrator rights, normally into
`%LOCALAPPDATA%\Programs\Filewheel`.

Quit any older Filewheel tray instance first, then double-click Setup. The wizard
has Welcome, destination, included components, optional shortcuts/startup, Install
with progress, Cancel, and Finish. The component page lists the private runtime
and whether LibreOffice/Pandoc will be reused or installed. Setup creates a Start
Menu entry and an Apps > Installed apps uninstall entry. Launch is optional at
Finish. Source documents and conversion results are never installer inputs.

## Existing dependencies

Setup checks the usual per-user/system locations, LibreOffice's installation
registry key, and absolute local-drive PATH entries. It checks tool version output before
offering reuse: **Pandoc 3.1+**, **LibreOffice 7.6+**. Compatible tools are reused by
default; their private copies are skipped. The checkbox lets a user choose the
included private copies instead. Undetected/custom installations use the bundled
fallback; Setup does not download or globally install dependencies.

Python 3.14, Qt/PySide6 6.12 and the image/PDF/Office/Markdown libraries are private
Filewheel components. An existing system Python or Qt is left alone; it cannot
safely replace the exact frozen runtime. Native runtime DLLs are also app-local.
No separate global Python, Qt or VC++ redistributable installer is run.

The installer records reused paths in `installation.ini` next to Filewheel.exe.
Runtime capability checks still apply; a version check does not guarantee every
tool build supports every conversion. If a reused tool is later removed, repair
by rerunning Setup and selecting the private copies. Uninstall never removes
reused system tools. Private runtime files are installed once, avoiding the
portable EXE's repeated temporary extraction.

## Tray and startup

- **Enable wheel** controls mouse/touchpad invocation together and remembers the
  choice. Both input routes are enabled on a fresh installation. Disabling the
  wheel leaves an already running conversion alone.
- **Start on login** toggles Windows current-user login startup. The same owned
  Run entry is used by Setup, the tray and `--startup install/remove`. It is opt-in
  on a fresh installation. An entry pointing elsewhere is preserved.
- **Quit Filewheel** cooperatively cancels/cleans up any running conversion before
  exiting. Setup/uninstall asks to quit an active new-version Filewheel rather
  than forcibly terminating it. Older builds lack this installer mutex: quit
  them manually before installing.

Injected touchpad gestures still require confirmation of the proposed exact file.
All provenance, freshness and path checks remain. Explorer **Send to > Filewheel**
is an optional setup task and provides the explicit-path fallback. A pre-existing
same-name Send to shortcut is preserved. Logs, COM cache and wheel preferences
remain under `%LOCALAPPDATA%\Filewheel`; uninstall preserves those preferences.

## Rebuild

Use the pinned Windows Python3.14 build environment. The builder downloads the
pinned official Inno Setup6.7.3 bootstrap only on the build machine, verifies its
SHA256, and extracts a private compiler under ignored `build-tools`. It does not
install a global compiler. Pandoc/LibreOffice inputs are complete local folders.

```powershell
.\.venv-build314\Scripts\python.exe packaging/build_installer.py `
  --libreoffice 'C:\Program Files\LibreOffice' `
  --pandoc "$env:LOCALAPPDATA\Pandoc" --skip-tool-probes
```

Output: `releases/FilewheelSetup.exe`, `INSTALLER-BUILD-INFO.json`, `SHA256SUMS.txt`.
Build logs are under `build/installer-*-build.log` / `build/installer-compile.log`.
The private onedir payload is under `build/installer-payload/Filewheel`; ship Setup
alone. Release EXEs use Git LFS. No code signing certificate is configured, so
Windows may display its normal unknown-publisher/SmartScreen prompt.

Compiler/API references: [Inno Setup file rules](https://jrsoftware.org/ishelp/topic_filessection.htm),
[captured version probes](https://jrsoftware.org/ishelp/topic_isxfunc_execandcaptureoutput.htm),
[running-app mutex](https://jrsoftware.org/ishelp/topic_setup_appmutex.htm).

## Verification limit and deferred acceptance

This task compiles the installer and statically reviews source/payload metadata.
No application tests, installer execution, login changes, conversion probes or
desktop automation are run while the user needs the PC. Compilation does not
establish install/upgrade/uninstall correctness on a clean family computer.

When the user resumes testing: install with existing compatible tools and confirm
the reuse summary/paths; install on a clean PC and confirm private fallback paths;
check wheel disable/relaunch, physical/touchpad targeting, login toggle and sign-in;
convert/cancel/retry; rerun Setup with Filewheel active; uninstall and confirm that
system tools and converted files remain. Finish the interrupted native UI trial
and at least 50 normal conversions without pill disappearance. Preserve explicit
D3D11/software options and the Widgets fallback during those checks.
