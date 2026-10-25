# Overnight continuation — G6-A, then G6-B/C, G7 and G8

G5 core and background UI are implemented and Linux-tested. Current bounded work:
register/review G7 expanded PillowEngine and PdfImagesEngine with real fixtures.
G6-A/B/C are implemented/Linux-tested and separately committed. Then continue
immediately to G8 240px sizing/transparency/readability and real result feedback.
Do not stop after G7.

Working base: clean HEAD1a4a525 at overnight start. Preserve commits and Mouse3.
G4 basic Windows launch/render user-verified; all new conversions and detailed
DPI/focus remain WINDOWS_VALIDATION_REQUIRED. No wait for live Windows host.
MarkItDown0.1.9 excludesPython3.15; keep that runtime's capabilities hidden and
provide compatible3.14 instructions rather than forcing unsupported dependencies.
