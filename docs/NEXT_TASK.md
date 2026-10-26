# Next planned task: native standalone Windows build (G11)

The user accepts the current source/venv application: conversions work, completion
status is correct, Windows remains responsive and the UI is satisfactory. The
WinError109 acceptance checkpoint is closed by user report. No urgent runtime
fix is queued, and no further Mouse3/GUI redesign is requested.

When development resumes with an action request, prioritize building/testing the
existing standalone recipe on Windows 11 with standard 64-bit Python 3.14:

```powershell
powershell.exe -NoProfile -ExecutionPolicy Bypass -File .\scripts\build-windows.ps1
& .\dist\Filewheel\Filewheel.exe --self-test
& .\dist\Filewheel\Filewheel.exe --tray
```

Follow PACKAGING.md. Move the whole onedir folder to a location without the venv
and verify GUI/Mouse3/Send to, real conversions, spawned-worker completion/cancel,
repeated invocation and clean Quit. Native frozen execution has not been tested
by Codex; Linux tests/source acceptance do not establish it.

Then optionally verify the existing personal startup registration (starts tray
with Mouse3 off), and G12 complete portable LibreOffice using
PORTABLE_LIBREOFFICE.md. System-installed LibreOffice already satisfies DOCX→PDF;
its portable bundle is optional for daily source usage. Remembering Mouse3 opt-in
across launches would be a separate explicitly chosen preference feature, not
an automatic startup change.

Last automated suite: 382 tests /398 subtests passed. This planning checkpoint
changes documentation only. Do not push without separate authorization.
