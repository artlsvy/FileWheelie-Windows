# Offline converter review (2026-10-27)

Source/documentation review only. No tests, benchmarks or desktop automation were
run in this pass. Cleanup/main integration was completed first (b9b77a3), including
the previous standalone EXE through Git LFS. New converter changes below have
not received native runtime acceptance in this pass.

## Demand signals, not a global ranking

There is no independently audited worldwide conversion-frequency dataset here.
Operator "popular/common" lists are a useful but biased practical signal:
[Zamzar](https://www.zamzar.com/?gad=1) highlights PDF/Word, image/PDF and media
pairs; [CloudConvert](https://cloudconvert.com/) highlights PDF/DOCX, DOCX/PDF
and HTML/text. These are operator selections, not measured market-share claims.

| Family | Current decision |
|---|---|
| PDF/Word, PDF/JPG/PNG, JPG/PNG/PDF, HEIC/JPG, WebP/PNG | Already implemented; keep existing routes |
| PowerPoint/PDF and Excel/PDF | Add PPTX/XLSX-to-PDF through already-bundled LibreOffice |
| Excel/CSV and CSV/Excel | Feasible, but sheet selection/formula/cache semantics need a separate bounded design |
| MP4/MP3, MOV/MP4, WAV/MP3 | Feasible with a separately bundled media transcoder and validation; not added to this cleanup task |
| Scanned PDF/image OCR | Requires an OCR engine/models and content checks; not invented as MarkItDown support |

## Added routes

PPTX uses `impress_pdf_Export`; XLSX uses `calc_pdf_Export`. The existing DOCX
route retains `writer_pdf_Export`. These are official
[LibreOffice conversion filters](https://help.libreoffice.org/latest/en-US/text/shared/guide/convertfilters.html).
All routes reuse private fixed-name input, isolated LO profile, size/ZIP/content
checks, external-resource/macro rejection, output validation and no-overwrite
manager publication. XLSX also rejects connections/query tables/external links,
macro sheets and network/active formulas. This is conservative; formulas such as
HYPERLINK may be rejected even if a particular workbook could render safely.
Layout/print-area/font fidelity remains LibreOffice-dependent. No new dependency.

## MarkItDown audio/video

The installed MarkItDown0.1.9 code and Microsoft's
[speech helper](https://github.com/microsoft/markitdown/blob/main/packages/markitdown/src/markitdown/converters/_transcribe_audio.py)
call SpeechRecognition's `recognize_google`. That sends audio to online speech
recognition. Its MP3/MP4 path first uses pydub to decode audio; that does not make
the transcription local. Media metadata is not a spoken-word transcript.
Do not enable this route. Azure/YouTube paths likewise fail the offline requirement.

An independent local model (for example whisper.cpp) can provide offline speech
recognition once weights are present, but would be a different engine, model
bundle and acceptance task. It is not silently included in this release.

## C assessment

No C rewrite is needed based on current source and accepted behavior. Python
coordinates work already done by compiled libraries and native subprocesses;
moving that coordination does not remove the large conversion dependencies.
Retaining Qt Quick/QML would require a Qt C++ layer/bridge, and preserving
MarkItDown/pdf2docx keeps Python or requires replacements. The observed UI issue
was mitigated by backend choice, not a demonstrated host-language bottleneck.
See PERFORMANCE_ARCHITECTURE.md. No C implementation or new performance tests.
