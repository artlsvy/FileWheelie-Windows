# Native Dolphin complete; next: bounded GNOME feasibility

User verified Plasma/stock Dolphin's second-application middle-click works.
The default AppImage installer and --integration install now configure this
route automatically for available engine input MIME types, preserving the first
application. Existing normal handlers remain first; Filewheel is second.
No private Dolphin, input hook, selected-file guessing or converter changes needed.

Actual checks: 114 tests passed/4 intentional media skips; final frozen AppImage
40 checks/32 actual pairs. Real KDE KApplicationTrader verification passes for
PNG/PDF before/setup/remove in isolated XDG. Frozen install→disable→upgrade→
re-enable→uninstall passes for26 MIME types, with defaults unchanged. The actual
installed profile also has Filewheel second for26 types with every primary app
unchanged. Source/CLI compile and scoped Ruff pass. See new native-Dolphin evidence
and LINUX_USE.md for status/disable/re-enable commands. Symlinks, foreign ownership,
late user edits, interrupted setup and concurrent management are protected.

Current artifact: build/linux-native-dolphin/*.AppImage. Installed copy is
~/.local/share/filewheel/app/Filewheel.AppImage. Old private-browser artifacts and
prototype code are preserved but no longer required for ordinary Dolphin.
A user-created untracked assets/ui/wheel.jpg was present before this task; leave
it untouched and uncommitted. Source archive assembly excludes unrelated untracked
assets. No commits pushed; branch feat/linux-port.

GNOME is deferred until this completed milestone. The user has no GNOME desktop.
Next investigate exact target Nautilus/GNOME versions and whether their native
middle-click activation can supply the actual file URI through a supported API.
Do not assume a MenuProvider/context-menu extension supplies a Mouse3 callback,
or that a GNOME Shell button observer knows the file. File identity and native
Wayland popup placement are separate requirements. A container/offscreen run can
check file-manager code but cannot prove GNOME compositor focus/placement/input.
Do not install/replace the host desktop, change file defaults, patch Nautilus or
add root input permissions implicitly. Report precise API/environment blockers
if native GNOME acceptance requires a real guest/session. Preserve working Plasma,
Windows, converter engines, Send to, UI and all private prototype infrastructure.
