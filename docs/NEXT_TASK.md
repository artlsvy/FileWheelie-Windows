# Next task: Windows acceptance of persistent simple conversion status

The user confirms the grouped Explorer fix works. Do not repeat that investigation.
Current UI changes: only In progress/percentage plus the existing round ring;
results use simple words, with details retained in tooltips/logs. Conversion and
results stay in a non-modal topmost Tool window when clicking elsewhere. Selection
menus still use normal popup dismissal. Wheel size stays 170 logical pixels.

Linux checks: 357 tests / 362 subtests passed, plus scoped Ruff, compilation
and focused review. Native Windows persistence still requires acceptance.

## Windows test

Quit the old tray process, update the checkout, then start:

```powershell
.\.venv-filewheel\Scripts\python.exe -m filewheel --tray
```

Enable Experimental Mouse3, open a file and choose a conversion. Use a conversion
long enough to click Explorer/Notepad while it runs. The circular progress window
must remain visible at its original position, above ordinary windows, without
cancelling or blocking interaction with the other app. It should show only In
progress, a percentage/ring and Cancel. After completion, simple Done/File saved
(or Failed/Cancelled) must remain visible until Done/Escape. Hover for output,
warning or error details; detailed diagnostic logging must still be available.

Cancel or Escape while busy should show Stopping until the worker finishes,
then Cancelled; it must not destroy a running worker. Tray Quit must still exit
cleanly after owned cleanup. Start a second invocation while busy: it must reject
without cancelling. After finishing/dismissing, open another file: the normal
category/format wheel must again dismiss on outside click and keep correct near-
cursor/DPI placement. Check transparent corners and no native rectangular frame.

Linux offscreen flags/worker/visibility tests do not establish Windows z-order,
focus or compositor behavior. Record actual native acceptance in STATUS.md.
Send to and Mouse3 evidence filters are unchanged. Do not push without separate
authorization.
