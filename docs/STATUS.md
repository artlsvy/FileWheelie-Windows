# Current status

Filewheel v0.2 (app/setup 0.2.0) is published for Windows 11 x64:
https://github.com/artlsvy/fileconverter/releases/tag/v0.2

Only FilewheelSetup.exe is attached. GitHub's asset checksum matches the local
installer:0d04e761c680ad0a8addc54924841a82282df39520ac42a637f1e77425f0ba31.
The current tree excludes the portable EXE and 35 obsolete docs/captures. README
uses plain installation/use instructions. Main and release publication succeeded.

Build/static checks:75 Python source/build files compiled; ten packaged runtime
sources match; all17753 payload files included. Full record is in releases.
No tests, installer execution, login changes, conversion probes or desktop
automation ran. Clean-machine install/login/upgrade/uninstall checks remain
pending. Preserve input/path safeguards and injected-input confirmation.
