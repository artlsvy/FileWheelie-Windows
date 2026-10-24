# Explorer exact-file hit testing — FIRST technical gate

## User contract
On a middle-button press over an **actual filesystem file in Windows 11 Explorer**, resolve the **specific file underneath the pointer**. The file may be unselected; another file can be selected. A false positive is worse than returning None. No conversions or graphical wheel during the initial proof-of-concept.

## Proposed evaluation pipeline (research, not a claimed solution)
1. `WH_MOUSE_LL` receives `WM_MBUTTONDOWN` with physical desktop coordinates; queue minimal event; immediately `CallNextHookEx` (do not swallow during POC). Use an appropriate Windows message-loop thread. Document injected-event handling and deduplication.
2. Determine foreground/ancestor window and process; only proceed if this is a supported `explorer.exe` file-content view, **not** an arbitrary Explorer UI area. Do not rely solely on the process name (other windows and Shell surfaces may use it).
3. On a separate COM-initialized worker, `IUIAutomation::ElementFromPoint()` gets the element. Inspect ancestry, control type, bounds, automation ID, native window handle, process, view and selection metadata. Reject non-file rows and backgrounds.
4. Identify a Shell item through `IShellWindows` / Shell view COM (`IFolderView`/`IFolderView2`/`IShellItem`) or another **verified** item identity mechanism. Test whether mapping UIA identity/geometry to Shell item is deterministic on the installed Explorer build. Do **not** assume `ElementFromPoint` contains an absolute path or that the UIA label equals the true filename.
5. Convert only a proven filesystem `IShellItem` to a path. Validate existence/type and that it corresponds to the pointer location in that Explorer view. Fail closed if ambiguous or inaccessible. Record evidence and confidence (avoid guessing).
6. Emit `TargetResolution(source='explorer_hover', path, window_id, point, timestamp)` or `None`. Neither selected nor focused item is a valid substitute.

## Distinguish three questions
- Did we intercept the click? (Win32 hook)
- What Explorer *visual row/item* was under that point? (UIA)
- Which real filesystem Shell item does that row represent? (Shell API + **validated correspondence**)
Each needs independent evidence. There is no documented one-call `point → filesystem path` API that is known to work in every Win11 Explorer configuration.

## Experimental strategies to compare
A. UIA element at point + Shell view item mapping via stable identity or audited bounding geometry. Prefer if demonstrably correct.
B. Explorer-specific hit testing if the target Windows build exposes a stable, documented API. Research before committing; avoid undocumented UI tree assumptions.
C. Windows Shell supplied path via `Send to` or Explorer context menu launcher (`%1`/multi-selection contract). This is deterministic for the explicit item but **not middle-click-on-hover**. Fallback when A/B fail.

### No unsafe shortcuts
- Do not call `SelectedItems()` / `FocusedItem()` as if it were the pointer target.
- Do not reconstruct `parent_path / displayed_UIA_name` without an explicit proof of uniqueness and extension resolution. Hidden extensions, localized UI labels, shortcuts, duplicate display names and virtual items break it.
- No OCR, screen-coordinate filenames, or pixel-to-row-order assumptions in production resolver.
- Do not click/select the hovered row to discover path unless separately approved as a UX-changing fallback; never silently mutate selection.

## Debug tool and logs
Write an opt-in diagnostic that outputs (JSONL) event coordinates, foreground HWND/process, UIA ancestry with safely bounded properties, candidate Shell item identity, resolved path or reason for rejection, timing, Windows build, Explorer view and DPI. Avoid logging unrelated user activity; diagnostic mode only, default disabled. Logs can contain private local filenames; keep them local and gitignored.

## Windows acceptance matrix (record actual evidence)
- Explorer Details, List, Small/Large icons
- Tabbed Explorer windows; 2 Explorer windows; desktop vs folder view
- Click item A while B is selected; click B while A focused
- Hidden extensions; identical displayed stems; Unicode filenames; spaces; long paths
- Empty pane, filename column edge, navigation pane, command bar, folder, Quick Access, archives, libraries
- Sort/filter/reorder/scroll; grouped items; virtual/cloud placeholders
- Display scale 100% and 150%+; secondary monitor / negative coordinates
- Explorer elevated/unprivileged behavior where relevant; locked/unlocked desktop
- Rapid click, repeated clicks, Explorer restarts; hook lifecycle and process exit

## Gate decision record
G2 may be marked `WINDOWS-VERIFIED` only with actual correct results for the core matrix and documented exclusions. If deterministic item identity cannot be proven, switch the *invocation mechanism* to explicit Shell path passing (G2-F). Do not continue to wheel integration on an unreliable resolver.

## Primary API references
- https://learn.microsoft.com/en-us/windows/win32/winmsg/lowlevelmouseproc
- https://learn.microsoft.com/en-us/windows/win32/api/uiautomationclient/nf-uiautomationclient-iuiautomation-elementfrompoint
- https://learn.microsoft.com/en-us/windows/win32/api/shobjidl_core/nf-shobjidl_core-ifolderview2-getitem
- https://learn.microsoft.com/en-us/windows/win32/api/shobjidl_core/nf-shobjidl_core-ifolderview-getitemposition
- https://learn.microsoft.com/en-us/windows/win32/api/shldisp/nn-shldisp-ishellfolderviewdual
