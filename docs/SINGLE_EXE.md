# Filewheel: one Windows EXE

For the current recommended family installer, use **FilewheelSetup.exe** and
[INSTALLER.md](INSTALLER.md). This document describes the older portable onefile
artifact; it has not been rebuilt with the finalized tray/startup changes.

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

Output: **`releases/Filewheel.exe`**, versioned through Git LFS. Give family members that EXE alone.
`BUILD-INFO.json` beside it records its SHA256 and size; it is not a runtime
dependency. The existing `dist/Filewheel` diagnostic build is preserved.
The build log is `build/single-exe-build.log`.

## Run

Quit an older Filewheel tray owner first; repeated launches forward to that owner
and cannot replace its code. The older committed portable artifact has the
Experimental Mouse3 tray toggle. Newly built source and the installed version
start the wheel by default and expose Enable wheel, Start on login, Quit.
All target validation and injected-gesture exact-path confirmation remain.

This build defaults to the accepted Quick glass UI and its Windows OpenGL
preference. Explicit environment/backend choices are preserved. Widgets remains
available through `Filewheel.exe --tray --ui-backend widgets`.

Shortcuts and Send to must point to the real EXE, never its temporary unpacked
folder. Remove/reinstall integrations if you move the EXE. They are opt-in:

```powershell
& .\releases\Filewheel.exe --sendto install
& .\releases\Filewheel.exe --startup install
```

## Verify the packaged file

```powershell
$env:FILEWHEEL_LOG_DIR = "$PWD\artifacts\single-exe\manual"
& .\releases\Filewheel.exe --self-test --ui-backend quick
Get-Content "$env:FILEWHEEL_LOG_DIR\self-test.json"
.\.venv-build314\Scripts\python.exe scripts/compare_quick_windows.py `
  --executable releases/Filewheel.exe --cycles 100 `
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

## Build records and current verification limit

The baseline EXE with SHA256
`4a46099d87b9d67f65aefa956801dee0b682cfedff83f64c3d0bdc70b01b131c`
was natively checked:34 checks/26 pairs and real worker cancellation/retry passed.
Its UI trial completed46 cycles before user interruption. Its source suite had
660 tests/407 subtests passed,4 skips. Those are historical results for that build.
The exact baseline is recoverable from the b9b77a3 commit through Git LFS.

The current cleanup/converter review adds PPTX/XLSX-to-PDF. Per user instruction,
no tests, native tool probes, benchmarks or desktop automation are being run.
The new EXE is rebuilt with `--skip-tool-probes`; compilation success does not
renew the previous native acceptance. Check the current SHA256 and build metadata
in releases/SHA256SUMS.txt and releases/BUILD-INFO.json.

For a test-free rebuild matching this pass:

```powershell
.\.venv-build314\Scripts\python.exe packaging/build_single_exe.py --skip-tool-probes
```

Read [CONVERTER_REVIEW.md](CONVERTER_REVIEW.md) for scope and restrictions. Existing
[baseline verification](standalone/verification.json) remains explicitly historical.
Do not restart the interrupted UI automation without the user's request.

Current compiled artifact: SHA256
`a0bf33614ee5eb24269add1b871a7c28c9470fcc7c2a293eccc41f77ef37feb1`.
Build/probe status is in [cleanup-build.json](standalone/cleanup-build.json).
No current runtime test result is implied by successful compilation.
