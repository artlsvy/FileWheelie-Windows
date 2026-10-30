# Current Linux checkpoint — single-file personal package

2026-10-30, branch `feat/linux-port`. Source native Wayland private-Dolphin exact
clicks, wheel placement, PNG→JPEG/TXT→MD, persistent progress and Quit were accepted
by the user. That original private-browser test did not establish stock-Dolphin
or universal Wayland Mouse3 support.
The native stock-Dolphin second-application route is also user-verified; the
installer now sets it up automatically. Current checks and artifacts are below.
Packaged private-Dolphin interaction is now user-reported working; original
demo hashes remain unchanged. First-run install dialog and broader DPI/desktop
acceptance remain pending. Historical probe/checkpoint notes follow.

## Image-only PDF OCR repair

User accepted the progress positioning fix on Plasma, then reported PDF→MD failing
with "Image-only PDF conversion requires Windows local OCR." Confirmed in the
installed debug log: a platform-specific helper was called for image-only PDFs
on Linux. Shared PDF OCR assembly now dispatches recognition by platform. Linux
uses local Tesseract; Windows native recognition and compatibility entry points
are retained. Picture-only Markdown preserves linked original-page images even
when OCR finds no letters. DOCX still requires recognized editable text.

Tesseract executable, English/orientation models and native libraries/notices are
now bundled by the baseline build. Recognition uses explicit bundled language data,
no network, bounded subprocesses and existing safe staging/publication. Text-layer
PDF extraction stays unchanged. Source repair is committed as `7b1cafc`.

Delivered updated `dist/Filewheel-Linux-x86_64.AppImage`: 476,301,816 bytes
(454 MiB), SHA-256 `56656b2dba024e4999bd9ce0b7c03002345bf6e19ecca14d6f66dd7f6d3109a1`.
All **140 source tests pass /4 intentional same-format skips**, Ruff/compile pass.
The actual frozen onedir, extracted AppImage, ordinary FUSE AppImage and offline
Debian12 runtime each pass **44 checks**. The new checks recognize actual scanned
PDF text in DOCX and Markdown, verify page-image links, preserve a picture-only
PDF, and require OCR from the bundled tree. Debian runtime has no Python,
Tesseract or other converter tools installed; network is disabled. Actual final
install/upgrade/remove preserves documents and 26 Dolphin associations. One test
harness cleanup initially raced asynchronous FUSE unmount in a temporary root;
rerun with a separate mount-temp directory completed cleanly. The installed app
and running tray were not silently replaced/killed. No user assets modified.

English recognition data is included. OCR may make mistakes; complex layouts are
not reconstructed. PDFs with both text-layer and scanned pages keep existing
extraction/limitations warnings. Windows dispatch has a portable regression test;
no new native Windows test was claimed. Progress-position fix stays intact and is
user-accepted. See linux-evidence/final-installer.json. No push.

## Previous package after native progress fix

Current installer: **`dist/Filewheel-Linux-x86_64.AppImage`**, 467,491,320 bytes
(446 MiB), source fix commit `abc4fb8`. SHA-256:
`95f70cf62f81c0e7cbd44a46081c0edbc5ef5a44806d973c5a32a6a49619241c`.
Python3.14/Qt/converters/FFmpeg/Pandoc/full LibreOffice are bundled. No private
Dolphin, external Python/pip setup, or root installation is required. Default
installer sets the reversible ordinary-Dolphin second-app integration, preserving
primary handlers. GNOME integration remains deferred.

The screenshot's expanded-progress overflow was reproduced and corrected in the
scoped KWin script. Native before/after measurements show 102.06 px usable-area
overflow corrected to 16 px panel clearance. Dark/animated and light/reduced-motion
six-stage native Quick checks pass. Source tests: 127 passed /4 intentional
same-format skips; scoped Ruff, compilation and whitespace checks pass.

The final binary passes 40 checks /32 real conversion pairs in each of frozen
onedir, AppImage extract-and-run, ordinary FUSE AppImage, and network-disabled
Debian12 with no Python or converter executables installed in that runtime.
The new placement module is present in the frozen Python archive. Actual final
AppImage install→upgrade→remove passed in isolated XDG directories: 26 MIME types
configured, launcher/payload removed and user document preserved. Initial upgrade
QA hit a full /tmp RAM disk; repeating in the workspace passed. The existing
running tray was not killed or silently upgraded. Quit/reopen it to load this fix.

Evidence: `linux-evidence/final-installer.json`,
`linux-evidence/progress-placement-fix.json`. Full build reports remain under
`build/linux-final-installer`. Frozen native interaction after restart, actual
simultaneous mixed-DPI outputs and physical panel relocation still warrant user
acceptance; modeled permutations and source-native rendering are not those tests.
No universal distro/desktop or GNOME Mouse3 claim. Older build directories remain
historical artifacts; distribute the file under `dist/` above. No push.

## Initial milestone 1 — historical blocker checkpoint

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


## Shared native wheel/conversion integration

The source Linux owner now has an explicit private-Dolphin option and a Qt D-Bus
receiver (no PyGObject dependency in the app). Authenticated fresh click URIs are
revalidated through the shared controller as `dolphin_click`, never Explorer hover.
A scoped temporary KWin script positions only Filewheel-owned surfaces; cursor
lookup and script calls are asynchronous. Tool surfaces avoid an unparented
Wayland popup grab. Progress keeps independent job ownership. Owned private
Dolphin is shut down asynchronously before the tray owner exits; no GUI join.
Its XDG config/cache/state/data remain isolated from the installed Dolphin.

Native automated probe: cursor (921,452), actual 240 px Quick frame (801,332),
matching cursor centering. Native owner/private-child boot/quit returns 0. User
then confirmed PNG→JPEG and TXT→MD, correct near-cursor wheel, progress remaining
visible after moving away, and tray Quit. The JPEG dimensions/content and Markdown
text were checked, all three demo source hashes remain unchanged, and no staging
leaks remain. Evidence: `linux-evidence/native-demo-acceptance.json`.

Final current portable suite: **86 passed / 4 intentional same-format skips**.
That includes 27 Linux tests, a real Quick background job after progress collapse,
URI policy, source/collision preservation, owned worker/tool cancellation and the
existing media fixtures. Source Quick smoke again passes **31 checks /24 actual
pairs**. Scoped Ruff and compilation pass. Enable wheel now controls private
forwarding; its prototype does not restore Dolphin default middle-file opening
when disabled. See LINUX_USE.md. Broader DPI/desktop/long-session and Windows-native
regressions remain pending; no installer or cross-distribution claim yet.

## Desktop integration and per-user installer checkpoint

Added owned XDG application/icon and Dolphin service entries, source/frozen launch
commands, AppImage install/upgrade/remove by manifest+SHA256, explicit first-run
install choice and a tray file picker. Login startup remains opt-in. Foreign or
modified launchers/binaries and symlinks are preserved; uninstall leaves source
files, converted results, preferences and logs untouched. Install source must
have a real AppImage ELF marker. Linux-only management is rejected on Windows.

33 Linux tests pass at this checkpoint, including actual GIO argument-boundary
round-trip with Unicode, spaces, quotes, backslashes and metacharacters. Launcher
executable paths containing `=` or `%` are rejected explicitly due to desktop
parser limitations; input filenames can contain these characters. The native
first-run install dialog and frozen integration still need packaging acceptance.
No host integration or startup was installed during automated tests (isolated XDG).

Installer follow-up: same-session login actions now use the stable installed
AppImage path; removal also checks that exact installed startup command when
invoked from the downloaded copy. A foreign startup entry remains untouched.
38 Linux tests pass, including this regression and strict frozen-family gates.
Packaging prototypes identified and corrected Ubuntu LibreOffice FHS relocation,
dynamically loaded NSS modules, and cross-distro launcher library contamination.
Intermediate build/linux-preview, linux-final and linux-kubuntu-preview artifacts
are marked SUPERSEDED, not accepted deliverables. The final delivery build is
rebuilding against this source; no final package acceptance is claimed yet.

## Installable Linux preview (milestones 5–6)

Built from CPython3.14.10 on a digest-pinned Ubuntu22.04 container, using a
51-distribution hashed Linux lock and a Linux-only PyInstaller onedir spec.
The one downloaded AppImage includes Python/Qt, existing image/PDF/Markdown/media
engines, complete relocated LibreOffice, Pandoc3.12.1 and FFmpeg4.4.2. Added fonts,
NSS runtime modules, native dependency closure, package notices and a source
snapshot. Tool launchers avoid host utilities under bundled library paths and use
LibreOffice's native restart helper. Host GPU drivers and glibc are not bundled.
Build inputs are pinned/recorded; native apt mirrors remain mutable, so no
bit-for-bit reproducibility or signature claim. A separate manual Linux CI exists;
the Windows release workflow and conversion algorithms are preserved.

Actual artifacts (ignored build outputs, not committed binaries):

- `build/linux-delivery/Filewheel-0.3-linux-preview-linux-x86_64.AppImage` — 445.8MiB.
- `build/linux-delivery/filewheel_0.3.0~linux1_amd64.deb` — 497.8MiB.
- `build/linux-kubuntu-delivery/Filewheel-0.3-linux-preview-kubuntu2604-private-dolphin-x86_64.AppImage` — 452.3MiB.

The last includes the isolated browser prefix, **not its system Qt/KF6 stack**.
It is only a matched Kubuntu26.04/KWin6.6.6/Qt6.10.2/KF6.24/Dolphin25.12.3 preview.
An explicit tray action opens it; default startup does not replace/patch Dolphin.
The compiled ELF GLIBC requirements do not certify those additional KDE APIs.
Core ELF audit ceiling is GLIBC2.35. ARM64/musl and other desktop Mouse3 adapters
are not provided. GNOME/Thunar have explicit Open With invocation, not a tested
custom global middle-click route. See LINUX_PACKAGING.md and LINUX_USE.md.

Actual checks: **97 passed /4 intentional same-format media skips**; separate
suite against the *shipped* FFmpeg: **59 passed /4 same skips**. Both final
AppImages pass **40 frozen checks /32 real pairs**, including actual Quick wheel
and pill rendering, transparent corners, dialog input, owned workers, cancellation
and retry. Normal FUSE AppImage launch passes the same checks on Kubuntu; the
builder also checks extract-and-run. Runtime-only Debian12 (standard GL/fonts/
D-Bus/Wayland libraries, no Python or converter tools) passes all40 offline with
network disabled. Real DEB install→40 checks→remove passes in that container and
preserves a test document. Real AppImage install→upgrade→startup→uninstall passes
in isolated XDG directories; desktop-file-validate passes and the test document
survives. Strict package checks fail if a required converter silently disappears.
Scoped Ruff, compilation and patch whitespace checks pass.

Evidence: `linux-evidence/package-acceptance.json`; build manifests, source hash,
per-ELF requirements and actual frozen reports beside each artifact. Intermediate
packaging prototypes are marked SUPERSEDED and must not be installed. Final
packaged native mouse/focus/tray acceptance is separately pending user feedback;
source acceptance is not promoted to frozen acceptance. First-run GUI install,
long sessions, large/grouped folders, fractional/mixed DPI, GNOME/Xfce/X11 and
Windows-native regression remain unverified. Copyleft corresponding-source and
license redistribution audit is required before public release; this is a local
unsigned personal preview. No commits were pushed.


## Packaged acceptance and stock-Dolphin route correction

User reports: "all works in private dolphin". The three demo source hashes remain
unchanged. This accepts the basic packaged private-browser workflow, without
inventing a separate Quit/first-install/mixed-DPI result.

Further review found an overlooked **built-in stock Dolphin route**. The installed
Ubuntu source (4:25.12.3-0ubuntu1) has `slotfileMiddleClickActivated`, which queries
KApplicationTrader by the clicked KFileItem MIME type and launches its second
associated application, passing `item.targetUrl()`. Shift selects the third.
Regular file clicks reach this branch; directory/archive/tab-as-file behavior
can take a different branch. Confirmed against the actual container source and
[KDE25.12.3 source](https://github.com/KDE/dolphin/blob/v25.12.3/src/dolphinviewcontainer.cpp).

The earlier lack of an external generic Mouse3 plugin remains accurate, but the
broader implication that a private build was necessary was **too broad**. Registering
Filewheel as the second application for supported MIME types could provide exact
file invocation in ordinary Dolphin, preserving the existing default app. That
association route still needs a stock-Dolphin hardware test; no user MIME settings
have been changed. Current KWin placement can be reused on Plasma. Other
compositors/file managers require independently verified input/identity/placement
adapters; Nautilus's supported MenuProvider is a menu API, not a middle-click API.


## Default native stock-Dolphin integration

User confirmed that manually making Filewheel the second application works in
ordinary Dolphin on Plasma. This is now the default per-user installer behavior,
also included in `--integration install` for source/DEB setups. Setup discovers
available registry input MIME types, preserves the current primary, and places
Filewheel second using XDG Added/Default Applications order. KDE's fallback-default
list precedence is handled explicitly. No hooks, provisional identities, patches
to system Dolphin or conversion changes are introduced. The broad application/
octet-stream declaration was removed from the launcher so unsupported/no-handler
types do not acquire Filewheel as their first application. The context action
continues to validate any explicit input through the shared controller.

An owned per-entry write-ahead journal allows repeatable upgrade and removal.
Unchanged entries restore prior values; later user edits are retained except for
Filewheel's ID. Foreign launchers/state, symlinks, duplicate entries and concurrent
management fail safely. Explicit disable (`--dolphin remove`) survives upgrades;
`--dolphin install` re-enables it. Missing default handlers, existing Filewheel
primary choices, user exclusions and unavailable desktop tools are reported and
preserved. Automatic setup is limited to Plasma with Dolphin/gio/kbuildsycoca6;
no GNOME integration or native GNOME claim is added. Private-browser code stays
available, and its toggle is shown only when that experiment is in use.

Actual validation: **114 passed /4 intentional same-format skips**, Ruff and
compilation. Read-only target-built KApplicationTrader probe confirms PNG/PDF
ordering and rollback in isolated XDG preferences, including multiple fallback
apps. The actual frozen installer confirms all26 available MIME types keep their
primary and place Filewheel second; disable→upgrade keeps the opt-out, re-enable
and uninstall restore preferences. The user's installed copy was then upgraded;
real KDE queries confirm all26 existing primary applications are unchanged and
Filewheel is second in every configured type. The user's earlier stock-Dolphin
hardware test is the basis for native click acceptance; ordering queries are not
presented as new synthetic hardware tests. First-run GUI dialog and mixed-DPI /
other desktop acceptance remain separately scoped.

Current core AppImage: `build/linux-native-dolphin/` (same converter runtime;
40 frozen checks/32 actual pairs). Current native evidence is
`linux-evidence/dolphin-default-acceptance.json`. Build manifests record source
and artifact hashes. Unrelated untracked user assets are excluded from source
snapshots. The user's untracked wheel.jpg was left untouched. No push.

## Progress view boundary correction

User reported a cropped progress/detail view in the home-directory screenshot.
The original image was visually inspected without modifying it. Reproduced on
native KDE Wayland at the current1.55 output scale: the compact frame was correctly
anchored, but changing height72→190 left its top coordinate unchanged. Expanded
bottom exceeded KWin's usable area by102.06 logical pixels. Qt's availableGeometry
also included the panel; client global positioning cannot repair a Wayland Tool.

The scoped compositor script now re-anchors Filewheel-owned progress windows on
actual frame size, show/reuse, output and work-area changes, using live KWin
MaximizeArea coordinates. It retains the invoking output while the cursor moves,
handles removed outputs, avoids geometry feedback and never focuses progress or
moves another application's windows. No display-DPR multiplication, polling,
conversion changes or GNOME work was added.

Actual native before/after frames show expanded bottom now16 logical pixels above
the panel. Real Quick images were generated and visually inspected. Six native
stages each pass for dark/animated and light/reduced-motion presentations, including
failure and repeated collapse/expand. Source suite: **127 passed/4 intentional
skips**, including production-JS signal tests for negative/fractional coordinates,
multiple outputs, panel edges, removal, late initial sizing and foreign-window
protection. Scoped Ruff, compilation and whitespace checks pass. Evidence:
linux-evidence/progress-placement-fix.json. Actual simultaneous mixed-DPI outputs
and physical panel relocation were not exercised; those permutations have JS
model coverage. Final single-file installer assembly follows this code checkpoint.
