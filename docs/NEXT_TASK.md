# Next task: Windows acceptance of large-folder Mouse3 fix

The confirmed 32-item gate is replaced by bounded targeted Shell lookup. G10's
confirmation dialog, Send to fallback and trusted resolver are unchanged.
No conversion/UI/LibreOffice/packaging work is part of this fix.
Linux validation: 331 tests / 305 subtests, scoped Ruff and compilation pass;
focused review found no remaining material blockers. Native acceptance is pending.

## Windows 11 acceptance

Quit the old resident Filewheel tray process before launching the updated source:

```powershell
.\.venv-filewheel\Scripts\python.exe -m filewheel --tray
```

Enable Experimental Mouse3 using the existing tray checkbox. Use a local Explorer
folder with **at least 500 files** and show file-name extensions. Scroll and
middle-click an item whose index is **greater than 32** (for example a file near
the end of a 600-file view). Verify that confirmation shows the exact intended
absolute path. Cancel must do nothing; confirming must open the existing radial
converter at the event point. Repeat with a second high-index file and a different
active tab whose folder has a different size. Ensure activation stays responsive.
Small folders must retain their existing behavior.

Large folders intentionally reject hidden/shortened labels, conflicting evidence,
and ambiguous names; incomplete listings never justify bypassing duplicate-name
protection. Test a full-name collision such as photo.png plus photo.png.txt and
ensure it rejects conservatively. Check background/chrome rejection and the
unchanged Send to fallback. Do not revisit already-confirmed conversion types.

The implementation makes two indexed native GetItem reads and one independent
Shell automation Item(index) read per large active view. Inactive tabs collect no
items. Filename ambiguity uses at most three returned Win32 search names, not a
Python/Shell directory walk. Actual filesystem query latency/wildcard behavior
still requires Windows acceptance; the existing freshness deadline is retained.

Record Windows results in STATUS.md. If a concrete regression appears, fix only
that blocker. Existing G11/G12 native packaging validation remains queued from the
prior milestone, but is outside this G10 directory-size task. Do not push unless
the user separately authorizes it.
