# Conversion matrix — planned, NOT implemented

Capability categories: `editable`, `extracted-content`, `rasterized`, `transcoded`. Every edge needs tests before appearing in the wheel.

| Input | Output | Engine candidates | Capability | Phase |
| --- | --- | --- | --- | --- |
| PDF | DOCX | Installed Word COM; pdf2docx | editable best effort; scanned PDFs need OCR | Early document |
| DOCX | PDF | LibreOffice headless or installed Word | rendered layout | Early document |
| DOCX | MD | MarkItDown Python API | extracted-content | Early document |
| PDF | MD | MarkItDown Python API | extracted-content; scanned limitations | Early document |
| PPTX | MD | MarkItDown Python API | extracted-content | Early document |
| XLSX | MD | MarkItDown Python API | extracted-content | Early document |
| HTML | MD | MarkItDown Python API | extracted-content | Early document |
| JPG/PNG/WebP/HEIC | JPG/PNG/WebP etc. | Pillow + pillow-heif | transcoded, possible quality loss | Images |
| Images | PDF | Pillow | rasterized | Images |
| PDF | JPG/PNG | PyMuPDF | rasterized | Images |
| MD | DOCX | Pandoc | formatted best effort | Follow-up |
| MD | PDF | Pandoc + PDF backend | rendered layout | Follow-up |
| PPTX/XLSX | PDF | Office/LibreOffice | rendered layout | Follow-up |
| CSV | XLSX | openpyxl/csv | structured data | Follow-up |
| audio/video | common formats | FFmpeg | transcoded | Optional |

Rules: No extension renaming as conversion; file extension is only a hint, verify input file type when feasible. Local/offline only. Do not expose unsupported targets or pretend extraction is visually lossless. Licensing is not a primary architecture driver for private use.
