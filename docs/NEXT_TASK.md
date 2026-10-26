# Next task: Windows acceptance of the optional glass renderer

The performance/glass task is implemented and Linux-checked. Do not repeat the
prototype or migrate languages. QWidget remains the working default; Quick is
an explicit experimental choice. See PERFORMANCE_ARCHITECTURE.md for actual
measurements and their limits, and GLASS_UI.md for exact commands/checklists.

1. On Windows 11, exit the current tray owner, build the updated onedir with
   scripts/build-windows.ps1, then run `Filewheel.exe --self-test --ui-backend quick`.
   Confirm actual nonblank QML rendering/alpha and converter results. Keep the
   complete onedir tree and repeat away from the development checkout/venv.
2. Launch `Filewheel.exe --tray --ui-backend quick`. Exercise physical Mouse3,
   Send to, lens movement/selection, keyboard/Back/Escape, focus/outside dismissal,
   persistent conversion/results, light/dark, mixed DPI and monitor edges.
3. Compare source/frozen startup and resident stages using GLASS_UI.md's opt-in
   benchmark procedures. Record actual graphics backend, power mode, sample
   counts, frame tails and memory. Linux software frames cannot prove D3D11 FPS.
   Keep the default unchanged until native acceptance justifies promotion.
4. Complete the earlier native queues: D-020 large-PDF Cancel -> same-file retry
   -> Cancel/tray Quit/relaunch; D-021 laptop three-finger tap opt-in with mandatory
   exact-path consent even when physical confirmation is disabled. Check physical
   middle-click, unrelated apps, invalid targets and lower-integrity rejection.

Current evidence: Python 3.14.4 / Qt 6.12.0 Linux offscreen suite **514 tests and
406 subtests passed**; actual source Quick render plus 11 converter-pair smoke
passed; wheel/QML-resource and packaging seams checked. Windows Quick/frozen,
newer touchpad and cancellation acceptance have not been performed here.
The renderer shares the existing controller/registry/worker, with no conversion
or trust-policy changes. The native design skill is
.agents/skills/filewheel-glass/SKILL.md. Do not push without authorization.
