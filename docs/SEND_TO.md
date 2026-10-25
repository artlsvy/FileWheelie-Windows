# Explicit-path launcher, radial converter and personal Send to

Basic headless single-file direct CLI and Explorer Send to are **WINDOWS-VERIFIED**
from user evidence: build26200, Python3.15.0, exact AGENTS.md path, source
shell_explicit, accepted=true. Direct193.127ms/Send to0.334ms are diagnostic timings.
Do not repeat that basic diagnostic without a regression. User also reports G4
successfully launched/rendered on Windows after the monitor fix. Converters and
240px refinement are Linux-tested only; detailed Windows acceptance is queued.
**GUI format clicks now perform real conversion.** See [engines, installation and
Windows smoke tests](CONVERTERS.md); headless diagnostics remain metadata-only.

## Install and launch the radial GUI on Windows

From the updated project root (Python3.15 target supported by PySide6>=6.12):

```powershell
.\.venv\Scripts\python.exe -m pip install -e ".[ui,images,pdf,heif,markdown,office]"
.\.venv\Scripts\python.exe -c "import sys, PySide6; print(sys.version); print(PySide6.__version__)"
.\.venv\Scripts\python.exe -m filewheel.platforms.windows.sendto stage --mode gui
.\.venv\Scripts\python.exe -m filewheel.platforms.windows.sendto install --mode gui
```

Inspect staged logs/sendto-stage/Filewheel preview.lnk if desired. Right-click
one file → classic menu / Show more options → **Send to → Filewheel preview**.
The GUI shortcut targets pythonw.exe directly, so no console stays open. It is
separately named and owned from Filewheel diagnostic; installing it preserves the
working diagnostic entry. To switch the visible menu entirely, remove the old
entry explicitly with `sendto remove --mode diagnostic`. No manual shortcut edits.

Direct GUI command (console useful for dependency/desktop errors):

```powershell
$filewheelInput = (Resolve-Path .\AGENTS.md).Path
.\.venv\Scripts\python.exe -m filewheel.platforms.windows.explicit_path_diagnostics --gui -- $filewheelInput
$LASTEXITCODE
```

PNG offers real JPEG/WebP (when codecs are available) and Document/PDF. PDF offers
editable DOCX, raster page images and Markdown when installed/supported. DOCX→PDF
needs LibreOffice; Markdown pairs need the supported Python3.14 environment.
AGENTS.md is not a supported conversion input and shows no available formats.
The shortcut's historical **Filewheel preview** label is preserved for ownership
compatibility, but the menu now converts. Choose category then format to start a
worker; success/error and actual output names appear in the popup. Existing output
is never silently replaced. Escape/outside cancels cooperatively. Default GUI
invocation writes no diagnostic logs; add --enable --output-dir before -- to opt in.

Remove just the owned GUI entry (repeat safely):

```powershell
.\.venv\Scripts\python.exe -m filewheel.platforms.windows.sendto remove --mode gui
```

All ownership, non-overwrite and same-checkout/interpreter rules below apply to
both modes. Diagnostic remains the default mode for backward compatibility.

## Preserved headless diagnostic command

From the updated repository root, Python3.12+ and the existing venv:

```powershell
.\.venv\Scripts\python.exe -m pip install -e .
$filewheelInput = (Resolve-Path .\AGENTS.md).Path
.\.venv\Scripts\python.exe -m filewheel.platforms.windows.explicit_path_diagnostics --enable --output-dir logs\invocations -- $filewheelInput
$LASTEXITCODE
```

Expect accepted=true, source=shell_explicit, the exact absolute path and
action=diagnostic_only. A unique UTF-8 JSONL artifact appears in logs/invocations.
Console output uses ASCII escapes for compatibility with legacy redirected
streams. `--output NEWFILE` may replace --output-dir; existing logs are preserved.
The -- delimiter separates program options from file arguments. --enable opts
in to local filename logging; logs are private and gitignored.

## Stage, install, remove

Optional staging creates logs/sendto-stage/Filewheel diagnostic.lnk for inspection
in Explorer Properties, without adding it to the menu:

```powershell
.\.venv\Scripts\python.exe -m filewheel.platforms.windows.sendto stage
```

Install for the current user, without admin rights or registry changes:

```powershell
.\.venv\Scripts\python.exe -m filewheel.platforms.windows.sendto install
```

Right-click one file, open the classic context menu if necessary, then choose
**Send to → Filewheel diagnostic**. The console may appear briefly. Read the
latest artifact rather than relying on that window remaining open:

```powershell
$filewheelLatest = Get-ChildItem .\logs\invocations\*.jsonl | Sort-Object LastWriteTime | Select-Object -Last 1
Get-Content -LiteralPath $filewheelLatest.FullName -Encoding UTF8
```

Remove only this checkout/interpreter's owned shortcut:

```powershell
.\.venv\Scripts\python.exe -m filewheel.platforms.windows.sendto remove
```

These operations are idempotent. A differing existing shortcut is preserved and
the operation fails. Stage/install save to a private temporary link then move
without replacement. Removal checks description, interpreter, arguments and
working directory before deleting the link. Logs and source files remain intact.
Run from the same project/interpreter used to install; --project-root accepts
the absolute project directory when running elsewhere. Remove before moving a
checkout and reinstall afterward.

Management uses packaged PowerShell/WScript.Shell. ExecutionPolicy Bypass applies
only to that child process; no system policy is changed. Invoked filenames never
enter cmd/PowerShell: the .lnk targets Python directly with fixed arguments and
--, then Explorer appends file paths. See Microsoft's
[Send to command-line behavior](https://devblogs.microsoft.com/oldnewthing/20170403-00/?p=95885)
and [shortcut properties](https://learn.microsoft.com/en-us/troubleshoot/windows-client/admin-development/create-desktop-shortcut-with-wsh).
The same CLI is suitable for a future context-menu entry; none is registered now.

## Shared controller and limitations

Exactly one ordinary absolute drive-letter Windows file path is accepted.
Unicode, spaces, apostrophes and literal &, %, ! and ^ are preserved; no quote
stripping, environment expansion or shell evaluation. Missing/inaccessible
files, folders, reparse points, relative paths, UNC/device paths, alternate data
streams, traversal and malformed/multiple paths reject. Initial exclusions may
be revisited separately. Metadata inspection never reads/modifies file contents.
Validation is a snapshot; later conversion must revalidate/open its input.

handle_explicit and handle(MouseEvent) return the same TargetResolution class:
path/source/point/timestamp. Explicit source is shell_explicit, window_id=0;
future verified hover source is explorer_hover. Explicit invocation captures
the current physical cursor at startup, not the historical file-row point.
The Qt consumer maps coordinates at its boundary and uses either source
identically. Cancel/newer requests invalidate pending results. No UIA/selection
query, comtypes or hook is loaded; Qt is imported only after GUI path validation. Mouse3 code is
preserved, with unverified hover still returning None.

CLI exit codes:0 accepted/logged;2 rejected path/count or argparse usage error;
3 unavailable Windows cursor context;4 log creation failure;5 GUI dependency/desktop failure;6 conversion failure. Shortcut management
returns0 on success or1 on script failure. Rejected inputs must never open UI.

## Manual Windows acceptance (pending)

Record revision/build/runtime, expected path, JSONL result and process exit:

1. Basic headless AGENTS.md direct/Send to delivery is already user-verified.
   Do not repeat it unless diagnosing a regression.
2. Repeat actual Unicode/spaces and literal &/%/apostrophe/!/^ filenames. Inspect
   UTF-8 artifacts for exact preservation and ensure filenames execute no commands.
3. Send a folder: expect not_a_file. Invoke a nonexistent path directly: expect
   missing_file. Pass two direct CLI paths: expect expected_one_path.
4. Try Explorer multi-selection; record argument_count/process count. Every
   process receiving multiple arguments must reject. If Explorer launches one
   process per item, record that behavior; batch conversion is unsupported.
5. Repeat install; remove twice; confirm the entry disappears. Confirm a differing
   same-name shortcut survives a refused install/remove operation.

PowerShell syntax/COM/shortcuts, Explorer quoting and physical cursor values
cannot be certified by Linux fakes. Keep their validation queue in STATUS.md.
GUI development proceeds independently under the user's updated priority.

## Current Windows acceptance

Follow [CONVERTERS.md](CONVERTERS.md) for the unique PNG smoke, real conversions,
engine dependencies, Python3.15 Markdown limitation, cancellation,240px transparency
and mixed-DPI tests. Basic G4 rendering is user-verified; these new behaviors are
not. The prior match_qt_screen failure was fixed by unique full monitor geometry
and DPR association instead of comparing Win32 device IDs to Qt friendly names.
Structured gui_startup_error still reports native geometry/stage on failures.
No shortcut reinstall is needed solely for that fix. No Mouse3 lookup is used.


## Tray and packaged application

The current GUI shortcut uses the shared app entry so repeated launches route to
one current-user owner. Start the optional tray with:

```powershell
.\.venv-filewheel\Scripts\python.exe -m filewheel --tray
```

Mouse3 is off by default. Enable experimental Mouse3 through the tray checkbox;
D-016 makes per-file confirmation an optional second checkbox, off by default; Send to requires no Mouse3 listener. The wheel uses the cursor at
launch time, not the location of the file before the context-menu interaction.

For an owned current-development shortcut use `python -m filewheel --sendto
stage` / `--sendto install` / `--sendto remove`. A known older source GUI link may
require removal with its original interpreter, then reinstall. Foreign targets
are preserved. Packaged equivalents are `Filewheel.exe --sendto stage`,
`--sendto install` and `--sendto remove`; see PACKAGING.md. No integration is
installed automatically by a build or normal launch.
