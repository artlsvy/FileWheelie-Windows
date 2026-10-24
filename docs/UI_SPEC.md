# UI specification — next prototype milestone

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
2. **Format**: dynamic concrete outputs in category (e.g., PNG → Image → JPG, WebP, TIFF; DOCX → Markdown/Text → MD). Choosing a format starts the conversion **once**; during POC use a fake action showing source/output.

Controls: center=Back in stage 2; Escape/outside click=cancel; no hold or drag necessary; use hover highlight and clear labels; usable on keyboard/focus where practical. Reopening a wheel cancels the prior menu. Display source basename and readable format. Provide a non-radial fallback for 6+ choices or accessibility rather than overcrowding slices.

## Output behavior (later)
Default save location is alongside source; never change source. Output collision: produce `stem (2).ext`, `stem (3).ext`, etc., using race-safe allocation. Toast on success and actionable error on failure. No network dependency.

## State contract
`Dormant → Resolving → CategoryWheel → FormatWheel → Converting → Result → Dormant`; `Resolving` can transition directly to `Dormant` on None/timeout, and Escape cancels before conversion. No wheel appears before a validated target.

## Open questions (do not block resolver work)
- Whether to intercept/suppress native Mouse3 in Explorer when our menu appears; **POC should not intercept**.
- Whether multiple-selection should ever convert more than the clicked file; default **single hovered file**.
- How to visually represent categories with one format.
