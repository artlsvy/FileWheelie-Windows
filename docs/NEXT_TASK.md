# Overnight continuation — G6-A, then G6-B/C, G7 and G8

G5 core and background UI are implemented and Linux-tested. Current bounded work:
finish/register/review LibreOffice DOCX→PDF (office.py/test_office.py); actual local
smoke conversion passed outside desktop sandbox. G6-A/B are complete/Linux-tested.
Continue immediately to
DOCX→PDF, image/PDF expansion and240px UI polish. Do not stop between milestones.

Working base: clean HEAD1a4a525 at overnight start. Preserve commits and Mouse3.
G4 basic Windows launch/render user-verified; all new conversions and detailed
DPI/focus remain WINDOWS_VALIDATION_REQUIRED. No wait for live Windows host.
MarkItDown0.1.9 excludesPython3.15; keep that runtime's capabilities hidden and
provide compatible3.14 instructions rather than forcing unsupported dependencies.
