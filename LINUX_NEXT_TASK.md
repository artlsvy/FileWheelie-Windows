# Current task: finish hosted v0.3.1 release retry

Branch feat/linux-port; original v0.3.1 source tag remains416dac5 (immutable).
First Actions run41117762409: Windows build/frozen smoke/attestation/upload passed;
Linux container checks passed but extracted AppImage smoke on host exited1, with
logs not printed/uploaded by that workflow. Release publication correctly skipped.

Retry orchestration commit1ac7259 / tagbuild-v0.3.1-1 explicitly checks out
v0.3.1 application source in BOTH jobs. It provisions documented desktop libs on
the Ubuntu host, prints smoke logs/reports on failure, and uploads diagnostics.
Current retry: https://github.com/artlsvy/FileWheelie-Windows/actions/runs/41131902385
Monitor jobs via GitHub connector; on failure fetch logs and PRINT ONLY RELEVANT
TAIL/ERRORS (full logs exceed300k tokens). Diagnose before changing application
code. Build tags build-v0.3.1-* allow CI-only retries without rewriting v0.3.1;
publish targets that original tag and requires both jobs to pass.

User authorized push AND publication. Do not upload workstation installers or
claim release exists until GitHub confirms published assets. README/release docs
updated; version metadata0.3.1. Repo was renamed; canonical repository is
artlsvy/FileWheelie-Windows (old origin redirects). Preserve unrelated untracked
assets/ui/wheel.jpg and wheel (2).pdf/.png. No forced tray quit. After success,
record actual asset hashes/run and push docs checkpoint; provide release link.

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
