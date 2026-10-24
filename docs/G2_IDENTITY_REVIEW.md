# G2 identity review — 2026-10-25

## Probe result and decision

The supplied g2-control-class-1 capture reports native view=SHELLDLL_DefView,
items_view=DirectUIHWND and browser=ShellTabWindowClass. No standard SysListView32
content was observed. The standard list-view hit-test route is therefore not
applicable to this sampled surface under the current documented-control guard.
Do not send LVM messages to it or infer compatibility from UIA's DUIListView label.

The capture separately hit a conservative diagnostic guard: an inactive tab had
51 entries, with the expected32 logged. Positive native HWND exclusion identifies
that tab as unrelated to the hovered view. The assessor now permits a consistent
bounded prefix for that excluded peer; it still requires the hovered candidate
set to be complete. Replay yields provisional tests/a.txt, not a new native run.

The missing identity bridge remains. D-011 selects the explicit Shell-path
fallback as the next implementation baseline, with hover retained diagnostic-only.
This is a workflow compromise, not a claim that hover is impossible. G2-F must
be implemented and verified independently before UI/converter work. Do not repeat
the control-class/filename experiments to seek a guarantee they cannot establish.
The probe setup below is retained as historical evidence, not the next task.

## What the supplied Windows evidence establishes

Build26200/DPI96, Python3.15.0/comtypes1.4.17, UIA MTA and Shell STA:

| Concern | Observed evidence | Limit |
| --- | --- | --- |
| Pointer vs selection | Correct provisional candidates for previously unselected files in Medium icons/Details | Native Mouse3 selects the clicked file before async UIA; use operator notes |
| Native tab association | Correct alternating paths in two tabs, unique HWND match among three registrations in names-2 | Sampled relationships, not a guarantee across tab/navigation races |
| Index consistency | UIA and both Shell sources agree, including reassigned indices after sort/view changes | No documented AutomationId-to-view-index contract |
| Hidden extensions/Unicode | unicode-æøå UIA stem maps to exact Shell unicode-æøå.txt path | Path is a candidate until row-to-item identity is proven |
| Duplicate display stems | Both report labels reject as ambiguous_display_name | Safe exclusion; no guessed file |
| Non-file areas | Folder, background, command-bar and search-box rejection | Other virtual/elevated/restart/DPI cases remain pending |
| Shell geometry | GetItemPosition consistently reports E_NOTIMPL | No independent Shell hit rectangle/point correspondence |

The requested provisional implementation exists and has live diagnostic evidence.
The **trusted G2 milestone remains pending**. No converter or UI may depend on
the candidate paths; ExplorerTargetResolver.resolve still returns None.

## Why another equivalent click batch cannot close the identity gap

[ElementFromPoint](https://learn.microsoft.com/en-us/windows/win32/api/uiautomationclient/nf-uiautomationclient-iuiautomation-elementfrompoint)
identifies a UIA element, while
[IFolderView2.GetItem](https://learn.microsoft.com/en-us/windows/win32/api/shobjidl_core/nf-shobjidl_core-ifolderview2-getitem)
retrieves an indexed Shell item. The observed numeric relationship is useful
empirical evidence, but UIA identification properties do not document that
Explorer's AutomationId is this native index. Sampling the same index twice or
matching its displayed name does not create an independent identity comparison.
See Microsoft's [UIA testing guidance](https://learn.microsoft.com/en-us/windows/win32/winauto/uiauto-usefortesting).

Likewise [GetItemPosition](https://learn.microsoft.com/en-us/windows/win32/api/shobjidl_core/nf-shobjidl_core-ifolderview-getitemposition)
documents only an item's upper-left position, not a hit-test rectangle; in our
supplied captures it is not implemented. Further DPI/race acceptance testing is
still required eventually, but cannot establish a missing API identity contract.

## Next bounded feasibility probe

The diagnostic now reads the actual native class names for the sampled view,
content and browser HWNDs using
[GetClassNameW](https://learn.microsoft.com/en-us/windows/win32/api/winuser/nf-winuser-getclassnamew).
Results are optional strings under:

`shell_candidates.matching_windows[*].active_view_association.native_window_classes`

This is separate from UIA's provider class_name. It is read-only, worker-side,
and does not change any assessment/trust flags. New fields have Linux fake-test
coverage only; no Windows values have been supplied yet.

[ListView_HitTest](https://learn.microsoft.com/en-us/windows/win32/api/commctrl/nf-commctrl-listview_hittest)
is documented for a standard list-view HWND. Do not assume Explorer's UIA
DUIListView label makes its HWND a standard control. Only if an applicable native
control is present should a further independently audited hit-test experiment be
scoped. That would still need to establish correspondence to native Shell items;
do not send pointer-bearing LVM messages into Explorer using local Python memory.
This change implements no LVM messages, process-memory operations or hooks.

After syncing, click ONE existing ordinary file, then stop:

```powershell
.\.venv\Scripts\python.exe -m filewheel.platforms.windows.diagnostics --enable --dry-run-mapping --output logs\g2-control-class-1.jsonl
$LASTEXITCODE
```

Inspect native_window_classes on the matched registration. No new files or
Unicode/duplicate-label retest is needed. If no applicable standard list view is
present, record that this route is unavailable; that does not prove every native
identity mechanism impossible. A LegacyIAccessible hit alone would establish
another visual row, not an IShellItem identity. Scope further work only around a
documented independently comparable identity; otherwise make the G2-F explicit
Shell-path fallback decision required by EXPLORER_HIT_TEST.md. No fallback change
was made by the initial review; the subsequent D-011 decision above now selects
the next baseline. No unsupported hover scenario is silently enabled.
