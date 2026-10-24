"""Shell-only evidence collector; construct, call and close in one apartment."""

from filewheel.platforms.windows.native import Native, require_windows


class ShellEvidenceCollector:
    def __init__(self, *, native_probe: bool = False):
        require_windows()
        import comtypes.client

        self._shell = comtypes.client.CreateObject("Shell.Application", dynamic=True)
        self._view_probe = None
        if native_probe:
            from filewheel.platforms.windows.shell_view import ShellViewProbe

            self._view_probe = ShellViewProbe(Native())

    def close(self) -> None:
        self._view_probe = None
        self._shell = None

    def collect(self, hwnd: int, ancestry: list[dict] | None = None) -> dict:
        windows = self._shell.Windows()
        matches = []
        for index in range(min(windows.Count, 64)):
            window = windows.Item(index)
            if int(window.HWND) != hwnd:
                continue
            document = window.Document
            items = document.Folder.Items()
            candidates = []
            for item_index in range(min(items.Count, 32)):
                item = items.Item(item_index)
                candidates.append({
                    "enumeration_index": item_index,
                    "candidate_path": str(item.Path)[:2048],
                    "is_folder": bool(item.IsFolder),
                    "is_filesystem": bool(item.IsFileSystem),
                })
            matches.append({
                "hwnd": hwnd, "item_count": items.Count,
                "truncated": items.Count > 32, "candidates": candidates,
                "active_tab_proven": False, "geometry_available": False,
            })
            if ancestry is not None and self._view_probe is not None:
                rows = [row for row in ancestry if row.get("class_name") == "UIItem"
                        and row.get("control_type") == 50007]
                if len(rows) == 1 and str(rows[0].get("automation_id", "")).isascii():
                    value = rows[0]["automation_id"]
                    if value.isdecimal() and len(value) < 10:
                        try:
                            matches[-1].update(self._view_probe.capture(window, ancestry, int(value)))
                        except Exception as error:
                            matches[-1]["active_view_association"] = {
                                "status": "unproven", "error_type": type(error).__name__,
                            }
        return {"matching_windows": matches, "windows_truncated": windows.Count > 64}
