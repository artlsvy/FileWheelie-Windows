# Next: prove stock Dolphin's built-in second-application route

User now reports the packaged private Dolphin works; demo source hashes unchanged.
See linux-evidence/package-acceptance.json. Keep extended native acceptance scoped:
Quit, first-run GUI install, mixed DPI and other desktops are not inferred.

An overlooked existing stock-Dolphin feature should be tried FIRST. Installed
Dolphin25.12.3's slotfileMiddleClickActivated obtains the actual clicked KFileItem
and launches the second application returned by KApplicationTrader for that MIME,
passing item.targetUrl(). Shift+middle uses the third. Verified in the actual
Ubuntu source inside filewheel-dolphin-probe:25.12.3 and KDE's25.12.3 tag.
No generic external hook or selected-file guessing is needed for this route.
The previous claim that a private build was required for all routes was too broad.

Bounded next test: use the existing installed Filewheel desktop launcher and
configure it SECOND for image/png, preserving the first/default viewer. Back up
and restore only exact owned/user-approved MIME changes. keditfiletype is installed.
Test a real middle-click of an unselected PNG in ordinary /usr/bin/dolphin, with
other files selected and duplicate names in different tabs; verify path, near-cursor
KWin placement, conversion/source integrity and unchanged normal-open behavior.
Archives/directories and file-tab mode may take other branches; do not promise
those automatically. Do not replace Dolphin, rewrite converters or add global hooks.
User has asked how to achieve broader integration; no MIME preferences changed yet.

If this works, implement opt-in per-MIME second-app setup/restore in the installer,
derived from working registry capabilities. Then investigate file-manager adapters
for GNOME/Nautilus, Thunar/Nemo plus compositor placement separately. GNOME menu
extensions alone do not expose an exact hovered-file Mouse3 callback. A compositor
button signal alone is insufficient identity. No universal Wayland Mouse3 claim.

Existing final artifacts: build/linux-delivery and build/linux-kubuntu-delivery.
97 tests/4 intentional skips; shipped-media59/4; frozen40 checks/32 actual pairs;
FUSE/extract-and-run, real user install and offline Debian12 DEB checks passed.
Other packaging directories are SUPERSEDED. Branch feat/linux-port; no push.
