# Next bounded Codex task

**Task G2-E: collect and review operator-annotated mapping acceptance evidence.**

The supplied g2-sta-1 run completes native collection: b.txt/index3 matches both
Shell sources, active-view HWND chain and file/snapshot checks pass. It reports
110.607ms, zero drops/queue remainder and exit0 on Python3.15.0/comtypes1.4.17.
GetItemPosition returned E_NOTIMPL; independent Shell geometry remains absent.
Selection snapshot true, operator expectations absent. Candidate stays provisional;
trusted resolution remains None. Narrow smoke is observed; G2 is not complete.
Current83 Linux tests pass, including a sanitized projection of the supplied run.
Read `STATUS.md`, `G2_MAPPING.md` and D-008 in `DECISIONS.md`.

1. Execute the G2_MAPPING.md acceptance table using a new log such as
   logs/g2-acceptance-1.jsonl, with the same checkout/environment. Start with A
   hovered/B selected in Details and icons. Number the clicks and manually record
   expected full hovered path, selected file before/after, view/sort/tab settings.
2. Cover the remaining cases: ascending/descending sorts, hidden extensions,
   duplicate stems, two tabs with different/same filenames, Unicode, empty space
   and Explorer chrome. Keep trusted resolution disabled and native Mouse3 passive.
3. Review each operator expectation against provisional paths, native HWND chain,
   both Shell sources and snapshot checks. Selection snapshots alone cannot prove
   selection independence. Missing position evidence cannot prove Shell geometry.
   Record failures/exclusions; don't fix them by assuming index identity.
   Retain build/revision/view/DPI, latency, console drop count, capture summary
   and exit code. A wrong provisional path is a failed trial even though trusted
   resolved_path stays null. All-selected snapshots cannot prove independence.
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
