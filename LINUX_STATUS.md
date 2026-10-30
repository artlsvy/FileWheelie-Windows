# Linux milestone 1 — precise blocker checkpoint

2026-10-30, Windows source baseline `48a28c4`, branch `feat/linux-port`.
**Native Wayland Mouse3 parity is NOT demonstrated. Milestone 2 has not started.**

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
