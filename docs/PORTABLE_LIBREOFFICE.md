# Portable LibreOffice backend

Filewheel prefers a complete LibreOffice tree at `tools/libreoffice` beside the
frozen EXE (or in the source checkout). It falls back to an independent system
installation when the bundle is absent or structurally incomplete. PDF → DOCX
uses pdf2docx and does not depend on LibreOffice; DOCX → PDF does.

Supported tree layouts are a normal installation's `program` and `share` folders,
or a PortableApps tree containing `App/libreoffice/program` and `share`. Keep the
entire vendor tree, including DLLs, registry/configuration data, resources and
license notices. Copying `soffice.exe` alone is rejected. Structural validation
cannot establish that every native DLL or runtime dependency is present.

Obtain a Windows build from [The Document Foundation's download options](https://www.libreoffice.org/download-other/)
or its linked portable provider. Extract/install into a dedicated staging folder;
Filewheel does not download, run an installer or modify a system installation.
A portable package may still depend on Windows runtime components. Keep those
requirements from the vendor alongside the build instructions.

From a Python 3.14 development checkout on Windows:

```powershell
.\.venv-filewheel\Scripts\python.exe -m filewheel.libreoffice_bundle --validate "D:\Tools\LibreOfficePortable"
powershell.exe -NoProfile -ExecutionPolicy Bypass -File .\scripts\build-windows.ps1 -LibreOfficeDirectory "D:\Tools\LibreOfficePortable"
& .\dist\Filewheel\Filewheel.exe --self-test
Get-Content "$env:LOCALAPPDATA\Filewheel\logs\self-test.json"
```

The build validates before copying and at the destination. Source and output
must not contain one another. Inspect the self-test report's LibreOffice source:
`bundled` establishes which route was selected; `system` does not validate a
portable bundle. Test the entire output folder on Windows without a system
LibreOffice installation, including a DOCX with text, tables and Unicode paths.

Each conversion uses a private temporary input/output directory and fresh
`UserInstallation` profile, a bounded subprocess lifetime, PDF validation and the
shared collision-safe publisher. Frozen execution restores the external child's
library environment rather than exposing PyInstaller's native libraries. Failed
LibreOffice output includes bounded stdout/stderr in the private debug log.

A fresh profile and new office process add startup cost on each conversion. No
resident office service is introduced. Package size varies greatly by languages
and vendor layout: budget hundreds of megabytes, potentially over 1 GB for a full
multilingual tree. These are planning estimates, not measurements of a Filewheel
Windows bundle. Measure the actual staged tree and cold/warm conversion latency
on the target machine before choosing which languages/resources to retain.

Preserve LibreOffice's license notices and third-party notices. Consult
[LibreOffice licensing](https://www.libreoffice.org/licenses/) and the portable
provider's additional terms; retain applicable source/license offers if sharing
the bundle. The app's build script does not strip these files.

Validated here: structure/discovery/environment/cleanup tests and an actual Linux
DOCX → PDF conversion through a bundle-shaped wrapper around installed
LibreOffice. That wrapper is **not** a self-contained portable distribution.
Acquiring, building and testing a complete Windows portable tree remains
`WINDOWS_VALIDATION_REQUIRED`.
