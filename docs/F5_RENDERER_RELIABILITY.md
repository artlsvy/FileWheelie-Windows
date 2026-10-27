# F5: Windows Quick renderer reliability

## Decision and evidence (2026-10-27)

User acceptance follow-up: the user tested the F5 version and reports all good,
with no disappearing pill observed. They also report pushing this version to Git.
Treat F5 as user-reported Windows-passed on this machine; exact conversion count,
edge-case coverage and remote push status were not independently verified.

Prefer **OpenGL RHI for Windows Quick**, configured before Qt imports/application
creation in `app.main`. Widgets remains the overall default and escape route.
Explicit Qt graphics environment settings are preserved, including empty values;
no runtime graphics switching or automatic renderer retry is attempted.

User evidence: default lost progress after about 5-10 conversions; software lasted
>20 with a circular artifact and first-conversion pointer lag; OpenGL lasted
>30-40 without those symptoms. These historical runs have no captured effective
API, PID/owner or initialization logs. They cannot retrospectively prove D3D11
use, full restarts, absence of combined variables, or a permanent fix.

Independent fresh-process native runs here: Windows 11 Pro 10.0.26200, CPython 3.14.5,
PySide6/Qt 6.12.0, Intel Arc B580, driver 32.0.101.9033. No resident Filewheel process
was observed before the initial baseline. After the interrupted session resumed,
an existing `dist/Filewheel` owner was present and left untouched; stress runs
still used isolated processes without broker forwarding. The runner removes conflicting scenegraph, RHI,
software preference, render-loop, OpenGL and platform settings. Each test is an
isolated process that does not use the tray single-instance broker.

| Request | Effective API on wheel/pill | Completed cycles | Result |
|---|---|---:|---|
| Qt platform default | Direct3D11 / Direct3D11 | 5 | Desktop pill missing on cycle 6 |
| Explicit d3d11 | Direct3D11 / Direct3D11 | 5 | Desktop pill missing on cycle 6 |
| Explicit opengl | OpenGL / OpenGL | 100 | Passed state, frame and desktop-pixel checks |
| Software scenegraph | Software / see note | 100 | Passed state, frame and desktop-pixel checks |

Qt initialization logs explicitly select Arc B580 for D3D11 and report Intel
OpenGL 4.6.0 for OpenGL. This is hardware OpenGL, not Mesa/CPU software rendering.
The initial software observer missed the pill initialization signal; wheel API
and Qt's `Loading backend software` establish the process adaptation. Diagnostics
now query the always-available renderer API immediately and on first frame too;
the initial pill field `uninitialized` is retained in raw evidence, not rewritten.

The explicit D3D11 failure is particularly useful: `visible=true`, `exposed=true`,
`entrance=1`, `converting_compact`, no active transition, no graph invalidation.
The captured desktop region was entirely the controlled magenta background,
while subsequent `grabWindow()` returned a correctly rendered pill. Capture is
deliberately taken BEFORE grabWindow, which may itself force rendering. See
[missing desktop pill](f5/d3d11-missing-desktop.png),
[intact render target](f5/d3d11-intact-render.png), and
[OpenGL cycle100](f5/opengl-cycle100-desktop.png).

This supports a native presentation/backend interaction and argues against an
exclusively Python job-state or opacity failure. It does **not** establish that
D3D11 itself or Intel's driver is defective. Qt's D3D11 log mentions Direct
Composition for transparent windows; a Qt/driver/compositor interaction remains
plausible. Timing differences could still mask a lifecycle race. There is no
upstream bug ID, driver bisect, Qt-version bisect or second-machine validation.

## Lifecycle review and changes

- Wheel and pill are retained QQuickViews; normal cycles reuse both. There is no
  application-owned QRhi render target, texture, external graphics command stream
  or manual GPU resource cleanup. Qt owns these resources. Default persistent
  graphics/scenegraph hints are already true; adding them again would not fix this.
- Wheel switches Popup/Tool for selection versus persistent feedback. Pill stays
  Tool and changes its focus flag for explicit expansion. Native changes are
  guarded against hide reentrancy. Trace showed two scenegraph initializations,
  no invalidations and no platform-surface destruction before D3D11 failure.
  Thus flag changes did not recreate these native surfaces in the observed run.
- `ProgressSurface.set_accepts_focus` now returns when flags are unchanged, as
  the wheel setter already does. Explicit D3D11 still failed with that guard:
  this is bounded redundant-work removal, **not the claimed reliability fix**.
- Existing animation endpoints, tokens, cancellation, success-expiry and recovery
  remain intact. No state-machine rewrite, new recovery timer, converter change,
  QML/design alteration or framework migration was made.
- Early OpenGL selection is the practical mitigation. `FILEWHEEL_QUICK_RHI=default`
  permits a genuine Qt-default diagnostic run. Explicit `QSG_RHI_BACKEND`,
  `QT_QUICK_BACKEND`, `QMLSCENE_DEVICE`, `QT_OPENGL`, or
  `QSG_RHI_PREFER_SOFTWARE_RENDERER` prevents Filewheel from supplying OpenGL.
  Conflicting user settings are recorded/preserved, never silently repaired.

The original default/OpenGL baseline processes loaded before the no-op flag guard;
explicit D3D11/software loaded after it. Both D3D11 results agree. Initial harness
development encountered a render-thread Python callback stall before any cycle;
all delivered diagnostics use queued GUI-thread slots. This harness defect is not
counted as a reproduction of the original incident. `graphicsApi()` is documented
as callable on any thread; `getResource()` has different render-thread restrictions.

Do not generalize the source baseline into a deterministic cycle-number failure:
the frozen D3D11 run completed 65 cycles, then failed on 66 with the same blank
desktop/intact render target and full-opacity/exposed state. Packaging,
first-frame diagnostic delivery and timing differ from the source baseline.
A timing-sensitive application/Qt lifecycle interaction remains in consideration.

Frozen comparisons of the delivered runtime changes: preferred OpenGL 100 passed
(149.64s,47.02 process CPU seconds, working set244.3 to269.0MiB); software 100 passed
(147.88s,10.89 CPU seconds,164.0 to167.3MiB), with both software surfaces now
explicitly identified as Software. D3D11 completed 65 (165.42s before failure,
15.22 CPU seconds,214.1 to217.5MiB). Hardware runs retained two graph
initializations and zero invalidations; GDI handles remained flat.

One additional tracing-disabled run stopped at initial wheel exposure before any
conversion. The test backing window's asynchronous initial activation could
dismiss the Popup; the harness now settles that activation before opening it.
This is a test-only startup correction, not a production recovery timer. The
failed zero-cycle result is retained, not counted as a long-session progress
failure or silently discarded. A subsequent untraced source run passed 100; a
frozen run completed 89 then hit an unclassified UI-wait deadline. Its old harness
did not record the predicate/phase, so the exact cause is unknown. The final
harness records failure state and named waits and allows at most three selection
opens before starting a job, counting any reopens. Expected Popup focus dismissal
must not be confused with missing progress; no job or pill failure is retried.
Both incomplete trials are preserved in the evidence summary.

The final packaged untraced rerun completed **100/100 cycles with zero selection
reopens**:149.85 wall seconds,46.63 process CPU seconds, working set227.5 to254.1MiB.
No progress failure was retried. This used the final classified harness, the
packaged working directory and no source PYTHONPATH. The final source untraced
run also passed100. See [machine-readable native results](f5/native-results.json),
including all failures/incomplete trials, PIDs, counters and resource endpoints.

## Stress protocol and measurement limits

`scripts/compare_quick_windows.py` launches fresh processes serially, bounds each
run, captures Qt diagnostics and writes per-cycle state/resource evidence.
`--ui-stress-test OUTPUT --ui-stress-cycles 100` also works in the frozen EXE.
This isolated test never forwards to an existing tray owner. Do not run multiple
native tests concurrently or cover the test surfaces with other topmost windows.

Each cycle opens the real wheel, selects category/format through its session,
starts a controlled worker through the real ConversionController/ConversionJob,
morphs, expands/collapses rapidly, changes focus to a controlled backing window,
completes or cancels, verifies terminal state and exercises success expiry/fade.
Every fourth cycle completes during morph; every fifth eligible cycle cancels;
the next cycle retries. Success dwell is shortened by invoking the production
expiry callback; the fade itself is real. No converters or actual source files
are used. Separate existing QML input tests exercise pointer/keyboard handling.

Desktop pixels are checked against a known backing color, render-target pixels
must be nonblank, and live cycles must produce new frames and different desktop
animation pixels. This is stronger than isVisible() or a valid object, but it is
not physical-display photometry, an occlusion-independent compositor oracle, or
proof across all monitors/driver states. Screenshots contain only synthetic test
window regions. This opt-in harness does not capture user documents.

| Baseline | Wall seconds | Process CPU seconds | Working set first/last MiB | GDI first/last |
|---|---:|---:|---|---|
| Qt default (5 complete) | 12.78 | 1.77 | 203.6 /205.2 | 20 /20 |
| D3D11 (5 complete) | 12.69 | 1.47 | 205.1 /206.5 | 20 /20 |
| OpenGL (100 complete) | 149.63 | 45.80 | 236.7 /257.5 | 32 /32 |
| Software (100 complete) | 147.59 | 10.44 | 155.6 /157.9 | 21 /21 |

OpenGL submitted 24,307 frames, software 8,158; Qt reports a 5ms vsync interval for
hardware here. CPU numbers include instrumentation/screenshots and differing
frame rates; they are not idle-use or GPU-utilization benchmarks. No GPU memory
counter was measured. OpenGL's working-set growth warrants longer-session
observation; these results cannot prove absence of a slow leak. First cycle
includes initialization, harness waiting and interaction, so its 2.26s OpenGL
duration is not launch latency. Actual pointer latency was not measured.

## Software anomalies and compatibility

Software uses Qt's CPU raster adaptation, not OpenGL RHI. Qt documents different
text-transform quality, partial-update behavior and unsupported shader effects.
Filewheel has no ShaderEffect here. Its circular progress uses two PathArcs with
coincident endpoints at zero and two half-arcs at full progress. That boundary
and software partial updates are candidates for the reported artifact, not a
confirmed diagnosis. The pill uses Rectangles/Text, not that circle. No speculative
geometry redesign was made. These UI-only tests do not reproduce the user's first
real conversion CPU workload or establish the source of pointer lag.

OpenGL requires a working driver (Qt documents OpenGL 2.1+ on Windows). Dynamic
OpenGL can fall back to Mesa on some systems, so the API name alone cannot prove
hardware acceleration; inspect QSG_INFO vendor/renderer too. Only this Arc desktop
was tested. Integrated/discrete switching, older drivers, Remote Desktop,
sleep/resume, mixed-DPI/multi-monitor and other GPUs remain unverified. Preserve
Widgets, explicit D3D11 and software startup options. Never switch APIs after
Quick initialization. A fatal native driver initialization failure cannot reliably
be caught by the Python fallback.

## Diagnostics and exact PowerShell commands

Automated checks: **45 focused tests passed**, scoped Ruff passed, and patch
whitespace checks passed. The full Windows suite reported **650 passed,
407 subtests passed, 11 skipped and 6 failed**. All six failures reproduced in an
isolated unmodified HEAD checkout: frozen path separators, LibreOffice path
separators, POSIX library-path semantics, ZIP backslash normalization, subprocess
locale decoding, and offscreen monitor matching. Those existing failures remain
outside F5; the full suite is not claimed green.

PyInstaller 6.22.3 produced the separate Windows onedir with exit code 0.
It includes qwindows.dll, Qt6OpenGL.dll, opengl32sw.dll and all three QML files.
The final packaged [self-test](f5/frozen-selftest.json) passed **33 checks / 26 real
conversion pairs**, including both Quick renders, transparent corners, source
hashes and collision protection. It used system Pandoc 3.13 and LibreOffice;
these optional tools were not bundled for F5. Frozen tests run from the package
directory with PYTHONPATH removed. Relocation outside the checkout and deployment
to another machine were not tested.

Delivered executable: `artifacts/f5/frozen/Filewheel/Filewheel.exe`; keep its
entire onedir. SHA256:
`BF605715D823C4E0FF27606E6FEDE4802E99C7469A6BAED61601A829CD0791A6`.
It was built from the F5 working tree before the local commit; no release or
automatic push is part of this milestone. The existing `dist/Filewheel` build
was preserved and must be rebuilt separately to acquire the change.

Quit Filewheel through its tray first, allowing any running job to finish or
cancel. Verify there is no owner; if using source Python also check Task Manager
for the Python tray process. A later launch forwards to the existing owner and
cannot change its environment or backend.

```powershell
Get-Process Filewheel -ErrorAction SilentlyContinue | Select-Object Id,Path
# Rebuild the usual dist location when desired:
powershell.exe -NoProfile -ExecutionPolicy Bypass -File .\scripts\build-windows.ps1
$exe = (Resolve-Path .\dist\Filewheel\Filewheel.exe).Path
# Or use the isolated F5 build delivered in artifacts\f5\frozen\Filewheel.

# Clear prior experiments in THIS PowerShell, then use the preferred OpenGL:
'QT_QUICK_BACKEND','QSG_RHI_BACKEND','QMLSCENE_DEVICE','QT_OPENGL',
'QSG_RHI_PREFER_SOFTWARE_RENDERER','FILEWHEEL_QUICK_RHI' | ForEach-Object {
    Remove-Item "Env:$_" -ErrorAction SilentlyContinue
}
$env:FILEWHEEL_UI_TRACE = '1'
& $exe --tray --ui-backend quick
Get-Content "$env:LOCALAPPDATA\Filewheel\logs\ui-renderer.jsonl" -Tail 12
```

Normal logs record PID, owner/forwarding outcome and effective API after actual
initialization/first frame. `FILEWHEEL_UI_TRACE=1` additionally records sequence,
presentation, animation transitions, creation/destruction, visibility/exposure,
platform-surface events, flags and recovery. Choose **Save UI trace snapshot** in
the tray when feedback disappears; it records current state and frame counters
without forcing rendering, capturing the desktop, or restarting. No filenames,
contents, coordinates or raw Qt error strings are logged. Local JSONL is capped
at 1MB with two backups and 10,000 events per surface; no per-frame file writes.
Unset the variable for normal operation. Snapshot collection requires tracing
to have been enabled at launch; it cannot retrofit earlier events.

For alternatives, fully quit between commands and clear the previous selection:

```powershell
Remove-Item Env:QT_QUICK_BACKEND -ErrorAction SilentlyContinue
$env:QSG_RHI_BACKEND = 'd3d11'
& $exe --tray --ui-backend quick

# After quitting: explicit OpenGL
$env:QSG_RHI_BACKEND = 'opengl'
& $exe --tray --ui-backend quick

# After quitting: CPU scenegraph
Remove-Item Env:QSG_RHI_BACKEND -ErrorAction SilentlyContinue
$env:QT_QUICK_BACKEND = 'software'
& $exe --tray --ui-backend quick

# After quitting: genuine Qt platform default
Remove-Item Env:QT_QUICK_BACKEND -ErrorAction SilentlyContinue
$env:FILEWHEEL_QUICK_RHI = 'default'
& $exe --tray --ui-backend quick

# Existing escape route, after quitting
& $exe --tray --ui-backend widgets
```

Repeatable native comparison (source or frozen), each 100 cycles:

```powershell
.\.venv-build314\Scripts\python.exe scripts/compare_quick_windows.py `
    --cycles 100 --output artifacts/f5/recheck --backends default opengl
.\.venv-build314\Scripts\python.exe scripts/compare_quick_windows.py `
    --executable $exe --cycles 100 --output artifacts/f5/frozen-recheck `
    --backends preferred d3d11 software
# Normal-operation diagnostics disabled, fresh output directory:
.\.venv-build314\Scripts\python.exe scripts/compare_quick_windows.py `
    --executable $exe --cycles 100 --output artifacts/f5/untraced-recheck `
    --backends preferred --no-trace
```

For Qt device details use `QSG_INFO=1` and `QT_FORCE_STDERR_LOGGING=1`; the runner
captures them. Treat raw Qt diagnostic output as private when collecting outside
the synthetic harness. Do not infer success from launch or API selection alone:
read `result.json`'s passed flag, cycle count and error, plus the captures.

Real-world acceptance still required: in ONE preferred-OpenGL tray session perform
at least 50 normal conversions (mix representative existing formats and short/long
jobs). Every fifth job expand/collapse and focus another app; cancel/retry at 10,
25 and 40; let success expire on at least 10 jobs. Include completion during morph,
Mouse3 and Send to. Check each output and visible progress, first-conversion
pointer responsiveness, and no artifact. Record sequence/PID/API; take a tray
trace snapshot immediately if anything disappears. Do not restart before capture.

## Primary sources (installed Qt6.12)

- [Qt Windows graphics and QSG_INFO](https://doc.qt.io/qt-6.12/windows-graphics.html)
- [QQuickWindow lifecycle and graphics selection](https://doc.qt.io/qt-6.12/qquickwindow.html)
- [Renderer API and thread guarantees](https://doc.qt.io/qt-6.12/qsgrendererinterface.html)
- [QWindow flags](https://doc.qt.io/qt-6.12/qwindow.html#flags-prop)
- [Software adaptation limitations](https://doc.qt.io/qt-6.12/qtquick-visualcanvas-adaptations-software.html)
