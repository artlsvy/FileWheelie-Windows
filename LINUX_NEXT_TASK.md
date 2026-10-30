# Current task: GitHub Actions cross-platform v0.3.1 release

The user has accepted Linux OCR and authorized push/release. Commit/push
feat/linux-port and tag v0.3.1 after local checks. Monitor publish-release.yml;
both independent hosted Windows and Linux builds/checks/attestations must pass
before release assets publish. Do not upload the workstation AppImage in place
of CI output. Report precise hosted failures if any; do not claim publication
before the release exists. See RELEASING.md and RELEASE_NOTES_0.3.1.md.
Previous local implementation evidence follows.

# Current checkpoint: Linux PDF OCR fixed and AppImage rebuilt

User accepted the progress-position fix. Subsequent image-only PDF→MD failure
was caused by calling Windows native OCR on Linux. Shared PDF assembly now
selects local Tesseract on Linux while retaining Windows recognition. The AppImage
includes Tesseract, English/orientation models and native libraries/notices.
Markdown preserves original page images even when OCR recognizes no text;
scanned DOCX includes editable text and original-page references. Existing text
PDFs, conversion safety, cancellation, UI, Dolphin/tray behavior stay in place.

Deliverable: dist/Filewheel-Linux-x86_64.AppImage (454 MiB).
SHA-256: 56656b2dba024e4999bd9ce0b7c03002345bf6e19ecca14d6f66dd7f6d3109a1
Source repair: 7b1cafc. Current source suite: 140 passed /4 intentional skips.
Ruff/compilation pass. Frozen onedir, extracted AppImage, FUSE AppImage and
network-disabled Debian12 each pass 44 checks, including real OCR content/link
checks. Actual final install/upgrade/remove passes in isolated XDG directories;
26 Dolphin MIME registrations and document preservation verified. See
linux-evidence/final-installer.json and LINUX_PACKAGING.md.

User next action: finish any jobs, Quit the OLD tray, install the updated dist/
AppImage with --install-user, then start the installed --tray --ui-backend quick.
Retest the previously failing PDF→To MD and keep its generated linked PNG page
images beside the Markdown file. English OCR models are included; other languages
and mixed text/scanned-page extraction are not newly claimed complete.

Task complete as far as automated checks permit. GNOME remains deferred. Preserve
all existing Windows/private-Dolphin/converter code and unrelated assets/ui/
wheel.jpg and wheel (2).pdf/.png. No automatic push or forced tray shutdown.
