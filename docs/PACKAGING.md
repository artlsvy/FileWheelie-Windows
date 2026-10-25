# Windows application bundle — G11

The source includes a Windows-only PyInstaller onedir build recipe. It has been
statically checked and its portable contract tests run on Kubuntu; **no Windows
EXE has been built or executed here**. Native DLL/plugin/model completeness,
Microsoft Defender behavior and clean-machine operation remain acceptance items.
A Linux build is not a Windows cross-build.

## Supported build interpreter

Use **64-bit standard-GIL CPython 3.14 on Windows 11** (win-amd64, not ARM64 or free-threaded). This single interpreter covers Qt,
Pillow/HEIF, PyMuPDF, pdf2docx and MarkItDown; MarkItDown0.1.9 excludesPython3.15.
The build lock resolves Windows amd64 wheels, not Linux wheels. Do not force it
onto another Python ABI/platform or use an unsupported wheel override.

The version-controlled `packaging/windows-py314.lock` pins every runtime/build
package and its selected wheel SHA256. The environment is dedicated to building;
the script preserves an existing incompatible/incomplete environment by failing
rather than deleting/recreating it. Keep source changes committed or inspect the
manifest's dirty-source status before treating a build as reproducible.

## Build on Windows

From a complete updated checkout with Python3.14 installed:

```powershell
py -3.14 -c "import sys; print(sys.version)"
powershell.exe -NoProfile -ExecutionPolicy Bypass -File .\scripts\build-windows.ps1
```

If the Python launcher is unavailable, select the interpreter explicitly:

```powershell
powershell.exe -NoProfile -ExecutionPolicy Bypass -File .\scripts\build-windows.ps1 -Python "C:\Path\Python314\python.exe"
```

The script:

1. Requires Windows CPython3.14 amd64 and creates `.venv-build314` only if absent.
2. Installs hash-checked, wheel-only dependencies; installs this checkout without
   resolving extra dependencies or creating a second isolated build environment.
3. Runs `pip check`, then the checked-in spec with PyInstaller6.22.3.
4. Runs `dist\Filewheel\Filewheel.exe --self-test` with a three-minute deadline; a nonzero exit fails build.
5. Records `BUILD-MANIFEST.json`, `DEPENDENCIES.txt` and `DEPENDENCIES.lock` beside
   the executable, including source revision/status and lock digest.

Building downloads pinned dependencies. Runtime conversion is local; there is no
account, upload, LLM client or plugin service. Process-only ExecutionPolicy Bypass
is used in the example; it does not change the system policy. No administrator
rights are needed when checkout/output folders are writable by the current user.
PyInstaller rebuilds its own `dist\Filewheel` output; keep unrelated files out of
that folder. The script never deletes source files or an existing build venv.

## Folder layout and launch commands

Keep the **entire directory** together, not just Filewheel.exe:

```text
dist/Filewheel/
  Filewheel.exe
  _internal/                 Qt plugins, Python engines, native DLLs and data
  BUILD-MANIFEST.json
  DEPENDENCIES.txt
  DEPENDENCIES.lock
  tools/libreoffice/         optional complete G12 portable office installation
```

```powershell
& .\dist\Filewheel\Filewheel.exe --self-test
& .\dist\Filewheel\Filewheel.exe --tray
& .\dist\Filewheel\Filewheel.exe --gui -- "C:\Users\you\Pictures\image.png"
& .\dist\Filewheel\Filewheel.exe --sendto stage
& .\dist\Filewheel\Filewheel.exe --sendto install
& .\dist\Filewheel\Filewheel.exe --sendto remove
& .\dist\Filewheel\Filewheel.exe --startup install
& .\dist\Filewheel\Filewheel.exe --startup remove
```

Launching without a file or with --tray runs the tray; direct --gui is transient.
Mouse3 stays **disabled by default**. Enable experimental
candidate confirmation explicitly with `--tray --experimental-mouse3`; candidates
never become trusted hover targets. A user confirmation and fresh explicit-path
validation are required before normal conversion. Send to explicit-path routing
is independent of the experimental listener. Startup integration is personal and
owned; move a bundle only after removing its old integrations, then reinstall.
No integration is silently installed by the build itself.

The frozen app is windowed. Conversion errors retain a concise engine/reason and
private traceback-log pointer; use its explicit diagnostic/self-test report paths
for detail rather than expecting a console to remain visible.

## Optional complete LibreOffice tree (G12)

The build does not download or install LibreOffice. Supply an existing complete
flat or PortableApps-style directory; it must include libraries, resources and
license files, not only soffice.exe:

```powershell
powershell.exe -NoProfile -ExecutionPolicy Bypass -File .\scripts\build-windows.ps1 -LibreOfficeDirectory "D:\Tools\LibreOfficePortable"
```

The G12 validator runs before copying and again on the destination. The full tree
is copied to `dist\Filewheel\tools\libreoffice` **beside** the executable, outside
`_internal`. A source directory inside the rebuilt output is rejected before
PyInstaller runs. Without this tree, installed LibreOffice detection may still
supply DOCX→PDF; an unavailable engine must stay hidden/gracefully unavailable.
See the converter documentation for the final G12 runtime selection rules.

## Frozen resources and diagnostics

- `entry.py` calls `multiprocessing.freeze_support()` before Filewheel/Qt imports,
  so spawned conversion workers do not recursively launch the tray.
- The early runtime hook disables ONNX telemetry without importing ONNX, COM or
  Qt. It chooses a writable per-user generated-COM cache; worker code initializes
  and configures COM on its proper owner before requesting UIA generated types.
- `sendto_shortcut.ps1` lives beside its Python module inside `_internal`.
- Explicit collections include HEIF codecs, PyMuPDF/pdf2docx/OpenCV, Office
  templates, MarkItDown/Magika model assets and ONNX inference libraries. Qt uses
  Essentials/platform hooks; unrelated QtWebEngine/QtPdf and other GUI bindings
  are excluded. Dependency metadata/license files are preserved in the bundle.

Primary references: [PyInstaller spec files](https://pyinstaller.org/en/stable/spec-files.html),
[runtime resource paths](https://pyinstaller.org/en/stable/runtime-information.html),
[comtypes generated cache behavior](https://github.com/enthought/comtypes/blob/1.4.17/comtypes/client/_code_cache.py).

## Windows acceptance still required

Build on the actual Windows3.14 amd64 environment, inspect PyInstaller warnings,
then move the entire folder to a different writable directory without its venv or
checkout. Verify frozen self-test, all required conversion fixtures, Unicode and
spaces, worker spawn/cancel/exit, native Qt rendering/focus/DPI, personal Send to
and startup removal/ownership, and optional Mouse3 candidate confirmation.
Repeat the test with and without portable/installed LibreOffice. Do not certify
those behaviors from Linux AST/fake/offscreen tests or dependency resolution.

## Repeated launches and local reports

The main entry uses a current-user lock and UserAccess local Qt endpoint. Repeated
GUI launches forward one explicit path and its launch-time cursor point to the
owner, then exit. Busy conversions reject new requests rather than spawning more
workers. The protocol cannot enable Mouse3; an existing tray's experiment is
changed only by its checkbox. If already running, quit it before trying the
--experimental-mouse3 startup flag. No TCP listener or remote IPC is used.

Read `%LOCALAPPDATA%/Filewheel/logs/self-test.json` after --self-test; full actual
exceptions are in conversion-debug.log. Frozen Windows stdio may be unavailable,
so report/log paths are the supported diagnostic surface. Self-test generates
private temporary fixtures for real PNG/PDF/DOCX and all5Markdown pairs, and also
runs DOCX→PDF when an engine is available. It tests packaged imports/models/DLLs;
Qt desktop/compositor and Mouse3 still need interactive acceptance.

Existing development links have a different target from the packaged EXE. Remove
the owned old GUI entry using its original interpreter before installing the new
one; a different target is preserved, not silently overwritten. Known earlier
source launcher arguments are accepted for ownership-checked removal only; install
requires explicitly removing/reinstalling them to update single-instance routing.
