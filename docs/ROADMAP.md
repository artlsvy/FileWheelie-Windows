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
| G9-A | Rendering + conversion diagnosis — WINDOWS-VERIFIED (user report) | Single separator strokes; engine/operation/traceback logs |
| G9-B | Unified Python3.14 — WINDOWS-VERIFIED (user report) | One supported runtime/all current converters |
| G10 | Opt-in Mouse3 candidate confirmation/tray — IMPLEMENTED/LINUX-TESTED | Never promote candidates without explicit confirmation |
| G11 | Reproducible Windows onedir packaging — IMPLEMENTED/STATIC-TESTED | Build scripts/spec; native build/acceptance pending |
| G12 | Portable LibreOffice integration — IMPLEMENTED/LINUX-TESTED; Windows bundle pending | Full bundle preferred; isolated profile/process deadline |

## Current focus

G5–G8 converters/UI remain implemented and Linux-tested. The user has now tested
G9-A/B successfully on Windows. G10 tray/candidate consent, G11 Windows onedir
recipe and G12 portable LibreOffice integration are implemented and checked as
far as Kubuntu permits. Final Linux suite: 312 tests and 241 subtests pass.

Next is Windows acceptance of the tray workflow, packaged build and complete
portable LibreOffice tree. These are not certified by Linux mocks/offscreen
checks. Send to stays available, and experimental Mouse3 is off by default.
See NEXT_TASK.md for exact steps. No unrelated conversion expansion is queued.

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
