# Current task: final single-file package after progress boundary fix

Native stock-Dolphin default integration is implemented and user-tested. Preserve
it and the existing engines/UI. User then reported expanded progress spilling past
the screen in /home/lsvy/ui bad allignment.jpg; image was inspected and exact bug
reproduced on native Wayland. KWin placed initial72px surface only; height190 later
kept its old Y. It overflowed usable area by102.06 logical pixels at1.55 scale.

Fix is in linux/kwin_placement.py, used by KWinBridge: event-driven live KWin work
area clamp on resize/reuse/output changes, original monitor retained, no focus
steal or foreign-window changes. Native before/after expanded bottom now has16px
panel clearance. Dark animated and light reduced-motion six-stage real Quick
checks pass. 127 tests pass/4 intentional skips; Ruff/compile pass. See
linux-evidence/progress-placement-fix.json and scripts/linux/check_progress_placement.py.

Finish building one final AppImage with --artifact-name Filewheel-Linux-x86_64.AppImage,
run frozen and installer checks, place a clear final artifact under dist/ and
record its hash. No Python/pip/private Dolphin should be needed. Automatic second
app setup for26 MIME types stays in the installer. Preserve helpers/diagnostics.
Do not force-kill the running tray/any worker to update it; instruct Quit/reopen
for the new compositor script. Do not push or start GNOME work in this task.

User untracked assets/ui/wheel.jpg and wheel (2).pdf/.png pre-existed this task;
leave untouched/uncommitted, exclude from distributable source snapshots.
Branch feat/linux-port. Previous artifacts under build/linux-native-dolphin do not
contain the progress fix. Current requested deliverable is the final corrected
single installation file, not an additional prototype browser.
