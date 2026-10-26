# Experimental native glass wheel

The user accepted the [Phase 1 geometry/leave correction](GLASS_UI_PHASE1.md)
on Windows. Phase 2 progress UX and Markdown expansion are now authorized;
see STATUS.md and NEXT_TASK.md for the current implementation checkpoint.

The default is still the working **170 px QWidget** wheel. The experimental
Quick backend uses a **240 logical pixel window / 220 px circular surface**, a
moving annular lens, forest/ivory/brass material, sharp labels and transparent
corners. Both consume the same controller target, registry and conversion job.
No conversion engines, Mouse3 trust rules or Send to registration were changed.

This is implemented and Linux-tested. **Windows D3D11, laptop frame pacing,
focus/compositing, mixed DPI and frozen Quick execution remain unverified.**
The comparison and migration recommendation are in
[PERFORMANCE_ARCHITECTURE.md](PERFORMANCE_ARCHITECTURE.md). The
[visual proof](performance/glass-proof.png) uses actual Quick raster images over
synthetic backdrops, not desktop capture or Windows screenshots.

## Build and select a renderer on Windows 11

Close the existing Filewheel instance first. Backend selection is startup-only:
launching a second process forwards to the existing owner and does not replace
its renderer. From the updated checkout, using the existing Python 3.14 recipe:

```powershell
powershell.exe -NoProfile -ExecutionPolicy Bypass -File .\scripts\build-windows.ps1
& .\dist\Filewheel\Filewheel.exe --self-test --ui-backend quick
Get-Content "$env:LOCALAPPDATA\Filewheel\logs\self-test.json"
& .\dist\Filewheel\Filewheel.exe --tray --ui-backend quick
```

The explicit Quick self-test must report `quick_qml_render: true`, `corner_alpha: 0`
and an actual `graphics_api`, alongside normal converter results. It verifies a
nonblank DPI-scaled frame (240 logical pixels), not just imports. If FILEWHEEL_LOG_DIR is set, the report is
under that directory instead. Keep the whole onedir folder together. No Windows
EXE was built in the Kubuntu environment.

Source equivalent (use the project's existing 3.14 environment):

```powershell
.\.venv-filewheel\Scripts\python.exe -m filewheel --tray --ui-backend quick
```

An explicit validated file can open directly:

```powershell
& .\dist\Filewheel\Filewheel.exe --ui-backend quick --gui -- "C:\path\to\sample.png"
```

With the Quick resident owner running, existing Mouse3 and Send to invocations
reach that same host. The normal file confirmation preference is unchanged;
**injected touchpad events always require path confirmation** when their separate
opt-in is enabled. Do not bypass it to evaluate animation.

## Acceptance checklist

1. Enable the existing Experimental Mouse3 action. Invoke on a known file; check
   compatible categories then actual formats. Sweep across neighboring labels,
   including the last/first boundary. The lens should take the short path; clicks
   must select the original stable sector even while the lens is moving.
2. Test arrows/Tab/Home/End, Enter/Space, center Back, Backspace, Escape, outside
   click, focus loss and reopening. Empty capability lists say No formats. Check
   selection windows close on circular mouse leave and finish once and transient Send to processes exit normally.
3. Convert a PNG, a normal PDF and an installed document pair. Check the output
   opens, the source is unchanged and collisions create new filenames. During
   conversion click elsewhere: progress/results stay visible and topmost, with
   short status words. Hover the center result for escaped full details.
4. Test Cancel during the original large PDF, immediate same-file retry, then
   Cancel -> tray Quit -> relaunch. That previous D-020 native queue remains open.
5. Test touchpad opt-in and a physical middle button. Injected input must still
   confirm even with physical confirmation disabled; unrelated apps/background,
   folders, invalid targets and lower-integrity input must remain rejected.
6. Test light/dark Windows appearance, bright/detailed desktop content, 100/150%
   scaling, monitor edges and a secondary monitor with negative coordinates.
   Check circle shape, clear corners, no rectangular OS shadow, correct hits and
   work-area placement. Linux alpha tests cannot certify these Windows behaviors.
7. Test the source and frozen build, then move the full onedir tree away from the
   venv/checkout. Repeat launch, conversion, repeated Send to, tray Quit and
   resource loading without a Qt SDK on PATH.

## Reduced effects and fallback

These settings apply to the next app start. Exit the current instance first:

```powershell
$env:FILEWHEEL_REDUCED_MOTION = '1'
$env:FILEWHEEL_LOW_EFFECTS = '1'
& .\dist\Filewheel\Filewheel.exe --tray --ui-backend quick
```

Reduced motion removes lens/label transitions; low effects makes materials
opaque and static. Windows reduced-motion/high-contrast settings are not claimed
to be automatically detected; these explicit fallbacks are available. Qt follows
system light/dark color changes where supported.

To test Quick's software scenegraph instead of the default native graphics path:

```powershell
$env:QT_QUICK_BACKEND = 'software'
& .\dist\Filewheel\Filewheel.exe --tray --ui-backend quick
```

A recoverable Quick import/QML-load error is logged and falls back to QWidget.
A fatal GPU driver error cannot be recovered by Python. The reliable startup
escape route is to exit/relaunch with the old renderer:

```powershell
& .\dist\Filewheel\Filewheel.exe --tray --ui-backend widgets
Remove-Item Env:QT_QUICK_BACKEND,Env:FILEWHEEL_REDUCED_MOTION,Env:FILEWHEEL_LOW_EFFECTS -ErrorAction SilentlyContinue
```

`FILEWHEEL_UI_BACKEND=quick` is an optional environment alternative; an explicit
`--ui-backend` wins. Without either, QWidget remains the default. No preference
is silently persisted and no second IPC/service was introduced.

## Native measurements

Run benchmarks **serially**, on the same power mode/hardware. Record monitor
refresh/scaling, graphics device/backend and sample counts. Native GPU timings
are pending; a backend name alone does not establish smooth 60 FPS.

For renderer-only synthetic input, using the source 3.14 environment:

```powershell
$env:QT_QPA_PLATFORM = 'windows'
.\.venv-filewheel\Scripts\python.exe scripts\benchmark_ui.py --backend widgets --diameter 240 --iterations 100 --output logs\widgets-native.json
.\.venv-filewheel\Scripts\python.exe scripts\benchmark_ui.py --backend quick --iterations 100 --output logs\quick-native.json
Remove-Item Env:QT_QPA_PLATFORM
```

Use QT_QUICK_BACKEND unset for native RHI, then repeat software fallback if
needed. Frame intervals include tails, not just averages. Quick measurements
associate an input with its synchronized scene and subsequent frameSwapped;
queued presentation is still not physical display time. QWidget completion is
paint submission, so the two boundaries are not interchangeable.

For **actual frozen launch** timing, close the owner before each run and use a
real absolute input path plus a fresh absolute output name. Press Escape when
shown; do not choose a format. The helper never force-kills an app on timeout:

```powershell
$filewheelInput = 'C:\path\to\sample.png'
$filewheelTiming = Join-Path (Get-Location) 'logs\quick-cold-1.json'
.\.venv-filewheel\Scripts\python.exe scripts\benchmark_launch.py --exe .\dist\Filewheel\Filewheel.exe --file $filewheelInput --backend quick --output $filewheelTiming
```

Repeat for widgets and repeat fresh processes to separate first-ever QML/DLL
cache costs from later starts. The helper measures from immediately before
Popen to the first actual paint/queued Quick frame; it excludes the user's time
before pressing Escape. A forwarded invocation with no first frame is rejected
as a launch sample. It does not clear OS/QML caches or pretend warm caches are
cold. A source launch can use `--python .\.venv-filewheel\Scripts\python.exe`.

For **resident Mouse3 stages**, set FILEWHEEL_TIMINGS to a fresh absolute JSON
path before starting the owner, exercise 30+ valid regular-file invocations, then
Quit normally so the bounded buffer flushes. The fixed stage names distinguish
queue, resolver, candidate, GUI handoff and paint/frame boundaries. Run negative
rejection tests separately; do not sum overlapping p95 values or include human
confirmation delay. No names, titles or pointer coordinates enter timing files.

Measure idle/active memory and installed payload separately on Windows:

```powershell
Get-Process Filewheel | Select-Object Id,WorkingSet64,PeakWorkingSet64
(Get-ChildItem .\dist\Filewheel -Recurse -File | Measure-Object Length -Sum).Sum
```

Keep source/frozen, first-process/resident and effect modes separate. Report any
missing resources, frame stalls, focus failures or unusual driver behavior before
making Quick the default.
