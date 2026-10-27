# Actual local conversion matrix

Implemented means real engines and Linux output-content/structure fixtures, not
Windows certification. Options are generated only from available codecs/tools.
The [captured Linux registry](conversion-capabilities-linux.json) contains 42
pairs in the full tested environment; another installation may expose fewer.

| Input | Outputs | Engine | Availability / limitations |
|---|---|---|---|
| PNG, JPG/JPEG, WebP | Other PNG/JPEG/WebP formats, PDF | Pillow | Codec-gated; single image/frame; transparency flattened for JPEG |
| HEIC/HEIF | JPEG, PNG, WebP, PDF | Pillow + pillow-heif | Optional working HEIF codec; single frame |
| PDF | DOCX | pdf2docx | Editable text/layout best effort; scanned PDFs require OCR |
| PDF | JPG, PNG | PyMuPDF | Every page exported separately; short labels, all-pages tooltips |
| DOCX | PDF | LibreOffice | Optional installed or complete portable engine; fonts/layout vary |
| DOCX, PDF, PPTX, XLSX, HTML, HTM | MD | MarkItDown 0.1.9 Python API | Local content extraction, lossy layout; no plugins/cloud/OCR |
| TXT | MD | structured-markdown | Fenced text; UTF-8 or BOM UTF-16 |
| CSV | MD | structured-markdown | Escaped table, bounded consistent rows/columns |
| JSON | MD | structured-markdown | Parsed readable JSON fence; ambiguous/nonfinite/deep input rejected |
| XML | MD | structured-markdown + defusedxml | Hierarchical text/attributes; DTD/entities rejected |
| EPUB | MD | MarkItDown Python API | Bounded archive, validated package/spine and staged snapshot |
| ZIP (text-only subset) | MD | archive-markdown | TXT/CSV/JSON/XML/MD/HTML/HTM only; no nesting, binaries or extraction |
| MD | DOCX, HTML, TXT, RTF, ODT, EPUB, PPTX | Pandoc executable | Optional actual sandboxed writer probes; HTML is standalone; slides are heading-based |
| MD | PDF | Pandoc + LibreOffice | One staged DOCX→PDF transaction; no intermediate publication |

Semantic categories retain image transcoding, document rendering and extracted
content. Navigation groups actual .md destinations under **To MD** (direct when
sole output); MD input uses **From MD** then an available target format.

These are **not implemented/exposed**: legacy XLS→MD, Outlook MSG→MD, general
recursive/binary ZIP conversion, image OCR/vision, audio transcription, cloud
APIs/Azure/YouTube, new audio/video transcoders, PPTX/XLSX→PDF and CSV→XLSX.
Upstream library support alone is not an installed Filewheel capability.

All source files remain unchanged, outputs use collision-safe names and manager
publication validates real outputs. Quotas and fidelity limits: CONVERTERS.md and
PANDOC.md. Python runtime remains 3.14; optional tools do not require another
Python environment. Windows baseline progress checks passed per user; new F
polish, Markdown families and frozen optional-tool operation require acceptance.
