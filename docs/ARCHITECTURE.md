# Architecture and portable test seams

Target: Python 3.12+; Windows 11 at runtime; Kubuntu for primary development.

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
               [G4] PySide6 radial wheel / tray process
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
- `src/filewheel/ui/`: wheel later.
- `tests/unit/`: fakes and pure tests; `tests/windows/`: marked tests requiring an interactive Win11 session.

Not required yet: a GUI, installers, image libraries, MarkItDown or LibreOffice. Add dependencies only when milestone demands them.

### Correctness and latency
- Record event quickly and return from the hook before doing any UIA/COM work; the OS may silently remove timed-out hooks.
- UIA element lifetimes are transient. Timeouts and race conditions return None, not a stale previously selected file.
- Marshal between threads explicitly and initialize COM per owning thread. Avoid accessing COM objects on another thread without proper marshaling.
- All screen coordinates must be consistently physical vs Qt logical; normalize at the UI boundary, not within the resolver.

### Tests and platform behavior
- Pure modules import and run on Kubuntu without Windows packages.
- Windows tests run only with explicit `@pytest.mark.windows_integration` and do not run in headless Linux CI.
- Fake resolver returns target or None and records invocations. Negative tests are more important than proving file A worked once.
