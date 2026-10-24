"""Read-only Shell view probe. Bindings and objects stay on the COM worker.

Only interface prefixes through the called methods are bound. Unused preceding
slots preserve SDK order with opaque struct pointers; no mutators are called.
See docs/G2_MAPPING.md for API sources and Windows validation limitations.
"""

import os
import stat
from pathlib import PureWindowsPath

from filewheel.core.probe_errors import ProbeFailure, probe_step
from filewheel.platforms.windows.native import require_windows


def _bindings():
    require_windows()
    import ctypes as c
    from ctypes import wintypes as w

    from comtypes import COMMETHOD, GUID, HRESULT, IUnknown

    P = c.POINTER
    V = c.c_void_p
    def IN(kind, name):
        return (["in"], kind, name)

    def OUT(kind, name):
        return (["out"], P(kind), name)

    class IOleWindow(IUnknown):
        _iid_ = GUID("{00000114-0000-0000-C000-000000000046}")
        _methods_ = [
            COMMETHOD([], HRESULT, "GetWindow", OUT(w.HWND, "window")),
            COMMETHOD([], HRESULT, "ContextSensitiveHelp", IN(w.BOOL, "enter")),
        ]

    class IShellBrowser(IOleWindow):
        _iid_ = GUID("{000214E2-0000-0000-C000-000000000046}")
        _methods_ = [
            COMMETHOD([], HRESULT, "InsertMenusSB", IN(V, "menu"), IN(V, "widths")),
            COMMETHOD([], HRESULT, "SetMenuSB", IN(V, "menu"), IN(V, "ole_menu"), IN(w.HWND, "active")),
            COMMETHOD([], HRESULT, "RemoveMenusSB", IN(V, "menu")),
            COMMETHOD([], HRESULT, "SetStatusTextSB", IN(w.LPCWSTR, "text")),
            COMMETHOD([], HRESULT, "EnableModelessSB", IN(w.BOOL, "enable")),
            COMMETHOD([], HRESULT, "TranslateAcceleratorSB", IN(P(w.MSG), "message"), IN(w.WORD, "id")),
            COMMETHOD([], HRESULT, "BrowseObject", IN(V, "pidl"), IN(w.UINT, "flags")),
            COMMETHOD([], HRESULT, "GetViewStateStream", IN(w.DWORD, "mode"), OUT(V, "stream")),
            COMMETHOD([], HRESULT, "GetControlWindow", IN(w.UINT, "id"), OUT(w.HWND, "window")),
            COMMETHOD([], HRESULT, "SendControlMsg", IN(w.UINT, "id"), IN(w.UINT, "message"),
                      IN(w.WPARAM, "wp"), IN(w.LPARAM, "lp"), OUT(c.c_ssize_t, "result")),
            # IShellView inherits IOleWindow at the same interface prefix.
            COMMETHOD([], HRESULT, "QueryActiveShellView", OUT(P(IOleWindow), "view")),
        ]

    class IServiceProvider(IUnknown):
        _iid_ = GUID("{6D5140C1-7436-11CE-8034-00AA006009FA}")
        _methods_ = [COMMETHOD([], HRESULT, "QueryService",
                              IN(P(GUID), "service"), IN(P(GUID), "iid"),
                              OUT(P(IUnknown), "object"))]

    class IShellItem(IUnknown):
        _iid_ = GUID("{43826D1E-E718-42EE-BC55-A1E261C37BFE}")
        _methods_ = [
            COMMETHOD([], HRESULT, "BindToHandler", IN(V, "context"), IN(P(GUID), "handler"),
                      IN(P(GUID), "iid"), OUT(V, "object")),
            COMMETHOD([], HRESULT, "GetParent", OUT(P(IUnknown), "parent")),
            # Keep the allocated pointer so CoTaskMemFree can release it explicitly.
            COMMETHOD([], HRESULT, "GetDisplayName", IN(w.UINT, "form"), OUT(V, "name")),
            COMMETHOD([], HRESULT, "GetAttributes", IN(w.ULONG, "mask"), OUT(w.ULONG, "attrs")),
        ]

    class IFolderView2(IUnknown):
        _iid_ = GUID("{1AF3A467-214F-4298-908E-06B03E0B39F9}")
        _methods_ = [
            # IFolderView slots 3..16, followed by IFolderView2 through GetItem.
            COMMETHOD([], HRESULT, "GetCurrentViewMode", OUT(w.UINT, "mode")),
            COMMETHOD([], HRESULT, "SetCurrentViewMode", IN(w.UINT, "mode")),
            COMMETHOD([], HRESULT, "GetFolder", IN(P(GUID), "iid"), OUT(V, "folder")),
            COMMETHOD([], HRESULT, "Item", IN(c.c_int, "index"), OUT(V, "pidl")),
            COMMETHOD([], HRESULT, "ItemCount", IN(w.UINT, "flags"), OUT(c.c_int, "count")),
            COMMETHOD([], HRESULT, "Items", IN(w.UINT, "flags"), IN(P(GUID), "iid"), OUT(V, "items")),
            COMMETHOD([], HRESULT, "GetSelectionMarkedItem", OUT(c.c_int, "index")),
            COMMETHOD([], HRESULT, "GetFocusedItem", OUT(c.c_int, "index")),
            COMMETHOD([], HRESULT, "GetItemPosition", IN(V, "pidl"), OUT(w.POINT, "point")),
            COMMETHOD([], HRESULT, "GetSpacing", OUT(w.POINT, "point")),
            COMMETHOD([], HRESULT, "GetDefaultSpacing", OUT(w.POINT, "point")),
            COMMETHOD([], HRESULT, "GetAutoArrange"),
            COMMETHOD([], HRESULT, "SelectItem", IN(c.c_int, "index"), IN(w.DWORD, "flags")),
            COMMETHOD([], HRESULT, "SelectAndPositionItems", IN(w.UINT, "count"), IN(V, "pidls"),
                      IN(P(w.POINT), "points"), IN(w.DWORD, "flags")),
            COMMETHOD([], HRESULT, "SetGroupBy", IN(V, "key"), IN(w.BOOL, "ascending")),
            COMMETHOD([], HRESULT, "GetGroupBy", IN(V, "key_storage"), OUT(w.BOOL, "ascending")),
            COMMETHOD([], HRESULT, "SetViewProperty", IN(V, "pidl"), IN(V, "key"), IN(V, "value")),
            COMMETHOD([], HRESULT, "GetViewProperty", IN(V, "pidl"), IN(V, "key"), IN(V, "value_storage")),
            COMMETHOD([], HRESULT, "SetTileViewProperties", IN(V, "pidl"), IN(w.LPCWSTR, "properties")),
            COMMETHOD([], HRESULT, "SetExtendedTileViewProperties", IN(V, "pidl"), IN(w.LPCWSTR, "properties")),
            COMMETHOD([], HRESULT, "SetText", IN(c.c_int, "kind"), IN(w.LPCWSTR, "text")),
            COMMETHOD([], HRESULT, "SetCurrentFolderFlags", IN(w.DWORD, "mask"), IN(w.DWORD, "flags")),
            COMMETHOD([], HRESULT, "GetCurrentFolderFlags", OUT(w.DWORD, "flags")),
            COMMETHOD([], HRESULT, "GetSortColumnCount", OUT(c.c_int, "count")),
            COMMETHOD([], HRESULT, "SetSortColumns", IN(V, "columns"), IN(c.c_int, "count")),
            COMMETHOD([], HRESULT, "GetSortColumns", IN(V, "columns"), IN(c.c_int, "count")),
            COMMETHOD([], HRESULT, "GetItem", IN(c.c_int, "index"), IN(P(GUID), "iid"),
                      OUT(P(IShellItem), "item")),
        ]

    return c, w, GUID, IServiceProvider, IShellBrowser, IFolderView2, IShellItem


class ShellViewProbe:
    def __init__(self, native):
        self._native = native
        self._types = _bindings()
        c, w, *_ = self._types
        self._ole = c.WinDLL("ole32", use_last_error=True)
        self._ole.CoTaskMemFree.argtypes = [c.c_void_p]
        self._ole.CoTaskMemFree.restype = None
        native.user.IsChild.argtypes, native.user.IsChild.restype = [w.HWND, w.HWND], w.BOOL
        native.user.ClientToScreen.argtypes = [w.HWND, c.POINTER(w.POINT)]
        native.user.ClientToScreen.restype = w.BOOL
        native.kernel.GetDriveTypeW.argtypes = [w.LPCWSTR]
        native.kernel.GetDriveTypeW.restype = w.UINT

    def capture(self, shell_window, ancestry: list[dict], index: int) -> dict:
        """Return observed relationships, not a trusted pointer-to-file assertion."""
        completed = []
        try:
            result = probe_step(completed, "native_probe", self._capture,
                                shell_window, ancestry, index, completed)
        except ProbeFailure as error:
            return {"active_view_association": {"status": "unproven", **error.evidence}}
        result["probe_steps"] = completed[:32]
        return result

    def _capture(self, shell_window, ancestry: list[dict], index: int, completed: list) -> dict:
        c, w, GUID, service_type, browser_type, folder_type, item_type = self._types
        def step(stage, operation):
            return probe_step(completed, stage, operation)

        service = step("query_service_provider", lambda: shell_window.QueryInterface(service_type))
        unknown = step("query_top_level_browser_service", lambda: service.QueryService(
            c.byref(GUID("{4C96BE40-915C-11CF-99D3-00AA004AE837}")),
            c.byref(browser_type._iid_),
        ))
        browser = step("query_shell_browser_interface", lambda: unknown.QueryInterface(browser_type))
        view = step("query_active_shell_view", lambda: browser.QueryActiveShellView())
        view_hwnd = step("get_active_view_hwnd", lambda: view.GetWindow()) or 0
        tabs = [a["native_hwnd"] for a in ancestry if a.get("class_name") == "ShellTabWindowClass"]
        contents = [a["native_hwnd"] for a in ancestry if a.get("class_name") == "UIItemsView"]
        roots = [a["native_hwnd"] for a in ancestry if a.get("class_name") == "CabinetWClass"]
        associated = (
            len(tabs) == len(contents) == len(roots) == 1
            and tabs[0] and contents[0] and roots[0]
            and self._native.user.IsChild(tabs[0], view_hwnd)
            and (view_hwnd == contents[0] or self._native.user.IsChild(view_hwnd, contents[0]))
            and self._native.user.GetAncestor(view_hwnd, 2) == roots[0]
        )
        association = {
            "status": "matched" if associated else "unproven",
            "method": "active_shell_view_hwnd_chain", "view_hwnd": view_hwnd,
            "tab_hwnd": tabs[0] if len(tabs) == 1 else None,
            "browser_hwnd": step("get_browser_hwnd", lambda: browser.GetWindow()) or 0,
            "items_view_hwnd": contents[0] if len(contents) == 1 else None,
            "windows_verified": False,
        }
        if not associated:
            return {"active_view_association": association}
        folder = step("query_folder_view2", lambda: view.QueryInterface(folder_type))
        count = step("get_view_item_count", lambda: folder.ItemCount(2))  # SVGIO_ALLVIEW
        if not 0 <= index < count <= 32:
            return {"active_view_association": association, "native_error": "view_index_or_size"}
        item = step("get_indexed_shell_item", lambda: folder.GetItem(index, c.byref(item_type._iid_)))
        path = step("get_filesystem_path", lambda: self._path(item))
        attributes = step("get_shell_item_attributes", lambda: item.GetAttributes(0x60000000))
        local_path = PureWindowsPath(path)
        local = (
            local_path.is_absolute() and len(local_path.drive) == 2
            and self._native.kernel.GetDriveTypeW(local_path.anchor) == 3  # DRIVE_FIXED
        )
        file_state = {"exists_regular_file": False, "is_reparse_point": None}
        if local:
            try:
                info = os.stat(path, follow_symlinks=False)
                file_state = {
                    "exists_regular_file": stat.S_ISREG(info.st_mode),
                    "is_reparse_point": bool(getattr(info, "st_file_attributes", 0) & 0x400),
                }
            except OSError:
                pass
        position = None
        position_error = None
        try:
            pidl = step("get_position_pidl", lambda: folder.Item(index))
            try:
                point = step("get_item_position", lambda: folder.GetItemPosition(pidl))
                if self._native.user.ClientToScreen(view_hwnd, c.byref(point)):
                    position = [point.x, point.y]
            finally:
                self._ole.CoTaskMemFree(pidl)
        except ProbeFailure as error:
            position_error = error.evidence  # Position is supplementary, never identity proof.
        again = step("recheck_active_shell_view", lambda: browser.QueryActiveShellView())
        second_item = step("recheck_indexed_shell_item", lambda: folder.GetItem(index, c.byref(item_type._iid_)))
        stable = (
            step("recheck_view_hwnd", lambda: again.GetWindow()) == view_hwnd
            and step("recheck_view_item_count", lambda: folder.ItemCount(2)) == count
            and step("recheck_filesystem_path", lambda: self._path(second_item)) == path
        )
        return {
            "active_view_association": association,
            "native_view_candidate": {
                "index": index, "candidate_path": path,
                "is_filesystem": bool(attributes & 0x40000000),
                "is_folder": bool(attributes & 0x20000000),
                "item_position_screen": position,
                "position_error": position_error,
                "view_mode": step("get_view_mode", lambda: folder.GetCurrentViewMode()),
                "view_item_count": count,
                "snapshot_stable": bool(stable), **file_state,
                "local_fixed_drive": bool(local),
            },
        }

    def _path(self, item) -> str:
        c = self._types[0]
        pointer = item.GetDisplayName(0x80058000)  # SIGDN_FILESYSPATH
        try:
            if not pointer:
                raise ValueError("Shell item has no filesystem path")
            path = c.wstring_at(pointer)
            if len(path) > 32767:
                raise ValueError("Shell path too long")
            return path
        finally:
            self._ole.CoTaskMemFree(pointer)
