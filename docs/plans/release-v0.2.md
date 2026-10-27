# Release v0.2 ? complete

Goal: clean main, a readable README and an installer-only GitHub release.

1. Complete: removed35 obsolete docs/captures without rereading them; removed the
   portable EXE/build record from main. Kept current installer/status/task docs.
2. Complete: rebuilt app/setup0.2.0; compiler/static checks passed. No tests,
   installer execution, login changes, conversion probes or desktop automation.
3. Complete: main pushed and releasev0.2 published with two short installer/login
   notes and one attached installer. GitHub asset size and SHA256 verified.

Release: https://github.com/artlsvy/fileconverter/releases/tag/v0.2
Release target:c745f8806433a3647988791da99d5bf4a763a961.
Installer:415407573 bytes; SHA256
0d04e761c680ad0a8addc54924841a82282df39520ac42a637f1e77425f0ba31.
Static evidence:75 Python files compile, ten packaged sources match, all17753
payload files included once. Runtime acceptance remains deferred by the user.
Old files remain recoverable through Git history; no history purge performed.
Next: stop. No other feature development authorized by this release request.
