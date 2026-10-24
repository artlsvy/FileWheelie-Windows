# Next bounded Codex task

**Task G0-A: platform seam and diagnostic contracts for Explorer hover resolution.**

1. Inspect existing repository source before creating or modifying files; preserve working code.
2. Research the best documented Win11 APIs for `mouse point → Explorer visual element → Shell item/path`; if using subagents, request ONE researcher report only; no speculative file edits by researcher.
3. Implement a minimal portable, typed `MouseEvent`, `TargetResolution` and `TargetResolver` protocol plus a small controller; use project existing layout if present, otherwise `src/filewheel/core/`.
4. Write Linux-run unit tests with fake resolvers validating correct hovered path returned, None handling, selected-file trap, cancellation/deduplication, no Win32 import on Linux. Don't pretend fakes prove real hit-testing.
5. Create a Windows-only diagnostic POC behind platform guards to log UIA element properties and Shell candidate evidence on Mouse3. Do not yet render UI or perform conversions. Isolate and document the uncertain mapping function; return None if not proven. Ensure hook's callback does zero COM/UIA work.
6. Run actual available Linux tests/linters and report exit codes; if a library is not installed, say so and do not claim success.
7. Request reviewer inspection for wrong-target and callback/COM risks, address critical findings.
8. Update `docs/STATUS.md` and `docs/NEXT_TASK.md` with the next independent Linux job and the Windows-only acceptance tests that must be run on the tower.

Do not ask for more input to complete this bounded task. Do not expand into GUI, conversion engines or remote Windows automation. If source architecture differs from the proposal, adapt rather than overwriting existing work.
