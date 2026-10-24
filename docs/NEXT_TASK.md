# Next bounded Codex task

**Task G2-E4: retest unique native tab disambiguation on Windows.**

The supplied two-tab/Details run safely rejected all four captures because the
frame has two Shell registrations. Each record nevertheless has exactly one
native HWND chain matching the hovered tab, and a positively different inactive
browser/view. Core now uses that unique relationship, then all existing native
candidate checks. Unknown/errored/duplicate/missing relationships still reject.
New policy is Linux-replay-tested only. Trusted resolution stays None; D-010
describes the boundary. GetItemPosition remains E_NOTIMPL.
Current96 Linux tests pass, including four-capture tab replay and adversarial
registration tests. Independent review/compile/whitespace checks pass.
Read `STATUS.md`, `G2_MAPPING.md` and D-008 in `DECISIONS.md`.

1. Sync and repeat the four-click same-window/two-tab comparison in G2_MAPPING.md
   with NEW logs/g2-tabs-2.jsonl. Tabs show tests and repository parent respectively.
   Alternate tests/A, parent/README, tests/B, parent/AGENTS. Switch tabs with
   left click; never send Mouse3 to tab headers. Record expected paths, views,
   tab switches, drops and exit code. Inspect shell_window_count and chosen
   selected_shell_window_index plus raw HWND chains. Safe rejection beats wrong tab.
2. After reviewing this comparison, cover the remaining cases: explicit ascending
   sort baseline if still unrecorded, hidden extensions,
   duplicate stems, same filename in different tab folders if needed, Unicode, empty space
   and Explorer chrome. Keep trusted resolution disabled and native Mouse3 passive.
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
