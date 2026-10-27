# Cleanup/main integration in progress

Priority1 is the clean commit/main integration. The stable Windows onefile is
now tracked through Git LFS at releases/Filewheel.exe with a SHA256 sidecar.
Historical verification belongs to standalone/verification.json; no tests or
interactive automation are being run in the current review pass.

After this cleanup checkpoint, add only bounded PPTX/XLSX-to-PDF routes through
already-bundled LibreOffice, rebuild the EXE without running validation probes,
and document that those additions have not been runtime-tested in this pass.
MarkItDown speech transcription calls online Google recognition and remains off.
C source/context review says no rewrite is currently justified.

Current state: plans/cleanup-main.md. Do not restart the interrupted desktop test.
