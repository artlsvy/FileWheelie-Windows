---
name: filewheel-glass
description: Design, refine and measure Filewheel's native Qt Quick radial glass UI, including its hover lens, readable fallbacks and Windows overlay constraints. Use for Filewheel QML/PySide6 visual work, not HTML/CSS or conversion engines.
---

# Filewheel native glass

Use the installed Liquid Glass skill only as optical inspiration. Filewheel is a
native PySide6 utility: no DOM, CSS, WebView, Electron, desktop capture or Apple
assets. Work from `docs/PERFORMANCE_ARCHITECTURE.md` and the current
`src/filewheel/ui/qml/GlassWheel.qml` / `Lens.qml`; those files are the material
source of truth. Default QWidget remains available until native acceptance.

## Material and legibility

- One 220 px circular material inside a 240 logical pixel transparent window.
  Forest/ivory/brass, one continuous outer rim, restrained upper reflection and
  raised selected lens. Avoid separate outlined wedges and rectangular shadows.
- Light foreground `#20392F`, ivory material `#F4F0E5`, brass `#65532A`.
  Dark foreground `#F3ECDD`, forest material `#182C24`, brass `#D6BF83`.
  Default material alpha about 0.85–0.88; the lens can be more opaque for depth.
  Low-effects surfaces are opaque. Keep text fully opaque and sharp.
- Label size 14 logical pixels, at most two lines with elision. Emphasize via
  transform scale 1.04 and the lens alone, without moving actual hit regions.
  Do not reintroduce independent label dots that can disagree with the lens.
  Esc/Back/Cancel/Done belong in the center. Keep engine logs in escaped tooltips,
  not the wheel face. Progress/result words should fit at a glance.
- Check sampled rendered text/material contrast >=4.5:1 over black and white,
  both themes and the selected lens. Also inspect detailed light/dark/media/list
  backgrounds. A pleasing image on a flat dark gradient is insufficient evidence.

## Lens and input

- Stable hit geometry: center (120,120), inner action radius 40, outer radius 110.
  `quick_geometry.hit_test` owns sectors; optics never change click targets.
- Lens stays within the annulus (centerline r76, cap radius <=28). Outer/inner
  arcs are concentric and each semicircular end uses two quarter arcs. Narrow
  menus adapt thickness only when option count changes. All rotating Shapes use
  explicit local (0,0), TopLeft origin translated to wheel (120,120). Static path
  geometry changes with option count only. Animate the item rotation/opacity,
  not paths, fonts, textures or layout each frame.
- Use shortest-arc movement, about 145 ms OutCubic; appearance 70 ms and label
  emphasis 120 ms. Highlight selection immediately; transitions must not defer
  choosing, backing or rendering a new menu level. Stop animation when idle.
- Honor `FILEWHEEL_REDUCED_MOTION=1` with immediate transitions and
  `FILEWHEEL_LOW_EFFECTS=1` with opaque/static simple effects. Color follows Qt's
  light/dark appearance. Keep the static hover fallback usable.
- Test actual QML pointer and keyboard events as well as pure state methods:
  MouseArea has a `wheel` signal, so resolve the Python session through the root
  alias. Direct session tests alone previously missed that shadowing bug.

## Window, worker and performance constraints

- Request alpha before the first Quick window; clear transparent, frameless,
  no OS rectangle shadow. Reuse the window. Share physical-to-logical monitor
  mapping and work-area clamping with QWidget; never divide global coordinates
  by one DPR. Test mixed scaling and negative monitor origins on Windows.
- Selection also dismisses 75 ms after circular mouse leave, with a current-
  cursor logical-coordinate recheck. Center/sector motion and quick re-entry stay
  open. No new global hooks. Conversion/results never auto-dismiss on leave.
- Selection dismisses on Escape/outside/focus loss; conversion/results persist
  topmost until explicit action. Native hide must finish a transient invocation
  once. Retain the conversion job until its owned worker/cleanup completes.
- Consume only the shared controller's TargetResolution. Preserve Mouse3/touchpad
  trust and mandatory injected-candidate consent. Use the existing capability
  registry and ConversionJob; visual work cannot alter converter/file safety.
- No perpetual animation, per-frame file writes, desktop sampling, blur stacks or
  Python render-thread application work. Shader effects require measured benefit
  and software fallback; the current retained-shape lens needs no shader.
- Use `scripts/benchmark_ui.py` serially for widgets and quick at 240 px. Measure
  first-render startup, peak RSS, pointer/level latency, frame interval tails and
  heartbeat under spawned work. Widget paint completion, Quick GUI preparation
  and frameSwapped queued presentation are different boundaries. Bind traced
  input to its synchronized scene, never an arbitrary next swap. Offscreen
  software rendering cannot establish D3D11/display FPS.
- Render current visual proof with `scripts/render_glass_preview.py`; label its
  backdrops as synthetic. Keep native Windows visual/focus/frozen validation
  pending until actually performed. Preserve the widget startup escape route.
