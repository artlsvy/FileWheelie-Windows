# Glass UI correction — Phase 1 review build

**Phase 2 has NOT started. Stop here until the user explicitly approves this UI
in a subsequent message.** Tests, screenshots, automatic resume and silence do
not constitute approval. No converter pairs or Markdown navigation changed.

## Evidence and corrections

The three supplied Windows screenshots were visually inspected before changes:
`/home/lsvy/1.jpg` (Text), `/home/lsvy/2.jpg` (Image), `/home/lsvy/3.jpg` (Docs).
They show a detached glare stroke, inconsistent contours and label-relative dots.

The glare Shape used implicit bounds/default rotation origin rather than the
explicit local origin used by the lens. It now has a zero-sized local coordinate
space at wheel center (120,120), TopLeft origin and exact polar circle endpoints.
Static reflection arcs also use the same center. The raised lens uses concentric
inner/outer arcs and two explicit quarter-circle arcs per rounded end. One subtle
outline replaces the duplicate inner edge/displaced shadow. Crowded menus adapt
thickness when their count changes; sector motion rotates rigid geometry.
Shortest-path motion uses the currently displayed rotation even when interrupted.
The yellow dots were removed. Hit regions and the 240 logical pixel size remain.

Selection stages dismiss after a **75 ms circular leave debounce**, not just a
rectangular MouseArea exit. Re-entry cancels it; timeout rechecks QCursor mapped
through QWindow's logical coordinates. Center Back/Esc and sector changes stay
open. Pending timers stop on reopen, finish and conversion start. Progress and
results retain their existing persistent/topmost behavior. There is no extra
mouse hook, converter change or modification to Mouse3 target trust rules.

The Quick smoke check now accepts a DPI-scaled raster: 240 logical pixels become
360 physical pixels at 150%. This fixes a self-test false failure, not a change
to menu coordinates or Windows monitor selection.

## Actual before/after renders

These are **real Qt Quick software-renderer captures** on Kubuntu, composited
onto synthetic dark/light document lists. They are not Windows screenshots or
proof of Windows compositing. Raw images retain transparent corners.

- [Before: Text / Image / Docs](ui-phase1/before/references.png), rendered with
  the unmodified QML pair from `f0e3203`.
- [After at 100%: same three hover states](ui-phase1/after-100/references.png).
- [After at 150%: same states](ui-phase1/after-150/references.png).
- [Every sector for 2, 3, 4, 5, 6 and 8 options](ui-phase1/after-100/all-sectors.png).
- [150% option matrix](ui-phase1/after-150/all-sectors.png).
- [Reduced-motion light capture](ui-phase1/after-100/reduced-motion-light.png).

The individual RGBA snapshots are beside each board, for example
`docs/ui-phase1/after-100/ref1-text-dark.png` and
`docs/ui-phase1/after-150/ref3-docs-light.png`. The before/after reference boards, option matrices and reduced-motion captures
were visually inspected. Software capture cannot certify native D3D11 antialiasing.

Reproduce corrected previews from the checkout:

```bash
QT_QPA_PLATFORM=offscreen QT_QUICK_BACKEND=software PYTHONPATH=src \
  .venv-ui/bin/python scripts/render_glass_phase1.py --output-dir /tmp/glass-100
QT_QPA_PLATFORM=offscreen QT_QUICK_BACKEND=software QT_SCALE_FACTOR=1.5 PYTHONPATH=src \
  .venv-ui/bin/python scripts/render_glass_phase1.py --output-dir /tmp/glass-150
```

To reproduce the old scene without reverting source work:

```bash
mkdir -p /tmp/filewheel-before-scene
git show f0e3203:src/filewheel/ui/qml/GlassWheel.qml > /tmp/filewheel-before-scene/GlassWheel.qml
git show f0e3203:src/filewheel/ui/qml/Lens.qml > /tmp/filewheel-before-scene/Lens.qml
QT_QPA_PLATFORM=offscreen QT_QUICK_BACKEND=software PYTHONPATH=src \
  .venv-ui/bin/python scripts/render_glass_phase1.py --scene-dir /tmp/filewheel-before-scene --output-dir /tmp/glass-before
```

The script uses explicitly labeled preview fixtures, never real conversions or
new production capabilities. It exposes the window, positions the pointer and
asserts the requested hover state before capturing; queued cursor events cannot
silently turn the proof into repeated unselected wheels.

## Run the correction on Windows 11

Once this commit is in the Windows checkout, **quit the current tray owner first**.
A second invocation forwards to the owner, so it cannot replace an old renderer.
For a source run in the existing Python 3.14 environment:

```powershell
.\.venv-filewheel\Scripts\python.exe -m pip install --no-deps -e .
.\.venv-filewheel\Scripts\python.exe -m filewheel --tray --ui-backend quick
```

For the updated standalone application:

```powershell
powershell.exe -NoProfile -ExecutionPolicy Bypass -File .\scripts\build-windows.ps1
& .\dist\Filewheel\Filewheel.exe --self-test --ui-backend quick
Get-Content "$env:LOCALAPPDATA\Filewheel\logs\self-test.json"
& .\dist\Filewheel\Filewheel.exe --tray --ui-backend quick
```

Existing Send to and Mouse3 reach that owner. An explicit file invocation is:

```powershell
& .\dist\Filewheel\Filewheel.exe --gui --ui-backend quick -- "C:\path\to\sample.pdf"
```

The QWidget fallback remains available after quitting the owner:

```powershell
& .\dist\Filewheel\Filewheel.exe --tray --ui-backend widgets
```

## Windows acceptance still required

1. Repeat Text/Image/Docs states matching the supplied screenshots. Check the
   lens stays centered over its label and the glare follows the same wheel rim.
   Sweep rapidly, including last-to-first, and click while motion is in progress.
2. Move into a transparent corner without clicking: selection closes after about
   75 ms. Repeat beyond the window rectangle; re-enter quickly before timeout.
   Check center/sector movement never dismisses, and reopening resets navigation.
3. Check formats, center Back, Escape, outside click, focus loss and keyboard.
4. Start a conversion, then move outside. Progress must stay visible, without
   cancellation; the result must also persist until explicit dismissal. Check
   Cancel, a same-file retry and tray Quit as in the earlier native queue.
5. Check light/dark at 100% and 150%, monitor edges/mixed DPI, a negative-origin
   monitor if available, alpha corners and native shadow/artifact behavior.
6. Repeat reduced motion (`$env:FILEWHEEL_REDUCED_MOTION='1'` before start), then
   remove it for normal motion. Repeat in the rebuilt onedir away from the venv.

No native Windows run or build occurred on Kubuntu. Native acceptance remains
pending; this delivery is for user review, not authorization to begin Phase 2.
