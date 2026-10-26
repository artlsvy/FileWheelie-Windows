# Conversion matrix — implemented local pairs and future work

Capability categories: `editable`, `extracted-content`, `rasterized`, `transcoded`. Every edge needs tests before appearing in the wheel. Live capabilities are engine/codec-gated; see CONVERTERS.md. MarkItDown is unavailable on Python3.15.

| Input | Output | Engine candidates | Capability | Phase |
| --- | --- | --- | --- | --- |
| PDF | DOCX | pdf2docx (Word COM deferred) | editable best effort; scanned PDFs need OCR | Implemented; optional local dependencies |
| DOCX | PDF | LibreOffice headless (Word COM deferred) | rendered layout | Implemented; optional local dependencies |
| DOCX | MD | MarkItDown Python API | extracted-content | Implemented; optional local dependencies |
| PDF | MD | MarkItDown Python API | extracted-content; scanned limitations | Implemented; optional local dependencies |
| PPTX | MD | MarkItDown Python API | extracted-content | Implemented; optional local dependencies |
| XLSX | MD | MarkItDown Python API | extracted-content | Implemented; optional local dependencies |
| HTML | MD | MarkItDown Python API | extracted-content | Implemented; optional local dependencies |
| JPG/PNG/WebP/HEIC | JPG/PNG/WebP etc. | Pillow + pillow-heif | transcoded, possible quality loss | Implemented (single-frame) |
| Implemented (single-frame) | PDF | Pillow | rasterized | Implemented (single-frame) |
| PDF | JPG/PNG | PyMuPDF | rasterized | Implemented (single-frame) |
| MD | DOCX | Pandoc | formatted best effort | Follow-up |
| MD | PDF | Pandoc + PDF backend | rendered layout | Follow-up |
| PPTX/XLSX | PDF | Office/LibreOffice | rendered layout | Follow-up |
| CSV | XLSX | openpyxl/csv | structured data | Follow-up |
| audio/video | common formats | FFmpeg | transcoded | Optional |

Rules: No extension renaming as conversion; file extension is only a hint, verify input file type when feasible. Local/offline only. Do not expose unsupported targets or pretend extraction is visually lossless. Licensing is not a primary architecture driver for private use.


Phase 2 C additions (implemented/actual Linux fixtures; Windows acceptance pending):

| Input | Output | Engine | Limits/status |
|---|---|---|---|
| TXT, CSV, JSON, XML | MD | structured-markdown | Useful fenced text, escaped tables, structured JSON/XML; bounded, no network |
| HTM, EPUB | MD | MarkItDown 0.1.9 | Actual Python API; EPUB archive/spine preflight and validated snapshot |
| ZIP (textual members only) | MD | archive-markdown | No nesting/binaries/extraction; strict quotas and production pre-publication timeout |
| XLS, MSG | MD | none registered | Optional future work; dependencies/real fixtures not introduced |

See CONVERTERS.md for exact quotas and known lossy behavior. This does not enable
MarkItDown image OCR, audio transcription, Azure, YouTube or third-party plugins.
