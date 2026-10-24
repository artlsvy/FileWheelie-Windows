# Next bounded Codex task

**Task G2-C: localize the native Shell COM failure, then fix its observed cause.**

The first G2 Windows dry run started and collected 17 records, but all native
probes failed with COMError; no stage/HRESULT was logged, so the cause is unknown.
The returned fixture is prior run-2 replay data, not a successful native run.
Stage/HRESULT failure diagnostics are now implemented, with 67 Linux tests passing;
these new diagnostics have not run on Windows. The API route is unchanged and
trusted resolution remains None. All observed selected snapshots remain true.
Read `STATUS.md`, `G2_MAPPING.md` and D-008 in `DECISIONS.md`.

1. Run ONE Details-view file click using the updated command in `G2_MAPPING.md`
   (`logs/g2-probe-stage-1.jsonl`). Stop and inspect active_view_association.stage,
   hresult_hex/name and completed_stages, plus console drops/exit status.
   Do not rerun the full matrix until native collection works.
2. Use that actual failure code/stage to research and implement only the bounded
   correction. Do not guess a different service GUID, infer a tab from its title,
   or bypass native validation using the index/name correlation. Add regression
   tests and independent review; keep G2 Windows acceptance pending.
3. Once native collection works, execute the acceptance table: A hovered/B selected,
   Details/icons, ascending/descending sorts, hidden extensions, duplicate stems,
   multiple tabs, Unicode, empty pane and chrome. Record independent expected
   paths and selection before/after, build/revision/view/DPI, latency, console
   drop count, capture summary and exit code. Keep all trusted resolved paths null.
   Compare UIA index, Folder.Items candidate, native GetItem path/index and
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
