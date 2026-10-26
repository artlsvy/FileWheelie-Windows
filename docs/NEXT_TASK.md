# Next task: Windows completion-status verification

User confirms conversion outputs, curved/translucent UI and cursor performance
work on Windows. The reported false Failed/WinError109 after success is addressed
by normalizing poll-time closed-pipe EOF; the supervisor still requires a valid
outcome and clean child exit. Engines, publishing and UI behavior are unchanged.

Linux checks: 382 tests /398 subtests, scoped Ruff, compilation and focused review
pass. Tests include Windows-style poll EOF after a real spawned conversion;
these simulations do not establish native Windows acceptance.

Quit the old Filewheel tray process, update the source checkout and run:

```powershell
git pull --ff-only origin main
.\.venv-filewheel\Scripts\python.exe -m filewheel --tray
```

Repeat one conversion that previously produced a valid output but displayed
Failed/pipe ended. Expect Done/File saved, readable output and no WinError109.
Keep the original and earlier outputs; a repeated conversion uses a collision-
safe numbered name. Check another conversion if practical. Actual failures and
Cancel must still show Failed/Cancelled; a missing outcome or crashed worker must
never be marked Done just because an output file exists.

Record native results in STATUS.md. No process-isolation rollback, conversion
retry, unrelated engine work or extra diagnostic tooling is needed. DOCX→PDF
setup remains in DOCX_TO_PDF.md. Do not push without separate authorization.
