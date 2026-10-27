# Next: native Windows acceptance of the completed Phase 2 build

Implementation checkpoints are complete: A `4329317` (independent jobs/glass
progress pill), B `5767151` (To MD / From MD), C `116f5c2` (bounded offline
Markdown inputs), F `67c96cd` (selection motion/lifecycle recovery), and D
`2409f61` (real Pandoc writers/staged PDF). E adds optional native-tool packaging,
artifact hashes, expanded smoke tests and the final conversion matrix. Do not
repeat those implementations or restart the approved design. Nothing was pushed.

Final Linux evidence: **656 tests / 408 subtests passed** with actual Pandoc
3.12.1 and LibreOffice. Source and separately installed Python-wheel Quick smoke
each passed **32 checks / 26 real conversion pairs**, including wheel/pill renders.
Changed Python files pass Ruff; repository-wide Ruff retains 25 findings in
unchanged files. Compilation, spec syntax, wheel resources and diff checks pass.
This does not establish native Windows or frozen-EXE success.

## Single next job

On Windows 11, quit the old tray owner, rebuild and run the new onedir through
the acceptance procedures in [PACKAGING.md](PACKAGING.md),
[UI_LIFECYCLE_POLISH.md](UI_LIFECYCLE_POLISH.md), [PROGRESS_UX.md](PROGRESS_UX.md)
and [PANDOC.md](PANDOC.md). No additional user approval gate blocks this testing.

1. Verify repeated conversions in one tray session: collapse → expand → collapse,
   completion/cancel during morph, failure details, success expiry, same-file
   retry, repeated Send to and tray Quit while busy. The eight baseline progress
   checks already passed per user report; the original intermittent missing
   transition has no reliable reproduction and is **not declared resolved**.
2. Check selection entrance 140 ms / leave exit 110 ms, leave tolerance r118 with
   100 ms debounce while actual sector hits stay r110, short PDF JPG/PNG labels,
   reduced/low effects and mixed-DPI/negative-coordinate placement.
3. Exercise new To MD inputs TXT/CSV/JSON/XML/HTM/EPUB/text-only ZIP, and From MD
   DOCX/HTML/TXT/RTF/ODT/EPUB/PPTX with actual Pandoc. PDF additionally requires
   LibreOffice. Verify useful content, Unicode paths, collisions, cancellation,
   source hashes and no intermediate/staging leaks. XLS/MSG/OCR/audio/general
   recursive ZIP remain unimplemented; do not enable them from upstream claims.
4. Test optional complete Pandoc/LibreOffice bundles, missing tools, moved onedir
   outside checkout/venv, and packaged source/output separation checks. Confirm
   `pandoc_source: bundled` when intended. Run Quick self-test and inspect its
   JSON rather than assuming launch implies successful conversion.
5. Recheck physical Mouse3, opted-in touchpad confirmation, Send to and direct
   invocation through the shared host. Preserve all provenance/validation rules.

Record actual Windows findings in STATUS.md. If the intermittent transition
recurs, capture the exact lifecycle sequence and local error details before
making another targeted fix; do not assume a GPU/worker cause or add telemetry.
Use `--ui-backend widgets` as the existing fallback. Do not push automatically.
