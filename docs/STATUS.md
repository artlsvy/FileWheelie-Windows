# Status and Windows-validation queue

Updated: 2026-10-24
Current gate: G0 → G1/G2 (first research/prototype). No Windows tests claimed.

## Implemented
- Codex project instructions, roadmap, initial contracts, and QA plan included in starter kit.
- No functional application code included in this documentation package.

## Tests actually run
- Starter TOML syntax parsed in artifact validation (package assembly only).
- No Windows Explorer hit-test, GUI, converter, or runtime test executed.

## Required Windows validation (keep until genuinely tested)
- `WINDOWS_VALIDATION_REQUIRED`: Win11 Explorer Mouse3 event and exact under-cursor path resolution across Details/Icons and wrong-selection tests.
- `WINDOWS_VALIDATION_REQUIRED`: native hook lifecycle, foreground-window filtering, UIA/Shell mapping and DPI behavior.

## Research and implementation blockers
- Point→Shell item mapping remains a research hypothesis, not a demonstrated reliable implementation.
- Windows tower is not available during Kubuntu overnight execution; no live UI assertions then.

## Next
See `docs/NEXT_TASK.md`. Update this document after each bounded task with commit, changed modules, tests run with exit codes, and honest unverified statuses. Keep entries concise, don't overwrite unresolved issues.
