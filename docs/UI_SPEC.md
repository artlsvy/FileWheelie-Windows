# Radial conversion UI — G8

## Activation and placement

A controller-validated TargetResolution is required before opening. Send to uses
one explicit absolute path. Experimental Mouse3 now opens the wheel directly by
user request after fresh evidence/path checks, with source experimental_candidate;
it does not claim trusted hover identity. The optional tray checkbox “Confirm
file before opening” restores the per-file dialog. The listener remains opt-in.
No selected/focused-file lookup or permanent main window.

Default widget diameter 170 logical pixels, internally configurable 170–324.
Paint and hit testing share scaled geometry. Segment labels use a larger readable
minimum (9.5pt below 220px; 10.5pt at larger sizes); compact Docs/Text-MD
labels and deliberate wrapping avoid clipping. The smaller center contains only Esc at the category level and Back at
the format level. Clicking Esc dismisses; clicking Back returns to categories.
Source path remains available in the tooltip rather than crowding the center.
Selection uses a frameless/translucent Qt.Popup; conversion/results use a
non-modal Qt.Tool with WindowStaysOnTopHint. Explicit transparent clearing, no system
background/autofill or native rectangular drop shadow. Painted shadow follows the
circle. Light/dark variants use forest green, warm ivory and muted brass, with semantic
surface/text/outline/accent roles and animated hover. Token text pairs meet 4.5:1
and meaningful outline/control contrast meets 3:1 in automated calculations.

Native monitor origin/dimensions uniquely match Qt geometry and DPR, independent
of friendly display names. Cursor conversion is relative to that monitor; edge
rounding is bounded to it. Placement clamps to available work area. Real Windows
compositor, detailed mixed-DPI and focus behavior remain acceptance items.

## Navigation and real capabilities

Level1 contains only categories with installed working engines (Image, Document,
Markdown/Text; Audio/Video hidden until implemented). Level2 contains specific
formats from the same injected registry. Unknown inputs show No available formats.
Clicking a format starts exactly one real conversion worker. The old injected
preview registry remains a test-only seam with explicit PREVIEW/dry-run UI.

Center/Backspace navigates back from formats. In selection menus, Escape,
outside any-button click or focus loss dismiss; inner choices are left-click only. Gaps/invalid indices do
nothing. Tab/arrows + Return provide basic keyboard access. Reopening resets idle
menu state; a busy instance rejects new invocations without cancelling current
work. Six or more injected options use a compact scrollable list.

## Conversion feedback and exit

The 170px status face shows only “In progress”, a percentage and the circular
progress ring. Backend phase messages, filenames and detailed warnings/errors
stay in metadata, tooltips and local logs. Success shows “Done” and “File saved”
(or a file count); failure shows “Failed” with details available on hover.

Conversion/results remain visible above ordinary windows during outside clicks
and focus loss. Status mode uses a non-modal Qt.Tool rather than Qt.Popup, so it
does not retain a popup mouse grab while the user works in Explorer. A guarded
window-type transition preserves geometry and prevents Qt's temporary hide from
cancelling work or emitting completion. Results stay until Done/Escape or a new
intentional invocation. Reopening restores normal selection-menu popup behavior.
Native Windows z-order/focus acceptance remains required.

Cancel or Escape while working requests cooperative cancellation and shows
“Stopping…” until cleanup finishes, then “Cancelled”. It keeps the window
visible. Programmatic dismissal/Quit can still hide the window and wait for its
owned worker to finish. A QThread supervises the spawned backend process;
signals update Qt on its GUI thread. A stuck encoder receives a two-second
cancellation grace period before its owned process is stopped and staging is
cleaned. Saving is protected by a publication permit and is never force-stopped;
that short transaction must finish/roll back. OS process termination and file
cleanup can add time beyond the grace period. Workers remain owned until exit.

Outputs are adjacent to source, numbered on collision, validated before atomic
publication. See CONVERTERS.md for limits, alpha behavior, OCR/fidelity and engine
availability. No real conversion is claimed for preview edges or missing engines.


## Tray host and experimental consent (G10)

`python -m filewheel --tray` keeps a lightweight tray icon and reusable popup.
The Mouse3 checkbox is off by default; per-file confirmation is separately off
by default per D-016. Startup waits off the Qt event loop;
disabling immediately invalidates pending consent, then reports stopping until
owned threads exit. Quit waits for owned listener and conversion cleanup.
A failed listener returns the tray to off; Send to remains available.

Direct experimental activation consumes the current token immediately and requires
the original event to remain fresh (<=500 ms), then revalidates the path through
the shared controller. No conversion starts until the user chooses a format.
The source stays experimental_candidate. If optional confirmation is enabled,
the complete proposed path appears in a topmost plain-text dialog with Cancel
default and a 30-second deadline; approval yields user_confirmed_candidate after
fresh path validation. Both anchor at the original Mouse3 point. Neither proves
UIA-to-Shell identity. Native validation of the new direct/UI behavior is pending.

All progress/results and preview confirmations share the wheel's circular
silhouette, replacing the previous intentionally rounded-rectangle panel.
A circular progress ring, compact Cancel/Done control and chord-constrained text
retain transparent corners and consistent hit regions. Selection menus dismiss
on outside click; conversion/results persist. Cancel/Escape while busy requests
cancellation visibly, and worker ownership remains until cleanup completes.


## Curved labels, surface transparency and responsiveness

Empty capability state reads “No formats”. Category/format glyphs follow measured
circular baselines, reverse on the lower half for readable orientation, and elide
within sector arc limits. Compact aliases and full-label tooltips remain. The
forest/ivory/brass surface uses alpha 235/255; text and action controls stay
opaque, rather than lowering whole-window opacity. Hover tint preserves surface
alpha. Text/outline contrast is checked against black/white composited backdrop
extremes; native Windows rendering still needs acceptance.

Production ConversionManager jobs now run in one spawned process, with the Qt
worker only supervising bounded progress/outcome messages. Common native-library
thread limits and reduced child scheduling priority are best effort. Progress
updates are throttled instead of flooding the UI. Cancellation, persistent status,
ring and output safety remain; injected fake-manager tests retain an explicit
in-process seam. No production spawn failure falls back to a converter thread.

## Experimental Quick glass variant (D-022)

The current170px QWidget remains default. An explicit startup selection enables
the separate240px QQuickView with220px circular translucent material, forest/
ivory/brass tokens,14px opaque text, continuous illuminated rims and a raised
annular hover lens. Keyboard selection shares the same highlight. Lens rotation
uses shortest-arc145ms easing; appearance70ms and label-scale120ms transitions
never delay selection or alter hit geometry. Reduced-motion/low-effects switches
are explicit; low effects is opaque and static. No desktop capture/refraction,
shader dependency or permanent main window is introduced.

The shared controller/registry/worker path, mandatory injected consent, status
persistence, Cancel/Back/Escape and outside/focus selection dismissal are retained.
See GLASS_UI.md for native acceptance and startup fallback; source/offscreen
visual proof does not establish Windows compositor/driver/focus correctness.


## Phase 1 glass correction and review gate

All Quick rotating annular elements use local (0,0) with an explicit TopLeft
origin translated to (120,120). Lens arcs share a centerline; quarter-circle end
caps remove diametric-arc ambiguity. One subtle contour replaces duplicate
outlines/shadows. The label dots are removed; the lens alone shows selection.
Interrupted transitions always choose the shortest rotation from the displayed
angle, including first appearance. Default size, colors and fixed hits remain.

Only category/format selection auto-dismisses after 75 ms outside r110, including
transparent rectangular corners. Re-entry stops the timer; expiration rechecks
QCursor through QWindow mapping. Center, Back, sector movement and keyboard remain
usable. Progress/results remain persistent; no new global hook is installed.

The user subsequently approved Phase 1 and authorized Phase 2 progress UX and
Markdown expansion. The earlier hold is satisfied (see STATUS.md).
See GLASS_UI_PHASE1.md for real rendered before/after evidence and native checks.

## Phase 2 A — wheel to compact progress

Keep approved selection appearance and 75 ms circle-leave behavior. Running work
collapses to a separate green/ivory/brass 272×72 logical pill, with 210 ms
coordinated fade/scale/move toward the original monitor workarea edge. It does
not request focus. Click expands 272×190 details with explicit Cancel/Hide or
Details/Reveal/Dismiss. Current stage fractions remain indeterminate, not exact
percentages. Success remains 4.5 s then fades 180 ms; failures/cancel persist until
acknowledged. Reduced motion is immediate. Job ownership is independent of native
Hide/Close and popup geometry. PROGRESS_UX.md includes actual rendered states.

## Phase 2 B — Markdown destinations

Navigation is derived from the supplied capability list through core/navigation.
For non-Markdown input, every actual .md destination is grouped under To MD;
choosing its sole format returns the normal selection immediately, with no
redundant format wheel. The existing renderer/controller job path then starts
the same progress workflow. Image and Document categories remain distinct.
Markdown input groups genuinely offered outputs under From MD and retains the
second format step and Back. No installed capability means no category. Preview
fixtures use the same navigation code but do not attest conversion engines.


## F1–F4 selection motion / lifecycle correction

Current selection uses opacity-only140 ms entrance/110 ms leave exit, immediate
hit testing and r118/100 ms leave tolerance. Actual sectors stay r110. Selection
callbacks are independent of progress morph; native popup dismissal wins when
necessary. PDF formats use JPG/PNG with all-pages behavior in descriptions and
tooltips. Invocation/motion tokens and finite endpoint/surface recovery preserve
observable jobs through repeated operations. See UI_LIFECYCLE_POLISH.md for
actual rendered states and the unresolved native intermittent acceptance item.

From MD now contains only actual probed Pandoc writers; PDF additionally needs
LibreOffice. New To MD inputs use the same navigation/job/progress surfaces.
Missing tools hide capabilities without changing geometry or trust rules.
Current conversion availability and native verification boundaries are recorded
in CONVERSION_MATRIX.md and PANDOC.md.
