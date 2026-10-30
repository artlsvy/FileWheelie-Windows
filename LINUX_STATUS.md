# Linux milestone 1 — precise blocker checkpoint

2026-10-30, Windows source baseline `48a28c4`, branch `feat/linux-port`.
**Native Wayland Mouse3 parity is NOT demonstrated. Milestone 2 has not started.**
The user subsequently authorized an isolated patched-Dolphin prototype; see the
new checkpoint below. Stock Dolphin's accessibility limitation remains.

## Environment actually examined

The workspace's live KDE Wayland desktop was reached through its owned session
bus/socket from SSH. Installed packages: Plasma/KWin 6.6.6, Dolphin 25.12.3,
KDE Frameworks 6.24.0, system Qt 6.10.2. The isolated PySide6 probe uses Qt 6.12.0.
This establishes the workspace host, not a separate chat laptop if that is a
different device. No X11/XWayland substitution, root access or input permissions
were used. All visible probe windows and temporary scripts/effects were removed.

## Results

| Requirement | Actual evidence | Result |
|---|---|---|
| Native file manager | Temporary Dolphin fixture window appears as `KWin::XdgToplevelWindow` | Demonstrated on workspace desktop |
| Button event API | Temporary JS KWin effect loads; logs `mouseChanged=function`; then unloads | API runtime demonstrated; **physical click not verified** |
| Ordinary KWin script | `cursorPos` and its change signal exist; `mouseChanged`, `registerPointerShortcut`, `startMousePolling` are undefined | Script API alone is insufficient |
| Exact hovered-file identity | Three real fixture items expose Accessible/Component/TableCell, name/type/bounds, **empty attributes and no Hyperlink/URI interface** | **BLOCKER** for tested AT-SPI route |
| Native surface placement | Qt Wayland probe requests (80,90); KWin sees (819,443), then bridge sets frame to (80,90) | Compositor-assisted test-surface placement demonstrated |
| Cursor-centered Filewheel wheel, focus, pill, fractional DPI | Not integrated/tested | Pending, not inferred from placement probe |

The fixture accessibility data contains filenames, not authoritative file paths.
Knowing our temporary directory does not justify general name-to-directory
concatenation. No candidate was accepted and no conversion was started.

### Route A: supported file-manager extension

Exact KIO 6.24.0 `KAbstractFileItemActionPlugin` exposes `actions(...)` for a
context menu's file items. It does not expose a middle-button callback. Dolphin
25.12.3 has internal item/controller signals, but their existence is not a
supported external input extension contract. No binary injection, event-filter
attachment through incidental widget internals, or Dolphin patch was attempted.

### Route B: compositor bridge plus accessibility

Exact KWin 6.6.6 `EffectsHandler` connects pointer-button changes to `mouseChanged`;
`ScriptedEffect` exposes this object as `effects`. A temporary user script-effect
loaded successfully and confirmed that signal at runtime. Unlike stale examples,
this version does not require an exposed `startMousePolling()` call. Thus global
button observation is a plausible next test, **not proven impossible** and not
proven by seeing a callback property. No actual physical press was requested or
observed in the five-second API smoke test.

Even with that event, Dolphin's tested accessibility items do not supply exact
local URIs. Its exact-version accessible delegate source provides display text
and spoken descriptions. Compositor cursor/window information cannot fill that
identity gap. This blocks the combined route under the plan's identity rules;
it does not prove every possible future Dolphin integration impossible.

## Reproduce (shows brief native windows; no conversion)

Run on the same current-user KDE desktop with system PyGObject/AT-SPI and the
existing PySide6 environment. Reports must not already exist:

```bash
/usr/bin/python3 scripts/linux/probe_wayland.py \
  --qt-python .venv-ui/bin/python --report /tmp/fw-wayland-check.json
/usr/bin/python3 scripts/linux/probe_kwin_effect.py \
  --seconds 5 --report /tmp/fw-effect-check.json
```

The first probe creates only scratch files and an owned 220 px test surface,
loads a temporary KWin inspection/placement script, then cleans up. It bounds
accessibility traversal to 800 nodes / 4 s plus individual call timeouts. It
uses the current UID's `wayland-0`; other socket names need explicit adaptation.
The second temporarily loads a user JS effect; it logs only a unique READY marker
and middle presses over Dolphin, with no file paths/coordinates, for at most 60 s.
For a deliberate future hardware test use `--seconds 30` and middle-click a
scratch text file in Dolphin. A marker still would not prove correct file identity.
No persistent configuration, listener or app integration is installed. The
finite probe's own marker can remain in the user's existing KWin journal.

## Checks and scope

Both probes executed on native Wayland; final placement/accessibility evidence
is in `linux-evidence/milestone-1.json`. Changed-script Ruff and compilation pass.
No production source, conversion engine, Windows build or release artifact changed.
The application regression suite was not run because this is an isolated
feasibility probe, not an application port. No hardware Mouse3, touchpad, focus,
mixed-DPI or laptop end-to-end acceptance is claimed.

Initial `--version` calls without a display aborted Qt startup; installed versions
were instead obtained with dpkg-query. No application malfunction was inferred.
An initial effect metadata smoke was rejected for missing `KPackageStructure`;
after adding `KWin/Effect`, native load/READY/unload succeeded.

## Exact-version primary sources checked

- [KIO 6.24.0 action plugin](https://github.com/KDE/kio/blob/v6.24.0/src/widgets/kabstractfileitemactionplugin.h)
- [Dolphin 25.12.3 accessible delegate](https://github.com/KDE/dolphin/blob/v25.12.3/src/kitemviews/accessibility/kitemlistdelegateaccessible.cpp)
- [KWin 6.6.6 workspace wrapper](https://github.com/KDE/kwin/blob/v6.6.6/src/scripting/workspace_wrapper.h)
- [KWin 6.6.6 pointer signals](https://github.com/KDE/kwin/blob/v6.6.6/src/effect/effecthandler.cpp)
- [KWin 6.6.6 script effect globals](https://github.com/KDE/kwin/blob/v6.6.6/src/scripting/scriptedeffect.cpp)

Upstream exact-release sources were compared with installed package versions;
Ubuntu downstream patches were not exhaustively audited. Live runtime and
accessibility observations take priority over assumptions from upstream docs.

## Authorized private Dolphin prototype (2026-10-30)

User explicitly approved: "Yes, isolated Dolphin prototype". Implemented a small
opt-in patch against Ubuntu's Dolphin 25.12.3 source and compiled it successfully
inside a disposable Ubuntu 26.04 Docker build. Qt 6.10.2 / KIO 6.24.0 match the
host versions. No host packages or installed Dolphin files were changed;
`dpkg -V dolphin` reports no changed package files. Windows app code is untouched.

The private handler gets `m_model->fileItem(index).url()` from the real middle
press/release path. A directed session-bus signal carries that exact URI, a
per-process sequence and CLOCK_MONOTONIC timestamp. It is disabled without this
run's destination/secret environment variables. The receiver only accepts its
own child PID/executable, matching secret, fresh nonreplayed payload and an
existing non-symlink scratch fixture. No application target/conversion is emitted.
This bypasses the AT-SPI URI gap by changing a private file-manager build;
it does not establish a supported stock-Dolphin extension or universal support.

Private artifacts are in ignored `build/dolphin-probe/`. Source patch, Dockerfile,
safe extractor, test receiver and instructions are in `prototypes/dolphin-bridge/`.
Image ID, compiled binary/library hashes and build-package versions are recorded
in `linux-evidence/dolphin-prototype-build.json`. The private binary version smoke
passes. Three portable boundary tests pass (Unicode/spaces/same names across tabs,
invalid tokens/URIs, stale/future/replay, missing files and symlinks). Scoped Ruff,
compilation and exact-source patch dry-run without fuzz pass.

A bounded native test was launched with private XDG config/cache/state/data and
scratch Tab A/Tab B. **Hardware click/active-tab acceptance remains pending user
input**. The 240-second run timed out with zero accepted/rejected messages and
closed its owned child; evidence is `linux-evidence/dolphin-prototype-live.json`.
Zero observed messages must not be called success. No wheel/converter
integration or packaging milestone has started. Prototype maintenance and a
supported integration strategy still need evaluation after the physical test.


## Human acceptance and Linux platform foundation

User confirmed all physical tests passed. `/tmp/fw-human-test-1.json` contains
six accepted exact URIs (three filenames in both tabs), sequences 1–6, zero
rejections, and normal private-child exit. The preserved evidence is
`linux-evidence/dolphin-human-acceptance.json`. This verifies only the private
patched Dolphin route on the tested KDE Wayland desktop, not stock Dolphin,
other desktops, large/grouped folders or actual wheel/conversion integration.

The next foundation is implemented: source-aware POSIX target validation through
InvocationController, Linux entry/services, XDG preferences/logs/login ownership,
and per-session single-instance routing. Windows lexical/provenance rules stay
separate. Linux worker sessions/tool groups support owned pre-publication stop;
LibreOffice/Pandoc/FFmpeg discovery and subprocess environment have Linux paths.
No mouse adapter or compositor script is silently installed at application startup.

Actual Linux checks: **78 tests passed / 4 skipped** (same-format media cases are
not advertised), including 19 new Linux tests. Real spawned PNG conversion checks
Unicode paths, source hashes and collisions; an uncooperative session/tool-group
stop test passes. Actual source Quick self-test: **31 checks / 24 real pairs**,
with system FFmpeg/LibreOffice, no Pandoc installed. A shared DesktopApplication
POSIX-target offscreen presentation passed. Scoped Ruff and compilation pass.
Windows-native regression and frozen Linux/mixed-DPI checks remain unperformed.
Next: connect the accepted private Dolphin bridge and compositor-assisted wheel
placement to this shared host, then native UI/conversion acceptance and packaging.
