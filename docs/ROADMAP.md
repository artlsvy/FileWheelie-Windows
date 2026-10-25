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
| G6 | Document/Markdown MVP | PDF→DOCX, DOCX→PDF, MarkItDown (DOCX/PDF/PPTX/XLSX/HTML→MD); capability tests |
| G7 | Remaining image MVP | HEIC/JPEG/PNG/WebP, images→PDF, PDF→raster; representative real files |
| G8 | UX reliability | Errors, progress, output collision policy, notifications, batch (optional) |
| G9 | Optional expansion | MD→DOCX, PPTX→PDF, XLSX→PDF, CSV↔XLSX; OCR/media deferred |

## Current focus
**G4-A implemented 2026-10-25:** validated explicit paths can open a two-stage
PySide6 radial preview through the same TargetResolution boundary as future
trusted Mouse3. An injected preview registry supplies compatible choices; format
selection shows a dry-run confirmation and changes no files. GUI-mode Send to
has a separate owned shortcut, with stage/install/remove commands.

Basic headless direct CLI and Explorer Send to single-file delivery are
WINDOWS-VERIFIED from user evidence (build26200/Python3.15.0, AGENTS.md). This
narrow result does not verify GUI overlay/focus/DPI, Unicode/malformed paths,
multi-selection or removal. These remain independently queued in STATUS.md.
Do not repeat the completed basic diagnostic without a regression.

**Immediate G4 follow-up:** supplied direct GUI command validates the path but
failed screen matching because Qt reports a friendly name rather than the Win32
device ID. Unique monitor geometry/DPR association is implemented for the next
Windows retry; no native GUI success claimed.

**Following milestone: G5 PNG→JPEG conversion engine**, then PDF→DOCX and MarkItDown integration.
G4 native acceptance stays queued; Linux offscreen tests do not establish Windows
behavior. Mouse3 stays desired, preserved and experimental; no further mouse
research is part of this milestone.

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
