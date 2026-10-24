# Next bounded Codex task

**Task G2-B: validate the provisional index mapper in a Windows dry run.**

Two supplied Windows diagnostic runs support Mouse3 capture, UIA/Shell collection
and aggregate non-Explorer filtering. Run 2 has nine AutomationId/index matches,
but all selected-state snapshots are true and active-tab correspondence is
unproven. The G2 provisional assessor/native Shell view probe is implemented,
with 53 Linux tests passing. New COM bindings have not run on Windows.
Read `STATUS.md`, `G2_MAPPING.md` and D-008 in `DECISIONS.md`.

1. On interactive Win11 run the new `--dry-run-mapping` invocation in
   `G2_MAPPING.md` against a small ordinary local folder. First inspect a single
   Details hit for startup/binding failures, native view HWND chain and indexed
   IShellItem evidence. Unsupported associations must reject; don't guess a tab.
2. If collection works, execute the acceptance table: A hovered/B selected,
   Details/icons, ascending/descending sorts, hidden extensions, duplicate stems,
   multiple tabs, Unicode, empty pane and chrome. Record independent expected
   paths and selection before/after, build/revision/view/DPI, latency, console
   drop count, capture summary and exit code. Keep all trusted resolved paths null.
3. Compare UIA index, Folder.Items candidate, native GetItem path/index and
   repeated samples. A wrong provisional path is a failed trial. All-selected
   snapshots alone cannot prove the selection-independent user contract.
4. Address only observed diagnostic defects with bounded changes/tests/review.
   Update status and next task with the evidence actually supplied. Do not promote
   the index hypothesis to trusted routing without documented Windows acceptance
   and a justified independent identity correspondence. No GUI/converters.

Acceptance: reproducible native dry-run evidence either establishes the narrow
correspondence or identifies a concrete failure to investigate. Preserve G2 as
Windows-unverified unless its complete core matrix is genuinely satisfied.

## Independent Linux work if Windows evidence is unavailable

Do not block on an offline tower or Windows-MCP. The deferred G0-B task remains
available: extract a minimal portable diagnostic record/schema validator and
test cross-stage summary accounting, bounded payloads and malformed native
records. Avoid speculative new native APIs and preserve the candidate/trusted
boundary. Existing replay tests are not Windows verification. Run available
checks, request focused review and report actual results.

`WINDOWS_VALIDATION_REQUIRED`: retain the full matrix in `EXPLORER_HIT_TEST.md`.
Exact path emission eventually needs proven active-view/tab provenance, visual
point/bounds-to-Shell-item correspondence, filesystem identity/existence/type and
race rejection, independently of selection, names and enumeration order. If this
cannot be demonstrated, document G2-F explicit Shell path invocation fallback.
