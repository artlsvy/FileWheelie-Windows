# Filewheel installer

The current source build is **FilewheelSetup.exe**, version 0.2.1. Share this installer
alone. The older portable Filewheel.exe is no longer included in the repository.
The published v0.2 download remains the previous release until the updated
installer is published separately.

## What setup does

- Installs for the current user, normally in `%LOCALAPPDATA%\Programs\Filewheel`.
- Shows Next, Cancel, included components and installation progress.
- Adds a Start Menu shortcut and a Windows uninstall entry.
- Offers a desktop shortcut, Explorer Send to and start on login.
- Includes all fallback tools; no downloads are needed on the recipient's PC.

Compatible installed **LibreOffice 7.6+** and **Pandoc 3.1+** are reused by default
when found in normal locations, the LibreOffice registry entry or local PATH.
Their private copies are then skipped. Uncheck the reuse option to install the
bundled copies instead. Custom locations that are not found use private copies.

Python 3.14, Qt/PySide6 and conversion libraries stay private to Filewheel. Setup
leaves globally installed Python, Qt and other tools alone. Reused tool paths are
saved in `installation.ini`. If a reused tool is later removed, rerun Setup and
choose the bundled copies. `DEPENDENCIES.txt` lists the pinned build environment.

Quit an older Filewheel before setup. New builds prevent setup/uninstall while
the app is running. The installer and tray share an owned current-user login
entry; entries pointing elsewhere are preserved. Uninstall removes private app
files, not reused system tools, original documents or conversion results. Local
preferences/logs remain in `%LOCALAPPDATA%\Filewheel`.

## Build from source

Use Windows 11 x64, Python 3.14 and the pinned build environment prepared by
`scripts/build-windows.ps1`. Full local LibreOffice/Pandoc folders are build inputs.

```powershell
.\.venv-build314\Scripts\python.exe packaging/build_installer.py `
  --libreoffice 'C:\Program Files\LibreOffice' `
  --pandoc "$env:LOCALAPPDATA\Pandoc" --skip-tool-probes
```

The builder uses a checksum-pinned private Inno Setup 6.7.3 compiler in ignored
`build-tools`. Only the build machine may need to download that compiler.
Output is `releases/FilewheelSetup.exe`; checksums and build details are beside it.
The installed app uses a folder of private files, avoiding temporary unpacking
on every launch. Git stores the installer using Git LFS; download the release
asset directly, or run `git lfs pull` after cloning.

## Verification

The release build record in `releases/INSTALLER-BUILD-INFO.json` lists the checks
that ran. Build and static checks do not prove installation, login or uninstall
behavior on a clean PC. Developer tests and agent settings are kept locally and
are not part of this repository's current tree.
