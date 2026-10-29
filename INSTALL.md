# Filewheel installer

The current source build is **FilewheelSetup.exe**, version 0.2.7. Share this installer
alone. The older portable Filewheel.exe is no longer included in the repository.
The GitHub v0.3 release includes this installer and its SHA-256 checksum.

## What setup does

- Installs for the current user, normally in `%LOCALAPPDATA%\Programs\Filewheel`.
- Shows Next, Cancel, included components and installation progress.
- Adds a Start Menu shortcut and a Windows uninstall entry.
- Offers a desktop shortcut, Explorer Send to and start on login.
- Includes the conversion tools; local OCR uses the recipient's Windows OCR languages.

Compatible installed **LibreOffice 7.6+**, **Pandoc 3.1+**, and FFmpeg 9+
with H.264/AAC encoders are reused by default
when found in normal locations, the LibreOffice registry entry or local PATH.
Their private copies are then skipped. Uncheck the reuse option to install the
bundled copies instead. Custom locations that are not found use private copies.

Python 3.14, Qt/PySide6 and conversion libraries stay private to Filewheel. Setup
leaves globally installed Python, Qt and other tools alone. Reused tool paths are
saved in `installation.ini`. If a reused tool is later removed, rerun Setup and
choose the bundled copies. `DEPENDENCIES.txt` lists the pinned build environment.

Quit an older Filewheel before setup. New builds prevent setup/uninstall while
the app is running. The installer and tray share an owned current-user login
entry; entries pointing elsewhere are preserved. Uninstall removes private app
files, not reused system tools, original documents or conversion results. Local
preferences/logs remain in `%LOCALAPPDATA%\Filewheel`.

Image-only PDF to DOCX and Markdown use built-in Windows OCR through a packaged local helper.
At least one Windows OCR recognition language must already be installed; setup
does not install language packs or change Windows policy settings. Normal
text-layer PDF conversion does not need OCR. OCR runs in a bounded background
process, supports cancellation, and keeps page images in the output for reference.

## Build from source

Use Windows 11 x64, Python 3.14 and the pinned build environment prepared by
`scripts/build-windows.ps1`. Full local LibreOffice/Pandoc folders are build inputs.

```powershell
.\.venv-build314\Scripts\python.exe packaging/build_installer.py `
  --libreoffice 'C:\Program Files\LibreOffice' `
  --pandoc "$env:LOCALAPPDATA\Pandoc" `
  --ffmpeg 'C:\tools\ffmpeg\bin\ffmpeg.exe'
```

The FFmpeg package must contain `ffmpeg.exe` and its `LICENSE` or `COPYING.GPLv3`
file; the build records its version and GPLv3 configuration. The installer includes the GPLv3
license with the FFmpeg executable. FFmpeg's corresponding source and build
configuration are identified in `tools/ffmpeg/BUILD-INFO.txt`.

Filewheel's own code is [AGPL-3.0-or-later](LICENSE). The installed application
includes that license. Bundled LibreOffice (MPL-2.0), Pandoc (GPL-2.0-or-later),
and FFmpeg (the selected GPLv3 build) keep their upstream license and notice
files. Python package versions are pinned in `packaging/windows-py314.lock`;
their upstream license metadata is included in the frozen runtime.

The builder uses a checksum-pinned private Inno Setup 6.7.3 compiler in ignored
`build-tools`. Only the build machine may need to download that compiler.
Output is `releases/FilewheelSetup.exe`; checksums and build details are beside it.
For a public release candidate, `.github/workflows/release-build.yml` downloads
the native inputs listed in `packaging/native-artifacts.json`, verifies their
SHA-256 hashes, and builds on a GitHub-hosted Windows runner. That workflow
currently produces an **unsigned** installer for review.
The installed app uses a folder of private files, avoiding temporary unpacking
on every launch. Git stores the installer using Git LFS; download the release
asset directly, or run `git lfs pull` after cloning.

## Verification

The release build record in `releases/INSTALLER-BUILD-INFO.json` lists the checks
that ran. Build and static checks do not prove installation, login or uninstall
behavior on a clean PC. Developer tests and agent settings are kept locally and
are not part of this repository's current tree.

### Windows 11 acceptance for 0.2.7

1. Quit Filewheel from the tray and install the local `releases/FilewheelSetup.exe`.
2. Convert an image-only PDF to DOCX. Open the result: recognized text should be
   editable, original page images should remain in the reference section, and
   the source PDF must remain unchanged. The result details should mention OCR.
   Convert the same PDF to Markdown; check that recognized text appears and
   the linked page PNG is saved beside the Markdown file.
3. Open conversion **Details**, expand **Show Details**, then click **OK**.
   Repeat after a failed conversion and after a second conversion in the same launch.
4. Open **Accent color…**, choose a color and click **Cancel**: the old color stays.
   Repeat with **OK**, reopen, change again, and relaunch: the accepted color persists.
5. Convert `IMG_0585.MOV` to MP4, MKV and WebM. Confirm each video plays with audio;
   MP4/MKV should preserve HEVC/AAC, while WebM should use VP9/Opus. Check details
   for the omitted APAC positional audio and data tracks.
6. Extract MP3, M4A, WAV and FLAC from `IMG_0585.MOV`. Confirm the AAC track is used,
   APAC is reported as omitted, and FLAC explains that it cannot restore source quality.
7. Open the wheel again; test outside-click dismissal, Escape and conversion
   cancellation. Test both mouse and touchpad activation, plus Send to.
8. Check an ordinary text-layer PDF to DOCX still retains its text and basic layout.
9. Convert between MP4, MOV and MKV. Try an AVI, M4V and WebM input to MP4.
   Convert MP4/MOV/MKV to WebM and check playback. Check originals remain unchanged.
10. Convert MP3, M4A, WAV, FLAC, OGG and Opus samples to each advertised audio
   output. Extract MP3, M4A and WAV from a video with multiple audio tracks; verify
   the result details identify re-encoding and any track loss.
