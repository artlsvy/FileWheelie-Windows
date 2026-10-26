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
| G10 | Large-folder Mouse3 — WINDOWS-VERIFIED by user report; direct activation polish underway | Keep experimental provenance; optional confirmation per D-016 |
| G11 | Reproducible Windows onedir packaging — IMPLEMENTED/STATIC-TESTED | Build scripts/spec; native build/acceptance pending |
| G12 | Portable LibreOffice integration — IMPLEMENTED/LINUX-TESTED; Windows bundle pending | Full bundle preferred; isolated profile/process deadline |

## Current focus

The user reports successful Windows operation of G9-A/B and the G10 large-folder
Mouse3 fix. D-016 now authorizes direct experimental wheel opening without the
repeated file-confirmation dialog. Controller validation, freshness, ambiguous
file rejection and experimental source provenance remain; optional confirmation
can be restored in the tray. The listener stays opt-in and Send to stays usable.

Compact UI polish is implemented: 170px wheel, larger labels, small Esc/Back
center, forest/ivory/brass themes and circular progress/results. Linux checks:
377 tests and 387 subtests pass; new direct-route/native visuals await Windows
acceptance. G11/G12 source build/bundle seams remain implemented, with native
packaging/portable-office checks queued separately. No push was performed.

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


Grouped Explorer date sections now use bounded exact-name/active-parent Shell
corroboration, with group-local UIA IDs excluded from flat index claims. The user
confirms grouped activation works; detailed latency/DPI coverage remains pending. See
NEXT_TASK.md; no selected-file fallback or full-directory scan was introduced.


The user confirms grouped-folder activation now works. Current UI follow-up keeps
170px conversion/results topmost and visible through outside activity, with short
status words and the existing progress ring. Details stay in tooltips/logs; native
Windows focus/z-order acceptance is the next check (D-018, NEXT_TASK.md).


Current follow-up (D-019): spawned converter isolation, throttled progress,
curved sector labels and subtle surface transparency are implemented. The user
reported cursor stalls; original-file Windows responsiveness remains unverified.
DOCX → PDF setup is documented in DOCX_TO_PDF.md. No new conversion formats or
mouse-mapping changes are introduced by this task.
