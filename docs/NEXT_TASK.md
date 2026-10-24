# Next bounded Codex task

**Task G1-B: run and review the controlled Windows diagnostic smoke experiment.**

G0-A is complete. The user supplied an eight-event Windows session: positive
Mouse3/UIA/Shell collection worked on build 26200, DPI 96. Negative filtering,
selection independence, native behavior and shutdown were not demonstrated.
Read `docs/STATUS.md`, `docs/WINDOWS_SESSION_001.md`, and `docs/DIAGNOSTIC_POC.md`.
The diagnostic now has aggregate rejection counts, a capture summary and
read-only selected-state snapshots. These additions are Linux fake-tested only
(23 tests pass); the mapping seam still always returns None.

1. On interactive Win11, execute the exact six-click protocol in
   `DIAGNOSTIC_POC.md`. No Windows-MCP dependency. Capture revision, view,
   selected/hovered expectations, selection afterward, JSONL summary, drop count
   and process exit code. Do not assert success if the host is unavailable.
2. Review observed counters against six planned clicks, four accepted Explorer
   events and two unrelated-process rejections. Require no unrelated text/path
   payload, no evidence errors, no hook drops and a clean shutdown.
3. Inspect the three expected unselected file-row snapshots and background case.
   A null selected-state value is unknown. Do not substitute selection or join
   UIA names to candidate paths. Record exactly what the evidence proves.
4. Update status and next task. Only after diagnostic smoke evidence is adequate,
   scope an identity experiment tying a specific Shell view/tab and IShellItem
   identity to the containing UIA item. Automation IDs resembling Shell indices
   in the first tiny folder are not proof. Do not implement that hypothesis yet.

Acceptance: a reproducible, operator-annotated smoke record verifies the above
or precisely documents failures. G2 remains unverified; no GUI or converters.

## Independent Linux work if Windows evidence is unavailable

G0-B remains deferred, not completed: extract portable diagnostic record schema
and synthetic replay tests for provenance races, bounded/truncated candidates,
missing bounds, duplicate display stems, malformed data and summary accounting.
Keep logging scope/dependencies unchanged and the mapping seam always None.
Use unittest on Kubuntu, request focused review and report actual results.

`WINDOWS_VALIDATION_REQUIRED`: retain the full matrix in `EXPLORER_HIT_TEST.md`.
Exact path emission eventually needs proven active-view/tab provenance, visual
point/bounds-to-Shell-item correspondence, filesystem identity/existence/type and
race rejection, independently of selection, names and enumeration order. If this
cannot be demonstrated, document G2-F explicit Shell path invocation fallback.
