# Architecture and portable test seams

Target: Python 3.12+; Windows 11 at runtime; Kubuntu for primary development.

Current headless entry: explicit_path_diagnostics accepts Shell argv and calls
InvocationController.handle_explicit with injected file metadata inspection and
the current physical cursor. Its result.target and experimental handle(MouseEvent)
use the same TargetResolution DTO. source=shell_explicit has window_id=0; hover
keeps explorer_hover and its strict provenance requirements. The PySide6
consumer receives this DTO from either controller route. No UIA/selection lookup
is needed for the explicit route. See SEND_TO.md for install/remove and Windows
validation; GUI implementation is present; native acceptance remains queued.

```text
Windows hook (Win32 only) ----> MouseEvent queue
                                     |
                                InvocationController
                                     |
          ExplorerTargetResolver (Win32 UIA + Shell COM)
                                     |
                           Result: verified Path | None
                                     |
              [G3] Invocation DTO + capability registry
                                     |
               [G4] one PySide6 radial popup (no tray/service)
                                     |
              [G5+] conversion manager + backend registry
                                     |
                workers (MarkItDown/PDF/Image/Office)
```

Recommended first modules (actual names can adapt to existing repo):
- `src/filewheel/core/models.py`: `MouseEvent`, `TargetResolution`, `RejectionReason`; no Win32 imports.
- `src/filewheel/core/controller.py`: debounce, resolver interface, event handling; fully testable on Linux.
- `src/filewheel/platforms/windows/hook.py`: low-level hook, fast callback/message loop, Win32 imports guarded.
- `src/filewheel/platforms/windows/explorer_resolver.py`: UIA + Shell logic, COM worker apartment management.
- `src/filewheel/platforms/windows/diagnostics.py`: opt-in JSONL metadata for QA.
- `src/filewheel/ui/`: pure preview registry/state/placement and optional popup.
- `tests/unit/`: fakes and pure tests; `tests/windows/`: marked tests requiring an interactive Win11 session.

Optional UI dependency: PySide6 for the radial prototype, isolated as an optional
UI dependency. Image libraries, MarkItDown, LibreOffice and converters remain
deferred. The personal Send to shortcut is a small invocation integration, not a
distribution installer.

### Correctness and latency
- Record event quickly and return from the hook before doing any UIA/COM work; the OS may silently remove timed-out hooks.
- UIA element lifetimes are transient. Timeouts and race conditions return None, not a stale previously selected file.
- Marshal between threads explicitly and initialize COM per owning thread. Avoid accessing COM objects on another thread without proper marshaling.
- All screen coordinates must be consistently physical vs Qt logical; normalize at the UI boundary, not within the resolver.

### Tests and platform behavior
- Pure modules import and run on Kubuntu without Windows packages.
- Windows tests run only with explicit `@pytest.mark.windows_integration` and do not run in headless Linux CI.
- Fake resolver returns target or None and records invocations. Negative tests are more important than proving file A worked once.

### G4 invocation and UI boundary

explicit_path_diagnostics --gui validates through InvocationController once, then
lazily imports run_popup(target). Headless mode never imports Qt. GUI shortcuts
use direct pythonw with --gui; diagnostic shortcut identity/arguments are retained.
The immutable controller TargetResolution is the sole UI input, including future
trusted hover invocations. Provisional diagnostic candidates are never accepted.

ui/radial.py owns injected preview edges, navigation and DryRunSelection;
ui/placement.py owns pure geometry. ui/popup.py paints/hit-tests the same logical
geometry and owns the short popup event loop, timers and cleanup. Native Windows
monitor mapping lives in platforms/windows/qt_position.py and matches physical
monitor origin/dimensions to one QScreen using its logical size and DPR before
scaling relative to that screen's origin. Qt friendly names are diagnostic only. Work
area clamping happens in logical pixels. Real Windows overlay behavior is unverified.
No file I/O or engine runs in the UI. G5 will add PNG→JPEG through an independent
worker and actual capability attestation; other choices remain dry-run previews.
