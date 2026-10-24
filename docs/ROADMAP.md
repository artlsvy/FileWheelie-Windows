# Roadmap — ordered by risk, not appearance

States: `NOT STARTED` · `IMPLEMENTED/UNVERIFIED` · `MOCK-TESTED` · `WINDOWS-VERIFIED` · `BLOCKED`.

| Gate | Goal and deliverable | Exit criteria / prerequisite |
| --- | --- | --- |
| **G0** | Repo, interfaces, offline tests and diagnostic schema | Codex loads project rules; Linux tests pass; diagnostic records are reproducible |
| **G1** | Hook POC on Windows 11 | Mouse3 events captured, minimal callback, no unrelated-app interference; real Windows evidence |
| **G2** | Exact file-under-cursor resolver — experimental/deprioritized | Preserve implementation and evidence; expand only for a specific blocking issue; no trusted path promotion |
| **G2-F** | Explicit-path launcher + personal Send to — IMPLEMENTED/MOCK-TESTED | Real Win11 shortcut/path delivery still pending; see SEND_TO.md |
| G3 | Shared invocation/controller — IMPLEMENTED/MOCK-TESTED | Hover and explicit paths produce the same source-aware TargetResolution; cancellation/validation tests pass |
| **G4 NEXT** | Usable PySide6 two-stage radial prototype | Near cursor, compatible category→format choices, Escape/Back/outside cancel, shared controller; no conversion |
| G5 | Conversion registry + first smoke converter | Stubbed registry then image PNG→JPEG, background processing, tested output |
| G6 | Document/Markdown MVP | PDF→DOCX, DOCX→PDF, MarkItDown (DOCX/PDF/PPTX/XLSX/HTML→MD); capability tests |
| G7 | Remaining image MVP | HEIC/JPEG/PNG/WebP, images→PDF, PDF→raster; representative real files |
| G8 | UX reliability | Errors, progress, output collision policy, notifications, batch (optional) |
| G9 | Optional expansion | MD→DOCX, PPTX→PDF, XLSX→PDF, CSV↔XLSX; OCR/media deferred |

## Current focus
**User priority updated 2026-10-25:** headless G2-F launcher is implemented;
the NEXT development job is the usable PySide6 radial GUI (G4), using the shared
controller and explicit-path invocation. Mouse3 remains desired and experimental;
preserve it without further diagnostic expansion unless an actual blocker demands
it. No actual converters yet. A prototype preview registry may demonstrate tested
compatible category/format pairs, clearly marked as previews rather than claiming
installed conversion engines.

Windows Send to/cursor and GUI acceptance remain queued independently. Build and
test portable UI state/fixtures on Kubuntu; do not wait for an offline Windows
host or treat Linux checks as Windows verification. D-011's fallback decision
permits this GUI work; the strict hover trust gate remains unchanged.

## Definition of G2 success
- Middle-click on a **different unselected file** returns the hovered file, not the previous selection.
- Results are correct when file extensions are hidden, display names collide, and Explorer view changes.
- Returns **None** for background, navigation pane, folders (unless separately supported), UI chrome, ambiguous identities, non-filesystem virtual items and missing files.
- No unintended activation elsewhere, no selection mutation, no blocking UIA calls in the hook, no corrupted Unicode paths.
- Verified live on the target Win11 system. Fakes do not count.

## Overnight rules
Codex on Kubuntu can always advance G0/G3 tests, diagnostics, mocks, docs, and implementation behind `sys.platform == 'win32'` guards. It cannot certify G1/G2/G4. When validation is pending, log it and work on independent testable units; never call a gate complete by inference.
