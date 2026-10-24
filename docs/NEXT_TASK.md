# Next bounded Codex task

**Task G0-B: portable diagnostic record schema and evidence replay checks.**

G0-A is implemented and fake-tested (19 unittest tests); Windows behavior is
unverified and the mapping function always returns None. Read `docs/STATUS.md`
and `docs/DIAGNOSTIC_POC.md` before changing code. Preserve the unresolved G1/G2
queue; no GUI, converters, speculative path mapping or remote automation.

1. Extract diagnostic record construction/validation into a minimal portable
   module. Keep schema version, explicit unknown/unproven values, bounded
   properties, candidate-vs-resolved distinction, provenance and rejection reasons
   clear. Do not expand logging scope or add dependencies.
2. Add synthetic fixture/replay tests on Linux: foreground/process change drops
   payload, bounds missing/outside click cannot support a target, candidate
   truncation is explicit, ambiguous duplicate stems/hidden extensions do not
   become paths, malformed records fail closed. Never treat replay as Windows
   proof. Keep `proven_target_from_evidence` always None during this task.
3. Adapt Windows diagnostics to the portable record builder without changing
   hook behavior or inventing Shell/UIA identity correspondence. Test via fakes;
   use standard-library unittest if pytest/Ruff are still unavailable.
4. Run available checks, request focused review for evidence/identity mistakes,
   and update status/next task with actual commands and exit codes.

Acceptance: deterministic schema/replay tests pass, unknown or ambiguous evidence
never emits a resolved path, native dependencies remain guarded, and no live
Windows success is claimed without actual evidence.

## Independent Windows-only queue (not a Linux blocker)

`WINDOWS_VALIDATION_REQUIRED`: run the opt-in diagnostic on the interactive
Windows 11 tower per `docs/DIAGNOSTIC_POC.md`. First prove passive hook capture,
UIA/Shell imports/evidence and clean shutdown in Details and icon views, with B
selected and A middle-clicked. Record build, DPI, selected file, hovered file,
expected path, actual None/rejection and local log reference. These are G1
diagnostic smoke runs, **not G2 success**.

After smoke evidence exists, investigate a separately bounded IFolderView2/Shell
identity/geometry experiment. Require demonstrable pointer-to-item correspondence
across the full `docs/EXPLORER_HIT_TEST.md` matrix before emitting paths or marking
G2 verified. If correspondence fails, document the G2-F explicit Shell path
invocation decision. Do not depend on Windows-MCP being online.
