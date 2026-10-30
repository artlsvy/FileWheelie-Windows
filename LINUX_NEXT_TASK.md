# Current checkpoint: corrected single-file installer delivered

The user accepted ordinary Dolphin middle-click on Plasma. Default reversible
second-application setup is implemented. Progress overflow in the supplied home
screenshot was reproduced and fixed (source commit abc4fb8). Native KWin now
repositions progress on size/reuse/output/work-area changes; expanded details sit
16 logical pixels above the current panel, with no foreign-window movement.

Deliverable: dist/Filewheel-Linux-x86_64.AppImage (446 MiB). SHA-256:
95f70cf62f81c0e7cbd44a46081c0edbc5ef5a44806d973c5a32a6a49619241c

Bundled Python/Qt/converters/FFmpeg/Pandoc/LibreOffice; no private Dolphin needed.
Current checks: 127 source tests passed /4 intentional skips; Ruff/compile/diff
pass. Native dark animated and light reduced-motion six-stage checks pass.
Final frozen onedir, extracted AppImage, FUSE AppImage and offline Debian12 each
pass 40 checks /32 conversion pairs. Actual final install/upgrade/removal passes
in isolated XDG; 26 Dolphin MIME associations and document preservation verified.
See linux-evidence/final-installer.json and LINUX_USE.md.

Next user acceptance: finish current jobs, Quit the OLD tray, install the dist/
AppImage and reopen Filewheel. In ordinary Dolphin start a conversion, expand
progress near the bottom/taskbar, collapse/re-expand, then inspect failure details
if available. The old tray's script cannot acquire the fix without restarting.
Do not force-kill running jobs. Actual simultaneous mixed-DPI/other panel layouts
remain manual acceptance; native current-host fractional-scale checks passed.

This task is complete as far as automated/current-host checks permit. GNOME work
was deferred by the user until Dolphin completion; evaluate it separately next,
without claiming global native Wayland Mouse3 support. Preserve private browser
experiments, all converters, Windows behavior and fallback invocation paths.
No automatic push. Do not commit unrelated user assets under assets/ui/.
