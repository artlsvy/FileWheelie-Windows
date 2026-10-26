# Phase 1 rendered proof

Actual Qt Quick captures, Python 3.14.4 / Qt 6.12.0, Linux offscreen software
scenegraph. `before/` uses QML from f0e3203; `after-100/` uses the corrected scene
at QT_SCALE_FACTOR=1; `after-150/` uses QT_SCALE_FACTOR=1.5. The latter raw RGBA
frames are 360×360 for the unchanged 240 logical pixel window. Boards display
normalized logical sizes over synthetic lists. No desktop capture or native
Windows screenshot is represented by these generated artifacts.

Reference-state mapping: ref1=Text, ref2=Image, ref3=Docs, corresponding to the
user's /home/lsvy/1.jpg, 2.jpg, 3.jpg. originals were viewed but not edited/copied.
`all-sectors.png` exercises 2,3,4,5,6,8 preview choices; these fixtures add no
production conversion support. See ../GLASS_UI_PHASE1.md for reproduction and
Windows acceptance. Phase 2 awaits explicit user approval.
