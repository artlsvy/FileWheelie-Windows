# Status and Windows-validation queue

Updated: 2026-10-24
Current gate: two-tab native evidence collected, blanket multi-entry guard rejected.
Unique-HWND tab disambiguation correction implemented; Windows retest and trusted
mapping gate remain pending.

## Implemented
- Inspected all project guidance/configuration; repository initially had no
  application source. Existing documents/configuration preserved apart from
  this checkpoint, next task, and a README diagnostic link.
- `src/filewheel/core/`: immutable typed MouseEvent/TargetResolution, resolver
  protocol and synchronous controller with cancellation, sequence deduplication,
  debounce, injected-event rejection and event/result correspondence checks.
- `src/filewheel/platforms/windows/`: guarded ctypes passive hook/message loop,
  bounded queue, COM MTA worker, UIA/Shell candidate collection, opt-in JSONL CLI.
  Mapping seam **always returns None**; candidate strings are not verified paths.
- One read-only researcher report; API evidence, commands and limitations in
  `docs/DIAGNOSTIC_POC.md`.
- Focused review found generated UIA point-type mismatch, swallowed logging
  errors, and unrelated UIA payload risk during a window race. Fixed all three
  with regression tests; reviewer rechecked with no remaining material findings.
- Next diagnostic experiment adds aggregate provenance rejection counts, capture
  summary and read-only UIA selection snapshots. Mapping remains always None.
  User's existing hook import and bare-return edits were preserved.
- G2 adds a portable provisional index assessor and optional Windows native
  Shell view/IShellItem probe via `--dry-run-mapping`. Default behavior preserved;
  candidate paths are diagnostic only, resolver still always returns None.
  Provenance, age, geometry, index/name contradictions, incomplete/truncated sets,
  unsupported objects, ambiguous tabs and native errors reject. No GUI/converters.

## First supplied Windows evidence (reviewed 2026-10-24)
- Source: user-pasted JSONL, not a Codex-run Windows session. Build 26200,
  window DPI 96, eight non-injected records. Successful positive Mouse3 capture
  and UIA/Shell collection are supported for that session.
- UIA identifies a.txt/b.txt with point-containing item bounds in six events;
  two reach Items View background. Shell lists a folder and two file candidates.
  Worker evidence collection: 26.069–56.942 ms, not hook latency.
- No errors in supplied records. Selected files, expected hovered files, exact
  view setting, unrelated-app trials, callback timing, drop count, revision and
  shutdown results were not supplied. No G1/G2 gate completion claimed.
- Full interpretation and missing evidence: `docs/WINDOWS_SESSION_001.md`.

## Second supplied Windows evidence (reviewed 2026-10-24)
- Source: pasted contents named `logs/windows-run-2.jsonl` (not present in local
  checkout), not a Codex-run session. Build 26200: summary has 14 received,
  11 Explorer records, three non-Explorer rejections and zero queue remainder.
- Nine file hits matched numeric UIA AutomationId to Folder.Items index,
  including AGENTS.md=9, pyproject.toml=10, README.md=11. Two hits were chrome.
  This supports observed index correlation and aggregate negative filtering,
  not a documented identity bridge. All nine selection snapshots were true.
- Active-tab correspondence unproven; every resolved path null by design. No
  operator before/after selection evidence or hook-drop/exit result supplied.
  G2 selection independence, lifecycle and path identity remain pending.
- Research, sanitized replay provenance, limitations and next acceptance protocol:
  `docs/G2_MAPPING.md`. Microsoft documents no AutomationId-to-Shell-index contract.

## Tests actually run
- Kubuntu Python 3.14.4: `PYTHONPATH=src python3 -m unittest discover -s tests/unit -v`:
  96 tests passed, exit 0. Fake hovered vs
  selected path, None/no stale fallback, cancellation/reentrant invalidation,
  deduplication/debounce, timeout rejection, import isolation/platform guard,
  unconditional mapping rejection, generated point-type seam, UIA process/window
  races and visible JSONL write failure are covered.
- New tests cover provenance rejection categories, no UIA/Shell/payload access
  for unrelated apps, and read-only true/false/unknown selection snapshots.
  Focused review found no material code defects; its protocol handoff gap was
  addressed in `docs/DIAGNOSTIC_POC.md`.
- G2 replay: sanitized projection of all 11 supplied event records produces
  nine provisional candidates, two non-file rejections, never trusted targets.
  Adversarial tests cover index/name conflicts, forged bounds, stale/future time,
  tabs, truncation, unsupported paths/objects, native contradictions/errors,
  incomplete validation and untrusted flags. Probe fakes cover HWND chain,
  changed view, file checks and allocated-name/PIDL cleanup; not native ABI proof.
- G2 reviewer found dry-run session-label startup failure and ignored native
  probe errors; both fixed with regression tests. Focused recheck found no
  remaining material defects and independently reproduced all 53 tests,
  compilation and whitespace checks with exit 0. Native ABI remains unverified.
- Dry-run resolver wiring is replay-tested: candidate reports remain separate
  from trusted returns, and a window race discards both raw and candidate payload.
- Native failure diagnostics now capture the exact internal API stage, completed
  stages, signed/hex HRESULT and known symbolic code without exception messages,
  errorinfo or traceback payload. Synthetic failures exercise service and later
  path errors; nested errors retain their original stage. This improves
  observability only; no root-cause fix or alternative API is claimed.
- Focused review of the failure-diagnostic changes found no material defects;
  reviewer independently reproduced 67 tests, compilation and whitespace checks
  with exit 0. The original COM error still requires the new Windows capture.
- `python3 -m compileall -q src tests`: exit 0 (syntax compilation only).
- `git diff --check`: exit 0.
- `python3 -m pytest --version`: exit 1, pytest is not installed.
- `python3 -m ruff --version`: exit 1, Ruff is not installed; no lint pass claimed.
- No Windows/Windows-MCP execution by Codex. User's supplied diagnostic sessions
  are reviewed above; G2 additions have only Linux fake/replay-test evidence.
  Changes for this task are uncommitted; no commit fabricated.

## Required Windows validation (keep until genuinely tested)
- `WINDOWS_VALIDATION_REQUIRED`: retest corrected unique-HWND tab association
  with g2-tabs-2.jsonl after syncing, then
  then continue the broader operator-annotated matrix in
  `G2_MAPPING.md` now that one native STA hit completed. Begin with A hovered/B
  selected in Details/icons; then ascending/descending sorts, hidden extensions,
  duplicate stems, tabs, Unicode and negative areas. Retain drop/exit checks.
- `WINDOWS_VALIDATION_REQUIRED`: run `--dry-run-mapping` per `docs/G2_MAPPING.md`;
  first validate new COM bindings and active view HWND association in one local
  Details hit, then operator-annotated selection/sort/views/hidden-extension/tab/
  duplicate-stem/Unicode/negative trials. Preserve hook drop and shutdown checks.
- `WINDOWS_VALIDATION_REQUIRED`: exact under-cursor path across Details/List/Icons,
  A hovered while B selected/focused, hidden extensions, duplicate stems, Unicode,
  tabs/two windows, scroll/reorder/grouping, DPI/negative monitor coordinates.
  Current diagnostic-only seam cannot pass trusted positive path acceptance tests.
- `WINDOWS_VALIDATION_REQUIRED`: rejection of background, chrome, navigation,
  folders, virtual/cloud/archive items, missing files and stale elements; elevated
  windows, Explorer restart, hook lifetime and slow/blocked provider behavior.
  Use full matrix and evidence template in `docs/EXPLORER_HIT_TEST.md`.

## Research and implementation blockers
- Point→Shell identity remains unproven. Native active view/IShellItem evidence
  failed at GetWindow with 0x8001010D on the original MTA worker, but succeeded
  in one supplied STA sample. GetItemPosition returned E_NOTIMPL, so independent
  Shell geometry is unavailable in that sample. Numeric IDs, selection, focus and
  names never establish identity alone. Desktop remains excluded; initial scope
  is fixed local drives, <=32 candidates, standard views, no reparse points.
- UIA/COM can block the worker; no hard timeout/process isolation exists. Hook
  remains separate; shutdown reports a worker exceeding its bounded wait.
- Foreground HWND/event age and post-collection checks reduce races but cannot
  reconstruct historical tab/layout state. Bounded candidate logs can truncate.
- Linux tests prove portable behavior/fake seams only, not native ABI or Explorer
  behavior. G2-F remains available if true hover cannot be proven.

## Next
See `docs/NEXT_TASK.md`: collect/review the broader G2 acceptance evidence. Linux work
must preserve the trusted-target barrier until the Windows gate is satisfied.

## Third supplied Windows evidence: first G2 dry run (reviewed 2026-10-24)
- Source: latest user-pasted JSONL, not a Codex-run session. Build 26200, DPI96:
  17 worker events, 17 Explorer records, 17 native_probe_error rejections,
  zero queue remainder. Mode startup, UIA/Shell collection and safe rejection
  worked. All UIA repeat snapshots were stable; every selected snapshot true.
- All 17 active-view reports contain only status=unproven/error_type=COMError.
  The original logger omitted HRESULT and API stage, so the cause is unknown.
  No native candidate/tab correspondence was established; all trusted paths null.
  Collection took 66.726–92.865 ms. No hook-drop output/exit code supplied.
- IDs continue matching Folder.Items indices, including a/b now at 2/3 after
  the fixtures folder appears. Downstream false mapping checks reflect early
  rejection, not independent evidence of bad geometry or truncated enumeration.
- The appended sanitized fixture is the previous run-2 projection, not additional
  successful evidence from this failing run. It is preserved as prior replay data.
- Research rechecked the service GUID and documented route; no supported concrete
  constant/route correction was found. Stage/HRESULT diagnostics are the next
  bounded step, not guessed fallback APIs. New diagnostics are Linux-tested only.

## Fourth supplied Windows evidence: staged one-click run
- Source: user-pasted JSONL and PowerShell console, reviewed 2026-10-24.
  Build26200/DPI96, one event, one safe native_probe_error, queue remainder zero,
  hook drops zero, exit code0. Normal shutdown is supported for this session.
- Service provider, top-level browser service, browser interface and active view
  queries completed. GetWindow failed at get_active_view_hwnd with -2147417843 /
  0x8001010D = RPC_E_CANTCALLOUT_ININPUTSYNCCALL. UIA snapshot stable, selected
  true; latency79.383ms. No native view association/file identity proved.
- Microsoft documents GetWindow as input-synchronized. This supports investigating
  COM call context, but does not prove MTA causality. D-009 moves dry-run Shell
  collection/probing to a dedicated message-pumped STA, keeping UIA on MTA and
  passing only copied JSON DTOs. Timeouts discard late results; no provider
  cancellation or unsafe COM proxy transfer. Default diagnostic route preserved.
- Session metadata now reports Python/comtypes versions and apartment choices.
  Python3.15/comtypes compatibility warning is a separate variable, not proven
  causal. No dependency/runtime replacement was performed.
- New apartment behavior is Linux fake-tested only; no Windows/Windows-MCP run
  by Codex. Trusted resolver output stays None; no UI/converters were added.
- Current checks: all81 Linux unittest tests pass, compileall and diff checks
  exit0; pytest/Ruff probes still exit1 (not installed). Worker fakes verify
  ownership/pumping, DTO-only boundaries, timeout/late-result handling, bounded
  shutdown, startup failure and release before COM uninitialization. Review found
  and fixed an opaque-result cleanup lifetime defect, then independently passed
  all81 tests/compile/whitespace checks with no remaining material findings.

## Fifth supplied Windows evidence: first Shell STA candidate
- Source: user-pasted `g2-sta-1.jsonl` and console, reviewed 2026-10-24. Build26200,
  DPI96, Python3.15.0/comtypes1.4.17, UIA MTA/Shell STA. One received/recorded event,
  no queue remainder, zero hook drops, exit0. No Windows execution by Codex.
- GetWindow and native collection completed. Sampled HWND chain matches the
  hovered tab/content; Folder.Items and IFolderView2.GetItem both give b.txt at
  index3. Regular/local/nonreparse checks and repeated snapshots pass. Collection
  110.607ms. This is narrow native smoke evidence, not G2 completion or a general
  proof of all tab/view behavior. Operator expected path/selection notes absent.
- GetItemPosition returned E_NOTIMPL/0x80004001; no independent Shell position
  is available. UIA bounds contain the point, selected snapshot true. The report
  correctly remains provisional/identity_correspondence_unproven and resolved
  path null. No selected-item targeting, programmatic selection or suppression.
- Same Python3.15 compatibility warning remains; its presence did not prevent
  this sample. No dependency/runtime change is justified by the supplied result.
- Added labeled sanitized projection `tests/fixtures/windows_sta_1_sanitized.json`
  and replay regressions for the provisional boundary even with native checks
  passing, optional position failure, changed selection and caller-provided
  verified flags. Current83 tests, compileall/diff checks exit0. No runtime code
  change this round; no path promotion or additional APIs implemented.
- Focused review found no material fixture/replay issues and independently
  reproduced all83 tests, compileall and diff checks with exit0. Corrected stale
  apartment wording in the mapping implementation documentation.

## Sixth supplied Windows evidence: annotated acceptance console
- Source: user-pasted g2-acceptance-1 console plus per-click notes, reviewed
  2026-10-24. Six provisional candidates in order: A, B, A, B, README, README.
  Click3 was A while B selected; click6 README while README unselected. Both
  reported the hovered candidate, supporting selection independence for these
  observed provisional trials. Previous selected item on click6 unspecified.
- User observed native Mouse3 selects/highlights the clicked file. This explains
  why later asynchronous UIA snapshots can all be selected=true. It is not
  evidence the diagnostic selects files: code has no selection mutation call.
  Do not require the old selection to remain unchanged under passive Mouse3;
  record native selection effects separately from target correctness.
- Zero hook drops and exit0 reported. Full six-event JSONL, actual view/sort/
  extension settings and native per-event checks were not supplied. Do not infer
  those from console lines or mark G2 verified. Request/review the existing log
  before repeating these trials. Broader sorting, hidden extensions, duplicate
  stems, tabs, Unicode and negative-area coverage remains pending.
- Documentation-only checkpoint; no runtime code, trust policy or fixtures changed.
  Last code checks remain83 passing Linux tests; only git diff --check rerun,
  exit0. No new Windows execution by Codex.

## Sixth run follow-up: full acceptance JSONL and view settings supplied
- User confirms Medium icons for events1–4, Details for events5–6. Native view
  modes are1 and4 respectively. Full six-event log now supplied and reviewed;
  this resolves the missing-log/view limitations in the preceding checkpoint.
- All six events pass computed UIA containment/ancestry, freshness, complete
  candidate set, sampled active-view HWND association, both Shell path/index
  agreement, regular/local/nonreparse and snapshot checks. Latency72.965–94.449ms;
  six received/written, queue0. Prior console reports drops0/exit0.
- Operator notes establish A while B previously selected in Medium icons
  (event3), and README previously unselected in Details (event6). These narrow
  provisional cases are observed on Windows; they do not prove universal index
  identity. Native Mouse3 selection explains all async snapshots being true.
- Every GetItemPosition call reports E_NOTIMPL. No independent Shell geometry
  or multiple-tab/sort/hidden-extension behavior proved. All trusted paths null;
  no trust policy change. Next bounded Windows comparison is Name descending
  in Medium icons and Details, explicitly matching each expected path.
- Documentation-only evidence update; runtime/tests unchanged. Whitespace check
  exit0; no new native or Linux test execution claimed.

## Seventh supplied Windows run: descending-sort comparison
- User reports following the exact four-click pattern: Medium icons then Details,
  Name descending, alternating A while B selected and B while A selected.
  Supplied console and full JSONL report A/B/A/B correctly. Four received/written,
  queue0, drops0; process exit code not supplied for this run.
- All four native consistency sets pass, including sampled HWND association,
  matching paths/indices from both Shell sources and stable file/UIA snapshots.
  Latency73.105–95.414ms. GetItemPosition remains E_NOTIMPL throughout.
- Medium-icon records use A=2/B=3 with enumeration fixtures/unit/A/B. Details
  records use A=1/B=0 with enumeration B/A/unit/fixtures. UIA IDs and native
  GetItem agree with each new enumeration. This is observed index reassignment
  with correct provisional paths, not stable identity across samples. Never
  cache index-to-path mappings across view/sort changes.
- Operator reports descending for both views; the first two records do not
  independently establish reversed icon order, and sort columns are not logged.
  Preserve the evidence as supplied without inventing sort metadata. General
  index correspondence is still undocumented; no trusted targets emitted.
- Next: alternate four clicks across two tabs in the SAME Explorer window
  (tests/A, parent/README, tests/B, parent/AGENTS), using left-click tab switches.
  No fixture creation or runtime change needed. Hidden extensions/duplicate
  stems/Unicode and negative cases remain queued.
- Documentation-only checkpoint. Last code tests remain83 passed; whitespace
  check rerun exit0. No new Windows execution by Codex or new Linux tests claimed.

## Eighth supplied Windows run: two tabs, both Details
- User confirms exact alternating A/README/B/AGENTS pattern, Details in both tabs.
  Four events safely rejected as ambiguous_shell_windows, no candidate/trusted
  path emitted. Summary4 received/written, queue0, drops0, exit0. Latency
  106.962–136.163ms. UIA repeat snapshots stable; optional positions E_NOTIMPL.
- Each event has two same-frame registrations. Exactly one native association
  matches the hovered tab/browser, view and content HWNDs; inactive browser/view
  HWNDs are different. Correct native paths are present on the matched entry.
  Original core rejected all multiple registrations without examining this data.
- D-010 corrects the portable assessor using unique native HWND relationships
  and positive exclusion of all peers. Unknown/errored/duplicate/contradictory or
  truncated evidence still rejects; selected native-file checks remain mandatory.
  No filename/selection/order fallback or native API change. Diagnostic candidates
  remain provisional and the resolver continues returning None.
- Added labeled sanitized four-capture projection and adversarial replay tests.
  New policy is Linux-tested only; old Windows captures do not verify the changed
  live assessment. Retest same sequence after syncing per G2_MAPPING.md.
- Current96 Linux tests pass; compileall and whitespace checks exit0. Four
  captured records replay to the expected provisional paths and selected entry
  indices1/0/1/0. Negatives cover entry-order changes, duplicate/zero matches,
  malformed/errored/truncated peers, conflicting handles, wrong-frame/missing
  view, same-name cross-tab native conflict, stale/missing native and forged
  selection/verified flags. Reviewer independently reproduced all96 checks and
  found no material defects. No Windows/Windows-MCP run by Codex.
