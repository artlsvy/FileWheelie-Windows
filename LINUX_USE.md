# Linux source preview

This branch now supports the shared glass UI and real local conversions on Linux.
It is a source preview, not the finished cross-distribution installer. Python 3.14
and the desktop dependencies are required until packaging is complete.

## Explicit file (no custom file manager required)

From a desktop terminal in the checkout, using the prepared environment:

```bash
PYTHONPATH=src .venv-ui/bin/python -m filewheel --gui --ui-backend quick -- "$HOME/path/to/file.png"
```

Use a real absolute regular-file path. One file at a time; source symlinks,
directories and special files are rejected. Formats depend on installed codecs
and tools. FFmpeg supplies media, LibreOffice supplies Office→PDF, and Pandoc is
optional for Markdown publishing. Linux OCR is not implemented.

## Accepted private Dolphin route (KDE Wayland)

After building/extracting prototypes/dolphin-bridge, quit the existing Filewheel
tray owner and run:

```bash
PYTHONPATH=src .venv-ui/bin/python -m filewheel --tray --ui-backend quick \
  --private-dolphin "$PWD/build/dolphin-probe/bin/dolphin" \
  --dolphin-folder "$HOME"
```

Middle-click a file in **that private Dolphin window**, then select its category
and output. To MD starts directly. The shared controller revalidates the native
path before showing the wheel; conversion still uses the same safe worker and
output publication as Windows. The tray owns work and closes its private child
on Quit. Enable wheel controls forwarding; disabling forwarding in this prototype
does not restore normal file middle-click opening inside the private window.
Use ordinary Open or the unchanged installed Dolphin for that behavior.

Private Dolphin has isolated config/cache/state/data, not your regular Dolphin
preferences. Its source patch is opt-in and version-specific. Stock Dolphin,
GNOME and other Wayland file managers do **not** acquire Mouse3 support from this
command. No system file manager or persistent KWin plugin is replaced/installed.

KWin bridge scripts live only for the owner session. They obtain the current
cursor and position only Filewheel PID/title-matched surfaces; progress stays
near the original monitor edge. Other compositors can use explicit paths, with
compositor-chosen placement. They are not claimed cursor-centered/Mouse3-verified.

User-verified on the current KDE Wayland desktop: six exact-URI clicks across two
private tabs, near-cursor Quick wheel, PNG→JPEG, TXT→MD, persistent progress and
tray Quit. Source hashes/output content were independently checked. Mixed DPI,
large/grouped folders, long-job cancel/retry and frozen packaging need further
native acceptance. Detailed evidence and test counts are in LINUX_STATUS.md.

## Single-file Linux preview

Installer/build details and compatibility boundaries are in
[LINUX_PACKAGING.md](LINUX_PACKAGING.md). The AppImage offers a per-user installer;
no Python/pip is required. The optional matched private-Dolphin variant exposes
its browser through an explicit tray action. The core AppImage's context action
is a fallback and is not native Mouse3 parity on other file managers/desktops.

## Ordinary Dolphin middle-click (default installer integration)

The user has verified the native second-application route on Plasma. New installs
and upgrades now configure it automatically for input MIME types supported by
available engines. Your existing normal/default app stays first; Filewheel goes
second. No patched browser, global mouse hook or resident file-identity guess is
needed. Start Filewheel from the app launcher to keep a warm tray owner; middle-click
also launches it when it is not already running. Use ordinary Dolphin windows.

After quitting the old tray instance, install/upgrade the new core AppImage:

```sh
./build/linux-native-dolphin/*.AppImage --install-user
~/.local/share/filewheel/app/Filewheel.AppImage --tray --ui-backend quick
```

The first GUI install explains the association change. For source or DEB usage,
`--integration install` performs the same setup for that launch command. No setup
runs on every popup. Installation keeps original per-entry values in an owned
journal under `$XDG_CONFIG_HOME/filewheel`; removal restores them if untouched,
and preserves later user edits while removing Filewheel's ID. Legacy owned desktop
entries migrate safely; foreign/modified entries and symlinks remain protected.

Inspect, disable while keeping the launcher, or re-enable:

```sh
~/.local/share/filewheel/app/Filewheel.AppImage --dolphin status
~/.local/share/filewheel/app/Filewheel.AppImage --dolphin remove
~/.local/share/filewheel/app/Filewheel.AppImage --dolphin install
```

Explicit disable persists across upgrades. Uninstall restores managed associations
without changing documents/results. Automatic setup currently requires Plasma,
Dolphin, `gio` and `kbuildsycoca6`; skipped types/reasons print during installation.
No existing handler → skip, so Filewheel is not installed as that type's first app.
An existing Filewheel default or explicit user exclusion is preserved. Preferences
are keyed by MIME, so related extensions can share a route; unsupported extensions
still fail through the normal controller/registry. Archive browsing or file-tab
mode can take Dolphin's folder/tab branch instead. GNOME support remains separate
and unimplemented; this adds no GNOME hook or placement adapter.
