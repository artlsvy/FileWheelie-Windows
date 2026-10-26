# Architecture and portable test seams

Target: Python3.14; Windows 11 at runtime; Kubuntu for primary development.

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
UI dependency. Pillow, PyMuPDF, pdf2docx and MarkItDown are optional local extras; LibreOffice
is detected as an external local executable. The personal Send to shortcut is a small invocation integration, not a
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
No engine runs on the GUI thread. ConversionJob owns a QThread and cooperative
cancel event; popup lifetime extends until cleanup finishes. Normal launch injects
ConversionManager.registry, not preview edges. Actual outcome/path tuples survive
closure and are serialized safely by the CLI; headless diagnostics still never
import Qt or convert.

### G5–G8 local engines

converters/base.py defines capabilities, EngineOutput, ConversionResult and the
engine protocol. Registry includes only available engines/codecs. ConversionManager
revalidates source metadata, creates a private staging directory beside it, asks
the chosen engine to encode, validates every output, then atomically hardlinks to
unused names. Collision retry never replaces existing files. Cleanup removes the
stage and this job's known outputs on failure/cancel. Unsupported hardlink volumes
fail closed. Engine code does not choose arbitrary final paths.

Pillow handles image transcoding/alpha/orientation and image PDFs. PyMuPDF renders
all PDF pages with size limits. pdf2docx reconstructs editable text with scanned-PDF
rejection and fidelity warnings. MarkItDown registers one local Python converter
with plugins/builtins off and HTTP denied; the unifiedPython3.14 runtime satisfies upstream support metadata. ONNX telemetry opt-out is set before optional imports.
LibreOffice uses a private profile and fixed argv in a bounded process tree;
DOCX external resources/macros are not loaded. No Word/LLM/cloud service required.

UI geometry/transparency is independent of engines: configurable 170px wheel uses
one scaled reference layout for hit testing and paint, with transparent clear and
no OS rectangular shadow. Linux tests establish code paths, not native compositor
or Windows engine operation. CONVERTERS.md records runtime instructions/limits.


### G10–G12 desktop host and packaging

The normal `filewheel` entry owns one QApplication, tray host, controller and
conversion manager. Current-user lock/local Qt IPC forwards repeated explicit
invocations; it accepts no commands to enable experiments. Headless diagnostics
remain independently importable without Qt/COM. The tray listener transports
immutable ExperimentalCandidate evidence from existing workers to Qt. Candidate
consent is separate from trusted TargetResolution; one-shot confirmation and
fresh path validation create `user_confirmed_candidate`, never `explorer_hover`.

Frozen paths resolve beside Filewheel.exe, while resources remain under
_internal. Early freeze_support handles worker spawning. Complete portable
LibreOffice discovery and external-child environment isolation live in
libreoffice_bundle.py, outside Qt and the converter. LibreOffice remains optional
and is used only for DOCX → PDF. See PACKAGING.md and PORTABLE_LIBREOFFICE.md.


### Current personal direct-activation route (D-016)

The user has authorized direct Mouse3 wheel opening. CandidateGate.activate
consumes a current token, requires event age <=500 ms and revalidates the path
through InvocationController. Its TargetResolution source is explicitly
experimental_candidate. It never claims proven hover identity. Optional tray
confirmation still uses confirm() and source user_confirmed_candidate; Send to
uses shell_explicit. All share the same popup and conversion manager. Source is
kept distinct even though the validated-path DTO is shared.


### Grouped Shell lookup

Grouped views use native GetGroupBy metadata or an in-content UIA group marker.
The bounded grouped_name route cross-checks an active-view native anchor's parent
with the automation folder, parses one literal full filename, and corroborates
native child/parent paths through SHCreateItemFromParsingName. Collision and
snapshot checks remain mandatory. UIA IDs are never treated as flat indices in
this route; native_item_path_match is the shared positive path check after the
route-specific assessor succeeds. Indexed views still check range and native
index correspondence. Both remain experimental until a real identity bridge
exists. No full group enumeration or selection lookup is involved.


### Persistent conversion status (D-018)

The same RadialPopup changes its native window type from selection Popup to
non-modal topmost Tool for converting/result stages. The guarded flag transition
preserves geometry and suppresses hide-triggered finish/cancellation. Focus/outside
activity is ignored only in status stages. Reopening restores Popup mode. The
status face uses short words/percentages; actual engine messages and outcomes
remain unchanged in metadata/tooltips/logs. UI Cancel/Escape requests cooperative
cancellation without hiding, while explicit application dismissal/Quit retains
its cleanup contract. Busy invocation rejects without cancelling ongoing work.


### Isolated conversion execution

ConversionJob remains an owned QThread for supervision, but production
ConversionManager work runs in one fresh multiprocessing spawn child. Trusted
local engine/registry options are serialized as spawn arguments; no user file is
loaded as a pickle. The private result pipe uses strict bounded JSON. Child
progress is throttled, error types/engine/operation/log paths are reconstructed,
and outcome signals occur only after the child exits and its handles are closed.

The existing manager owns the complete staging/validation/publication/rollback
transaction in the child. Cancellation uses a shared Event and remains
cooperative; no forced termination risks interrupting publication. Unexpected
native process death is contained but may leave private staging/partial new
outputs, which are not blindly deleted by the parent. A hung native library can
still delay shutdown, while Qt and hook execution remain in another interpreter.
Common native pools are limited and child priority reduced best effort; this does
not promise a universal one-thread limit for every third-party library. HEIF
registration is performed in the fresh child because parent plugin state is not
inherited. Source/frozen entry freeze_support remains before GUI startup.
