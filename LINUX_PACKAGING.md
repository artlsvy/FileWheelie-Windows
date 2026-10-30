# Linux preview packaging

The AppImage contains a private Python3.14/Qt runtime, existing converters and
native FFmpeg/Pandoc/LibreOffice. It is a portable application with an explicit
per-user installer, not a system package. The optional DEB reuses the same onedir
payload. Neither replaces the system Dolphin or grants global Wayland input.

## Build

On x86_64 Linux, install Docker, Python3, binutils (`readelf`) and dpkg tools (for
DEB only). The build installs dependencies inside its container, not into the
host. No Python development environment is needed on an end-user machine.

```sh
./scripts/build-linux.sh --output build/linux-release --deb
```

Output must be a new directory. All build-time downloads are hash checked. The
51-package Linux wheel lock uses Python3.14 binary wheels. CPython3.14.10 is built
inside Ubuntu22.04. Native apt versions, image ID, source snapshot/hash, dependency
lock and every shipped ELF's GLIBC requirement are recorded. Mutable apt mirrors
and unsigned AppImages mean this is **not bit-for-bit reproducible or a signed
release**; the builder explicitly reports that limitation. CI is manual-only and
does not publish. Docker caches can accelerate repeated builds.

To build the optional current-host private-Dolphin variant:

```sh
./scripts/build-linux.sh --output build/linux-private-preview \
  --private-dolphin-prefix build/dolphin-probe
```

Build the isolated prefix first using `prototypes/dolphin-bridge/README.md`.
This adds a whole private prefix, not a lone `dolphin` executable. That variant
requires the tested Kubuntu26.04 Qt/KF6 stack and KWin APIs; it is **not** the
broad-compatibility AppImage. Its tray includes an explicit action to open the
private file browser. Middle-click works in that browser, not stock Dolphin.
The app never silently launches it on normal startup. The source flag remains:
`--tray --ui-backend quick --private-dolphin bundled`.

## Run/install/remove

```sh
chmod +x Filewheel-*.AppImage
./Filewheel-*.AppImage
```

The first uninstalled GUI launch offers **Install for this user**, **Run without
installing**, and **Cancel**. Installation copies the original AppImage into
`$XDG_DATA_HOME/filewheel/app/Filewheel.AppImage` (normally `~/.local/share`),
creates an application entry, icon and Dolphin context action. It does not change
MIME defaults, require sudo, download tools, or enable login startup by default.
Use the tray's file picker on desktops where a file action is unavailable.
An installed app launcher starts the tray without needing a file argument.

Explicit commands (replace the single filename):

```sh
./Filewheel-preview.AppImage --install-user
~/.local/share/filewheel/app/Filewheel.AppImage --gui --ui-backend quick -- /absolute/input.png
~/.local/share/filewheel/app/Filewheel.AppImage --startup install
~/.local/share/filewheel/app/Filewheel.AppImage --startup remove
~/.local/share/filewheel/app/Filewheel.AppImage --uninstall-user
```

Quit the tray before upgrading/removing. Upgrade uses the same install command;
a checksum manifest protects modified/unowned binaries and launchers. Uninstall
preserves preferences/logs and all user documents/results. There is no broad
recursive deletion. Executable install paths with `=` or `%` are refused because
of desktop parser restrictions; these characters in input filenames are supported.

If FUSE is unavailable, prepend `--appimage-extract-and-run` to app arguments.
For example:

```sh
./Filewheel-preview.AppImage --appimage-extract-and-run --install-user
```

This extracts temporarily, whereas a working FUSE mount avoids unpacking on each
launch. The installed desktop entry requires FUSE for normal launching; on a
FUSE-free machine prefer the DEB or extract once and install source-like desktop
integration using the extracted executable's `--integration install` command.
Do not delete that extracted payload while its launcher is installed.

Optional Debian/Ubuntu package:

```sh
sudo apt install ./filewheel_0.3.0~linux1_amd64.deb
/opt/filewheel/filewheel --integration install
# Remove that user's extra actions before package removal:
/opt/filewheel/filewheel --integration remove
sudo apt remove filewheel
```

DEB maintainers do not run GUI code as root. A per-user integration created by one
installation is preserved/refused by another, rather than overwritten silently.

## Scope and acceptance

Core target: glibc2.35+ mainstream x86_64 Linux with a functioning desktop, fonts,
OpenGL/EGL or Qt software rendering, D-Bus, and Qt-compatible XCB/Wayland system
libraries. ARM64, musl/Alpine and universal file-manager Mouse3 are not claimed.
GLIBC symbol audit alone does not prove distro/desktop compatibility. Test the
actual frozen app on native desktops (including mixed DPI) before release claims.
The private Dolphin variant has additional native KDE runtime requirements and exact-version
KDE dependencies; keep it separate from the core support claim.

Run the actual frozen smoke without a display, network or Python installed:

```sh
QT_QPA_PLATFORM=offscreen QT_QUICK_BACKEND=software \
FILEWHEEL_LOG_DIR=/tmp/fw-appimage-check \
./Filewheel-preview.AppImage --appimage-extract-and-run --self-test --ui-backend quick
cat /tmp/fw-appimage-check/self-test.json
```

Real native acceptance: file action/explicit path; wheel placement and transparent
corners; progress collapse/expand; cancel→retry; repeated invocation; Quit; then
install/upgrade/remove. For the matched private-Dolphin variant also test duplicate
names across tabs, Unicode, scrolled/grouped/large folders and touchpad Mouse3.
Other desktops have explicit invocation fallback; they have no demonstrated
native Mouse3 adapter yet.

## Redistribution

Keep LICENSE, collected package notices, complete native tool resources and the
Filewheel source snapshot together. Filewheel and PyMuPDF are AGPL; FFmpeg,
LibreOffice, Pandoc, Qt and their dependencies have their own obligations.
Before public redistribution, provide corresponding source/build materials for
all copyleft native components as required, audit notices and library choices,
and retain exact apt/tool versions. A source URL or a Python wrapper alone does
not establish compliance. This build is currently a personal preview, not a
legal compliance certification or a security update service.

The runtime-only Debian12 smoke image is reproducible from
`packaging/linux/RuntimeSmoke.Dockerfile`. It contains standard GL/EGL, font,
D-Bus and Wayland client packages, **no Python, FFmpeg, Pandoc or LibreOffice**.
Run the frozen AppDir with `--network none` and validate its report using
`packaging/linux/verify_smoke.py`. Optional-family skips are forbidden for release
checks, even though a partial source environment can legitimately omit tools.
Neither this nor an offscreen container establishes native GNOME/Xfce behavior.
