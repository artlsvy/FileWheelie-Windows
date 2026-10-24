# UI specification — G4 radial preview

## Activation
The primary prototype entry is an explicit path from Send to through
InvocationController. Future verified Mouse3 invocations use the same controller
and TargetResolution DTO. Hover diagnostics currently return None and must not
activate a wheel. No path lookup from selection or UIA is added for the GUI.
Show a compact frameless translucent wheel near the invocation's cursor point,
clamped within the monitor work area; default diameter260–320 logical pixels.
Convert the DTO's physical desktop coordinates at the Qt boundary, including
scaled displays and negative monitor coordinates.

## Stages
1. **Category**: dynamic available outputs for the detected input (Image, Document, Markdown/Text, Audio, Video); do not show empty categories.
2. **Format**: dynamic concrete outputs in category (e.g., PNG → Image → JPG, WebP, TIFF; DOCX → Markdown/Text → MD). Choosing a format records one dry-run selection and shows filename, original format, destination and intended output filename in the same popup. No files change; Done closes it.

Controls: center=Back in stage 2; Escape/outside click=cancel; no hold or drag necessary; use hover highlight and clear labels; usable on keyboard/focus where practical. Reopening a wheel cancels the prior menu. Display source basename and readable format. Provide a non-radial fallback for 6+ choices or accessibility rather than overcrowding slices.

## Output behavior (later)
Default save location is alongside source; never change source. Output collision: produce `stem (2).ext`, `stem (3).ext`, etc., using race-safe allocation. Toast on success and actionable error on failure. No network dependency.

## State contract
`Dormant → Resolving → CategoryWheel → FormatWheel → Converting → Result → Dormant`; `Resolving` can transition directly to `Dormant` on None/timeout, and Escape cancels before conversion. No wheel appears before a validated target.

## Open questions (do not block GUI work)
- Whether to intercept/suppress native Mouse3 in Explorer when our menu appears; **POC should not intercept**.
- Whether multiple-selection should ever convert more than the clicked file; default **single hovered file**.
- How to visually represent categories with one format.

## Implemented G4 prototype

324 logical pixel widget includes shadow; circular content is296px. Palette-based
light/dark styling, animated hover, topmost Qt.Popup with translucent corners.
Center displays an elided input filename; stage2 center/Backspace returns; Escape,
outside/focus loss and confirmation Done dismiss. Tab/arrows and Return select.
Reopening resets state; six or more injected choices use a scrollable compact list.

Injected CapabilityRegistry contains explicit preview edges only. PREVIEW appears
in the wheel and confirmation says No files changed. No engine is installed or
claimed. Unknown suffixes display No preview options. Source controller DTO is
required before opening; both invocation sources use present(target)/run_popup.
No selected-file lookup, conventional main window, tray or service is required.
Native Windows placement, activation and dismissal remain manual acceptance items.
