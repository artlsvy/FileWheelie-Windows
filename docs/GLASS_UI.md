# Current Windows glass UI

The approved forest/ivory/brass Qt Quick wheel and progress pill remain unchanged.
GlassWheel.qml, ProgressSurface.qml and Lens.qml are the visual source of truth.
The wheel uses a240 logical-pixel transparent window with a220px visible circle;
optical effects do not change sector hit geometry. Widgets remains a fallback.

The family EXE prefers Quick/OpenGL before initialization, respecting explicit
Qt settings. Repeated hardware-backend evidence and the user acceptance are in
F5_RENDERER_RELIABILITY.md. OpenGL was reliable in observed sessions; there is no
universal driver guarantee or claim that isVisible() proves desktop presentation.

Selection dismisses on outside/focus/leave; active conversion feedback persists
and may collapse/expand without cancelling the owned job. Cancel is explicit.
Progress is indeterminate where engines lack trustworthy total-work estimates.
Success expires; failure/cancellation remains actionable. PROGRESS_UX.md and
UI_LIFECYCLE_POLISH.md specify the tested lifetimes and stale-callback handling.

No desktop capture, browser framework or shader rewrite is needed. The local
filewheel-glass skill and render_glass_preview.py remain developer tools. Old
Phase1 screenshots/prototypes are recoverable from Git history, not current
runtime inputs. Do not restart interactive tests without the user's request.
