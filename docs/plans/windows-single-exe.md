# Windows-only self-contained EXE

Goal: deliver one Windows 11 amd64 EXE containing Python/Qt/converters, Pandoc
and a complete LibreOffice tree; no separate runtime/tool installation required.

Acceptance: Windows regression suite green; preserve OpenGL glass and cancellation;
onefile builds with bundled tools discovered inside extraction root; real packaged
conversion self-test and >=50 native UI cycles pass without source/PATH tools;
spawn/cancel cleanup works and final artifact/hash/build command documented.

Scope: remove active Unix host/runtime/test support and stale current setup
instructions. Keep ZIP/EPUB POSIX path syntax (archive format, not Unix support),
and historical measurements as historical evidence. Do not alter converters/formats
except a demonstrated bug. Preserve unrelated files and prior acceptance notes.

Milestones:
1. Complete: removed Unix runtime branches/tests and current Unix setup guidance;
   six original failures corrected (Windows paths, test fixture/encoding/monitor).
   Embedded tools use extraction root; stable EXE path retained for integrations.
2. Complete: onefile recipe embeds complete native dependencies and adjacent VC
   DLLs; build succeeded, EXE668358672 bytes, SHA2564a46099d87b9d67f65aefa956801dee0b682cfedff83f64c3d0bdc70b01b131c.
3. Delivered with explicit UI-test limit: relocated EXE passed self-test34/26 pairs
   and three frozen workers including cancel/retry. Native UI completed46 cycles;
   user interrupted to use PC. Do not restart interactive testing without request.

Decisions: executable-relative integration paths remain stable; bundled resources
use PyInstaller extraction root. Keep default Quick/OpenGL for the family artifact
with explicit widgets/graphics overrides preserved. No automatic push.
Evidence: full Windows suite660 tests/407 subtests passed,4 skips, no failures.
Scoped Ruff and whitespace checks pass. Native Windows process-tree timeout and
cancellation tests now run instead of Linux-only/skipped process inspection.
LibreOffice staged with adjacent MSVC DLLs from System32, not JDK/PATH copies.
Packaged self-test now exercises a real frozen child, cancellation and retry.
Native evidence: copied EXE outside checkout with stripped PATH, strict extraction
cleanup, bundled-only real self-test passed34 checks/26 pairs; both tools report
bundled and three real workers converted/cancelled/retried.
Initial verifier incorrectly required an entirely empty TEMP; fixed it to check
the _MEI extraction directory and record auxiliary tool cache entries separately.
The first functional self-test was successful. The subsequent UI run completed46
cycles before the user's interruption; selection exposure failed while the user
needed the PC. Do not count this as a completed100-cycle pass or diagnose an app
regression from that interrupted trial. Evidence: docs/standalone/verification.json.
Next: deliver dist/standalone/Filewheel.exe. Remaining100-cycle UI acceptance is
paused at the user's request; no active interactive test process remains.
