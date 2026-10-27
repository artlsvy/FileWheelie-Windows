# Active: finish Pandoc D and packaging E (F1–F4 committed next)

User reports all eight Windows progress-pill functional checks passed, but an
intermittent missing transition recovered after app restart. Do not attribute
it to GPU or worker failure without evidence. Phase 1 appearance is approved.

Current order (latest user steering):
1. F1 selection entrance140ms/leave fade110ms, immediatehit; independent from
   progress morph; instant reduced/low effects.
2. F2 dismissal radius118/debounce100ms, actual sector radius110 unchanged.
3. F3 short PDF labels JPG/PNG with all-pages descriptive metadata/tooltips.
4. F4 repeated-window/timer/animation lifecycle consistency and recovery. Preserve
   observable jobs if a surface/animation is unexpectedly stopped/hidden/destroyed.
   Do notclaim definitive native intermittentfix without reproduction.
Commit F separately after tests, real renders and review, then resume D/E.

A4329317 progress-pill and B5767151 To MD/From MD are complete. C116f5c2 bounded
text/HTM/EPUB/ZIP extraction is complete (601fullsuite, plus finaldeadline test
focusedpassing; next fullrun mayincreasecount). Do NOT repeat A–C.

Untracked D work preserved: converters/pandoc.py, pandoc_tool.py,
tests/unit/test_pandoc.py. Agentreported19 actualPandoc3.12.1 tests pass (7writers
and stagedPDF); not registered/committed yet. Tool module needs its own process/
discovery tests, integration review, registry gating and packaging validation.
Verified local testbinary /tmp/filewheel-pandoc-3.12.1/pandoc can be selected via
FILEWHEEL_PANDOC. Optional official Windowszip hash is recorded in session; do
not bundle giant tool by default. Finish D after F, then E.

Preserve converters, controller/trust/touchpad consent, Send to, tray, QWidget
fallback and file publication safety. No push. Native F/mixed-DPI/frozen/newtool
acceptance remains pending; Linux cannot establish it.

F1–F4 source/tests/rendered proof are implemented and checked:615tests/406subtests
(excluding preservedD tests),15smokechecks; focusedreview closed materialfindings.
Once F is committed, nextaction is integrate preservedPandocD, adddiscovery/process
tests and template-capability gating, then E packaging/locks/finalregression.
Do notrepeat A–C or redesign approvedglass.
