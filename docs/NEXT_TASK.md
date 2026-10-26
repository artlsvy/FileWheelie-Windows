# Current task: measured Qt Quick glass prototype

Phase1 timing instrumentation and architecture evaluation are implemented.
See PERFORMANCE_ARCHITECTURE.md and docs/performance/widgets-baseline-linux.json.
Local warm QWidget CPU/event dispatch is already ~1ms p95; Windows queue/Explorer
latency is pending. Do not migrate the application language based on assumption.

Continue the authorized separate QML radial prototype, moving annular hover lens,
measured comparison, selectable opt-in integration only if justified, and local
.agents/skills/filewheel-glass/SKILL.md. Preserve controller/worker/converter and
all Mouse3 trust rules. Keep QWidget as the default until native acceptance.
Commit prototype, lens and optional integration/design guidance separately.

Prior native queues remain: Precision Touchpad opt-in mandatory confirmation
(D-021), and large-PDF Cancel -> retry -> tray Quit (D-020). No Windows native
results for those newer changes have been reported. Existing Send to/physical
Mouse3 and earlier UI/normal conversions are user-reported working. Do not push.
