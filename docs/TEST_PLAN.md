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

## Implemented conversion/UI regression suite (G5–G8)

Run `QT_QPA_PLATFORM=offscreen PYTHONPATH=src .venv-ui/bin/python -m pytest -q`
with all extras installed onPython3.14.238 tests +211subtests passed at the overnight
checkpoint. Tests create real generated PNG/JPEG/WebP/HEIC/PDF/DOCX/PPTX/XLSX/HTML
fixtures and read outputs back. They cover alpha/size/hash preservation, collision
races, source identity changes, stage rollback, corrupt/encrypted/scanned documents,
engine availability, Markdownnetwork guard, child-process timeout, thread cleanup,
scaled geometry and transparent pixels. Optional missing packages are explicit
skips; a fully provisioned run reported none. LibreOffice needs usable runtime
storage even headless; sandbox failure must not be counted as an engine pass.

Native Windows follow-up is in CONVERTERS.md. Qt offscreen cannot verify DWM
transparency, native activation, real mixed-DPI monitors or Windows engine DLLs.
Wheel resolution for3.15 is compatibility metadata, not a native runtime test.
