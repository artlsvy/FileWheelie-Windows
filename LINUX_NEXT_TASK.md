# Next: final packaged native acceptance and compatibility hardening

The accepted native source route is complete. Final core AppImage, optional DEB
and matched private-Dolphin AppImage exist; see LINUX_STATUS.md / LINUX_PACKAGING.md.
97 portable tests pass (4 intentional skips), shipped-media suite59/4, frozen40
checks/32 actual pairs. Normal FUSE, extract-and-run, real AppImage installation/
upgrade/removal/startup ownership, and offline minimal Debian12 DEB install/smoke/
remove pass. Do not rebuild/retest these unchanged checks unnecessarily.

A **packaged** matched-Kubuntu AppImage was launched on the native Wayland session
with private Dolphin at build/linux-demo. An async question asks the user to check
PNG→JPEG, TXT→MD, near-cursor wheel, progress persistence and tray Quit. Source
acceptance already passed; do not confuse that earlier answer with this new test.
Read any new user reply and /tmp/fw-packaged-native.log; verify output/source hashes
and clean exit, then update linux-evidence/package-acceptance.json. If no reply,
keep frozen native acceptance pending and provide the exact runnable artifact.

Then test first-run GUI installation, tray browser action, cancel/retry, repeated
invocations, tabs/grouped/large folders, touchpad, fractional/mixed DPI and resume.
Do not infer those from container or basic source tests. Stock Dolphin still has
no supported exact-file external Mouse3 API; the private prefix is version-specific
and does not bundle system Qt/KF6. Other desktops currently use explicit file
invocation. Do not advertise universal Wayland parity or replace system Dolphin.

The delivered files are under build/linux-delivery and build/linux-kubuntu-delivery;
other earlier packaging directories are SUPERSEDED. No Python/pip is needed on
end-user systems. No public distribution until license/source audit; no push or
Windows release changes without authorization. The existing Windows source,
converters and diagnostics must remain intact. Branch: feat/linux-port.
