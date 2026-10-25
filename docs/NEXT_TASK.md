# Next task: Windows acceptance of G10–G12

G9-A/B are Windows-verified by the user's latest report. G10 tray implementation
and lifecycle follow-up are complete. G11 build recipe and G12 full portable-office
integration seams are complete; native packaging/bundling remain unverified.
Final Linux checks: 312 tests / 241 subtests; all-engine source self-test passed.
Do not repeat G9 diagnosis or expand Mouse3 diagnostics without an observed blocker.

## First: try the tray on Windows 11 / Python 3.14

```powershell
powershell.exe -NoProfile -ExecutionPolicy Bypass -File .\scripts\setup-windows.ps1
.\.venv-filewheel\Scripts\python.exe -m filewheel --tray
```

Use the tray checkbox to enable Experimental Mouse3 (confirmation required).
Middle-click a local file in Explorer. Confirm only the exact proposed full path;
Cancel must never open a converter. A confirmed path opens the normal wheel at
the Mouse3 event point. Test unselected files, tabs, ambiguous hidden extensions,
background/chrome and unrelated apps; ambiguous evidence must reject. Disable
while idle and during pending consent; checkbox/status must return to off. Quit
must release the hook/threads and exit. Experiment remains off on the next normal
launch. If a provider genuinely hangs, retain logs and diagnose that concrete
case; do not force-kill another application's process.

Send to continues independently. For a known older owned GUI shortcut, remove
with its original environment before installing through the current entry:

```powershell
.\.venv-filewheel\Scripts\python.exe -m filewheel --sendto remove
.\.venv-filewheel\Scripts\python.exe -m filewheel --sendto stage
.\.venv-filewheel\Scripts\python.exe -m filewheel --sendto install
```

If the existing link targets another environment, its original interpreter is
required for ownership-checked removal. Never delete a foreign shortcut blindly.
Repeated Send to/direct GUI calls should route to the existing owner; test busy
rejection, negative-coordinate monitors, DPI, focus and repeated shutdown/restart.
Startup is optional: `python -m filewheel --startup install` / `--startup remove`.
It starts the tray with Mouse3 off. No startup entry is created automatically.

## Then: build and validate the standalone folder

Follow PACKAGING.md and PORTABLE_LIBREOFFICE.md. Build on Windows, Python 3.14
amd64 standard-GIL; the script uses a separate hash-locked build environment.

```powershell
powershell.exe -NoProfile -ExecutionPolicy Bypass -File .\scripts\build-windows.ps1 -LibreOfficeDirectory "D:\Tools\LibreOfficePortable"
& .\dist\Filewheel\Filewheel.exe --self-test
Get-Content "$env:LOCALAPPDATA\Filewheel\logs\self-test.json"
& .\dist\Filewheel\Filewheel.exe --tray
```

Omit LibreOfficeDirectory if no complete vendor tree is available; this leaves
portable DOCX → PDF acceptance pending, not failed PDF → DOCX. Move the entire
folder to a clean Windows machine/location without Python/venv. Verify native Qt
plugins, all conversion families, repeated launch, Send to and startup ownership.
With a complete bundle and no system LibreOffice, self-test must report
libreoffice_source=bundled and DOCX → PDF must produce readable output. Record
actual directory size and cold/warm latency. Do not call Linux wrapper tests a
portable Windows validation.

Local errors: `%LOCALAPPDATA%/Filewheel/logs/conversion-debug.log`.
Keep source files unchanged and output collision checks in every acceptance run.
