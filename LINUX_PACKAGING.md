# Linux personal package

The AppImage contains a private Python3.14/Qt runtime, existing converters and
native FFmpeg/Pandoc/LibreOffice/Tesseract. It is a portable application with an explicit
per-user installer, not a system package. The optional DEB reuses the same onedir
payload. Neither replaces the system Dolphin or grants global Wayland input.

## Current single-file installer — OCR repair

Use `dist/Filewheel-Linux-x86_64.AppImage` (476,301,816 bytes, 454 MiB).
SHA-256:

```text
56656b2dba024e4999bd9ce0b7c03002345bf6e19ecca14d6f66dd7f6d3109a1
```

Source repair: `7b1cafc`. Frozen onedir, extracted AppImage, ordinary FUSE launch
and offline Debian12 each pass **44 checks**, including the existing 32 conversion
pairs and three real OCR/picture-only conversion cases. Actual final install,
upgrade and removal pass in isolated XDG directories, preserving documents and
26 Dolphin registrations. Source suite: **140 passed /4 intentional skips**;
Ruff/compilation pass. Evidence: `linux-evidence/final-installer.json`. Older build
artifacts below are historical; distribute the file under dist/ above.

## OCR implementation

The new Linux build bundles Tesseract, English recognition data, orientation data
and its non-glibc ELF dependencies. Image-only PDF→MD/DOCX dispatches to this local
backend; Windows keeps its native OCR helper. External-tool library isolation,
process-group cancellation, per-page 60s deadline, existing page/image/output limits,
staging cleanup and collision-safe publication stay in use. The wrapper caps OCR
OpenMP threads at 1. Language data is passed explicitly from the bundled tree; no
host Tesseract or runtime network download is needed.

The release gate now requires real scanned-PDF DOCX and Markdown content checks,
page image linkage, a picture-only PDF check, and `ocr_source=bundled`.
Tesseract/English/orientation apt versions and distribution copyright notices are
included in tools/BUILD-INFO.json and tools/distribution-notices. Tesseract usage
was checked against its [official command-line documentation](https://tesseract-ocr.github.io/tessdoc/Command-Line-Usage.html).

## Previous single-file installer (superseded by OCR repair)

Use `dist/Filewheel-Linux-x86_64.AppImage` (467,491,320 bytes, about 446 MiB).
Only that file is needed for installation; its checksum and build manifest are
optional verification sidecars. SHA-256:

```text
95f70cf62f81c0e7cbd44a46081c0edbc5ef5a44806d973c5a32a6a49619241c
```

Progress placement fix source: `abc4fb8`. The build contains no private Dolphin.
Frozen onedir, AppImage extract-and-run, ordinary FUSE AppImage and offline
Debian12 runtime checks each passed 40 checks /32 actual conversion pairs. Actual
AppImage install→upgrade→remove passed in isolated XDG directories, including
26 automatic Dolphin associations and document preservation. Source tests passed
127 /4 intentional same-format skips. Evidence: `linux-evidence/final-installer.json`.
Native source progress placement passed at 1.55 compositor scale; the updated
frozen GUI still warrants a normal user interaction check after tray restart.

## Build

On x86_64 Linux, install Docker, Python3, binutils (`readelf`) and dpkg tools (for
DEB only). The build installs dependencies inside its container, not into the
host. No Python development environment is needed on an end-user machine.

```sh
./scripts/build-linux.sh --output build/linux-release \
  --artifact-name Filewheel-Linux-x86_64.AppImage
# Add --deb only when a Debian/Ubuntu package is also wanted.
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
chmod +x Filewheel-Linux-x86_64.AppImage
./Filewheel-Linux-x86_64.AppImage
```

The first uninstalled GUI launch offers **Install for this user**, **Run without
installing**, and **Cancel**. Installation copies the original AppImage into
`$XDG_DATA_HOME/filewheel/app/Filewheel.AppImage` (normally `~/.local/share`),
creates an application entry, icon and Dolphin context action. It preserves
your normal primary/default applications. It requires no sudo or tool downloads;
login startup is off by default. On Plasma with Dolphin/gio/kbuildsycoca6, it adds Filewheel
as the second application for supported input MIME types. This is an owned,
reversible association change; inspect/disable/re-enable with `--dolphin` as
documented in LINUX_USE.md.
Use the tray's file picker on desktops where a file action is unavailable.
An installed app launcher starts the tray without needing a file argument.

Explicit commands (replace the single filename):

```sh
./Filewheel-Linux-x86_64.AppImage --install-user
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
./Filewheel-Linux-x86_64.AppImage --appimage-extract-and-run --install-user
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
./Filewheel-Linux-x86_64.AppImage --appimage-extract-and-run --self-test --ui-backend quick
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

The current default stock-Dolphin installer is `dist/Filewheel-Linux-x86_64.AppImage`
(build reports and AppDir: `build/linux-final-installer`). Older artifacts under
`build/linux-native-dolphin` predate the progress-boundary fix.
Its installer sets Filewheel second for available input MIME types on Plasma,
without replacing the normal first/default application. See LINUX_USE.md for
status/disable/re-enable commands and rollback behavior. The private-browser
artifact remains available for experiments but is no longer the normal Dolphin
route. `gio`/`kbuildsycoca6`/Dolphin are discovered host desktop tools and run with
frozen library/plugin paths sanitized; they are not bundled from another KDE ABI.
