# Next task: Windows EXE cancellation acceptance

Current fix (D-020) addresses Cancel hanging during a large PDF library call,
which also prevented tray Quit. Parent-owned staging plus a publication permit
allows a stuck pre-publication worker to be stopped after a two-second grace
period. Saving is never forcibly interrupted. OS termination and cleanup can
add time beyond that grace; errors are reported rather than pretending cleanup
finished. Mouse3 targeting, UI appearance, Send to and converter pairs are unchanged.

Linux: 402 tests /406 subtests passed; changed-file Ruff/compilation checks pass.
Repository-wide Ruff still has 31 findings in unchanged files. Review found no
material blockers; a detached POSIX Office session has a residual cleanup limit
if its worker never reaches cooperative cleanup (STATUS.md). Native Windows
termination, locked-stage cleanup and EXE behavior are not proved by Linux.

Exit the old Filewheel instance before rebuilding. From the updated Windows
checkout, use the existing Python 3.14 build recipe:

```powershell
powershell.exe -NoProfile -ExecutionPolicy Bypass -File .\scripts\build-windows.ps1
& .\dist\Filewheel\Filewheel.exe --self-test
& .\dist\Filewheel\Filewheel.exe --tray
```

Use the whole rebuilt onedir folder when running from another location.
Rebuilding is required; an already-built EXE does not load updated source.

Acceptance sequence:
1. Enable Experimental Mouse3; start the original slow large PDF conversion.
2. Cancel while it is working. Expect Stopping briefly, then Cancelled; keep
   moving the mouse and verify the desktop remains responsive. Verify the
   conversion worker/its children exit and no private .filewheel-* stage remains.
3. Retry exactly the same file from the same open Explorer folder. Verify its
   output opens, the source is unchanged, and previous outputs remain intact.
4. Repeat Cancel, immediately choose tray Quit, then relaunch. It should release
   the existing instance and start normally, without needing Task Manager.
5. Repeat a normal conversion and an explicit Send to invocation.

If Mouse3 still ignores the file until its folder is reopened, record the actual
rejection/log and compare with Send to using the same path. That symptom is not
yet diagnosed; do not weaken file identity checks or guess a selected file.

No extra conversion formats or packaging changes are queued by this bug fix.
Full clean-machine G11 and optional G12 portable Office acceptance remain pending
as described in PACKAGING.md and PORTABLE_LIBREOFFICE.md. Do not push without
separate authorization.
