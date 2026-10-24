# Next bounded Codex task

**Task G2-E5: validate hidden names, Unicode and non-file rejection.**

The corrected g2-tabs-2 Windows run reports all four expected provisional paths,
with chosen registrations1/0/1/0 and passing native/tab/file/snapshot checks.
Drops0/queue0/exit0, both Details; no need to repeat that sequence. Narrow tab
routing is observed; general G2 is pending. Trusted resolution stays None;
GetItemPosition remains E_NOTIMPL. No runtime change is needed for the next batch.
Current96 Linux tests pass, including four-capture tab replay and adversarial
registration tests. Independent review/compile/whitespace checks pass.
Read `STATUS.md`, `G2_MAPPING.md` and D-008 in `DECISIONS.md`.

1. Use the isolated temporary-fixture setup and seven-click protocol at the top
   of G2_MAPPING.md with logs/g2-names-1.jsonl. The user runs setup locally;
   do not create/overwrite their repository files. Details, Name ascending,
   hidden filename extensions, record actual visible duplicate labels.
2. Review plain/Unicode candidates, both report-stem cases, folder/background/
   chrome rejection. Duplicate display labels must never be guessed; if UIA
   exposes full distinct names, record the stronger provider data. Preserve
   native path/tab and snapshot checks. Keep Mouse3 passive and trusted paths null.
3. Review each operator expectation against provisional paths, native HWND chain,
   both Shell sources and snapshot checks. Operator pre-click selection notes
   matter: native Mouse3 can select the clicked file before the UIA snapshot.
   Missing position evidence cannot prove Shell geometry.
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
