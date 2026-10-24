# Status and Windows-validation queue

Updated: 2026-10-24
Current gate: G0-A complete; two supplied Windows diagnostic rounds reviewed.
G2 provisional mapping implemented / Linux replay-tested; Windows acceptance pending.

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
  53 tests passed, exit 0. Fake hovered vs
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
- `python3 -m compileall -q src tests`: exit 0 (syntax compilation only).
- `git diff --check`: exit 0.
- `python3 -m pytest --version`: exit 1, pytest is not installed.
- `python3 -m ruff --version`: exit 1, Ruff is not installed; no lint pass claimed.
- No Windows/Windows-MCP execution by Codex. User's supplied diagnostic sessions
  are reviewed above; G2 additions have only Linux fake/replay-test evidence.
  Changes for this task are uncommitted; no commit fabricated.

## Required Windows validation (keep until genuinely tested)
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
  is now implemented but not Windows-tested. Numeric IDs, selection, focus and
  names never establish identity alone. Desktop remains excluded; initial scope
  is fixed local drives, <=32 candidates, standard views, no reparse points.
- UIA/COM can block the worker; no hard timeout/process isolation exists. Hook
  remains separate; shutdown reports a worker exceeding its bounded wait.
- Foreground HWND/event age and post-collection checks reduce races but cannot
  reconstruct historical tab/layout state. Bounded candidate logs can truncate.
- Linux tests prove portable behavior/fake seams only, not native ABI or Explorer
  behavior. G2-F remains available if true hover cannot be proven.

## Next
See `docs/NEXT_TASK.md`: run/review G2 dry-run acceptance evidence. Linux work
must preserve the trusted-target barrier until the Windows gate is satisfied.
