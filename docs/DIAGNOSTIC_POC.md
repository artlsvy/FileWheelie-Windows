# Explorer diagnostic: first evidence reviewed, next experiment unverified

G2 update: two Windows diagnostic rounds are now reviewed. The optional
`--dry-run-mapping` mode reports provisional index candidates and native Shell
view evidence; see [G2 mapping and acceptance procedure](G2_MAPPING.md). The
original invocation below remains supported and still resolves no targets.

The portable controller is fake-tested on Kubuntu. The Windows adapter is a
diagnostic experiment, not a working target resolver. It always returns `None`.
No GUI, converter, selection change or middle-click suppression is implemented.
The user's first Windows session shows successful positive capture/UIA/Shell
collection; see `WINDOWS_SESSION_001.md`. Negative filtering, selection
independence and shutdown still need the controlled experiment below.

## Run portable checks

Python 3.12+ from the repository root; no third-party dependencies needed:

```sh
PYTHONPATH=src python3 -m unittest discover -s tests/unit -v
python3 -m compileall -q src tests
```

`pytest` and `ruff` are optional development dependencies. Their availability and
actual results must be recorded separately from unittest results.

## Run on the Windows 11 tower

Use a normal interactive console, a new local output file, and a disposable test
folder containing A and B. There is no MCP prerequisite. Install the project
in a virtual environment with its optional Windows dependency:

```powershell
py -3 -m venv .venv
.\.venv\Scripts\python.exe -m pip install -e '.[windows]'
New-Item -ItemType Directory -Force logs
.\.venv\Scripts\python.exe -m filewheel.platforms.windows.diagnostics --enable --output logs\first-session.jsonl
```

Select B and middle-click A in Explorer Details and icon views. Stop with Ctrl+C.
The source passively chains every hook event. Injected input is ignored. The
bounded queue holds 64 events and counts overflow; no COM/UIA/filesystem work
occurs in the hook. Foreground HWND is sampled in the callback; process, ancestor,
class and DPI checks occur on the worker. Desktop and other Shell surfaces are
currently excluded. Only foreground `explorer.exe` / `CabinetWClass` candidates
are logged; unrelated applications are ignored.

Logs contain private local filenames; they are opt-in, local, gitignored, and
created exclusively (an existing file is rejected). A session record includes
Windows build and DPI awareness. Event records contain physical point, monotonic
timestamp, HWND/process/class/DPI evidence, at most 12 UIA ancestors with bounded
properties, and at most 32 Shell folder candidates per matching Shell window.
Enumeration is capped at 64 Shell windows. Candidate paths are evidence strings,
not verified file paths. The diagnostic records unknown view, unavailable Shell
geometry, and unproven active-tab correspondence explicitly. No selected/focused
item is used for identity. No UIA name is joined to a directory. List-item
ancestors now include a read-only `selection_snapshot`: `is_selected` is true or
false when observed, null when unavailable/error. This is worker-time state,
not proof of selection at the original hardware event. The API is
[IUIAutomationSelectionItemPattern.CurrentIsSelected](https://learn.microsoft.com/en-us/windows/win32/api/uiautomationclient/nn-uiautomationclient-iuiautomationselectionitempattern).
No selection mutation methods are called.

On normal capture shutdown, a `capture_summary` record includes worker-received
event count, aggregate rejection/capture counts, and queue remainder. Rejected
unrelated applications produce counts only: no names, HWNDs, PIDs, paths or event
coordinates are added for them. Controller-skipped events are counted separately.
Hook queue drops still appear in console output. The summary is written before
COM release; require a successful process exit as well. A blocked/failed worker
may prevent the summary from being written.

## Next Windows experiment: six controlled middle clicks

Run the updated diagnostic using a new filename such as `logs/controlled-smoke.jsonl`.
Record the Git revision, command, actual Explorer view and test time. Use an
ordinary folder containing exactly `a.txt` and `b.txt` if convenient. Space
middle clicks at least one second apart, wait one second after each, and make
no other middle clicks while capture is active. Use left clicks for selection.

1. Details view: select B; middle-click the filename of A once. Record expected
   hovered A, selected B, and whether selection stayed on B afterward.
2. Select A; middle-click B once. Record expected hovered B, selected A and
   selection afterward.
3. Switch to an icon view; select B; middle-click A once. Record exact view,
   hovered A, selected B and selection afterward.
4. Middle-click empty folder background once, away from all items.
5. Bring an unrelated application such as Notepad to the foreground and
   middle-click its client area once.
6. Bring a second unrelated application to the foreground and middle-click
   its client area once. Stop with Ctrl+C after a one-second wait.

Expected evidence (compare to the actual operator notes, not assumptions):

- `worker_received=6`, `resolver_calls=6`, `explorer_accepted=4`,
  `records_written=4`, `mapping_unproven=4`, `non_explorer_process=2`,
  `queue_remaining=0`. Zero counters may be absent from the JSON dictionary.
  `controller_skipped`, `stale_event`, `window_mismatch`, `process_unavailable`
  and `evidence_error` should be absent/zero; otherwise investigate the deviation.
- Three item captures have the expected UIItem ancestor with containing bounds;
  `selection_snapshot.is_selected=false` supports unselected visual targeting at
  worker time. A null state is inconclusive, not a false value. A true state or
  changed selection requires inspection before claiming selection independence.
- The background capture has no containing file-item ancestor. Its reason still
  remains `mapping_unproven`; there is no file-row rejection classifier yet.
- No per-event payload for either unrelated application. Every resolved path
  stays null. Expect `Dropped hook events: 0`, prompt Ctrl+C exit, exit code 0,
  and no worker/shutdown errors. Record console output and PowerShell
  `$LASTEXITCODE` immediately after the diagnostic command.

Send the session/capture records, final summary and operator/console observations.
This validates a small G1 smoke scenario only. It cannot prove general filtering,
historical click identity or Shell mapping. Do not reinterpret UIA automation IDs
as Shell enumeration indices even if they happen to match.

The standalone process requests per-monitor v2 DPI awareness and fails startup
if it cannot establish that context. COM objects are created/used/released on a
dedicated MTA worker. COM calls have no hard timeout here: events older than
500 ms are skipped before collection, but a provider may block during a call.
The worker is a daemon with a bounded shutdown wait; blocked shutdown is reported
as failure. This is a known diagnostic limitation, not a latency guarantee. The
controller catches resolver exceptions but cannot interrupt a blocked provider.
Active tabs or file layout can change while asynchronous evidence is collected;
these snapshots cannot attest the historical clicked file.

## Mapping experiment and evidence limits

`proven_target_from_evidence` is the explicit uncertain mapping seam and always
returns `None`, including for apparently unique names. UIA bounding rectangles
do not by themselves prove Shell identity. Shell automation enumerates folder
items as a lightweight starting point; it does not provide `IFolderView2` item
geometry or prove which tab owns the click. Adding that evidence is a separate
experiment, not an implicit path-matching heuristic.

Research found documented APIs for individual steps, but no documented general
correspondence between UIA runtime IDs, display names, or geometry and Shell
view indices:

- [LowLevelMouseProc](https://learn.microsoft.com/en-us/windows/win32/winmsg/lowlevelmouseproc)
  requires a message loop and fast callback; timeouts can silently remove hooks.
- [ElementFromPoint](https://learn.microsoft.com/en-us/windows/win32/api/uiautomationclient/nf-uiautomationclient-iuiautomation-elementfrompoint)
  supplies a visual element, not a filesystem identity.
- [IFolderView2::GetItem](https://learn.microsoft.com/en-us/windows/win32/api/shobjidl_core/nf-shobjidl_core-ifolderview2-getitem)
  supplies a Shell item for an index;
  [IFolderView::GetItemPosition](https://learn.microsoft.com/en-us/windows/win32/api/shobjidl_core/nf-shobjidl_core-ifolderview-getitemposition)
  supplies a top-left position, not a documented UIA mapping or item rectangle.
- [IShellWindows](https://learn.microsoft.com/en-us/windows/win32/api/exdisp/nn-exdisp-ishellwindows)
  and [IShellBrowser](https://learn.microsoft.com/en-us/windows/win32/api/shobjidl_core/nn-shobjidl_core-ishellbrowser)
  identify registered windows and active views; tab correspondence needs evidence.
- [UIA threading guidance](https://learn.microsoft.com/en-us/windows/win32/winauto/uiauto-threading)
  recommends a separate MTA thread for desktop-wide UIA calls.

For G1, first verify imports/bindings, passive Mouse3 capture, shutdown and actual
JSONL evidence on Windows. For G2, this scaffold's unconditional rejection cannot
pass positive path tests. A future proven mapping must meet the full matrix in
`EXPLORER_HIT_TEST.md`, including B-selected/A-hovered, hidden extensions,
duplicate stems, Unicode, tabs, scrolling/grouping, background/chrome, folders,
virtual items, scaling and negative monitor coordinates. Record expected and
observed paths and build/view/DPI; no Linux test supplies this evidence. If a
deterministic mapping cannot be established, document the G2-F explicit Shell
path fallback decision before proceeding to the UI.
