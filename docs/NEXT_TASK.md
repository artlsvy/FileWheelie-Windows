# Next task: Windows acceptance of grouped Explorer lookup and 170px wheel

User reports later Downloads date groups do not activate Mouse3. A grouped_name
lookup now resolves the exact visible filename in the active real folder and
cross-checks native child/parent evidence. It does not treat group-local UIA IDs
as global Shell indices. Flat views retain indexed lookup. The route stays
experimental, with all ambiguity/freshness/path checks and optional confirmation.
No conversion, packaging or Send to behavior was changed.

Linux checks: 352 tests / 360 subtests, scoped Ruff and compilation pass.
Focused review found no remaining material blockers.

## Windows test

Quit the running tray process before launching the updated checkout:

```powershell
.\.venv-filewheel\Scripts\python.exe -m filewheel --tray
```

Enable Experimental Mouse3. In Downloads grouped by date, middle-click ordinary
files under Today, Yesterday and Earlier this week, including the first/last file
of each group. Verify the exact filename/path via tooltip and the intended output.
Test a later group after scrolling, sorting, collapsing/reopening a group and
switching Explorer tabs. Group headers/background must not activate. A duplicate
or hidden/shortened label remains a safe rejection; use visible file extensions
for the positive test. Confirm the previously working flat large folder still
works and latency is acceptable. No Windows success is claimed from Linux tests.

The wheel is now 170 logical pixels (50px smaller). Check Docs, Image and Text/MD
labels, hover, Back, Esc, outside dismissal, progress Cancel and result Done at
Windows DPI settings. Full category names and paths stay in tooltips. The same
circular forest/ivory/brass appearance remains.

If a later group still rejects, paste one existing rejection/evidence record;
actual group IDs/provider behavior are needed to isolate that specific case.
Do not add unrelated diagnostic tooling or guess a selected file. Keep Send to
available. Record native results in STATUS.md; do not push without authorization.
