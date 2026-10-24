# G2 provisional index mapping and Windows acceptance

## Current result: native probe fails; diagnose one click first

The user's first G2 dry run on build26200 received/recorded 17 Explorer events.
Every one rejected with `native_probe_error`; each native association reported
only `COMError`. UIA repeat snapshots were stable, all selected snapshots true,
and all resolved paths null. Collection ranged 66.726–92.865 ms. This validates
startup and fail-closed handling, not native mapping. The attached sanitized
fixture is prior run-2 data. No new native view/path success is present.

The old report omitted the failing call and HRESULT. The updated probe now
records `stage`, `completed_stages`, numeric `hresult`, `hresult_hex` and, when
known, `hresult_name` inside `active_view_association` on failure. No raw COM
error message, error-info strings or tracebacks are logged. Successful probes
include `probe_steps`; optional position failures have separate `position_error`
evidence. All these are worker-side diagnostics; the mouse hook is unchanged.
Research rechecked the GUID/route without finding a supported concrete fix.
Do not change the route until the actual failure is localized.

Run only this short diagnostic next; make one file click in Details, then Ctrl+C:

```powershell
.\.venv\Scripts\python.exe -m filewheel.platforms.windows.diagnostics --enable --dry-run-mapping --output logs\g2-probe-stage-1.jsonl
$LASTEXITCODE
```

The console includes failed stage/HRESULT; retain the event record and final
summary/drop/exit output. A code such as E_NOINTERFACE must be interpreted at its
actual stage, not assumed to mean every Shell interface is unsupported. A null
HRESULT is explicit lack of a numeric code. The new stage diagnostics have only
Linux fake-test coverage; Windows retest is pending. Resume the acceptance table
below only after native collection works.

## Run-2 evidence and API finding

Source: user-pasted `windows-run-2.jsonl` text, reviewed 2026-10-24. The named
file is not present on this Kubuntu checkout. The summary reports 14 worker
events, 11 Explorer captures, three non-Explorer rejections and zero queued at
shutdown. Nine captures contain file items and two show Explorer chrome. All
nine numeric UIA IDs match the Folder.Items candidate indices, including
AGENTS.md=9, pyproject.toml=10 and README.md=11. All nine selected-state snapshots
are true. This supports the empirical index hypothesis and aggregate filtering
in that session, not independence from selection or active-tab correspondence.
All paths remain null; native view/geometry evidence is absent. Operator
expected targets, selection before/after, hook drop output and exit code were
not supplied. Codex did not run Windows during this task.

`tests/fixtures/windows_run_2_sanitized.json` is an explicitly labeled projection
of these captures: private paths are replaced, unused ancestry nodes omitted,
and observed IDs/points/bounds/times/selection preserved. It is replay input,
not new native evidence. Old captures assess as nine provisional candidates and
two non-file rejections; no test claims a verified click-to-file mapping.

Microsoft's [AutomationId documentation](https://learn.microsoft.com/en-us/dotnet/api/system.windows.automation.automationelement.automationelementinformation.automationid?view=windowsdesktop-8.0)
warns against assumptions about other applications' IDs and promises uniqueness
only among siblings, not stability across builds. Neither
[FolderItems.Item](https://learn.microsoft.com/en-us/windows/win32/shell/folderitems-item)
nor [IFolderView2.GetItem](https://learn.microsoft.com/en-us/windows/win32/api/shobjidl_core/nf-shobjidl_core-ifolderview2-getitem)
documents correspondence with that ID. Folder.Items enumeration and native view
indices are separate hypotheses, especially after sorting/filtering. Their
agreement is useful corroboration, not a documented identity bridge.

## Implementation and trust boundary

`assess_index_mapping` in the portable core returns a report, not a
TargetResolution. The Windows resolver calls it only with `--dry-run-mapping`;
the original diagnostic mode and resolver return contract are preserved.
`proven_target_from_evidence` and `ExplorerTargetResolver.resolve` still return
None. There is deliberately no flag that promotes provisional candidates to
trusted targets. Reports use `status=provisional|rejected`, explicit rejection,
hovered item/ID/bounds, candidate path/index, and individual validation checks.
`identity_correspondence` and `filesystem_identity` remain false because the
point-to-Shell identity chain has not been demonstrated.

Structural checks require Explorer provenance, finite fresh timestamps (at most
500 ms through collection), computed containing rectangles, a unique file-item
ancestor in the content/tab/root chain, complete unambiguous candidate sets,
valid indices, ordinary absolute local paths and consistent names. Name equality
is supporting evidence only. Hidden-extension names remain uncertain; duplicate
display names fail closed. Missing/virtual/folder/reparse objects, unsupported
drives, contradictory native paths/indices, incomplete native checks and changed
snapshots reject. No path is synthesized from a display name or selected item.

The optional Windows-only `ShellViewProbe` adds independent evidence:

1. Query the Shell window's IServiceProvider for SID_STopLevelBrowser /
   [IShellBrowser](https://learn.microsoft.com/en-us/windows/win32/api/shobjidl_core/nn-shobjidl_core-ishellbrowser).
2. QueryActiveShellView, then the view's inherited
   [IOleWindow.GetWindow](https://learn.microsoft.com/en-us/windows/win32/api/oleidl/nf-oleidl-iolewindow-getwindow).
   Require observed native containment from the hovered ShellTabWindowClass to
   the view and on to UIItemsView, with the same frame root. Unique frame HWND
   alone does not prove tab association. Missing/ambiguous relationships reject
   trusted routing and are explicit in the report. `matched` describes a sampled
   HWND chain, not Windows acceptance or a historical-event guarantee.
3. Query IFolderView2 and GetItem at the provisional index for IShellItem. Obtain
   [SIGDN_FILESYSPATH](https://learn.microsoft.com/en-us/windows/win32/api/shobjidl_core/nf-shobjidl_core-ishellitem-getdisplayname)
   and filesystem/folder attributes; compare with the separate Folder.Items
   candidate. Check fixed local drive, regular-file existence and reparse status
   without opening file contents. Repeat view HWND, count and indexed path reads.
4. Collect [GetItemPosition](https://learn.microsoft.com/en-us/windows/win32/api/shobjidl_core/nf-shobjidl_core-ifolderview-getitemposition)
   converted to screen coordinates when available; this is a top-left point,
   not a hit rectangle or independent proof of pointer identity. Re-read UIA
   ancestry and compare names/IDs/runtime IDs/geometry/handles (selection excluded).

The guarded comtypes bindings retain SDK interface prefix ordering; unused
struct parameters are opaque pointers. Allocated PIDLs and display-name strings
are freed with CoTaskMemFree. Objects stay on the existing MTA worker. The hook
is unchanged, passive and free of COM/UIA/filesystem work. Bindings/child-window
assumptions are implemented and fake-tested, **not Windows-verified**. If
QueryService, native view association or another API is unavailable, the report
rejects or marks the view unproven; do not guess a tab from its title/path.

Current bounded scope: up to 32 candidates, fixed local drives, standard
filesystem folder views. Larger/truncated folders, network/virtual/archive
objects, reparse points, desktop and ambiguous tabs are safe exclusions. Shell
calls can block; no hard provider timeout is implemented. Repeat samples cannot
reconstruct a view/tab that changed between the event and first sample.

## Run the next Windows experiment

Use the same environment from `DIAGNOSTIC_POC.md`, with the updated checkout:

```powershell
.\.venv\Scripts\python.exe -m filewheel.platforms.windows.diagnostics --enable --dry-run-mapping --output logs\g2-index-run-1.jsonl
$LASTEXITCODE
```

The console prints candidate/status/reason; JSONL includes raw ancestry, Shell
candidates, active-view association, native candidate and mapping checks, total
collection `elapsed_ms` and capture summary. An old diagnostic invocation without
the new flag remains supported. Logs are private, opt-in, local and gitignored.
Use a small disposable local folder with A/B, `report.txt`/`report.md`, and a
Unicode file such as `資料 æøå.txt`. Creating test fixtures is manual; the
diagnostic never selects/modifies files. Space trials by at least one second.

Record build, Git revision, actual view/sort/extension settings, tab/folder,
selected file before and after, original point, expected full path, observed
candidate/status/reason, latency, drop count and process exit code for each run.
Operator expectations must be independent of the candidate being evaluated.

| Trial | Procedure | Required evidence |
| --- | --- | --- |
| Unselected target | Select B, middle-click A; repeat reversed | Operator before/after selection; A candidate, never B substituted |
| Views | Repeat in Details and icon views | Correct item bounds, view HWND chain and native candidate agreement |
| Sort | Name ascending then descending; repeat A/B | Numeric ID and both index sources recorded; mismatch explicitly rejects |
| Hidden extensions | Toggle extensions, repeat | Supporting name consistency; no guessed extension |
| Duplicate stems | Hit report.txt/report.md with extensions hidden | Ambiguous labels reject; no promotion from filename equality |
| Tabs | Two tabs with different files, then same filenames; alternate tabs | Actual active Shell view inside hovered tab, or explicit rejection; no cross-tab path |
| Unicode | Hit Unicode filename | Exact candidate spelling survives JSON and native API reads |
| Negative | Empty space, title/command bar and navigation pane | No candidate trusted; non-file/ancestry rejection |
| Race | Change tab/sort/scroll during collection | Snapshot disagreement/stale evidence rejects |

First collect one simple Details hit and inspect native probe errors/association.
Do not perfect unsupported cases before this works. Even a fully corroborated
candidate remains provisional until real Windows results establish a reliable
pointer-to-item relationship under the core acceptance matrix. All trusted
resolved_path fields must stay null in this experiment. A wrong provisional
candidate is a failed trial, even though the trust boundary prevented routing.
All-selected snapshots alone do not demonstrate an unselected hover; if Explorer
natively changes selection on Mouse3, record that fact without suppressing the
button or programmatically selecting a file. Keep G2 pending and evaluate the
documented explicit-path fallback if the primary contract cannot be satisfied.
