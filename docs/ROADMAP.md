# Roadmap — ordered by risk, not appearance

States: `NOT STARTED` · `IMPLEMENTED/UNVERIFIED` · `MOCK-TESTED` · `WINDOWS-VERIFIED` · `BLOCKED`.

| Gate | Goal and deliverable | Exit criteria / prerequisite |
| --- | --- | --- |
| **G0** | Repo, interfaces, offline tests and diagnostic schema | Codex loads project rules; Linux tests pass; diagnostic records are reproducible |
| **G1** | Hook POC on Windows 11 | Mouse3 events captured, minimal callback, no unrelated-app interference; real Windows evidence |
| **G2** | Exact file-under-cursor resolver — experimental/deprioritized | Preserve implementation and evidence; expand only for a specific blocking issue; no trusted path promotion |
| **G2-F** | Explicit-path launcher + personal Send to — basic single-file WINDOWS-VERIFIED | Direct CLI and Send to on build26200/Python3.15.0; Unicode/negative/removal matrix still pending; see SEND_TO.md |
| G3 | Shared invocation/controller — IMPLEMENTED/MOCK-TESTED | Hover and explicit paths produce the same source-aware TargetResolution; cancellation/validation tests pass |
| **G4** | PySide6 radial — basic launch/render WINDOWS-VERIFIED; full DPI/focus pending | Near cursor, compatible category→format choices, Escape/Back/outside cancel, shared controller; no conversion |
| **G5** | PNG→JPEG IMPLEMENTED/LINUX-TESTED | Background execution, valid output, no source overwrite; then PDF→DOCX and MarkItDown |
| G6 | Document/Markdown — IMPLEMENTED/LINUX-TESTED (MD needs Python<3.15) | PDF→DOCX, DOCX→PDF, MarkItDown (DOCX/PDF/PPTX/XLSX/HTML→MD); capability tests |
| G7 | Image/PDF expansion — IMPLEMENTED/LINUX-TESTED | HEIC/JPEG/PNG/WebP, images→PDF, PDF→raster; representative real files |
| G8 |240px UI refinement — IMPLEMENTED/OFFSCREEN-TESTED | Errors, progress, output collision policy, notifications, batch (optional) |
| G9-A | Rendering + conversion diagnosis — IMPLEMENTED/LINUX-TESTED | Single separator strokes; engine/operation/traceback logs |
| G9-B | Unified Python3.14 — IMPLEMENTED/LINUX-TESTED | One supported runtime/all current converters |
| G10 | Opt-in Mouse3 candidate confirmation/tray — IMPLEMENTED/LINUX-TESTED | Never promote candidates without explicit confirmation |
| G11 | Reproducible Windows onedir packaging — IMPLEMENTED/STATIC-TESTED | Build scripts/spec; native build/acceptance pending |
| G12 | Portable LibreOffice integration | Full bundle preferred; isolated profile/process deadline |

## Current focus

Authorized overnight G5→G8 implementation is complete and Linux-tested:
PNG/JPEG/WebP/HEIC, images/PDF pages, PDF→editable DOCX, local MarkItDown extraction,
LibreOffice DOCX→PDF, and240px configurable transparent radial UI with real worker
progress/results/errors. Missing codecs/engines stay hidden. All source/diagnostic
infrastructure is preserved. Separate milestone commits are recorded in STATUS.md.

User reports basic G2-F and G4 launch/render work on Windows11. New converters,
worker cancellation,240px compositing, detailed focus/DPI and integration still
require target acceptance. MarkItDown0.1.9 is unsupported onPython3.15; use3.14 for
those pairs. Word COM/OCR/media remain unimplemented optional work, not blockers.

Next work is native acceptance and narrowly evidenced fixes, not another engine
expansion. CONVERTERS.md and SEND_TO.md contain exact commands; NEXT_TASK.md has
the resume handoff. No Windows success is inferred from Linux tests.

## Definition of G2 success
- Middle-click on a **different unselected file** returns the hovered file, not the previous selection.
- Results are correct when file extensions are hidden, display names collide, and Explorer view changes.
- Returns **None** for background, navigation pane, folders (unless separately supported), UI chrome, ambiguous identities, non-filesystem virtual items and missing files.
- No unintended activation elsewhere, no selection mutation, no blocking UIA calls in the hook, no corrupted Unicode paths.
- Verified live on the target Win11 system. Fakes do not count.

## Overnight rules
Codex on Kubuntu can always advance G0/G3 tests, diagnostics, mocks, docs, and implementation behind `sys.platform == 'win32'` guards. It cannot certify G1/G2/G4. When validation is pending, log it and work on independent testable units; never call a gate complete by inference.

Overnight checkpoint: G5 real converter and background GUI implemented; G6-A next.

G6-A: PDF→editable DOCX implemented/Linux fixture-tested; G6-B MarkItDown next.

G6-B: local MarkItDown pairs implemented/Linux-tested on3.14; unavailable on3.15. G6-C next.

G6-C: LibreOffice DOCX→PDF implemented/real Linux-tested; bounded process-tree timeout. G7 next.

G7 complete with codec-gated real image/PDF paths; G8 240px transparency/feedback next.
