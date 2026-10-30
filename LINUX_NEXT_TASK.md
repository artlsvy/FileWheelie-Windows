# Next: complete and validate baseline Linux packaging

Native private-Dolphin exact clicks and PNG→JPEG/TXT→MD/progress/Quit are accepted.
Shared Linux desktop integration and owned per-user installer are implemented;
33 Linux tests include the real GIO desktop argv parser. Do not repeat accepted
source tests. No Windows behavior or installed system Dolphin is replaced.

Finish the in-progress Ubuntu22.04/CPython3.14.10 frozen bundle, AppImage installer
and optional DEB. Packaging code, lock, driver and CI are in the working tree.
Frozen PNG/PDF/Markdown/Pandoc tests passed until bundled LibreOffice failed during
MD→PDF; investigate native library/bootstrap lookup (wrappers must put the office
program directory before common native libraries). Do not ship a broken engine
or claim a successful frozen smoke. Current logs: /tmp/fw-linux-debug-build.log,
/tmp/fw-linux-frozen-build.log. Current debug Docker build targets freeze.

Keep core GLIBC2.35 goal separate from optional exact-version private Dolphin
(Ubuntu26.04/KF6 stack). Audit every shipped ELF, preserve notices/source snapshot,
test real AppImage install/remove in isolated XDG, then request packaged native
acceptance only when ready. No push without instruction.
