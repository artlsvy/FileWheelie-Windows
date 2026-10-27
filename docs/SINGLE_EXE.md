# Filewheel: one Windows EXE

Windows 11 amd64 only. The family build contains Python 3.14, Qt Quick, the
conversion engines, complete Pandoc and LibreOffice trees, and the MSVC runtime
DLLs used by LibreOffice. Windows and a working graphics driver remain required.
No separate Python/Pandoc/LibreOffice installation is intended for the recipient.

The executable unpacks its bundled files into a temporary directory automatically
at each fresh launch. Starting it is slower than the diagnostic folder build;
once the tray is running, conversion workers reuse the unpacked files.
It also uses the current user's local AppData for private logs and COM cache.
Conversions stay local. Source files and existing outputs remain protected.

## Build from Windows source

Use the pinned `.venv-build314` environment prepared by the existing onedir build
script. The single-file builder uses the installed complete native tool folders
as inputs; it does not download them or alter those installations.

```powershell
.\.venv-build314\Scripts\python.exe packaging/build_single_exe.py
```

Or supply the complete folders explicitly:

```powershell
.\.venv-build314\Scripts\python.exe packaging/build_single_exe.py `
  --libreoffice 'C:\Program Files\LibreOffice' `
  --pandoc "$env:LOCALAPPDATA\Pandoc"
```

Output: **`dist/standalone/Filewheel.exe`**. Give family members that EXE alone.
`BUILD-INFO.json` beside it records its SHA256 and size; it is not a runtime
dependency. The existing `dist/Filewheel` diagnostic build is preserved.
The build log is `build/single-exe-build.log`.

## Run

Quit an older Filewheel tray owner first; repeated launches forward to that owner
and cannot replace its code. Double-click the new EXE for its tray menu. Enable
Experimental Mouse3 to use the Explorer wheel. All existing target validation,
confirmation preferences and injected-touchpad consent remain in place.

This build defaults to the accepted Quick glass UI and its Windows OpenGL
preference. Explicit environment/backend choices are preserved. Widgets remains
available through `Filewheel.exe --tray --ui-backend widgets`.

Shortcuts and Send to must point to the real EXE, never its temporary unpacked
folder. Remove/reinstall integrations if you move the EXE. They are opt-in:

```powershell
& .\dist\standalone\Filewheel.exe --sendto install
& .\dist\standalone\Filewheel.exe --startup install
```

## Verify the packaged file

```powershell
$env:FILEWHEEL_LOG_DIR = "$PWD\artifacts\single-exe\manual"
& .\dist\standalone\Filewheel.exe --self-test --ui-backend quick
Get-Content "$env:FILEWHEEL_LOG_DIR\self-test.json"
.\.venv-build314\Scripts\python.exe scripts/compare_quick_windows.py `
  --executable dist/standalone/Filewheel.exe --cycles 100 `
  --output artifacts/single-exe/ui --backends preferred --no-trace
```

Read the JSON, not just whether a window appeared. Pandoc and LibreOffice must
report `bundled`, and all checks must pass. The packaged self-test also starts
real frozen conversion children, cancels one before publication, then retries.
The native UI test checks state, animation and desktop pixels in one process.

The onefile build enables `FILEWHEEL_BUNDLED_TOOLS_ONLY=1` by default: missing
embedded tools cannot silently fall back to an installed copy. Test environments
can additionally clear PATH tool entries and Python-related variables. Such a
local isolation test is not equivalent to a second clean Windows machine.

See STATUS.md and the task plan for actual build/test results. Historical Linux
measurements elsewhere in the repository do not imply a supported Unix target.

## Delivered build (2026-10-27)

- EXE size:668,358,672 bytes (about637MiB).
- SHA256:`4a46099d87b9d67f65aefa956801dee0b682cfedff83f64c3d0bdc70b01b131c`.
- Full Windows suite:660 tests and407 subtests passed;4 skips, no failures.
- Copied EXE alone outside the checkout, with Python variables and installed
  tool paths removed:34 self-test checks/26 conversion pairs passed. Pandoc3.13
  and LibreOffice report bundled. Three real frozen children converted,
  cancelled and retried successfully. The self-test extraction folder cleaned up.
- Native OpenGL UI:46 completed cycles, then user interrupted to use the PC.
  The planned100-cycle check is incomplete. No further interactive tests may run
  until the user authorizes them. The previous F5 build's100-cycle evidence is
  historical and is not substituted for this new artifact's result.

[Machine-readable verification](standalone/verification.json) preserves this limit.
The existing installed/tray build and unrelated local files were left untouched.
