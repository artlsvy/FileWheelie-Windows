# First Windows diagnostic session — supplied evidence review

Evidence source: JSONL pasted by the user in this conversation, reviewed
2026-10-24. Codex did not run or directly observe this Windows session. Test date,
Git revision, command line, console output and shutdown result were not supplied.
Private absolute folder names are deliberately omitted from this summary.

Session reports Windows build 26200, per-monitor v2 awareness and Explorer window
DPI 96. Eight sequential, non-injected events have matching foreground/root HWND,
`CabinetWClass`, and an `explorer.exe` process image. Each event collected UIA and
Shell data without `evidence_error` or `window_changed`. This supports Mouse3
capture and successful native/COM bindings in this session. It does not establish
lossless input capture, one event per physical press, callback latency, passive
native behavior, queue-drop count or shutdown correctness.

| Sequence | UIA item at point | Observation |
| --- | --- | --- |
| 1 | a.txt | Name property child, then containing UIItem row |
| 2–3 | b.txt | Name property child, then containing UIItem row |
| 4–5 | a.txt | Name property child, then containing UIItem row |
| 6 | b.txt | UIItem directly at point, icon-shaped bounds |
| 7–8 | none | Items View directly at point, consistent with background |

The rows in events 1–5 suggest a Details-like layout and event 6 suggests icons;
the actual view setting was not recorded (`explorer_view` is unknown). All named
UIItem bounds contain the click point and all ancestry process IDs match
Explorer. Ancestry reaches the expected root via a ShellTabWindowClass child.
The leaf name is often just “Name”, demonstrating why ancestors must be inspected.
No selection snapshot, selected-file report or operator expected-target report
was included, so independence from selection remains unverified.

Shell enumeration consistently returned three candidates: one filesystem folder
and two filesystem files corresponding to the two displayed names. Enumeration
was not truncated. UIA automation IDs “1”/“2” happen to resemble the candidate
indices in this folder. **This coincidence is not a documented identity mapping.**
UIA runtime ID for b.txt also changes between the row-shaped and icon-shaped
captures; it must not be interpreted as a persistent Shell identifier.

All eight paths correctly remain null with `mapping_unproven`, including the
background clicks. Background rejection is therefore safe but not yet specifically
classified as “no file item”. Candidate Shell identity correspondence, view
geometry and active-tab correspondence are explicitly unproven/unavailable.
Collection durations range from 26.069 to 56.942 ms; these measure worker evidence
collection, not hook time or total input-to-worker latency.

No unrelated-application events or planned click counts were supplied. The
records establish positive Explorer recognition only; they cannot verify that
negative filtering works. Tabs, duplicate display names, hidden extensions,
scroll/sort races, scaling and filesystem existence/type validation remain open.

## Next experiment: controlled diagnostic smoke test

Use the updated diagnostic in `DIAGNOSTIC_POC.md`. It adds aggregate filtering
counts and read-only UIA selected-state snapshots, never path matching. Execute
the numbered protocol there, record expected click counts and selected/hovered
files, and include the final capture summary plus console exit/drop results.
This tests the diagnostic's input/filter/visual-target behavior before investing
in native Shell view identity/geometry bindings. G2 remains unverified even if
this next smoke test passes.
