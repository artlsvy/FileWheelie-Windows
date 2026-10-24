# Headless explicit-path launcher and personal Send to integration

Implemented and Linux-tested; **Windows Shell integration is not yet verified**.
The launcher validates one explicit path through InvocationController and records
the shared TargetResolution DTO. No conversion or GUI action is implemented.
The next development priority is the PySide6 radial prototype.

## Direct Windows smoke run

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
The future Qt consumer maps coordinates at its boundary and uses either source
identically. Cancel/newer requests invalidate pending results. No UIA/selection
query, comtypes, hook or Qt dependency is loaded by this launcher. Mouse3 code is
preserved, with unverified hover still returning None.

CLI exit codes:0 accepted/logged;2 rejected path/count or argparse usage error;
3 unavailable Windows cursor context;4 log creation failure. Shortcut management
returns0 on success or1 on script failure. Rejected inputs must never open UI.

## Manual Windows acceptance (pending)

Record revision/build/runtime, expected path, JSONL result and process exit:

1. Run direct CLI on one existing file; then install and invoke Send to for it.
   Compare the received path/source with the independently expected path.
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
