# Next bounded Codex task

**Task G4-A: build the usable PySide6 radial menu prototype.**

The user explicitly made this the NEXT development priority after the now
implemented headless G2-F launcher. Do not return to Mouse3 diagnostics unless a
specific blocker requires it. Preserve all experimental source and its trust
barrier. No actual file conversion yet.

Read STATUS.md, ROADMAP.md, UI_SPEC.md, SEND_TO.md and D-012 in DECISIONS.md.
The shared InvocationController now exposes handle_explicit(arguments, point,
timestamp, inspect_file)->ExplicitInvocationResult and handle(MouseEvent)->
TargetResolution|None. Both successes use TargetResolution(path, source, point,
timestamp, window_id); GUI routing must be identical after that boundary.

1. Add PySide6 as an optional UI dependency and an executable prototype entry.
   Check actual wheel/runtime compatibility before pinning versions; keep
   existing diagnostics usable. Use the explicit-path validator/controller for
   real launching and injected DTOs for portable/offscreen testing.
2. Implement a small frameless radial wheel near the cursor, clamped to the
   current monitor work area. Handle physical-to-Qt coordinate mapping at the UI
   boundary. Test negative positions/edges/scaling with pure placement logic;
   actual Windows DPI/overlay behavior remains separately unverified.
3. First level shows compatible output categories; second shows concrete formats.
   Use an injected, explicitly declared/tested preview capability registry while
   engines are absent. Choices must be marked as previews; selecting a format
   records/displays a dry-run choice and changes no files. Unknown inputs show
   an honest no-capabilities state, never fabricated conversion pairs.
4. Implement Escape dismissal, center/back navigation and click-outside dismissal.
   Reopening cancels prior menu state. A rejected path or None target opens no
   wheel. Keep the state machine pure/testable and work bounded: no tray/IPC,
   installers, actual engines or unrelated design polish needed for this job.
5. Provide a GUI launch path using the same controller/DTO from Send to; retain
   the headless diagnostic command. Experimental hover can feed that same UI
   seam only when it returns a genuinely validated target; do not promote its
   provisional paths. The current resolver still returns None.
6. Run pure tests and Qt offscreen tests if available, request focused review,
   and document actual commands, failures/dependency availability and native
   validation limits. Update STATUS.md and one next bounded task.

Acceptance: a runnable two-stage radial prototype receives a validated explicit
path near the cursor and supports Escape/Back/outside dismissal with compatible
preview choices. No conversion/source mutation, no selected-file guessing, and
no need for an online Windows-MCP or host to implement the portable pieces.

## Independent Windows acceptance queue

G2-F headless integration is implemented/Linux-tested, not Windows-verified.
Run the direct CLI plus stage/install/Send to/remove steps in SEND_TO.md when
Windows is available. Record exact path/source/point, Unicode/spaces/metachar
preservation, multi-argument/folder/nonexistent rejection and install/remove
ownership behavior. Keep this pending while independent GUI development proceeds.
Qt popup placement, focus/click-outside behavior and scaling also need real Win11
validation before any claim of native UI success. Hover's stricter G2 matrix
remains queued only for future hover work; it must not block this GUI prototype.
