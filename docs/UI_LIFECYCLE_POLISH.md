# F1–F4: selection motion and progress lifecycle consistency

Windows user acceptance of the earlier progress build passed all eight functional
checks. A later intermittent missing pill transition recovered after restart;
its exact cause remains unproven. This milestone strengthens tested lifecycle
paths without attributing it to GPU or worker failure.

Selection opens with a 140 ms opacity-only fade. Hit regions are active from the
first frame; selection optics do not scale MouseArea. Mouse-leave dismissal uses
r118 (8 px beyond visible r110), 100 ms debounce/current-cursor recheck, then a
110 ms fade. Sector hit radius stays110: the invisible tolerance never selects a
format. Escape/native outside/focus dismissal can finish immediately, prioritizing
native popup correctness. Reduced motion/low effects are immediate. Choosing a
format cancels selection exit before starting the independent progress morph.

Selection callbacks, progress motion and invocation lifetimes have separate
tokens. Intentional hidden-wheel QML exits cannot collapse the new details view.
Repeated collapse is idempotent; stopped/invisible transitions normalize to a
readable surface. A finite one-shot recovery handles interrupted transitions or
unexpected surface destruction; there is no global hook or desktop polling.
Success expiry preserves its remaining time across native recreation. New
invocations invalidate old hide/morph/expiry callbacks; intentional reuse does
not enqueue native-hide recovery. None of this cancels a conversion implicitly.

These portable tests reproduce concrete stale/hidden-surface failures, but do
**not prove the original intermittent Windows incident resolved**. Long-running
native tray acceptance is still required.

PDF image labels are now **JPG** and **PNG**. Capability descriptions/tooltips say
“Export all PDF pages as … images”. Each page is still exported separately and
actual output filenames are unchanged. Use short format labels, keeping detailed
behavior in metadata/tooltips rather than squeezing prose into sectors.

[Actual rendered proof](ui-polish/ui-polish-proof.png) and individual RGBA images
in docs/ui-polish show opening, selection, formats, dismissal, compact progress
and completion. They were visually inspected. They use Linux Quick software
rendering and a controlled preview worker, not Windows screenshots.

```bash
QT_QPA_PLATFORM=offscreen QT_QUICK_BACKEND=software PYTHONPATH=src \
  .venv-ui/bin/python scripts/render_ui_polish.py --output-dir /tmp/ui-polish
```

From an updated Windows checkout, quit the existing tray owner first:

```powershell
.\.venv-filewheel\Scripts\python.exe -m pip install --no-deps -e .
.\.venv-filewheel\Scripts\python.exe -m filewheel --tray --ui-backend quick
```

Or rebuild:

```powershell
powershell.exe -NoProfile -ExecutionPolicy Bypass -File .\scripts\build-windows.ps1
& .\dist\Filewheel\Filewheel.exe --self-test --ui-backend quick
& .\dist\Filewheel\Filewheel.exe --tray --ui-backend quick
```

Verify fast hover/click during entrance, Escape/rapid reopen, tolerance without
invisible clicks and short PDF format labels. Repeat many conversions in one tray
session: collapse/expand/collapse, outside clicks, complete/cancel during morph,
new conversion while old success is visible, failure/acknowledgement and success
expiry. Observe status after focus changes and task switching. Repeat at100/125/
150%, mixed monitors and source/frozen modes. Record a sequence if the original
intermittent disappearance recurs; no verbose permanent tracing is added.
