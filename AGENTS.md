# Filewheel — repository instructions

## Objective
Build a **private, local-first Windows 11 file-conversion utility**. The primary UX is **middle-click on a file in Windows Explorer → cursor-centered radial menu → output category → concrete format → convert**. No accounts, cloud services, telemetry, monetization, or distribution infrastructure.

## Current milestone / source of truth
Latest user update: large-folder Mouse3 is user-reported Windows-verified. Direct
experimental wheel activation without per-file confirmation is now authorized
(D-016). Keep all evidence/freshness/path checks and experimental provenance;
never promote this route to trusted hover identity. Per-file confirmation is an
optional tray preference. Current UI task: compact 170px forest/ivory/brass wheel and grouped-folder support,
larger labels, small Esc/Back center and circular conversion feedback.

Read `docs/STATUS.md` and `docs/NEXT_TASK.md` first, then `docs/ROADMAP.md`, `docs/DECISIONS.md`, and task-specific specifications. **CURRENT PRIORITY (user update 2026-10-25): G9–G12 authorized sequentially: rendering/backend diagnostics, unified Python3.14, opt-in Mouse3 candidate confirmation/tray runtime, Windows onedir packaging and portable LibreOffice integration. Preserve trusted-target boundaries and Send to.** D-011 selects the fallback while Mouse3 remains desired but experimental. Preserve all Mouse3 code; expand diagnostics only for a specific blocking issue. Complete the authorized G9–G12 milestones; preserve diagnostics and record native verification limits. Keep Windows fallback/UI validation queued honestly; do not block independent Linux GUI work on an offline host.

## Development environment
- Codex runs on Kubuntu over SSH, including when the Windows 11 tower is off at night.
- Target environment is Windows 11 Explorer with an interactive desktop.
- On Linux, implement platform-independent interfaces, fakes, pure tests, contracts, logging, and Windows code behind guards. **Linux tests cannot prove Windows integration**.
- Windows-MCP is optional and ONLY available when the Windows machine is awake, unlocked, the server and SSH tunnel are running, and the MCP connection has been explicitly enabled.
- Never block Linux progress awaiting an offline Windows host. Move to independently testable subtasks; log a `WINDOWS_VALIDATION_REQUIRED` item in `docs/STATUS.md`.
- Never mark a Windows-dependent milestone verified based on mocks or Linux tests alone.

## Immediate architecture
- Python3.14 (>=3.14,<3.15). Windows API adapter isolated from Qt UI and future converters.
- Propose and test `WindowsMouseSource` (fast `WH_MOUSE_LL` callback → queue), `ExplorerTargetResolver` (point → validated item/path or None), and `InvocationController` (routing and deduplication).
- The hook callback must return quickly, avoid COM/UIA/filesystem calls, retain callback references and maintain a message loop. Do not suppress the middle click during the first proof-of-concept.
- Verify Explorer provenance, file-item control, bounding rectangle and item identity. **Do not substitute Explorer's selected or focused item for the item under the pointer**.
- Treat UIA element name as untrusted/ambiguous (hidden extensions, localization, duplicates); require verified Shell item identity or unambiguous evidence before emitting a path. Prefer no result over a wrong file.
- Diagnose and record limitations of Explorer views, tabs, scaling, virtual folders and elevated windows.
- Keep an invocation fallback whose Shell context passes an explicit path (`Send to` or context-menu command), and use it if true hover targeting cannot meet acceptance criteria.

## Future design constraints
- Qt/PySide6 frameless, translucent, DPI-aware radial wheel. Stage 1: valid output category; stage 2: valid extension; center=Back; Escape/outside=Cancel. Position within monitor work area.
- Formats displayed depend on validated conversion registry capabilities, never invented pairs.
- Later converters: PDF→editable DOCX (Word COM if locally available, pdf2docx alternative), DOCX/PDF/PPTX/XLSX/HTML→MD (MarkItDown Python API), DOCX→PDF (LibreOffice/Word), standard image conversions (Pillow, PyMuPDF, pillow-heif); MD→DOCX using Pandoc is P1. See `docs/CONVERSION_MATRIX.md`.
- Do not overwrite source files or silently overwrite output; no network uploads; conversion work outside UI thread; check real output validity.
- For private use, do not over-engineer redistribution/licensing, but obey applicable licenses and isolate optional dependencies.

## Agent operation / cost
- Main agent is coordinator and integrator. Researcher investigates uncertain Windows/COM/API questions **without editing**; implementer codes only bounded tasks; reviewer reports defects **without editing**.
- Spawn agents only when parallel, independent work is beneficial. Limit concurrent editors to one per file. Subagents increase aggregate token use in many cases; prefer concise evidence reports.
- For each bounded task: state acceptance criteria, implement/tests, run available checks, document what was actually tested, review only material changes.
- When unattended, do not ask questions if a documented reversible default suffices; do not falsely claim tests, Windows runs, or MCP connectivity occurred.

## Persistence / resume discipline
- Before ending a task update `docs/STATUS.md` with evidence, blockers, test results, and next steps; update `docs/NEXT_TASK.md` so resumed Codex has a single actionable next job.
- Keep Windows-only validation tasks listed even if other Linux work continues. Never conflate `implemented`, `mock-tested`, and `Windows-verified`.
- Avoid unbounded refactors, speculative feature expansion, and repetitive documentation rewrites.
- Do not modify the user's unrelated files. Do not run destructive or privileged system commands without explicit reason and scope.

## Definition of done
- Deterministic unit tests cover changed pure logic.
- No false claims about runtime. Source paths are verified; ambiguity fails closed.
- Windows-target behaviors are tested in Windows 11 on representative Explorer views before calling them verified.
- Status, decisions and next task accurately reflect reality.
