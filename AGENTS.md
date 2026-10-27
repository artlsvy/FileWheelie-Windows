# Filewheel — repository instructions

## Objective
Build a **private, local-first Windows 11 file-conversion utility**. The primary UX is **middle-click on a file in Windows Explorer → cursor-centered radial menu → output category → concrete format → convert**. No accounts, cloud services, telemetry, monetization, or distribution infrastructure.

## Current milestone / source of truth
Read docs/STATUS.md and docs/NEXT_TASK.md first. Current task: clean docs/README,
remove the portable EXE from main, push and publish installer-only releasev0.2.
Push and release publication are explicitly authorized. Do not reread obsolete
docs before removing them. Task state: docs/plans/release-v0.2.md. No tests or
interactive automation while user needs the PC; build/static checks are allowed.

Preserve the accepted Quick/OpenGL glass UI, durable progress and cancellation.
Mouse3 provenance remains experimental: all provenance/freshness/path checks and
injected input consent remain mandatory. Physical/touchpad routes are now on by
default; only their shared Enable wheel switch belongs in the normal tray menu.
No trusted-hover promotion. Keep Send to.
Only the installer and its records belong in releases; the EXE uses Git LFS.

## Development environment
- Filewheel targets Windows 11 amd64 only. Codex now runs directly on Windows.
- Use Windows CPython 3.14 and PowerShell; .venv-build314 is the build environment.
- Do not maintain Unix host branches, shell wrappers or Unix-only test jobs.
- Keep pure logic tests and fakes, but distinguish them from native Windows checks.
- ZIP/EPUB paths use forward slashes by format specification, not Unix support.
- Historical Linux measurements are retained as evidence, not current setup advice.
- Validate packaged UI, child processes, cancellation and tools on native Windows.

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
- Available conversions come from the registry in source. Do not add formats or
  advertise unsupported pairs while preparing a release.
- Do not overwrite source files or silently overwrite output; no network uploads; conversion work outside UI thread; check real output validity.
- For private use, do not over-engineer redistribution/licensing, but obey applicable licenses and isolate optional dependencies.

## Agent operation / cost
- Main agent is coordinator and integrator. Researcher investigates uncertain Windows/COM/API questions **without editing**; implementer codes only bounded tasks; reviewer reports defects **without editing**.
- Spawn agents only when parallel, independent work is beneficial. Limit concurrent editors to one per file. Subagents increase aggregate token use in many cases; prefer concise evidence reports.
- For each bounded task: state acceptance criteria, implement/tests, run available checks, document what was actually tested, review only material changes.
- When unattended, do not ask questions if a documented reversible default suffices; do not falsely claim tests, Windows runs, or MCP connectivity occurred.

## Persistence / resume discipline
- Before ending a task update `docs/STATUS.md` with evidence, blockers, test results, and next steps; update `docs/NEXT_TASK.md` so resumed Codex has a single actionable next job.
- Keep unverified Windows acceptance tasks listed while independent work continues. Never conflate `implemented`, `mock-tested`, and `Windows-verified`.
- Avoid unbounded refactors, speculative feature expansion, and repetitive documentation rewrites.
- Do not modify the user's unrelated files. Do not run destructive or privileged system commands without explicit reason and scope.

## Definition of done
- Deterministic unit tests cover changed pure logic.
- No false claims about runtime. Source paths are verified; ambiguity fails closed.
- Windows-target behaviors are tested in Windows 11 on representative Explorer views before calling them verified.
- Status, decisions and next task accurately reflect reality.
