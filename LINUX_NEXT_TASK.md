# Next: physically test the authorized private Dolphin URI bridge

User approved the isolated Dolphin prototype. It compiled successfully in Docker;
see LINUX_STATUS.md and prototypes/dolphin-bridge/README.md. The installed Dolphin,
Windows application and host packages were not replaced or modified.

Run on the actual KDE Wayland desktop (new report path required):

```bash
/usr/bin/python3 prototypes/dolphin-bridge/receiver.py \
  --dolphin build/dolphin-probe/bin/dolphin \
  --library-dir build/dolphin-probe/lib/x86_64-linux-gnu \
  --seconds 240 --report /tmp/fw-clicked-uri-next.json
```

In both private scratch tabs, left-click `previous selection.txt`, then physically
middle-click `report.txt`, `report.csv` and `unicode-æøå.txt` without preselecting
those targets. Compare each accepted relative path with the actual tab/file clicked.
Record user confirmation and the report, including failures. No conversion runs.
The receiver automatically closes only its private child and removes scratch
files. Ctrl+C also closes it and writes the report. If the chat laptop is a
separate host, the native test must run there; the workspace's windows are not
visible on an unrelated machine.

If those tests pass, the authoritative URI contract is demonstrated for this
patched Dolphin only. Then test large/grouped folders and stale events before
integrating an experimental Linux invocation adapter. Do not count compiler/API
smokes as physical acceptance. Do not infer stock-Dolphin, GNOME or general Wayland
support, or start packaging/converter work under this bounded prototype task.
Do not replace the system file manager or install a binary KWin plugin. No push.
