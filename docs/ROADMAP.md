# Roadmap — ordered by risk, not appearance

States: `NOT STARTED` · `IMPLEMENTED/UNVERIFIED` · `MOCK-TESTED` · `WINDOWS-VERIFIED` · `BLOCKED`.

| Gate | Goal and deliverable | Exit criteria / prerequisite |
| --- | --- | --- |
| **G0** | Repo, interfaces, offline tests and diagnostic schema | Codex loads project rules; Linux tests pass; diagnostic records are reproducible |
| **G1** | Hook POC on Windows 11 | Mouse3 events captured, minimal callback, no unrelated-app interference; real Windows evidence |
| **G2** | **Exact file-under-cursor resolver** | `docs/EXPLORER_HIT_TEST.md` test matrix passes on Win11; selected file must not be substituted |
| **G2-F** | **Fallback decision if G2 fails** | Shell `Send to`/context menu passes exact path; document UX compromise; no guessing |
| G3 | Headless invocation/controller contract | Event → verified Path or None; debounce and cancellation tests; mocks on Linux |
| G4 | Two-stage radial UI | UI categories/format choices, cancel/back/edge/DPI; Windows validation of overlay |
| G5 | Conversion registry + first smoke converter | Stubbed registry then image PNG→JPEG, background processing, tested output |
| G6 | Document/Markdown MVP | PDF→DOCX, DOCX→PDF, MarkItDown (DOCX/PDF/PPTX/XLSX/HTML→MD); capability tests |
| G7 | Remaining image MVP | HEIC/JPEG/PNG/WebP, images→PDF, PDF→raster; representative real files |
| G8 | UX reliability | Errors, progress, output collision policy, notifications, batch (optional) |
| G9 | Optional expansion | MD→DOCX, PPTX→PDF, XLSX→PDF, CSV↔XLSX; OCR/media deferred |

## Current focus
**G0/G1/G2 only.** The primary risk is Explorer item identity. A pixel-perfect wheel atop an unreliable resolver is wasted work.

## Definition of G2 success
- Middle-click on a **different unselected file** returns the hovered file, not the previous selection.
- Results are correct when file extensions are hidden, display names collide, and Explorer view changes.
- Returns **None** for background, navigation pane, folders (unless separately supported), UI chrome, ambiguous identities, non-filesystem virtual items and missing files.
- No unintended activation elsewhere, no selection mutation, no blocking UIA calls in the hook, no corrupted Unicode paths.
- Verified live on the target Win11 system. Fakes do not count.

## Overnight rules
Codex on Kubuntu can always advance G0/G3 tests, diagnostics, mocks, docs, and implementation behind `sys.platform == 'win32'` guards. It cannot certify G1/G2/G4. When validation is pending, log it and work on independent testable units; never call a gate complete by inference.
