# Durable background conversion feedback

Windows user acceptance: all eight functional progress checks passed. A later
intermittent missing transition recovered after restart; its cause remains
unproven. F1–F4 lifecycle polish/recovery still needs native acceptance.

The approved selection wheel still dismisses after circular mouse leave. Once a
format starts a job, moving away, outside click, focus loss or native popup Hide
collapses its feedback into a **272×72 logical pixel glass pill**. A coordinated
210 ms wheel scale/fade and pill fade/move avoids resizing a live native popup.
The pill moves to the opening monitor's bottom-right available work area, with
16 px margin and taskbar exclusions. All coordinates remain Qt logical units.

The compact Tool window does not request focus or cover unrelated desktop input.
Click it for a 272×190 detail view, with explicit Cancel while running, Hide to
collapse, error Details/local-log information or Reveal after success. Escape in
the expanded progress view requests cancellation. Closing that informational
surface collapses it; it does not cancel. The controller holds the worker until
QThread.finished, independently of both windows. Tray Quit explicitly requests
cancellation and waits asynchronously for cleanup. Repeated busy invocations are
rejected through the existing host, without starting another worker.

Current engines report stage fractions, not reliable percentages of remaining
work. The UI therefore shows indeterminate activity/Working instead of inventing
precise percentages or advancing a timer. Success shows Converted for 4.5 s,
then fades over 180 ms. Expanding pauses expiry. Failures/cancellation persist
until acknowledged; Details exposes the actual backend/cause and local log path.
Reopen clears presentation timers. Completion during collapse updates the same
pill immediately; it cannot restart the job. Reduced motion/low effects use
immediate transitions. QWidget keeps simpler persistent feedback and restores it
if a native hide occurs. A recoverable pill-QML load failure logs and restores
the persistent wheel, with no job cancellation.

## Rendered evidence

[Actual Quick state board](progress-pill/progress-proof.png) includes expanded,
transitioning wheel/pill, compact, converted and failed details. Raw RGBA images
are in docs/progress-pill. These use a controlled preview worker and Linux
software scenegraph; no real input/output files are converted by the renderer
script. They were visually inspected, not inferred from unit tests.

```bash
QT_QPA_PLATFORM=offscreen QT_QUICK_BACKEND=software PYTHONPATH=src \
  .venv-ui/bin/python scripts/render_progress_pill.py --output-dir /tmp/progress-proof
```

## Windows acceptance

Quit the current tray owner before selecting the updated renderer:

```powershell
.\.venv-filewheel\Scripts\python.exe -m pip install --no-deps -e .
.\.venv-filewheel\Scripts\python.exe -m filewheel --tray --ui-backend quick
```

Or rebuild and test the standalone application:

```powershell
powershell.exe -NoProfile -ExecutionPolicy Bypass -File .\scripts\build-windows.ps1
& .\dist\Filewheel\Filewheel.exe --self-test --ui-backend quick
Get-Content "$env:LOCALAPPDATA\Filewheel\logs\self-test.json"
& .\dist\Filewheel\Filewheel.exe --tray --ui-backend quick
```

Self-test must include `quick_qml_render` and `quick_progress_render` successes.
Start a slow conversion through Mouse3, opted-in touchpad, Send to and direct GUI.
Move/click/focus outside: the pill must remain without cancellation or focus
stealing. Expand, Cancel, retry, then try tray Quit while running. Check outputs
and collision suffixes. Test failure Details/Dismiss and success Reveal/expiry.
Test repeat Send to while busy and after completion. Repeat at 100/125/150%, mixed
DPI, negative coordinates and different taskbar positions. Verify the opening
monitor owns the pill even after changing foreground apps. Move the full onedir
away from the checkout and repeat. Use `--ui-backend widgets` for the fallback.

Linux tests establish actual QML rendering/input at startup scaling and pure
logical placement; they do not prove native mixed-DPI focus/compositor behavior.
No Windows build or new native pill test was performed in Kubuntu.


F1–F4 adds independent selection fades and tolerant leave geometry, plus tested
progress-window/timer recovery. See UI_LIFECYCLE_POLISH.md. The eight earlier
Windows functional checks are user-reported passed; the intermittent missing
transition is not declared definitively fixed without native reproduction.
