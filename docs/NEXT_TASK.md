# Next task: Windows acceptance of direct Mouse3 and compact circular UI

The user reports successful large-folder Windows Mouse3 operation and authorizes
removing the repeated file-confirmation dialog. The direct route opens the wheel
after the same evidence filters, original-event freshness check and controller
path revalidation, with source experimental_candidate. Trusted hover remains
unproven. Optional per-file confirmation remains in the tray menu; Send to is
unchanged. Do not repeat the old directory-size diagnosis.

Linux checks: 341 tests / 322 subtests, scoped Ruff, compilation and focused
review pass. No new Windows run by Codex is claimed.

## Verify on Windows 11

Quit the old Filewheel tray process, update the checkout, then run:

```powershell
.\.venv-filewheel\Scripts\python.exe -m filewheel --tray
```

Enable Experimental Mouse3. Leave “Confirm file before opening” unchecked.
Middle-click a local file: the wheel should open directly, with no extra dialog.
Hover to inspect the full path; no conversion happens until choosing a format.
Check a high-index file in the previously successful large folder. Ambiguous,
missing, stale or conflicting evidence must still reject. To restore the former
per-file dialog, check the confirmation option for this session.

The wheel is now 220 logical pixels with a small Esc/Back center, larger labels,
and forest/ivory/brass light/dark palettes. Check readability on your actual DPI
settings, correct hover regions, Back, Esc and outside dismissal. Progress and
results must stay circular without a square panel; verify Cancel, Done and error
details in tooltips. Source files and existing outputs must remain untouched.

Native visual/direct-route acceptance remains pending. Large-folder activation
itself is already user-reported successful. Prior standalone packaging/portable
LibreOffice native checks remain queued but are outside this UI task. Do not push
without separate authorization.
