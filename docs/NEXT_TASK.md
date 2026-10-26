# Next task: Windows responsiveness and curved/translucent UI acceptance

The interrupted implementation is complete: production conversions now run in one
spawned child, supervised by Qt. This addresses converter/hook shared-GIL
contention and limits common native worker pools best effort; actual Windows
cursor lag resolution still needs testing on the reported file. Keep all existing
Mouse3 identity checks, Send to, persistent status and manager output safeguards.

Linux validation: 377 tests / 387 subtests pass, with scoped Ruff, compilation
and focused review. Actual cursor-lag resolution on Windows is not yet verified.

Quit the old tray process, update the source checkout and run:

```powershell
git pull --ff-only origin main
.\.venv-filewheel\Scripts\python.exe -m filewheel --tray
```

No new Python dependency is required for process isolation. Enable Mouse3 and
repeat the conversion that previously lagged while continuously moving the cursor
and using Explorer/another app. Progress/results must stay visible and responsive;
Cancel/Escape/Quit must wait for owned cleanup, and no uncontrolled extra tray
processes should open. Check readable output, original bytes and collision names.
Test with Mouse3 off and Send to if lag remains, then provide conversion pair,
file size/page count and whether both invocation routes are affected. Do not claim
all possible CPU/memory/driver stalls were solved by the isolation change.

The 170px menu now says No formats, follows sector curvature and has a slightly
translucent surface with opaque labels/actions. Check upper/lower labels,
hover/separators, light/dark backdrop readability and transparent corners on the
actual Windows DPI setup. Full labels, paths and errors remain in tooltips/logs.

DOCX → PDF is already implemented. Follow DOCX_TO_PDF.md to install the normal
LibreOffice application, check LibreOfficeEngine detection in .venv-filewheel,
restart the tray to rebuild capabilities and choose Docs → PDF. Do not install a
Python package named libreoffice or confuse this with the PDF → DOCX engine.

Native Windows/frozen spawning, priority and compositor behavior remain pending;
Linux tests do not prove them. Cooperative engine hangs may delay shutdown and
catastrophic native crashes can leave staging artifacts; never blindly remove
unknown files. Record results in STATUS.md. Do not push without authorization.
