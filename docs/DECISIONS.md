# Architecture decisions (ADRs)

## D-001 — Windows Explorer Mouse3 first (2026-10-24, active)
Primary interaction is middle-click a file under pointer. A traditional desktop converter UI is secondary. Technical feasibility of correct hover resolution gates later conversion work.

## D-002 — Development on Kubuntu; target Win11 (2026-10-24, active)
Codex + Unsnooze continue on Kubuntu without Windows tower. Build portable tests overnight; label Windows-only verification clearly and collect evidence separately on live machine. Do not require Windows-MCP online to start sessions.

## D-003 — Conservative file identity (2026-10-24, active)
Use Win32 mouse event + Windows UI Automation + Shell APIs as a research path, **not an assumed finished solution**. Fail closed on ambiguous pointer-to-Shell-item mapping. Explorer selection/focus must not stand in for pointer target. If not robust, use a Shell invocation that passes explicit path.

## D-004 — Python/PySide6 (2026-10-24, provisional)
Python 3.12+; isolated Windows adapter, PySide6 for the future radial overlay, converter adapters later. Revisit only with evidence; optional native helper C++/C# can be considered if Explorer item identification proves impossible from Python bindings.

## D-005 — MCP only for development (2026-10-24, active)
Windows-MCP is optional interactive QA, not part of runtime app. Its Windows host must be running/unlocked for input testing. Remote access only over loopback + SSH tunnel, not an unauthenticated public endpoint. No overnight dependency.

## D-006 — Personal use (2026-10-24, active)
No release/distribution business requirements. Prefer quality and existing libraries; license compliance still applies. Avoid cloud processing.

## D-007 — Converter priorities after UI gate (2026-10-24, active)
Early: PDF→DOCX; DOCX→PDF; DOCX/PDF/PPTX/XLSX/HTML→Markdown; common images. MD→DOCX is a follow-up via Pandoc. PDF→PPTX is **not** an MVP target just because it was an example.

## D-008 — Provisional index mapping is diagnostic only (2026-10-24, active)

Run 2 observed UIA AutomationId == Folder.Items enumeration index for nine
file hits, including indices 9–11. This is implementation-specific evidence,
not a documented API contract. All selected-state snapshots were true; selection
independence and active-tab correspondence were not demonstrated.

Implement the index hypothesis behind `--dry-run-mapping`, with a portable
assessor and optional IServiceProvider/IShellBrowser/active IShellView/IFolderView2
probe. Native HWND containment, IShellItem filesystem path/attributes, regular
file checks and repeated samples corroborate or contradict the hypothesis.
Folder.Items and native view indices remain separate sources; disagreement
rejects. Hidden-extension ambiguity, truncation, stale evidence, unsupported
objects, tab ambiguity and native errors fail closed.

A provisional candidate is not TargetResolution. The resolver continues returning
None, and there is no CLI switch to promote candidates to trusted paths. Even
matching native evidence remains provisional until the real Windows acceptance
matrix proves the point-to-item correspondence. Keep selection diagnostic-only,
never mutate Explorer or suppress Mouse3. Start with small fixed-drive folders
and standard views. See `G2_MAPPING.md` for primary API sources and protocol.

## D-009 — Isolate native Shell probing on STA (2026-10-24, provisional)

The staged Windows run localized 0x8001010D to IShellView's inherited GetWindow,
after successful service/active-view queries. Microsoft documents GetWindow as
input-synchronized and names this HRESULT RPC_E_CANTCALLOUT_ININPUTSYNCCALL.
This supports a call-context/apartment experiment, not a proven MTA root cause.

For dry-run mapping, create/use/release all Shell proxies on a dedicated STA
with a message pump. Keep UIA on MTA, exchange only JSON-compatible DTOs, and
bound request/shutdown waits. Never transfer raw COM interfaces between workers.
Default non-mapping diagnostics preserve their existing collector route.
Do not retry/bypass the error or change service GUIDs. Validate one click before
the broader matrix; trusted resolution stays disabled. See G2_MAPPING.md for
primary sources and the exact Windows comparison procedure.

The first supplied STA sample completed native collection on build26200 with
Python3.15.0/comtypes1.4.17. Retain STA ownership. This is narrow smoke evidence;
GetItemPosition returned E_NOTIMPL and pointer-to-item identity remains unproven.
Do not promote the index hypothesis based on this single matched candidate.

## Pending experiments
- Descending-comparison captures show indices reassigned (A2/B3 to A1/B0) with
  correct candidates and matching native indices. Index-to-path associations
  must be fresh per invocation, never cached across view/sort changes.
- Annotated console trials support hovered candidates for A while B selected
  and for unselected README. Native Mouse3 selects the item before async UIA;
  use operator pre-click notes, not snapshot selection, as acceptance ground truth.
  Review full JSONL and extend sorting/view/tab tests before changing D-008.
- Which Windows 11 Explorer views provide stable point-to-Shell-item mapping?
- Native middle-click suppression after overlay opens vs passive processing?
- Explorer right-click/`Send to` fallback ergonomics and multi-selection behavior?
