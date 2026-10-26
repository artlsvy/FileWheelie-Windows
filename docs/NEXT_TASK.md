# HARD STOP: Phase 1 UI awaits user review

Phase 1 glass geometry and circular mouse-leave correction is delivered for
review. **Phase 2 has NOT started. Do not implement, research or restructure
Markdown/navigation/format support until the user explicitly approves Phase 1
in a subsequent message.** Passing tests, screenshots, automatic resume and
silence are not approval. Do not infer approval from an unrelated status request.

Read GLASS_UI_PHASE1.md for before/after images, exact Windows build/source/Quick
commands and acceptance. The original reference screenshots are /home/lsvy/1.jpg,
2.jpg,3.jpg; generated captures are docs/ui-phase1/{before,after-100,after-150}.
The default QWidget fallback and all converters/Mouse3/Send to/tray paths remain.

Next action is **wait for user feedback**, then address requested Phase 1 fixes
if any. Native Windows checks remain: common-pivot/lens appearance, circular
leave/re-entry/reopen, progress/result persistence, focus/keyboard, light/dark,
100%/150% mixed DPI, frozen resources/compositing. Linux offscreen checks cannot
establish those native behaviors. Earlier D-020 Cancel/retry/Quit and D-021
Precision Touchpad acceptance remain open; do not silently mark them verified.

If the user explicitly approves Phase 1, consult their Phase 2 specification
before planning any Markdown/Pandoc/format changes. No push is authorized.
