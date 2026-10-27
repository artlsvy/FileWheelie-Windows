# Optional local Markdown publishing

Filewheel uses a real **Pandoc 3.1+ executable**, not a Python wrapper or remote
service. Tested here: official Pandoc **3.12.1**, Linux amd64. Native Windows
execution remains pending. Startup discovery checks actual readers/writers and
runs small sandboxed output/content probes; missing reference templates hide
that writer rather than advertising a conversion that cannot run. Probes have
an aggregate 8 s budget and are cached by executable identity for the session.
Restart Filewheel after installing/changing tools.

With compatible Pandoc: **MD → DOCX, HTML, TXT, RTF, ODT, EPUB, PPTX**.
HTML is a full standalone document. With local LibreOffice too: **MD → PDF**,
using Pandoc → staged DOCX → LibreOffice PDF as one job. No intermediate files
are published, and the usual no-overwrite/cancellation/cleanup guarantees apply.
No LaTeX install, PDF-engine subprocess, Word automation or cloud service is
needed. Phase progress is shown as indeterminate/stage activity rather than a
fabricated elapsed-work percentage.

Headings, lists, links, tables and supported images have actual content/structure
fixture coverage. Publishing is not exact original layout/font preservation.
PPTX uses heading-based slide splitting; complex layout/notes may be lost. Only
.md input is registered. UTF-8 and BOM-marked UTF-16 text are accepted.

## Discovery and Windows use

Priority: explicit FILEWHEEL_PANDOC absolute path; validated tools/pandoc beside
Filewheel.exe; then system PATH. An invalid explicit override does not silently
select a different binary. No binary is downloaded at conversion time.

Install an external Pandoc using the official installer/portable release, or:

```powershell
winget install --source winget --exact --id JohnMacFarlane.Pandoc
```

Open a fresh terminal after installation, quit the old Filewheel owner, then:

```powershell
pandoc --version
pandoc --list-output-formats
& .\dist\Filewheel\Filewheel.exe --tray --ui-backend quick
```

Or select an existing executable explicitly before launch:

```powershell
$env:FILEWHEEL_PANDOC = 'C:\Tools\pandoc-3.12.1\pandoc.exe'
& .\dist\Filewheel\Filewheel.exe --tray --ui-backend quick
```

For source use the same environment variable with the existing Python 3.14
`.venv-filewheel\Scripts\python.exe -m filewheel --tray --ui-backend quick`.
Markdown input shows From MD only when real capabilities exist. Non-Markdown
inputs show To MD when a registered extraction engine supports them.

Optional complete portable bundling and pinned artifact hashes are documented
in PACKAGING.md; it is intentionally not part of the default payload. The
Windows official ZIP expands to approximately 225 MiB. Retain COPYRIGHT and GPL
COPYING notices with the executable. This project does not build a Windows EXE
or certify it merely from a Linux fixture.

## Resource and subprocess restrictions

The pipeline parses GFM without raw HTML into a Pandoc JSON AST, strips input
metadata/raw nodes and unsafe links, and writes only an explicitly prepared AST.
Only relative local PNG/JPEG/WebP raster images inside the source directory are
accepted; links/reparse points and traversal are rejected. Safe raster bytes
are decoded, re-encoded to PNG and embedded as data URIs. Remote/absolute/unsafe
or unsupported image references are omitted with warnings, never fetched. No
SVG helper, custom filter, user defaults/template or desktop capture is enabled.

Limits: 8 MiB input, 32 MiB AST, 64 MiB output, 32 image references, 8 MiB per
image, 16 million pixels per image, 32 MiB unique image bytes and cumulative
reference/AST budget. Repeated cached references consume the budget too. JSON
serialization is streamed and bounded before a large expansion can allocate an
unbounded string. AST traversal has depth/node limits. Each Pandoc call has a
45 s timeout and 512 MiB Haskell heap limit. Cancellation kills/reaps only the
owned tool tree before publication; diagnostic output is bounded. External
processes use fixed argument lists and frozen-safe DLL/environment handling.

## Verification still required on Windows

Create a Markdown fixture containing Unicode text, headings, bullets, a link,
a table and a relative PNG. Convert to each visible format and inspect actual
content; verify standalone HTML, editable Word content, EPUB reading order and
PPTX slide splitting. With LibreOffice installed/bundled, test PDF and cancel
between/within stages. Confirm source hashes, collisions, no leaked intermediate
DOCX/staging, pill status and same-file retry. Repeat missing Pandoc/LibreOffice,
spaces/Unicode paths, source and moved onedir builds. New output support is
implemented/actual Linux-tested, not Windows-verified yet.

Primary references: [Pandoc manual](https://pandoc.org/MANUAL.html),
[sandbox/security guidance](https://pandoc.org/MANUAL.html#option--sandbox),
[official installation options](https://pandoc.org/installing.html),
[official 3.12.1 release](https://github.com/jgm/pandoc/releases/tag/3.12.1).
