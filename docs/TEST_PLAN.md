# Verification plan

## Linux-only (Codex on Kubuntu, can run unattended)
- Static imports of pure modules on Linux with no `win32*` dependency errors.
- Fake `MouseEvent` and fake resolver driving `InvocationController` through valid/None/timeout and reentrant events.
- Unit tests verify no conversion or radial wheel appears when resolver returns None; events are idempotent/debounced where needed.
- Mock geometry and state machine tests for category→format→cancel/back (later).
- Ruff/pytest (only when project dependencies and code exist). Never report passing tests when no tests were run.

## Real Windows 11, interactive, required for gate G2
Use `docs/EXPLORER_HIT_TEST.md` acceptance matrix and diagnostic logs. Explicitly record Windows version, display scale, Explorer view, which file was selected vs hovered, exact expected path vs observed path, pass/fail/rejection reason.

## Failure / resilience
- Null result for click outside Explorer or unsupported view.
- File deleted, moved or renamed between event and resolution; no stale path.
- UIA error `UIA_E_ELEMENTNOTAVAILABLE`; fail closed.
- Hook process killed/restarted; callback references not garbage collected; event listener terminates cleanly.
- Slow UIA, blocked COM, stale views; hook callback stays fast.
- No globals requiring an unlocked desktop during Linux tests.

## Windows evidence template
```
Date/build: 
Git commit:
Explorer view / display scaling:
Selected file:
Hovered file and pixel:
Expected absolute path:
Observed path / None:
Pass / Fail / Unverified:
Trace/log path (local; no private paths committed):
```
