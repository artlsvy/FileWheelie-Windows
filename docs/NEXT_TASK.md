# F5 implementation complete — stop feature development

Only the requested F5 renderer investigation is authorized in this task. Do not
resume converters, formats, redesign, Phase 2 work or another milestone. Do not push.

Windows Quick now prefers OpenGL RHI before Qt initialization, while explicit
Qt backend settings and Widgets remain available. Native source D3D11 failed at
cycle 6, frozen D3D11 at 66; both showed absent desktop pixels with an intact pill
render target. Source and frozen OpenGL each passed 100 cycles, as did software.
This is evidence for a practical mitigation, not a universal Qt/driver diagnosis.
Final source and frozen OpenGL runs also passed 100 cycles with tracing disabled;
the final frozen run needed zero selection reopens. Packaged self-test: 33 checks
and 26 real conversion pairs passed. Raw summaries include earlier incomplete
trials rather than treating every test process as a success.

The next user acceptance step is at least 50 normal conversions in one OpenGL
tray session, including cancel/retry, focus changes and first-conversion pointer
responsiveness. Use the exact startup, override, trace-snapshot and regression
commands in [F5_RENDERER_RELIABILITY.md](F5_RENDERER_RELIABILITY.md). Fully quit the
old tray owner before changing settings. Retain the complete isolated onedir in
artifacts/f5/frozen/Filewheel, or rebuild dist/Filewheel using the existing
build script. If feedback disappears, use the opt-in tray trace snapshot before
restarting. Record effective API, PID and sequence.

Keep WINDOWS_VALIDATION_REQUIRED for mixed DPI/monitors, other GPUs/drivers,
sleep/resume, actual pointer latency and long real conversion sessions. Older
Mouse3/Send to/optional-tool acceptance queues in STATUS.md are preserved, not
claimed completed by this UI-only harness. Full-suite Windows baseline failures
are documented separately; do not silently broaden F5 to fix unrelated engines.
