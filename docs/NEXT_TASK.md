# Overnight continuation — finish G8 UI refinement and final integration

G5/G6-A/B/C/G7 engines are implemented and Linux-tested. G8 popup.py changes are
owned by implementer conversion_core: default240px configurable sizing, transparent
paint/OSshadow fix, readable labels, coherent scaledhitregions, resultactions and
cancellation feedback. Do not overwrite its ongoing edits. Review and test it,
update runtime/docs/Windows commands and commit G8 separately, then final audit.

Full suite last229pass; codec regression now27 focused tests pass. RealLibreOffice
fixtures need `env PYTHONPATH=src .venv-ui/bin/python -m pytest` outside desktop
sandbox (approvedprefix); restricted runtime dconf writes fail inside. No Windows
conversion/DPI claim. G4 basic launch/render is user-verified. Preserve Mouse3.
MarkItDown0.1.9 excludesPython3.15: extra marker skips it; Python3.14 for all MDpairs.
Continue until G8 and consolidated test/docs audit finished, no approval between
milestones and no waiting for liveWindows. No pushes authorized.
