# Filewheel architecture

Private Windows11 application. No accounts, uploads or telemetry. Python3.14
coordinates the native Qt UI, guarded Windows adapters and isolated converters.

| Area | Responsibility |
|---|---|
| app.py / ui/desktop.py | Startup, tray, single-instance forwarding and invocation routing |
| platforms/windows | Passive Mouse3 queue, Explorer/Shell evidence and explicit-path integrations |
| core | Target validation, freshness/provenance, deduplication and navigation |
| ui/quick_popup.py / qml | Retained glass wheel and durable progress surfaces |
| ui/conversion_controller.py | Application-owned job lifetime independent of windows |
| converters/process_worker.py | Spawned workers, bounded progress and cancellation/publication protocol |
| converters/manager.py | Private staging, output validation and collision-safe publication |
| converters/registry.py | Only genuinely available conversion pairs are exposed |
| packaging | Windows onefile/onedir builds, embedded native tools and runtime setup |

## Boundaries that must remain intact

- Hook callbacks enqueue and return quickly; no COM, filesystem or conversion
  calls in the hook. Selection/focus/name alone never establish hovered identity.
- Experimental Mouse3 retains its provenance and evidence checks. Injected input
  requires opt-in and exact-path confirmation. Send to passes an explicit path.
- Closing/hiding progress never cancels a job. Explicit Cancel and shutdown use
  owned worker cleanup. A publisher is never killed after publication permission.
- Source files and existing outputs are not overwritten. Real outputs are checked
  before publication; failure/cancellation cleans private staging.
- Quick/OpenGL is the family build preference; explicit settings and Widgets remain.
  UI details: GLASS_UI.md, PROGRESS_UX.md and F5_RENDERER_RELIABILITY.md.
- Embedded tools live under the extraction root; shortcuts point to the stable
  EXE path. Family mode cannot silently rely on installed Pandoc/LibreOffice.

The standalone file is versioned through Git LFS under releases. Build instructions
are in SINGLE_EXE.md. Safety/API evidence: EXPLORER_HIT_TEST.md and G2_MAPPING.md.
C assessment and current engineering tradeoffs: PERFORMANCE_ARCHITECTURE.md.
