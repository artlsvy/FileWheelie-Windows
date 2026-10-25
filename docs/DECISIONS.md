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

## D-010 — Disambiguate tab registrations by native HWND evidence (2026-10-24, provisional)

The supplied two-tab run shows two Shell registrations sharing one frame HWND.
For each click, exactly one sampled active-view chain matches the UIA content
and ShellTab HWND; the other registration has different browser/view HWNDs.
The old blanket multi-entry guard safely rejected all four but was too broad
for this observed case. Do not select registrations by path/name/index/order.

For a complete registration list, require exactly one matched chain whose
browser HWND equals the hovered tab HWND, view HWND equals its captured
DUIListView HWND, and content HWND equals its UIItemsView HWND. Every other
entry must have complete, non-errored native evidence positively excluding that tab/view.
Missing, contradictory, duplicate-match or truncated evidence rejects. The chosen
entry still needs all existing index/path/native/file/snapshot checks. Reports
expose registration count and chosen entry index. Candidates remain provisional;
active_tab_proven/windows_verified flags are not promoted. Retest on Windows;
Linux replay of old captures is not new native acceptance evidence.

The supplied g2-tabs-2 Windows retest now reports all four expected provisional
paths with selected entry indices1/0/1/0 and passing native checks, drops0/exit0.
Record this narrow live routing evidence; retain D-008's trust barrier and the
remaining acceptance matrix. No general point-to-item identity guarantee follows.

## D-011 — Explicit Shell path is the next safe invocation baseline (2026-10-25, active)

The native-class probe observes SHELLDLL_DefView hosting DirectUIHWND, not a
standard SysListView32 content control, on the tested Explorer view. Together
with GetItemPosition=E_NOTIMPL and the undocumented UIA-ID/Shell-index link,
the existing approach has not demonstrated the independent identity chain
required by D-003/EXPLORER_HIT_TEST.md. Equivalent click trials cannot supply
that missing guarantee. This does not prove all hover techniques impossible.

Keep Mouse3 resolution diagnostic-only and None-returning. Select G2-F explicit
Shell path passing as the next implementation baseline: a user-invoked Send to
or context command supplies the file path directly, without reading Explorer
selection or UIA names. This is an explicit UX compromise: the next baseline
requires a Shell menu invocation and does not activate by middle-click hover.
Retain the passive Mouse3 experiment separately for future evidence-based work.

G2-F is not implemented or Windows-verified by this decision. Next implement
only headless explicit-path validation/diagnostics, with a separately staged
direct-executable shortcut; no automatic Shell installation/registry edits,
accounts, GUI or converters. Source metadata must distinguish shell_explicit
from explorer_hover. Do not mark G2 verified, and gate later UI/conversion work
on actual explicit-path Windows acceptance.

An unrelated inactive tab may have a consistent bounded candidate prefix after
positive HWND exclusion. Its candidate list is not used for the hovered target;
the chosen registration remains complete and <=32. Unknown/error/contradictory
peers, inconsistent prefixes and globally truncated registration lists reject.
This narrow diagnostic correction does not relax D-008's trust barrier.

## D-012 — Usable radial prototype is next (2026-10-25, user-directed)

The user accepts temporarily deprioritizing Mouse3 and requests explicit-path
headless launching with personal install/remove, followed immediately by PySide6
radial GUI development. Preserve Mouse3 infrastructure; do not expand its
diagnostics absent a specific blocker. Both routes use InvocationController and
TargetResolution; explicit file paths never query selection or UIA.

The GUI prototype may progress on Kubuntu with injected preview capabilities and
offscreen tests while actual Send to/overlay Windows validation stays queued.
It must show compatible categories then concrete formats, near the cursor, with
Escape, Back and outside dismissal. No actual converters or invented working
engine capabilities. This priority supersedes earlier instructions to keep
investigating Explorer edge cases before any GUI work.

## D-013 — G4 preview UI and next engine (2026-10-25, user-directed)

User verified narrow single-file headless direct/Send to delivery on Windows11
build26200/Python3.15.0. G4 uses that validated explicit path and the existing
TargetResolution boundary. Optional PySide6>=6.12 supports the target3.15 and
Kubuntu3.14 according to published metadata. One short-lived popup/event loop,
pure preview registry/state and isolated native monitor mapping; no conversion,
service, UIA selection lookup or Mouse3 research. Diagnostic and GUI shortcuts
have distinct ownership identities; explicit --mode gui selects the new entry.

G4 native overlay/DPI/focus and broader explicit-path acceptance remain queued.
NEXT milestone G5 is real PNG→JPEG, followed by PDF→DOCX and MarkItDown. Preview
edges are no evidence of installed engine capability. Native G2 remains unproven.

## D-014 — Authorized local conversion milestones (2026-10-25, active)

User authorized autonomous G5→G8 without waiting for Windows. G4 basic rendering
is now user-reported Windows success. G5/G6/G7 use one safe staged manager and
optional available-engine registry, not preview claims. Same validated controller
input serves explicit Shell and future trusted hover; Mouse3 stays preserved.
Pillow/pdf2docx/MarkItDown/LibreOffice/PyMuPDF are local only. Word COM is optional
and not implemented. MarkItDown0.1.9 Python3.15 exclusion is honored; use3.14 for
those pairs. ONNX opt-out precedes imports, HTTP/plugins/LLM routes are disabled.
Qt work is separate from encoding; cooperative cancellation retains worker
ownership, and LibreOffice has bounded process-tree termination. Publication uses
no-replacement hardlinks; unsupported filesystems fail safely. G8 uses240px default,
transparent clear and no native rectangular shadow. Windows new behavior remains
provisionally implemented until actual target runs; no claim follows from mocks.

## Pending experiments
- Latest hidden-extension test preserves the non-ASCII Shell path and rejects
  both report labels. Keep D-008: no identity bridge follows from matching index
  sources. Native classes are now observed as DirectUI; D-011 selects the
  explicit-path fallback. Future hover research needs a concrete identity bridge.
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


## D-015 — Experimental consent and personal packaging (2026-10-25)

The user authorized G9–G12. Python 3.14 is the single desktop/build runtime.
G9-A/B Windows acceptance is user-reported. Mouse3 remains disabled by default
and uses an explicitly untrusted candidate with visible path confirmation and
fresh controller validation; D-008's identity limitation is unchanged. A tray
host owns listener/UI lifetimes. Send to remains the explicit-path fallback.

Package as a windowed Windows onedir application, built on Windows, with a
complete optional portable LibreOffice tree beside the EXE. Do not claim native
bundle acceptance from Linux structure/environment tests. Native Shell verb
IExecuteCommand::SetPosition could supply the original context-menu point, per
[Microsoft's API contract](https://learn.microsoft.com/en-us/windows/win32/api/shobjidl_core/nf-shobjidl_core-iexecutecommand-setposition).
It is not implemented; Send to uses the launch-time cursor without inventing
an original file position.


## D-016 — Direct personal Mouse3 activation and compact palette

After reporting successful Windows large-folder Mouse3 tests, the user explicitly
requests removing per-file confirmation. This supersedes D-015's requirement for
that dialog on every invocation. Direct activation is allowed only through the
existing experimental evidence gate, with fresh event/path checks and provenance
experimental_candidate. It does not turn provisional UIA/Shell correlation into
trusted hover identity. The listener stays opt-in; per-file confirmation remains
a tray preference, off by default. Send to retains its explicit-path semantics.

Use a 220 px wheel with a small Esc/Back center, larger segment labels and circular
progress/result surfaces. Forest green, ivory and brass express the requested
old-money style; semantic color roles and contrast come from
[Material color roles](https://m3.material.io/styles/color/the-color-system) and
[W3C minimum text contrast](https://www.w3.org/WAI/WCAG21/Understanding/contrast-minimum).
Target at least 4.5:1 for text and 3:1 for meaningful controls; measured token
contrast is portable evidence, not native Windows compositor acceptance.
