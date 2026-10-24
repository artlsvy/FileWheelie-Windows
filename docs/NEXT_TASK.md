# Next bounded Codex task

**Task G2-D: test the Shell STA correction against the localized GetWindow failure.**

The staged Windows run completed service and active-view queries, then failed
GetWindow with 0x8001010D (input-synchronization call-context error). It recorded
zero drops/queue remainder and exit0. Separate Shell STA ownership/message pumping
is now implemented as a bounded correction experiment; UIA stays MTA. This does
not prove MTA was the cause. New apartment behavior has only Linux fake tests.
No native path/view association succeeds yet, trusted resolution remains None,
and selection independence remains unproven. See D-009 in DECISIONS.md.
Read `STATUS.md`, `G2_MAPPING.md` and D-008 in `DECISIONS.md`.

1. Run ONE ordinary file click using the updated command in `G2_MAPPING.md`
   (`logs/g2-sta-1.jsonl`). Check shell_apartment=STA/uia_apartment=MTA and
   Python/comtypes version metadata. Stop and inspect get_active_view_hwnd
   success or failure, returned HWND association, later stage/code/completed
   stages, console drops, process exit and cleanup errors.
   Do not rerun the full matrix until native collection works.
2. If it still fails, investigate the actual new stage/code. Treat the Python3.15
   compatibility warning as a separate variable; a separate Python3.14 venv can
   compare the identical checkout/command without replacing the existing venv.
   Do not guess service GUIDs/tabs, bypass native evidence or add retry loops.
   Any correction requires bounded tests/review; G2 remains pending.
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
