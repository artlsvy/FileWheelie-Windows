Filewheel 0.3.1 adds an installable Linux build alongside the Windows installer.

- Linux: ordinary Dolphin second-application middle-click integration on Plasma Wayland; existing default handlers are preserved and changes are reversible.
- Corrected progress/details placement above the taskbar, including expansion/reuse.
- Offline Linux OCR for image-only PDF→Markdown/DOCX; English recognition data bundled. Picture-only Markdown preserves page images.
- Existing local image, document, Markdown, audio and video engines retained.

Download `FilewheelSetup.exe` for Windows11 x64 or `Filewheel-Linux-x86_64.AppImage` for x86_64 Linux (glibc2.35+). Quit older tray instances before installing. Run the AppImage and choose Install for this user; no Python/pip setup required. FUSE/normal desktop libraries are required for ordinary AppImage launching.

Both binaries are built from this tag by GitHub Actions, with frozen conversion checks, SHA-256 sums and signed build provenance. Verify with `gh attestation verify <downloaded-file> --repo artlsvy/FileWheelie-Windows`. This is provenance, not antivirus certification or Windows Authenticode signing.

Linux interaction was accepted on Plasma Wayland; GNOME Mouse3 and universal distro compatibility are not claimed. OCR may need correction and English data is included. The Windows installer remains unsigned. This release's hosted checks do not replace interactive testing on every desktop.
