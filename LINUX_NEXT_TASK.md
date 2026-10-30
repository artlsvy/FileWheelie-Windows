# Current task: rebuild after image-only PDF OCR repair

User accepted progress placement, then reported PDF→MD invoking Windows OCR on
Linux. Source repair adds offline Tesseract dispatch for PDF→MD/DOCX. The baseline
AppImage must bundle Tesseract, English/orientation models and native libraries;
new strict frozen checks must prove recognition and original-page linkage.
Picture-only Markdown retains original page images instead of failing on no text.
Windows OCR helper remains in use on Windows; no changes to Mouse3/trust/UI.

Finish tests/Ruff/compile, commit the focused source repair, rebuild to a fresh
build/linux-ocr-installer directory using workspace TMPDIR (the /tmp RAM disk is
nearly full), and run actual AppImage plus offline Debian12 OCR/content smoke.
Replace dist/Filewheel-Linux-x86_64.AppImage only after checks pass; record new
SHA/size/commit and update LINUX_USE/PACKAGING/STATUS/NEXT_TASK. Preserve user
assets/ui/wheel.jpg and wheel (2).pdf/.png; do not push or force-kill the old tray.
Final instruction: finish jobs, Quit old Filewheel, install/update the new single
AppImage and reopen before testing PDF→To MD. GNOME remains deferred.
