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
