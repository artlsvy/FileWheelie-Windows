# Windows single EXE ready — interactive tests paused

The current Windows-only packaging task produced dist/standalone/Filewheel.exe.
Give recipients that EXE alone. It embeds Python/Qt/conversion engines, complete
Pandoc and LibreOffice, and the native runtime DLLs used by LibreOffice.
The existing diagnostic folder builds were preserved.

Verified: full Windows suite660 tests/407 subtests passed,4 skips; scoped lint and
syntax checks. Copied EXE outside checkout with installed-tool lookup disabled:
34 checks/26 real pairs passed, both native tools bundled, three real frozen
workers converted/cancelled/retried, self-test extraction folder cleaned up.

The user interrupted native UI testing because they need the PC.46 cycles had
completed; the planned100-cycle run is not complete. Do not restart any test that
opens windows, moves the pointer or changes focus without the user's request.
No interactive test process remains. F5 progress and cancellation were previously
user-accepted; keep those historical observations separate from this artifact.

Next only when requested: finish native UI acceptance for this exact EXE while
PC is free, then test on a family Windows11 amd64 computer. A clean second machine
was not available here. No further feature development is authorized by this task.

Build/run details, exact hash and evidence: SINGLE_EXE.md and
standalone/verification.json. No automatic push.
