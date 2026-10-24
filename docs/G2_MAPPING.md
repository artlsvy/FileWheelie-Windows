# G2 provisional index mapping and Windows acceptance

## Current result: Unicode/hidden-label checks pass; identity review next

g2-names-2 preserves the full unicode-æøå.txt Shell candidate from UIA's hidden
stem and safely rejects both report labels as ambiguous_display_name. Unique
tab association works among three registrations. Queue0/drops0; exit code not
supplied. These cases do not need another fixture batch.

The remaining technical gap is an independent link from the hovered visual item
to the Shell identity. See [G2 identity review](G2_IDENTITY_REVIEW.md) for the
evidence table and next native control-class diagnostic. The new read-only
fields do not activate paths or send hit-test messages. One existing-file click
is sufficient to collect them; the filename setup sections below are historical.

## Latest result: negatives pass; non-ASCII and hidden-extension confirmation remain

g2-names-1 reports correct provisional plain.txt/unicodefile.txt/report.txt/
report.pdf paths. Folder rejection and three non-file rejections pass, queue0,
drops0/exit0, collection66.678–128.443ms. Raw non-file nodes are Items View,
command-bar input site and search TextBox. The operator notes two blank-space
clicks; both notes and provider classes are retained without assuming another
file target. No negative-area rerun is needed for these cases.

The actual unicodefile.txt name contains only ASCII characters; it cannot prove
non-ASCII paths. report.txt/report.pdf are distinct UIA names with extensions.
This proves same-stem differentiation for that provider data, not ambiguous-name
handling or a confirmed visual extension setting. No runtime correction follows.

Close only these gaps with three new temporary files. This code creates a fresh
GUID directory and builds æ/ø/å by codepoint, avoiding manual Unicode typing;
the report.pdf is an empty identity fixture, never opened/converted:

```powershell
$filewheelNamesDir = Join-Path $env:TEMP ('filewheel-names-' + [guid]::NewGuid().ToString('N'))
New-Item -ItemType Directory -Path $filewheelNamesDir | Out-Null
$filewheelUnicodeName = 'unicode-' + [char]0x00E6 + [char]0x00F8 + [char]0x00E5 + '.txt'
$filewheelUnicodeName, 'report.txt', 'report.pdf' | ForEach-Object { New-Item -ItemType File -Path (Join-Path $filewheelNamesDir $_) | Out-Null }
$filewheelNamesDir
```

Navigate Explorer to the printed directory. Set Details/Name ascending and turn
off File name extensions. Record whether the two report rows visually both say
report, or still include extensions. Do not rename them to simulate hiding.

```powershell
.\.venv\Scripts\python.exe -m filewheel.platforms.windows.diagnostics --enable --dry-run-mapping --output logs\g2-names-2.jsonl
```

Mouse3 unicode-æøå.txt, then report.txt, then report.pdf, at least one second
apart (use Type/icon to distinguish the report rows). Stop/Ctrl+C and record
$LASTEXITCODE. Supply JSONL/console plus visible-label/extension-toggle notes.
The Unicode candidate should retain exact codepoints. If UIA exposes both names
as report, ambiguity must reject; if UIA exposes full names while visual labels
are hidden, record that valid provider distinction and inspect the native paths.
Trusted paths stay null. Do not remove the earlier user-created repository files.

## Current result: tab retest passes; next names and negative-area batch

g2-tabs-2 reports the expected tests/A, root/README, tests/B, root/AGENTS candidates
using registration indices1/0/1/0. All six prior consistency classes and repeated
snapshots pass in all four events. Both tabs report view mode4, latency
105.009–127.815ms, drops0/queue0/exit0. This is supplied live evidence of corrected
provisional tab routing, not general G2 completion. Trusted paths remain null;
Shell positions are still E_NOTIMPL. No runtime change is needed for this batch.

Next create only a fresh temporary test folder with empty identity-test files
(the .pdf is not a real PDF and will not be opened/converted). Run locally in
PowerShell; a GUID directory avoids collisions or overwriting repository files:

```powershell
$filewheelCaseDir = Join-Path $env:TEMP ('filewheel-hit-test-' + [guid]::NewGuid().ToString('N'))
New-Item -ItemType Directory -Path $filewheelCaseDir | Out-Null
'plain.txt', 'report.txt', 'report.pdf', '資料 æøå.txt' | ForEach-Object { New-Item -ItemType File -Path (Join-Path $filewheelCaseDir $_) | Out-Null }
New-Item -ItemType Directory -Path (Join-Path $filewheelCaseDir 'subfolder') | Out-Null
$filewheelCaseDir
```

Navigate one Explorer tab to that printed folder. Use Details, explicitly Name
ascending, and hide filename extensions. Verify how both report files are
actually displayed; do not rename them to force a result. Then start:

```powershell
.\.venv\Scripts\python.exe -m filewheel.platforms.windows.diagnostics --enable --dry-run-mapping --output logs\g2-names-1.jsonl
```

Mouse3 these seven targets in order, at least one second apart:

1. plain.txt (select a different row beforehand with left click).
2. 資料 æøå.txt.
3. report.txt (use the Type column/icon to distinguish it).
4. report.pdf.
5. subfolder.
6. Empty file-pane space, away from all rows.
7. Explorer command-bar/chrome blank area (avoid tab headers and action buttons).

Stop with Ctrl+C; record `$LASTEXITCODE`. Supply JSONL/console, the actual folder
path and visible report labels. Plain/Unicode targets should produce the exact
provisional paths or an explained safe rejection. If both UIA item names are
only report, expect ambiguous_display_name rejection; if UIA supplies full
distinct names despite hidden visual extensions, record that stronger evidence
instead of assuming ambiguity. Folder/background/chrome must reject file mapping.
No candidate may be reconstructed from a label or silently become trusted.
Remaining broader race/scaling/unsupported-surface cases stay in the main matrix.

## Current change: unique native tab association can disambiguate registrations

The supplied g2-tabs-1 run used Details in both tabs, alternated A/README/B/AGENTS,
and safely rejected all four with ambiguous_shell_windows. Summary4 received/
written, queue0, drops0 and exit0. Each record contains TWO same-frame Shell
registrations, but exactly ONE sampled native chain matches the hovered tab.
The inactive entry has different browser/view HWNDs. Native collection itself
worked; the portable assessor rejected merely because the frame had >1 entry.
Latencies106.962–136.163ms; all optional position queries remain E_NOTIMPL.

The bounded assessor correction selects a registration only by unique native
HWND evidence: browser=hovered ShellTab, view=captured DUIListView, and content=
captured UIItemsView. Every peer must carry complete non-errored evidence with
different browser/view HWNDs. No matching by path/name/index/order, and no
discarding unknown peers. Duplicate matches, missing/contradictory relationships,
truncation, native errors and stale data still reject. Existing single-entry
contracts remain unchanged. The selected entry undergoes all previous candidate
and native-file validations; trusted resolution remains None.

`mapping.checks.shell_window_count` and `selected_shell_window_index` explain
the choice. Source projection in windows_tabs_1_sanitized.json preserves the old
rejections; new replay assessments are not new Windows runs. No native API or
hook changes were needed. D-010 remains provisional pending this retest.

After syncing, keep the same two tabs/views and repeat the four-file sequence
once with a fresh log:

```powershell
.\.venv\Scripts\python.exe -m filewheel.platforms.windows.diagnostics --enable --dry-run-mapping --output logs\g2-tabs-2.jsonl
$LASTEXITCODE
```

Left-click tab switches; Mouse3 tests/a.txt, parent/README.md, tests/b.txt,
parent/AGENTS.md, spaced at least one second apart. Expected provisional paths
must belong to the clicked tab. Preserve both raw registrations in the JSONL;
any ambiguity must still reject. Send JSONL plus console drop/exit output.
The prior g2-tabs-1 rejection is not proof this corrected assessor works live.

## Latest comparison: paths remain correct through index reassignment

The operator reports completing the four descending-sort trials exactly.
All four candidates match A/B/A/B, with matching native paths/indices, HWND
associations and stable snapshots; latency73.105–95.414ms, drops0, queue0.
Exit code was not supplied for this run. All paths remain provisional.

| Click | Reported view | A/B index evidence | Candidate |
| --- | --- | --- | --- |
| 1 | Medium icons, Name descending | A=2; enumeration fixtures/unit/A/B | a.txt |
| 2 | Medium icons, Name descending | B=3; same enumeration | b.txt |
| 3 | Details, Name descending | A=1; enumeration B/A/unit/fixtures | a.txt |
| 4 | Details, Name descending | B=0; same new enumeration | b.txt |

Both Shell sources and UIA agree after the index change. This supports resolving
against a fresh view snapshot, never treating an index as persistent identity.
The first two captures do not independently prove reversed icon order; native
sort columns are not logged. Retain the operator's setting report without adding
unsupported metadata. GetItemPosition is E_NOTIMPL in all four captures.

Next test two tabs in the SAME Explorer window, using existing files:

```powershell
.\.venv\Scripts\python.exe -m filewheel.platforms.windows.diagnostics --enable --dry-run-mapping --output logs\g2-tabs-1.jsonl
```

Open one tab at the repository tests folder and one at its parent repository
folder. Switch tabs using left click. Space Mouse3 file clicks at least one
second apart, in this order:

1. tests tab: a.txt.
2. parent tab: README.md.
3. tests tab: b.txt.
4. parent tab: AGENTS.md.

Stop with Ctrl+C and record `$LASTEXITCODE`. Send full JSONL/console and confirm
the two folders were tabs in one window, with their view settings. Expected paths
are tests/a.txt, parent/README.md, tests/b.txt, parent/AGENTS.md. Each sampled view
must belong to the hovered tab. An ambiguous association may reject, but any
other tab's candidate is a failed trial. Do not change the environment or create
files for this comparison. Duplicate-stem/hidden-extension/Unicode and negative
tests follow after tab behavior is understood.

## Latest acceptance notes: hovered candidates reported despite prior selection

The user supplied g2-acceptance-1 console, full six-event JSONL, zero drops,
exit0 and the following operator observations. Events1–4 were Medium icons;
events5–6 were Details (native view modes1/4). All six native validation sets
pass with stable snapshots and matched Shell paths/indices/active-view HWNDs.
Collection latency72.965–94.449ms. All GetItemPosition calls return E_NOTIMPL.

| Click | Hovered item | Selection before Mouse3 | Console candidate |
| --- | --- | --- | --- |
| 1 | a.txt | a.txt | a.txt / index2 |
| 2 | b.txt | b.txt | b.txt / index3 |
| 3 | a.txt | b.txt | a.txt / index2 |
| 4 | b.txt | b.txt | b.txt / index3 |
| 5 | README.md in parent folder | README.md | README.md / index11 |
| 6 | README.md | README unselected; selected item unspecified | README.md / index11 |

Clicks3/6 support the hovered-candidate behavior independently of pre-click
selection in these trials. The user observed that native Mouse3 selects the
clicked file. An asynchronous is_selected=true snapshot therefore cannot tell
us whether that item was selected before the click. The diagnostic remains
passive and contains no Select/AddToSelection mutation. Judge target correctness
against operator pre-click notes; record native selection changes separately.
Do not require native selection to stay on B as a prerequisite for this passive
experiment, and do not suppress Mouse3 to force that result.

The completed comparison challenged the index hypothesis with descending Name sort. It used the
same tests folder containing a.txt/b.txt and the same environment. Start capture:

```powershell
.\.venv\Scripts\python.exe -m filewheel.platforms.windows.diagnostics --enable --dry-run-mapping --output logs\g2-sort-desc-1.jsonl
```

1. Medium icons, Sort by Name descending: select B with left click, Mouse3 A.
2. Select A with left click, Mouse3 B.
3. Switch to Details, explicitly set Name descending; select B, Mouse3 A.
4. Select A, Mouse3 B. Stop capture with Ctrl+C.

Space Mouse3 clicks at least one second apart. Expected candidates are A/B/A/B;
any wrong path is a failed trial, even if rejected from trusted routing. Paste
JSONL and console exit/drop results, with confirmation that both views were Name
descending. This adds four cases rather than repeating the initial six. The
earlier run's sort order was not recorded, so it is not an explicit ascending
sort baseline. Hidden extensions, duplicate stems, multiple tabs, Unicode and
negative-area coverage remain pending. All candidates stay provisional.

## Current result: one native STA capture completed; expand acceptance

The supplied `g2-sta-1.jsonl` now completes GetWindow, HWND association and native
IShellItem collection. Build26200/DPI96, Python3.15.0/comtypes1.4.17, UIA MTA and
Shell STA; Folder.Items and native GetItem both report b.txt at index3. Bounds,
freshness, regular/local/nonreparse checks and repeated snapshots pass. Latency
110.607ms, zero drops/queue remainder and exit0. This supports the STA probe in
one sample, not general tab identity or selection-independent path resolution.

GetItemPosition reports E_NOTIMPL/0x80004001; the record has no independent Shell
item position. Its `view_mode=1` is retained as native evidence; do not infer the
operator's Explorer setting solely from the bounding shape. All identity checks
must continue to distinguish UIA geometry from Shell item correspondence.
The selected snapshot is true and no independent expected-target/selection notes
were supplied. `identity_correspondence_unproven` is the intended trust barrier,
not another COM exception to bypass. All trusted paths remain null.

Next run the acceptance table below, starting with A hovered while B is selected
in Details and then an icon view. Keep the current environment constant; no
runtime code/dependency change is required for this round. Use a new log:

```powershell
.\.venv\Scripts\python.exe -m filewheel.platforms.windows.diagnostics --enable --dry-run-mapping --output logs\g2-acceptance-1.jsonl
$LASTEXITCODE
```

For every numbered click, record view/sort/tab, hovered full expected path and
selected file before/after. The log alone cannot supply that ground truth. A
wrong candidate or index disagreement is a failed trial; a safe rejection is an
exclusion to record. The broader matrix remains required before a trust-policy
change. The previous one-click failure investigations below are historical.

## Latest result: GetWindow input-synchronization failure localized

The supplied staged run reached QueryActiveShellView successfully, then failed
at `get_active_view_hwnd` with signed HRESULT -2147417843 / `0x8001010D`.
Microsoft names this RPC_E_CANTCALLOUT_ININPUTSYNCCALL: an outgoing call cannot
be made while dispatching an input-synchronous call. Its
[Call Synchronization documentation](https://learn.microsoft.com/en-us/windows/win32/com/call-synchronization)
lists IOleWindow.GetWindow as input-synchronized. This localizes the failure to
call context; it does not prove that the MTA caused it or that STA will fix it.

The latest diagnostic tests that hypothesis: UIA remains on its MTA worker;
dry-run Shell collection and native view probing move together to a dedicated,
message-pumped STA. Shell objects are created/used/released only there, before
CoUninitialize. Only plain diagnostic DTOs cross workers; no marshaled/raw COM
proxy is reused from MTA. Requests and shutdown waits are bounded; a timed-out
provider is not forcibly cancelled and a late response cannot satisfy a newer
request. Reference: Microsoft's
[STA requirements](https://learn.microsoft.com/en-us/windows/win32/com/single-threaded-apartments).
The hook and trusted-target policy are unchanged. This correction is implemented
and fake-tested on Linux; its Windows outcome remains pending.

The user also supplied zero hook drops, queue remainder zero and exit code 0 for
that one-click run. This is positive shutdown evidence for that session, not
native mapping success. The Python 3.15/comtypes FutureWarning is recorded as a
separate compatibility variable, not an established cause. New session records
include Python/comtypes versions and Shell/UIA apartment choices. If needed,
repeat the same one-click comparison in a separate Python 3.14 venv; do not
replace the existing environment or conflate runtime and apartment changes.

After updating the checkout, run one ordinary file click, then Ctrl+C:

```powershell
.\.venv\Scripts\python.exe -m filewheel.platforms.windows.diagnostics --enable --dry-run-mapping --output logs\g2-sta-1.jsonl
$LASTEXITCODE
```

Check `shell_apartment=STA`, `uia_apartment=MTA`; inspect whether
`get_active_view_hwnd` succeeds, the active-view HWND chain, any later stage/code,
and drop/exit/cleanup output. Keep resolved_path null. Continue the full table
only after native collection works. Do not rerun the superseded stage-only
command below for the new experiment.

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
are freed with CoTaskMemFree. UIA objects stay on MTA; dry-run Shell objects
stay on their dedicated message-pumped STA. The hook
is unchanged, passive and free of COM/UIA/filesystem work. Bindings/child-window
assumptions have one supplied Windows smoke sample; broader Windows acceptance
remains pending. If
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
| Unselected target | Select B, middle-click A; repeat reversed | Operator before/after selection; A candidate, never B substituted; native Mouse3 may select A |
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
All-selected snapshots alone do not demonstrate an unselected hover; use operator
pre-click selection notes. If Explorer natively changes selection, record it without suppressing the
button or programmatically selecting a file. Keep G2 pending and evaluate the
documented explicit-path fallback if the primary contract cannot be satisfied.
