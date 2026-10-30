# Filewheel Linux port — execution plan

Planning baseline: `48a28c4` (Windows v0.3 release line), 2026-10-30.
Branch: `feat/linux-port`. This is the original plan; current progress is recorded
in LINUX_STATUS.md and the checkpoint below.
Implement one numbered milestone at a time; test and commit it before continuing.
Keep one shared codebase and merge the port back when stable; do not maintain a
separate permanent Linux fork. Do not push or change the Windows release workflow.

## Product and packaging decisions

- Preserve the approved glass wheel, progress pill, tray, preferences and current
  image/document/Markdown/**audio/video** engines. Keep Python 3.14 and PySide6;
  this is a platform port, not a rewrite. Windows OCR stays Windows-only; hide or
  clearly reject scanned-document OCR on Linux rather than inventing support.
- **First acceptance target: the user's laptop on native Wayland.** Do not ask
  the user to switch to X11 or count an X11-only build as meeting this target.
  The workspace's active graphical session is confirmed KDE/Wayland and Dolphin
  is installed; verify the laptop's desktop/file manager before choosing its
  bridge, rather than assuming the SSH environment identifies the chat device.
  Then expand to GNOME/Nautilus and Xfce/Thunar. Track desktop, compositor version,
  file manager and X11/Wayland separately from distro.
- Primary single download: `Filewheel-<version>-x86_64.AppImage`, with an explicit
  **Install for this user** / uninstall integration mode. AppImage is a portable
  bundle, not a conventional package installer; installation must be implemented.
  Optional secondary `.deb` uses the same payload for Debian/Ubuntu users. Neither
  format makes global middle-click work on every desktop automatically.
- Build a private Python/Qt runtime; users need no Python/pip. Ship native Linux
  FFmpeg/Pandoc and a complete LibreOffice tree for converter parity, retaining
  notices/hashes. Start development with discovered system tools, then validate
  bundled binaries. Do not copy Windows EXEs/DLLs or silently omit media support.
- Initial compatibility goal: Ubuntu/Kubuntu 22.04+, Debian 12+, plus tested recent
  Fedora, Mint, Arch and openSUSE. These are **targets**, not verified promises.
  Determine the actual glibc/libstdc++ floor from every shipped binary. The local
  PySide6 6.12 wheel is manylinux_2_34; the host is Ubuntu 26.04/glibc 2.43, so
  building only on this host would undermine broad compatibility. Use a pinned
  Ubuntu 22.04-compatible build container and audit the resulting ELF dependencies.
  ARM64 is a separate later build; Alpine/musl is not an initial target.

## 1. Prove native Wayland interaction first — bounded feasibility gate

On the laptop, prove **middle-click an unselected file in a native Wayland file
manager -> that exact file's path -> wheel near the event point**. Test three
independent requirements: event capture, file identity, and popup placement/focus.
Success at only one or two is not success for the interaction.

- Record desktop/compositor/file-manager versions and verify the file manager is
  native Wayland. XWayland, pynput/X11 hooks and `QT_QPA_PLATFORM=xcb` do not grant
  access to native Wayland input. Do not make them the laptop solution.
- Investigate at most two routes, in order: **(A)** a supported file-manager
  extension that can receive the actual middle-click and exact item URI;
  **(B)** a narrowly scoped compositor bridge for event/coordinates/activation,
  paired with bounded AT-SPI file-item hit testing. On Plasma, inspect the
  installed KWin scripting/effects API, not an old example's API names. Neither
  a Dolphin context-menu service nor a KWin script is assumed to expose a global
  button hook. If either required API is missing, record that immediately.
- Prefer user-installable, reversible scripted integration. A compiled KWin
  plugin may depend on its precise version/ABI and runs inside the compositor;
  document compatibility, failure risk and rollback before choosing it. Do not
  patch/rebuild Dolphin or KWin as an implicit porting step. The Filewheel backend
  and converters remain outside the compositor.
- Authenticate/bound any bridge-to-app messages to the current user/session;
  include fresh event identity, file-manager provenance and coordinates. A bridge
  reporting a click/window does not prove the hovered file. Accessibility names,
  selected items, window titles and clipboard contents are not file identity.
- Prove compositor-supported placement/activation of Filewheel's own surfaces,
  coordinate transforms at fractional scaling and durable progress-pill visibility.
  Knowing the pointer position does not make `QWindow.setPosition()` work on
  Wayland. The InputCapture portal's edge barriers are not a passive click hook;
  do not introduce screen capture, RemoteDesktop sessions or pointer interception.
- Check Dolphin icons/details, tabs, scrolled/grouped and large folders, duplicate
  names, Unicode, stale events and touchpad middle-click gestures. Do not globally
  suppress middle-click or break browsers, paste, file opening or tab behavior.

**Exit:** demonstrated laptop native-Wayland interaction, or a precise blocker
report covering the missing requirement. In the latter case, continue independent
explicit-path/conversion work but leave **laptop Mouse3 incomplete**; a context
action is a fallback, not substituted acceptance. Do not package/advertise full
Linux parity until this gate passes. No root daemon, `/dev/input` permission
changes, injected clicks, unsafe identity guesses or permanent input logging.

X11 is a later compatibility adapter, not a prerequisite: passive XInput2 button
**2** observation plus bounded AT-SPI/item-URI validation. Do not confuse X11
button 3/right-click with the product name Mouse3, or reuse X11 coordinates as
native Wayland evidence. GNOME/wlroots require their own demonstrated adapters;
a working Plasma bridge is not universal Wayland support.

## 2. Add platform seams and safe Linux explicit-file invocation

Current hotspots: `runtime.py`, `app.py`, `core/models.py`, `core/explicit_paths.py`,
`core/controller.py`, `core/experimental.py`, `ui/desktop.py`, `preferences.py`.
They enforce Windows paths/runtime or import Windows startup/inspection directly.

- Add isolated `platforms/linux/` adapters and a small platform-services factory
  for inspection, cursor/coordinates, mouse runtime, login integration and reveal.
  Retain the current Windows adapters and validation behavior.
- Permit native POSIX target paths through the shared invocation/controller DTO
  without disguising them as PureWindowsPath. Keep Windows-specific restrictions
  on Windows; validate Linux absolute regular files independently. Specify/test
  symlink handling, reject nonlocal URIs, devices/FIFOs/directories and ambiguous
  multi-argument requests. Decode local `file://` URIs once at the adapter boundary.
- Separate explicit-path provenance from provisional hover candidates; keep
  freshness, generation/deduplication and revalidation before conversion. Do not
  reuse Windows injection/integrity flags as Linux security guarantees.
- Use XDG config/state/runtime directories, session-scoped current-user IPC,
  optional XDG autostart, Qt/file-manager reveal and a visible launcher when a
  desktop has no tray support. Never write user state into a read-only bundle.

**Exit:** native Linux CLI -> shared controller -> existing Quick wheel -> actual
conversion works; invalid inputs cannot open it; Windows contracts still pass.

## 3. Port process/tool safety, then connect the proven mouse adapter

- Audit `converters/process_worker.py`, `converters/office.py`, `video.py`,
  `libreoffice_bundle.py`, `pandoc_tool.py`, `paths.py`, `selftest.py` and the
  packaging hooks. Current termination uses taskkill/CREATE_NO_WINDOW; bundled
  tool lookup still assumes Windows names/layouts in several places.
- Implement owned Linux process/session cleanup, cooperative cancel then bounded
  escalation/reaping, including FFmpeg/Pandoc/LibreOffice descendants. Never kill
  by process name; never force-kill an output publication already permitted.
- Discover executable Linux tool paths, validate codecs/writers, isolate
  LibreOffice profiles and sanitize frozen library paths for external tools.
  Keep collision-safe atomic outputs, original hashes and private staging cleanup.
- Integrate the milestone-1 adapter with the existing tray/controller/popup.
  Show unsupported-session status instead of a silently broken Enable wheel.
  Preserve selection dismissal, persistent progress, cancel/retry and clean Quit.
- Validate Qt XCB **and** Wayland plugins, transparency, focus, scaling and work
  areas. Do not force the Windows OpenGL preference onto Linux. On Wayland use
  compositor-approved placement; state when cursor-centering/topmost is unavailable.

**Exit:** real image, PDF, Markdown, audio and video conversions; responsive UI;
cancel -> retry and tray Quit leave no workers or temporary outputs behind.

## 4. Add reliable file-manager fallback/integration

Provide `filewheel --gui -- /absolute/file` everywhere; add Dolphin service menu,
then Nautilus/Thunar actions using their supported APIs. Desktop entries must
preserve argument boundaries, filenames with spaces/metacharacters and single-file
validation; no shell interpolation. A context action is explicit invocation, not
hover identity. Install/remove only owned entries; autostart remains opt-in.
GNOME tray absence must not require a shell extension just to convert a file.

## 5. Produce the single-file installer and optional DEB

- Add `packaging/linux/`, `scripts/build-linux.sh`, a Linux PyInstaller **onedir**
  spec, a hashed Linux Python 3.14 lock, and a separate Linux CI build. Reuse the
  app/engines; exclude COM, PowerShell and Windows OCR resources.
- Freeze in the baseline container, assemble an AppDir with both Qt platform
  plugins/QML/native codecs and tools, then create the AppImage. Do not nest a
  PyInstaller onefile unpacking layer inside it. Do not bundle host GPU drivers
  or assume distro accessibility libraries/GObject typelibs magically freeze.
- Add explicit install UI / `--install-user`: copy the **original** AppImage
  (validated APPIMAGE location, not temporary mount contents) to a stable
  user-owned directory, write launcher/icon and chosen file-manager integrations,
  and offer login startup. No sudo or install-time downloads. Use an ownership
  manifest and safe upgrade/uninstall; leave documents/results untouched.
- Generate `.deb` from that same payload only as a secondary package-manager
  option; do not auto-launch a GUI from root package-maintainer scripts. Include
  hashes, license notices, support matrix and FUSE/extract-and-run instructions.
- If Wayland needs a bridge, include install/disable/remove handling in the same
  installer. Version-check its desktop API and require explicit enablement; never
  silently replace compositor files. ABI-specific plugins require separately
  matched builds, not a claim that one AppImage supports all compositor versions.

**Exit:** one downloaded AppImage can run/install offline on a clean target with
no Python; upgrade and uninstall work. Optional DEB installs/removes cleanly.

## 6. Validation and handoff

- Add tracked portable tests: the current public tree tracks only
  `tests/unit/test_media_ffmpeg.py`; `.gitignore` hides most tests/docs. Add narrow
  exceptions for new tests. Do not claim historical hundreds of tests exist here.
- Unit/integration: POSIX/Windows path separation, URI decoding, Unicode/spaces,
  invalid/multiple targets, stale/ambiguous hover evidence, unrelated apps,
  process cancellation, source integrity, collisions, missing tools, repeated
  invocations, install ownership, upgrade/remove and all offered converter families.
- Run pytest, Ruff on changed files, compilation and frozen `--self-test` including
  real Quick wheel/pill renders. Preserve Windows CI/build smoke checks.
- Use real desktop VMs/machines: **the laptop's native Wayland session first**,
  then other Wayland desktops and X11 compatibility. Test 100%/125%/150%/mixed DPI,
  mouse and touchpad, suspend/resume, monitor changes and repeated conversions.
  Containers/offscreen rendering cannot prove global input, focus or tray behavior.
- Maintain `LINUX_STATUS.md` (evidence/blockers) and `LINUX_NEXT_TASK.md` (one next
  action), plus a concise install/support guide. Commit each milestone separately.
  Support claims must name **distro + desktop/session + file manager**; distinguish
  conversion availability from middle-click parity. No push without instruction.

## Primary references

- [Qt: Wayland positioning limits](https://doc.qt.io/qt-6/application-windows.html)
- [InputCapture portal lifecycle](https://flatpak.github.io/xdg-desktop-portal/docs/doc-org.freedesktop.portal.InputCapture.html)
- [Current KWin scripting API](https://develop.kde.org/docs/plasma/kwin/api/)
- [KWin effects development](https://develop.kde.org/docs/plasma/kwineffect/)
- [XInput2 protocol](https://www.x.org/releases/current/doc/inputproto/XI2proto.txt)
- [AT-SPI coordinate hit testing](https://docs.gtk.org/atspi2/method.Component.get_accessible_at_point.html)
- [Dolphin service menus](https://develop.kde.org/docs/apps/dolphin/service-menus/)
- [Desktop entry argv rules](https://specifications.freedesktop.org/desktop-entry/latest-single/)
- [XDG autostart](https://specifications.freedesktop.org/autostart/latest/)
- [AppImage compatibility](https://docs.appimage.org/reference/best-practices.html)
- [AppImage is portable, desktop integration is separate](https://docs.appimage.org/user-guide/run-appimages.html)
- [PyInstaller Linux compatibility](https://pyinstaller.org/en/stable/usage.html#making-gnu-linux-apps-forward-compatible)

Milestone 1 checkpoint: bounded native Wayland probes are now recorded in
LINUX_STATUS.md and linux-evidence/milestone-1.json. Compositor-assisted test
surface placement and the scripted-effect button API are demonstrated. Exact
hovered-file URI is blocked through the tested Dolphin accessibility route;
hardware click/end-to-end acceptance is not claimed. No application port has
started. The probed workspace desktop does not identify a separate chat device.

Subsequent user approval authorizes the isolated private Dolphin prototype now
documented in LINUX_STATUS.md. It compiles; deliberate physical-click acceptance
is pending. This does not authorize replacing the installed file manager.

## Current execution checkpoint

Milestones2–4 are implemented and source-native accepted on the tested KDE session.
Milestone5 provides real AppImage/user installation and an optional DEB, plus a
separate exact-version private-Dolphin variant. Milestone6 portable/frozen/offline
container/installer checks pass; final packaged native and broader desktop/DPI
acceptance remain pending. The original stock-Dolphin blocker is not erased.
Consult current LINUX_STATUS.md rather than interpreting early historical notes
above as the current implementation state. No push or universal support claim.
