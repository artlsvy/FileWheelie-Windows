# Radial conversion UI — G8

## Activation and placement

A validated TargetResolution from InvocationController is required before opening.
Normal activation is Explorer Send to with one explicit absolute path. Future
trusted Mouse3 uses the same interface; provisional hover candidates cannot open
it. No selected/focused-file lookup, tray, IPC or permanent main window.

Default widget diameter240 logical pixels, internally configurable220–324
(220–260 preferred;324 preserves legacy fixture geometry). The324-unit layout is
scaled identically for painting and hit testing; text has a readable minimum8pt.
Frameless/translucent Qt.Popup, explicit transparent source clearing, no system
background/autofill or native rectangular drop shadow. Painted shadow follows the
circle. Palette-based light/dark colors and animated hover are retained.

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

Center/Backspace navigates back from formats. Escape, outside any-button click or
focus loss dismiss; inner choices are left-click only. Gaps/invalid indices do
nothing. Tab/arrows + Return provide basic keyboard access. Reopening resets idle
menu state; a busy instance requests cancellation rather than starting overlapping
work. Six or more injected options use a compact scrollable list.

## Conversion feedback and exit

One popup displays preparing/encoding/rendering progress, percentage/bar, result
and errors. Source filename remains visible; long filename/output/warning details
are in tooltips. Multi-page results show first output plus count and all paths in
the tooltip. Success uses actual published paths, not predicted collision names.
Done closes. Conversion outcomes are converted/conversion_failed/conversion_cancelled,
including dismissal while working; the CLI returns6 for a conversion failure.

A QThread owns only backend work; signals update Qt on its GUI thread. Dismissal
requests cooperative cancellation, hides the popup and retains worker/widget
ownership until cleanup completes. Library calls cannot all be interrupted
mid-call; LibreOffice has a bounded process-tree deadline. The application does
not destroy a running QThread or leave an unowned worker behind.

Outputs are adjacent to source, numbered on collision, validated before atomic
publication. See CONVERTERS.md for limits, alpha behavior, OCR/fidelity and engine
availability. No real conversion is claimed for preview edges or missing engines.
