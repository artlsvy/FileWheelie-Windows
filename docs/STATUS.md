# Current status

Filewheel targets Windows 11 x64. Release v0.2 is built with an
offline installer, optional start on login and a three-entry tray menu.

Outdated documentation and old captures are removed without rereading them.
Only the installer remains in releases; the portable EXE is removed from main.
Current task state: plans/release-v0.2.md. Installer details: INSTALLER.md.
App/setup metadata:0.2.0. Static checks:75 Python files, ten packaged sources,
17753 installer payload entries. SHA256:
0d04e761c680ad0a8addc54924841a82282df39520ac42a637f1e77425f0ba31.
Build details and checksum are in releases. Push/release publication is next.

No tests, installer execution, conversion probes or desktop automation are run
in this pass. Earlier user acceptance of progress/cancellation remains valid for
the tested version; clean-machine install/login/upgrade/uninstall checks remain
pending. Keep provenance/path checks and injected-input confirmation unchanged.
