# Status and Windows-validation queue

Updated: 2026-10-25
Current checkpoint: authorized G5/G6-A/B/C/G7/G8 implemented and Linux-tested.
Real conversion registry and background radial UI are integrated; default240px.
User-verified Windows scope: basic G2-F invocation and G4 launch/render. New engine,
worker/compositor/DPI acceptance remains pending. No Mouse3 investigation resumed.

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
  139 tests passed, exit 0 (latest G2-F checkpoint below). Fake hovered vs
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
- `WINDOWS_VALIDATION_REQUIRED`: explicit Shell-path delivery/validation once
  the G2-F diagnostic is implemented; no automatic Shell installation. Hover
  identity/DPI/race matrix stays pending for any future return to trusted hover.
- `WINDOWS_VALIDATION_REQUIRED`: inactive-prefix assessor correction is replay-
  tested only; validate live if that diagnostic policy is relied on later.
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

## Ninth supplied Windows run: corrected two-tab routing
- Source: user-pasted g2-tabs-2 console/full JSONL, same four-file protocol.
  Expected tests/A, root/README, tests/B, root/AGENTS all reported correctly as
  provisional. Four received/written, queue0, drops0 and exit0. Both native view
  modes4 (Details), Python3.15.0/comtypes1.4.17, UIA MTA/Shell STA, build26200/DPI96.
- Two registrations per event; chosen entry indices1/0/1/0. Matching tab/browser,
  view/content HWND chains and both Shell path/index sources agree throughout,
  including changed root view/content HWNDs. File, freshness and repeated UIA/
  native snapshot checks pass. Latency105.009–127.815ms.
- This is live evidence for corrected provisional routing in this two-tab case,
  not general G2 verification. No independent Shell position (E_NOTIMPL), all
  selected snapshots true, identity flags remain false and trusted paths null.
- Next bounded batch uses a fresh isolated temporary folder for hidden extensions,
  duplicate stems, Unicode, folders/background/chrome. No runtime code changes
  needed this round; no repeated tab test requested. Remaining larger matrix
  exclusions/race/DPI cases stay queued per EXPLORER_HIT_TEST.md.
- Documentation-only checkpoint: last code checks remain96 Linux tests passed;
  whitespace check exit0. No new Windows execution by Codex or Linux tests claimed.

## Tenth supplied Windows run: names and non-file areas
- Supplied g2-names-1 JSONL/console:8 received/written,4 provisional file paths,
  1 unsupported_shell_object (blankfolder),3 non_file_element rejections, queue0,
  drops0 and exit0. Details/viewmode4, same build/runtime/apartments as prior runs.
  File candidates plain.txt/unicodefile.txt/report.txt/report.pdf match both
  Shell sources and sampled tab HWND chain; freshness/file/snapshot checks pass.
  Collection66.678–128.443ms. All trusted paths null; positions still E_NOTIMPL.
- Non-file evidence: event6 Items View background, event7 command-bar/input-site
  chrome, event8 search TextBox ancestry. User reports blank space clicked twice;
  retain that note alongside the actual provider classifications. All reject
  correctly; do not repeat completed negative-area trials merely for count7.
- unicodefile.txt is entirely ASCII: its name does not exercise non-ASCII path
  handling. UIA names report.txt/report.pdf are distinct and include extensions.
  Same-stem files were distinguished correctly, but visual hidden-extension
  settings were not confirmed and ambiguous UIA labels were not exercised.
  Do not count these as Unicode or ambiguous-name Windows verification.
- Setup differs from proposed fixture: files were created in repository root,
  not a fresh temporary folder. No automatic cleanup, deletion or modification
  of these user-created files. Next three-click batch uses a new GUID temp
  directory and constructs non-ASCII characters by codepoint to avoid typing
  ambiguity; user confirms visual labels/extension-toggle state.
- No runtime changes justified by this evidence. Documentation-only checkpoint;
  last code tests remain96 passing, diff check exit0. No new Windows execution
  by Codex or Linux tests claimed.

## Eleventh supplied Windows run: actual Unicode and hidden duplicate labels
- Source: user-pasted g2-names-2 JSONL/console, reviewed 2026-10-25. Three events:
  unicode-æøå UIA stem yields exact unicode-æøå.txt Shell candidate (provisional);
  both UIA report labels reject as ambiguous_display_name despite native indexed
  paths being available. Three same-frame registrations, unique matched entry0.
  All candidate freshness/tab/file/snapshot checks pass for the Unicode sample.
- Summary3 received/written,1 provisional+2 ambiguous rejections, queue0, drops0;
  process exit code not supplied this run. Collection122.096–152.508ms. All
  trusted paths null; GetItemPosition remains E_NOTIMPL. These close the actual
  Unicode/hidden-label gaps, not the overall G2 gate.
- Added sanitized three-record projection and replay tests preserving Unicode
  codepoints/extension and rejecting hidden duplicate stems even with native
  candidates. Research audit explains why empirical index equality still lacks
  an independent point-to-Shell identity bridge: G2_IDENTITY_REVIEW.md.
- Added bounded Native.window_class/GetClassNameW metadata for the validated
  view/content/browser HWNDs. UIA provider labels do not supply native classes.
  No list-view messages, selection, hook change or trust-policy promotion.
  New fields have not run on Windows. No repeat fixture-creation batch needed.
- Actual checks:104 Linux unittest tests pass, compileall/diff checks exit0;
  reviewer independently reproduced104 tests and checks, no material findings.
  Pytest/Ruff unavailable at last probes; no lint pass claimed. No Windows/MCP
  execution by Codex. Interrupted agent files were inspected and checks rerun.

## Twelfth supplied Windows run: native class probe
- Source: user-pasted g2-control-class-1 JSONL/console. One event/record, queue0,
  drops0, latency190.785ms; exit code not supplied. Selected tab is tests, hidden
  UIA label a, index1, correct native candidate tests/a.txt. Three registrations.
- Native classes observed: view=SHELLDLL_DefView, content=DirectUIHWND,
  browser=ShellTabWindowClass. No standard SysListView32 content was observed;
  do not apply its documented hit-test messages to this DirectUI HWND. This
  rules out that route for the sampled surface, not every possible hover method.
- ambiguous_shell_windows was caused by a distinct inactive tab with count51,
  capped32 candidates/truncated=true. Core previously demanded complete candidate
  lists even for tabs positively excluded by native browser/view HWNDs.
- Corrected only that diagnostic condition: positively excluded peers may carry
  the exact consistent min(count,32) prefix; matched tab still complete<=32.
  Unknown/error/contradictory/malformed peers and globally truncated registration
  lists still reject. Captured replay now produces provisional tests/a.txt from
  entry2, never a trusted path. New assessment is Windows-unverified.
- Added sanitized source projection; ALL unrelated filenames redacted, preserving
  counts/indices/type flags/classes/geometry/timing. Independent review found no
  material defects and reproduced111 tests, compileall and diff checks exit0.
  No Windows/Windows-MCP execution by Codex; no new native API or hook behavior.
- D-011 selects G2-F explicit Shell-path invocation as the next safe baseline.
  Hover stays research-only; fallback is not yet implemented/Windows-verified.
  No further equivalent click trials requested; no GUI/converters authorized yet.

## G2-F headless launcher and personal Send to integration
- User authorized explicit-path fallback now, with usable PySide6 radial GUI as
  the NEXT development priority. D-012 supersedes the earlier hover-only priority;
  existing Mouse3 implementation, diagnostics and strict trust barrier remain.
- Implemented portable explicit-path validation and InvocationController.handle_explicit.
  Exactly one ordinary absolute drive-letter file path is required; Unicode and
  spaces remain literal. Missing files, directories, reparse points, device/UNC
  paths, traversal, alternate streams and multiple arguments fail closed. No UIA,
  selected/focused-item lookup or file contents are used. Both invocation routes
  share TargetResolution; explicit source is shell_explicit.
- Added Windows explicit_path_diagnostics CLI: physical cursor capture, headless
  controller invocation, exclusive UTF-8 JSONL artifacts and meaningful exit codes.
  No UI or conversion yet. ASCII-safe console output preserves Unicode in logs.
- Added sendto stage/install/remove commands and packaged PowerShell shortcut
  helper. Stage writes a reviewable shortcut under logs/sendto-stage; install
  uses the current user's SendTo folder. Direct Python target receives appended
  file arguments, without a shell interpreting filenames. Existing differing
  shortcuts are refused; owned installs/removals are idempotent. New shortcuts
  save to a unique temporary name and move without replacement.
- Implementer supplied bounded validation/controller code and tests; focused
  reviewer found a Unicode console-encoding failure, fixed with regression test.
  Recheck found no outstanding material findings and reproduced 139 unit tests.
- Actual Kubuntu checks: 139 unittest tests pass; compileall and git diff --check
  pass. Built a wheel and verified the PowerShell helper is packaged. pytest,
  Ruff and PowerShell are unavailable here; no lint or PowerShell execution pass
  claimed. Tests cover Unicode, spaces/metacharacters, absent/directory/multiple
  paths, controller cancellation, exclusive logs, argument quoting/import isolation.
- WINDOWS_VALIDATION_REQUIRED: follow docs/SEND_TO.md for direct CLI, staged
  shortcut, personal installation, actual Explorer argument delivery and removal.
  Verify Unicode/spaces/metacharacters, invalid/multiple paths, cursor point and
  ownership refusal. Explorer multi-selection may invoke separate processes;
  record observed process/argument counts. No Windows/MCP run or live shortcut
  installation occurred here. Native acceptance remains pending, not completed
  by fakes or Linux tests.
- Next bounded job: docs/NEXT_TASK.md G4-A, optional PySide6 two-level radial UI,
  shared controller input, near-cursor placement, Escape/Back/outside dismissal,
  explicitly declared preview capabilities and no real conversion. Windows GUI
  placement/focus/DPI checks remain a separate native validation requirement.

## User Windows acceptance: basic G2-F single-file invocation
- WINDOWS-VERIFIED (narrow, user-reported): Windows11 build26200, Python3.15.0;
  direct CLI and subsequent Explorer Send to both accepted exactly one explicit
  absolute path C:\Users\lsvy\fileconverter\AGENTS.md, source=shell_explicit,
  argument_count=1, accepted=true, action=diagnostic_only, no rejection/error.
  Direct elapsed193.127ms; Send to artifact elapsed0.334ms. These are diagnostic
  timings, not UI startup measurements. Codex did not execute this Windows run.
- Do not repeat this basic smoke test without a regression. This does not verify
  Unicode, malformed/nonexistent paths, folders, multi-selection, shortcut
  removal or native cursor/DPI/GUI behavior. Those broader cases remain queued.

## G4-A implemented: radial GUI and launcher integration
- Optional PySide6 radial popup (~300 logical pixels; 324 including shadow):
  translucent frameless topmost popup, palette-based light/dark colors, filename
  center, animated hover, category→format, center/keyboard Back, Escape,
  transparent-corner/outside and focus-loss dismissal. One window also shows
  filename, original/destination formats and intended filename after selection.
- Pure injected preview capability registry and state machine have no Qt/file I/O.
  PREVIEW and dry-run confirmation distinguish them from absent conversion engines.
  Unknown suffixes show no choices; invalid indices/gaps perform no action.
  Intended paths are descriptive only; no allocation, conversion or source changes.
- Reusable RadialPopup.present(TargetResolution) and run_popup consume the shared
  controller result, regardless of source. None/invalid argv opens no UI. No hook,
  UIA, selected-file lookup, resolver trust change, IPC or background service.
- Existing explicit_path_diagnostics gains optional --gui after validation;
  headless options/JSONL behavior remain. GUI mode does not write diagnostic logs
  unless explicitly requested. Separate --mode gui shortcut uses pythonw.exe,
  avoiding a console window; diagnostic shortcut remains available. Mode-specific
  names/markers preserve full ownership checks and atomic no-replacement save.
- Qt coordinates stay isolated: native MonitorFromPoint/GetMonitorInfoW identify
  physical monitor/device; matching QScreen origin + relative DPR gives logical
  point, clamped to availableGeometry. Negative-origin/scaled mapping is fake-
  tested; real Windows mixed-DPI/display changes/activation remain unverified.
- Implementer built UI/pure tests; researcher checked official PyPI/Qt metadata:
  PySide6 6.12 introduces Python3.15 support; 6.10.1 introduced3.14. ui extra uses
  PySide6>=6.12,<7. Downloaded and ran6.12.0 on Kubuntu Python3.14.4; Windows3.15
  compatibility is published support, not a locally executed Qt runtime test.
- WINDOWS_VALIDATION_REQUIRED: GUI-mode staging/install/Explorer launch; actual
  category/format interactions, focus/activation/outside click, Escape/Back/Done,
  clean exit, negative monitors,100/150/200% mixed DPI and light/dark palette.
  Broader G2-F Unicode/invalid/multi-selection/remove ownership remains pending.
  See docs/SEND_TO.md; basic headless test need not be repeated.

- Final G4 checks: full suite165 tests pass with PySide6 6.12.0, including10
  actual Qt offscreen tests; system Python without the optional dependency runs
  the same165 with10 Qt tests skipped. compileall and git diff --check pass.
  Built a wheel and verified UI modules, native monitor adapter, PowerShell helper
  and optional dependency metadata are included. Screenshots of category, format
  and confirmation were rendered and visually inspected. Qt offscreen reports
  unsupported raise/keyboard-grab operations; native behavior is not established.
- Reviewer reproduced165 passing tests and checks. Fixed its two findings:
  any-button outside dismissal (inner actions still left-only) and completion of
  invalid/failed popup replacements so event-loop waiters cannot remain blocked.
  Three added regressions pass; focused recheck has no remaining material findings.
  No PowerShell or Windows GUI execution by Codex. No converter added.

## Windows G4 startup failure: accepted path, desktop failure
- User supplied direct --gui console: build/runtime context Python3.15.0,
  path C:\Users\lsvy\fileconverter\AGENTS.md, argument_count1, accepted=true,
  source=shell_explicit, action=radial_preview, elapsed0.341ms, point[362,888].
  Then GUI desktop initialization failed. Acceptance describes path validation,
  NOT popup success. No native GUI success is claimed. Cause remains unknown:
  previous catch combined RuntimeError/OSError without reporting failing stage.
- Separate supplied diagnostic_only record has argument_count0 and safely rejects
  expected_one_path (elapsed0.025ms). It is not the failed one-argument GUI launch;
  its exact launch method was not supplied. Do not infer selected-file loss.
- GUI stage/install both report Already configured. This narrowly supports
  idempotent matching-owned-link detection, not GUI shortcut execution/removal.
- Added DesktopInitializationError and ASCII-safe gui_startup_error stderr JSON.
  Stages identify native monitor lookup/info, native-device-to-QScreen matching,
  DPR scaling, logical screen selection, positioning, application creation and
  popup display. Details contain desktop geometry/names/numeric error codes,
  never input paths or arbitrary exception messages. No guessed monitor fallback,
  new Mouse3 diagnostic, dependency replacement or native mapping change.
- Actual checks:169 tests pass with Qt offscreen; compileall and whitespace checks
  pass. New regression tests cover error stages/metadata/CLI reporting, plus
  preserved failed-replacement completion. WINDOWS_VALIDATION_REQUIRED: sync and
  rerun the same direct GUI command once; capture gui_startup_error JSON. No
  shortcut reinstall or repeat basic headless Send to diagnostic is needed.
- Focused reviewer independently reproduced169 tests/compilation/whitespace checks;
  no material findings. Root cause and Windows GUI success remain unverified.

## Windows G4 cause identified: native device ID differs from Qt display name
- User supplied gui_startup_error stage=match_qt_screen: physical_point[444,706],
  native_device=\\.\DISPLAY1, qt_screen_names=[MAG 244F], monitor_rect[0,0,1920,1080].
  Explicit AGENTS.md validation accepted (0.293ms); GUI exit5. This identifies the
  name-equality assumption as the failing step; no Qt screen geometry was supplied
  and no popup success is implied.
- Corrected association: require exactly one QScreen whose origin equals the
  physical monitor origin and whose logical width/height times valid DPR match
  physical dimensions within rounding tolerance. Names are desktop diagnostics
  only; no index/primary/single-screen shortcut. Zero or duplicate matches reject.
  Relative-origin scaling stays; rounded points are clamped inside the verified
  screen to prevent right/bottom edge rounding from leaving Qt screen bounds.
  Work-area placement stays unchanged.
- Qt's official high-DPI model documents Windows screen positions staying native
  while sizes scale (https://doc.qt.io/qt-6/highdpi.html). QScreen.name is not used
  as a Win32 device-ID contract. No selected-file lookup or Mouse3 expansion.
- WINDOWS_VALIDATION_REQUIRED: sync and retry the same direct --gui command once.
  No shortcut reinstall needed. If popup opens, check Back/Escape/confirmation,
  then actual GUI Send to; if not, retain new stage and screen-geometry metadata.
  Mixed-DPI/negative-monitor and native focus/cleanup acceptance remain queued.
- Actual Kubuntu checks:176 unit tests pass including Qt offscreen; compileall and
  git diff --check pass. New fakes cover friendly-name matching with explicitly
  supplied Qt geometry (not present in the Windows log), screen order changes,
  contradictory/mirrored geometry, invalid DPR, fractional rounding and scaled
  negative-origin edge pixels. No new Windows runtime execution by Codex.
- Independent reviewer reproduced176 passing tests/compile/whitespace checks;
  edge-rounding finding fixed and rechecked with no remaining material issues.

## Overnight authorization / fresh checkout audit
- Resumed at HEAD1a4a525 with clean tree; no existing G5 converters were present.
  Preserve intervening commits and all Mouse3/diagnostic code. User reports G4
  successfully launched/rendered on Windows; no expanded DPI/focus claim follows.
- Authorized sequential G5, G6-A/B/C, G7, G8 without further confirmation or waiting
  for Windows. Separate commits per milestone when safe; no pushes requested.

## G5 — PNG → JPEG implemented
- Pillow engine handles RGB/RGBA/grayscale PNG; alpha composites onto white,
  quality90, output decoded/validated as JPEG. Source is unchanged. Same-directory
  staging and atomic hardlink publication never replace existing output; collisions
  get numbered names. Unsupported hardlink filesystems fail safely. Cancel/failure
  cleans temporary/new artifacts; multi-output protocol is ready for PDF pages.
- Available-engine registry now feeds the actual Send to GUI: installed working
  pairs only, no speculative preview edges in live launch. Existing preview API
  remains for tests. QThread worker supplies progress and result/error; dismissed
  work is cancelled cooperatively and resources survive until the worker finishes.
- Actual Linux checks: initial192 pytest tests pass (197 subtests), including real
  PNG/JPEG and Qt-worker integration. Reviewer identified two failure windows:
  publication metadata lookup after hardlink, and synchronous selected subscribers
  closing before worker ownership. Both fixed with regressions; final counts below.
- Windows G5 conversion/NTFS publication/worker dismissal remains unverified.
  Continue directly to G6-A PDF→DOCX; user explicitly authorizes provisional progress.
- G5 review recheck:202 full-suite tests pass (includes8 independently prepared
  G6-A engine tests); compileall/whitespace pass. Scoped new G5 code/tests Ruff
  checks pass. No remaining material review findings; no Windows run claimed.

## G6-A — editable PDF → DOCX implemented
- Registered optional pdf2docx backend; normal text PDFs reconstruct editable Word
  text and basic table structure. Decoded DOCX archive/text validation precedes safe
  publication. Corrupt/encrypted/empty/image-only PDFs fail with explicit errors;
  scanned text needs OCR (not implemented). Mixed image-only pages carry warnings.
- Real generated PDF fixtures and DOCX readback cover editable text/table, scans,
  corrupt/encrypted input, cleanup, cancellation and100page/50MiB limits. No Word
  installation required. No OCR, network or external services used.
- PyMuPDF1.28.2/pdf2docx0.5.13 tested on Python3.14; constrain PyMuPDF<2 to avoid
  unrelated new2.0 ML/layout dependencies. pdf2docx is unmaintained upstream; output
  fidelity is best effort, and cancellation is cooperative around its inline call.
  PyMuPDF licensing remains AGPL/commercial; this private local workflow uses its
  documented package, no redistribution infrastructure is added. Word COM deferred.
- Actual focused tests:9 real/fake engine tests pass; scoped Ruff checks pass.
  Windows PDF→DOCX remains pending. Continue directly to G6-B MarkItDown.
- G6-A final suite203 tests pass (197 subtests),9 focused tests independently
  reproduced by reviewer; no material findings. Compilation/whitespace pass.

## G6-B — local MarkItDown Python API implemented
- DOCX/PDF/PPTX/XLSX/HTML→UTF-8 MD, actual document fixtures validate useful
  headings/lists/tables/text and Unicode. Built-ins/plugins are disabled and only
  the selected local document converter is registered; convert_local is called
  directly with a network-denying requests session. No CLI, LLM or cloud adapter.
- ORT_DISABLE_TELEMETRY=1 set at package bootstrap before optional dependency
  imports; disable_telemetry_events also called. Lossy extraction/OCR limitations
  are reported; scanned PDFs and corrupt documents fail without published output.
- MarkItDown0.1.9 officially supports Python>=3.10,<3.15. Per-format availability
  hides missing dependencies, and all its pairs are hidden on3.15. The markdown
  extra uses a Python<3.15 marker; use a Python3.14 environment for these features.
  Do not force-install an unsupported release on the target's3.15 runtime.
- Actual checks:8 focused fixture tests +5 subtests passed before review; full
  suite215 passed including prepared G6-C tests. Review found a missingpdfplumber
  availability guard; added guard and regression. Native Windows MD conversion
  and Python3.14 environment setup remain queued. Continue directly G6-C.
- G6-B regression fixed;9 focused tests +5 subtests and scoped Ruff pass.

## G6-C — LibreOffice DOCX → PDF implemented
- Optional engine detection (PATH/Windows ProgramFiles, prefer soffice.com for
  Windows command-line use), isolated per-run profile/private input/output, fixed
  argument list with no shell,90second default deadline, validated readable PDF.
  Expanded archives/macros/external resource relationships reject before rendering.
  Collision-safe shared publication preserves source/existing files.
- Timeout kills the owned process tree (POSIX process group; Windows taskkill/T),
  then bounded cleanup. No unrelated Office process/profile is targeted. Worker
  cancellation is checked around the renderer call, not immediate interruption.
- Actual LibreOffice fixture renders editable DOCX text/table to readable PDF,
  preserving source and collision sentinel. Initial sandbox run failed dconf
  readonly runtime storage; rerun outside that sandbox passed. Additional tests
  cover missing engine, corrupt DOCX, safe argv/profile/timeout and a real dummy
  wrapper/descendant timeout. Reviewer rechecked process-tree fix; no material
  findings. Windows binary/process-tree behavior remains pending.
- Continue directly to G7 image/PDF expansion; no Word automation required.

## G7 — image and PDF expansion implemented
- Real PNG↔JPEG/WebP and JPEG↔WebP, JPEG input aliases, optional HEIC/HEIF→JPEG/PNG,
  supported images→single-page PDF, all PDF pages→PNG/JPEG at144DPI. JPEG/PDF
  transparency flattens white; PNG/losslessWebP preserve alpha. EXIF orientation
  is applied. Animated/multi-image inputs reject rather than silently losing frames.
- Available codec/engine registry gates JPEG/zlib/WebP/HEVC decode dependencies.
  PDF raster outputs use numbered-page names and shared atomic collision-safe
  publication. Limits bound image bytes/pixels and PDF pages/bytes/pixels. Sources
  unchanged; partial-page failure/cancellation never publishes partial batches.
- Actual fixtures exercise HEIC encoder+decoder installed here, all image pairs,
  alpha/grayscale, multipage PDF dimensions/readability, collisions and cleanup.
  Reviewer found missingJPEG/zlib gates; fixed with regression, also gated PDF
  page validation and HEVC-specific decode support.27 focused engine/core tests
  +15 subtests pass, scoped Ruff passes. Previous full suite229 +209 subtests
  passed before the added codec guard test. No native Windows G7 run claimed.
- Continue directly to G8 configurable240px wheel, transparency and feedback.

## G8 — compact transparent UI and complete integration
- Default240px internally configurable220–324, with a single scaled reference
  layout for painting/hit regions. Minimum8pt labels, full filename/path/warning
  tooltips, progress percentage/bar and success/error/cancel results. Outputs
  include all PDF pages and actual collision-safe paths in GUI/console metadata.
- Transparent Source clear each frame, no autofill/system background and no native
  rectangular OS drop shadow; alpha corners verified across stage changes. Only
  the existing painted circular shadow remains. Real Windows compositor boundary
  fix is not claimed verified. Live registry displays real capabilities only.
- Conversion outcome is recorded even when dismissed during work; no false dry-run
  action after real work. CLI reports radial_menu intent, full outputs and exit6
  on failure. Headless diagnostics remain metadata-only and import-isolated.
- Actual final suite238 tests +211 subtests pass, including real codecs/HEIC,
  PDF text/table/rasters,5 Markdown input types, LibreOffice render/child timeout,
  Qt background lifecycle and smaller-size/transparency tests. Reviewer independently
  reproduced238/211; no material remaining findings. Scoped production/new-test
  Ruff checks pass, compileall and whitespace checks pass. No skipped/failing
  tests in the fully provisioned run. Restricted desktop sandbox LO failure was
  documented and resolved by approved test execution outside that sandbox.
- Screenshots rendered/inspected for live categories/formats and real JPEG success
  at240px. Published WindowsPython3.15 amd64 wheels/dependency resolution succeeds
  for Pillow13, PyMuPDF1.28.2, pdf2docx0.5.13, pillow-heif1.8.1, Qt6.12 and dependencies;
  this is resolver evidence, not a Windows run. MarkItDown0.1.9 remains3.14-only.
- UI extra uses PySide6-Essentials (all usedCore/Gui/Widgets/Test modules belong to
  it), avoiding unusedWebEngine/Addons. Existing fullPySide6 installations work.
- WINDOWS_VALIDATION_REQUIRED: actual conversion outputs, collision/source hashes,
  errors/cancel cleanup/exit, LibreOffice binary/process tree, supported3.14 MD
  environment,240px transparent boundary/focus/negative mixed-DPI. Basic G4 render
  success does not verify these new behaviors. CONVERTERS.md has exact smoke steps.
- Final packaging audit built a wheel containing all engines/UI/native adapter,
  PowerShell helper and Python-version optional-extra markers. QtEssentials-only
  isolated installation passed10 popup +7 polish tests using systemPython3.14;
  this confirms unusedAddons/WebEngine packages are unnecessary. Full suite remains
 238passed/211subtests. Final scopedRuff, compileall, git diff --check pass.
- Completed milestone commits:4f6d556 G5;8601f65 G6-A;666c0f4 G6-B;7ff785e G6-C;
 36098aa G7; G8 checkpoint commit follows. No force-push/discard/unrelated changes.
  All authorized milestones are now implemented and checked as far as this host
  permits. Word COM/OCR/media and broader product work were not implemented.

## G9–G12 authorization and Windows evidence update
- Starting clean HEAD1e21084. User confirms G5–G8 radial UI launches on Windows
  and implemented format choices are visible. No conversion-output correctness,
  transparency/compositor, packaging or Mouse3 identity success is inferred.
- Send to's current launch-time cursor is the final menu click, not original file
  position; do not reconstruct the file-row point. Mouse3 uses its actual event
  point. G10 permits only opt-in explicitly confirmed provisional candidates.
- G9-A: correcting duplicated sector outlines; logging engine/operation/actual
  exception locally and distinguishing missing dependencies. PDF→DOCX is pdf2docx;
  LibreOffice is only DOCX→PDF, never assumed to repair pdf2docx errors.

## G9-A — rendering and backend failure diagnostics
- Continuous annulus fill with no stroked sector polygons; each separator/inner/
  outer border drawn once. Shared separator geometry drives hit testing.240px,
  transparent source clear and OS shadow suppression preserved. Offscreen spies/
  pixel checks cover1/2/3sectors and alpha corners; Windows compositor retest pending.
- Conversion errors identify selected engine, operation, dependency-vs-failure kind
  and rotating local debug log. Full actual exception chain is written locally;
  no console/cloud required. Windows log is LOCALAPPDATA/Filewheel/logs/
  conversion-debug.log; FILEWHEEL_LOG_DIR overrides for testing. Logs contain local
  paths/tracebacks and rotate2MB×4. Log failures never replace conversion errors.
- PDF→DOCX selects pdf2docx, while DOCX→PDF selects LibreOffice; tests assert backend
  identity. No supplied Windows converter traceback yet, so no unsupported claim
  that installing LibreOffice fixes PDF→DOCX. Progress also names the engine.
- Full suite246tests/220subtests passed; focused reviewer found wrapped-dependency
  classification and log-path failure masking, both fixed with regressions. Final
  focused9tests/9subtests pass; no native rendering or conversion success inferred.

## G9-B — one Python3.14 runtime
- Project requires>=3.14,<3.15; .python-version and setup-windows.ps1 create/check
  .venv-filewheel without replacing existing environments. Pinned desktop extra
  includesQtEssentials/Pillow/PyMuPDF/pdf2docx/MarkItDown/heif and Windowscomtypes.
  Normal usage no longer splits Markdown into a separate runtime. Old shortcut
  removal remains importable; GUI on3.15 returns actionable runtime error/code7.
- Windows3.14 amd64 wheel/dependency resolution succeeded for the complete engine
  set,comtypes1.4.17 and PyInstaller6.22.3. Linux3.14 engines remain fixture-tested.
  This is metadata/resolver evidence, not a Windows native DLL/runtime test.
- Runtime/setup tests10passed/5subtests with GUI boundary tests. Docs now use one
  .venv-filewheel and explain safe old-shortcut migration. Native3.14 setup still
  WINDOWS_VALIDATION_REQUIRED; proceed to G10 without waiting.

## G10 — opt-in tray Mouse3 and candidate confirmation
- Added source entry `python -m filewheel --tray`, passive existing hook/source,
  existing UIA MTA + Shell STA evidence and shared controller. Experiment off by
  default; explicit --experimental-mouse3 or tray checkbox enables for this run.
  No program is suppressed and no COM/UIA runs inside hook callback.
- ExperimentalCandidate is separate from TargetResolution. Factory reruns the
  existing assessor with known stable snapshots, all fresh HWND/tab/index/path/
  filesystem native checks; conflicts/ambiguity reject. Trusted resolver remains
  unmodified and alwaysNone. The proposed full path is shown with Cancel default;
  only explicit Use this file +one-shot30s current token +freshpathvalidation
  creates source=user_confirmed_candidate. It never claims explorer_hover identity.
  OriginalMouse3 physical point anchors the menu after confirmation. Send to still
  uses launch-time cursor and cannot infer original file location.
- Existing COM implicit import/atexit ownership corrected for this process: main
  STA bootstraps comtypes, worker explicitly owns balanced MTA ref; all actualUIA/
  Shell calls stay offQtmain. Readiness waits run in an owned Qt startup worker,
  not the event loop. Disable/Quit invalidates gates and waits for threads/jobs;
  stopped-worker cleanup warnings are logged without hangingQuit. A genuinely
  blocked provider is not forcibly killed; live shutdown remains unverified.
- Optional HKCU startup registration explicit --startup install/remove, ownership-
  checked and disabledbydefault; command starts tray with experiment off. No
  registration occurs automatically. Fakes verify normal/foreign entry behavior.
- Focused core/runtime/Qtconsent tests28passed/6subtests (including real Qt consent
  ordering, supersession, no pre-confirm validation, async heartbeat, COMownerfake
  and deadworkerQuit). Full suite result recorded next. Native hook/COM/tray/
  startup/focus/point behavior WINDOWS_VALIDATION_REQUIRED; no trust promotion.

## G11 — reproducible onedir recipe and frozen integration
- Added Windows CPython3.14amd64-only windowed onedir spec, early freeze_support,
 54-package wheel/hash lock, isolated non-destructive build venv/script, dependency/
  source manifests and bounded frozen self-test. Collections include QtEssentials
  plugins, native engines, dynamically imported converters, Magika/ONNX resources,
  metadata/licenses and PSshortcut helper. Unused WebEngine/Addons not required.
- Frozen startup/self-test errors use private logs with no console requirement.
  Self-test creates only temporary fixtures and actually exercises all current
  engine families; source execution passed here with a positive JSON report.
- Added current-user QLockFile + UserAccess QLocalServer/Socket bounded JSON route.
  Repeated GUI launches forward to one owner; busy rejects, no candidate/experiment
  commands accepted over IPC. Only exclusive lock owner removes a stale endpoint.
  Separate-process forwarding tests passed; an earlier same-process QThread test
  stalled because blocking Qt socket waits prevented the Python server from
  running, so acceptance now uses real separate clients like deployed invocation.
- Packaged Send to targets Filewheel.exe --gui directly (never.exe -mPython),
  source uses the main app for same routing. Old known source arguments can be
  removed with strict target/root/marker ownership; arbitrary links are protected.
  Startup remains opt-in and does not enableMouse3 bydefault.
- Static/portable packaging tests, lock dependency-marker audit and source smoke
  checks pass. NO Windows EXE was built/run on Kubuntu. Native build, clean-machine
  plugins/DLLs, repeated launch/tray/Sendto/startup and WindowsIPC remain pending.
  Proceed G12fullportableLibreOffice seams; noWindowscrosscompileclaim.
- G11 integration checks:12 packaging/IPC/frozen-plan tests +7 malformed-reply
  subtests pass; full suite307/234 passed before added reply/late-hook regressions.
  Source --self-test reports all real engine fixtures successful. Build/self-test
  deadlines and bidirectional portable-source/output containment guards checked.
  Native EXE build/clean-machine operation remains unverified.


## User acceptance update — G9-A/B

The user reports testing G9-A/B successfully on the Windows 11 target. Record
rendering fixes and the unified runtime work as WINDOWS-VERIFIED by user report.
This does not establish G10 tray/hook acceptance or a G11/G12 packaged build.

## G10 tray completion follow-up

The tray checkbox starts Mouse3 asynchronously and is disabled while startup or
shutdown is pending. Disabling invalidates candidate consent immediately, shows
“stopping”, then restores the off state when listener threads exit. Runtime
failure clears the active tooltip. Confirmation requests topmost/foreground
presentation with Cancel as default. An unavailable system tray rejects tray
startup rather than leaving an invisible owner. Nine Qt consent/lifecycle tests
pass on Linux; native tray, COM, focus and hook behavior remain pending.
