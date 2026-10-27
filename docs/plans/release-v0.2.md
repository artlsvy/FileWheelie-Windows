# Release v0.2

Goal: clean main and a simple public-facing README; publish only the installer.
Acceptance: outdated docs removed without rereading, no portable EXE on main,
version0.2.0 in app/setup, installer checksum matches release asset, main pushed,
GitHub releasev0.2 published with short installer/login notes.

Constraints: no tests or desktop automation, no feature work/history rewrite,
keep source/tests/build recipes and input/conversion safeguards. Old docs and
portable binaries remain recoverable from Git history; no history purge requested.

1. Complete: removed35 obsolete docs/captures by path and the portable EXE/build
   record. Rewrote README/current guides; no obsolete document contents read.
2. Complete: app/setup0.2.0, installer compilation and static artifact checks.
3. Active: commit/push main, publish and verify release asset, stop.

Decision: retain INSTALLER, STATUS, NEXT_TASK and this plan as current docs.
The release asset is the real EXE; repository copy uses Git LFS. Release notes:
"Added a Windows installer and optional start on login."

Preflight: origin fetched; main has the unpushed installer commit only. GitHub
authentication has push access; v0.2 does not exist. Release upload API is used
because the connector has no release-upload endpoint. No tests/UI automation.

Build evidence:75 Python source/build files compile; ten packaged runtime sources
match. All17753 payload files included exactly once. Setup compilation234.922s.
Installer SHA256:
0d04e761c680ad0a8addc54924841a82282df39520ac42a637f1e77425f0ba31.
No installer execution, login changes, conversions or desktop tests ran.
