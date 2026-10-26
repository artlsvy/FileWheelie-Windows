# Next task: native Precision Touchpad acceptance

D-021 implements an explicit opt-in for injected middle-clicks that are not
marked lower-integrity. Physical Mouse3 and Send to retain their behavior.
Every injected candidate requires the exact-path confirmation dialog, regardless
of the normal physical-candidate confirmation preference. Explorer provenance,
geometry, active tab, filesystem/path corroboration, freshness and snapshot
checks remain mandatory. The flag does not identify the injecting device/app.

Implemented/Linux-tested, **not yet Windows-verified**. Full suite: 478 tests
and 406 subtests passed. Changed-file Ruff/compilation/diff checks pass; 25
pre-existing lint findings remain in unchanged files. Focused review found no
material issues. No push was performed.

After transferring the new commit to the Windows checkout, exit the old app and
rebuild the EXE (an old EXE does not load new source):

```powershell
powershell.exe -NoProfile -ExecutionPolicy Bypass -File .\scripts\build-windows.ps1
& .\dist\Filewheel\Filewheel.exe --self-test
& .\dist\Filewheel\Filewheel.exe --tray
```

Laptop acceptance:
1. Keep Windows Settings configured for three-finger tap -> Middle mouse button.
2. In the tray, turn Experimental Mouse3 off if running. Wait for shutdown, then
   check Touchpad middle-click (always confirm), and enable Experimental Mouse3.
   The touchpad setting is session-only and off after a fresh app launch.
3. Disable Confirm file before opening to test the mandatory injected override.
   Three-finger tap a regular Explorer file. Verify the dialog shows its exact
   path before any wheel or conversion appears. Cancel must do nothing; repeat
   and Use this file must open the correct wheel and normal converter workflow.
4. Tap blank space, a folder and a browser hyperlink. Filewheel must not propose
   a target there; normal browser middle-click behavior should remain intact.
5. Stop Mouse3, uncheck the touchpad option and restart Mouse3. Injected taps
   should again be ignored. A physical middle button must still work.
6. Repeat physical Mouse3 with touchpad opt-in on; the physical confirmation
   preference must be respected. Verify explicit Send to still works.

Lower-integrity flags are always rejected; do not enable a lower-integrity
bypass if the particular laptop gesture remains rejected. Existing standalone
diagnostics keep their physical-only policy; they do not enable the tray opt-in.
If necessary, use a narrowly evidenced follow-up to determine the remaining
rejection; do not weaken candidate identity/provenance safeguards.

Keep the separate previous acceptance queue: cancel the original slow large PDF,
retry the same file without reopening Explorer, then Cancel -> tray Quit ->
relaunch. D-020's bounded pre-publication cancellation was Linux-tested; its
native EXE results have not been reported here.

Full clean-machine packaging/portable Office checks remain in PACKAGING.md and
PORTABLE_LIBREOFFICE.md. No new formats, broad diagnostics or UI redesign are
authorized by this change. Do not push without separate authorization.
