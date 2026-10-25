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
            rows = [row for row in ancestry or [] if row.get("class_name") == "UIItem"
                    and row.get("control_type") == 50007]
            provisional_index = None
            if len(rows) == 1:
                value = rows[0].get("automation_id", "")
                if (isinstance(value, str) and value.isascii() and value.isdecimal()
                        and len(value) < 10):
                    provisional_index = int(value)
            entry = {
                "hwnd": hwnd, "item_count": None, "truncated": False, "candidates": [],
                "lookup_mode": "targeted_index", "active_tab_proven": False,
                "geometry_available": False,
            }
            matches.append(entry)
            if self._view_probe is not None:
                if ancestry is None or provisional_index is None:
                    continue
                try:
                    entry.update(self._view_probe.capture(window, ancestry, provisional_index))
                except Exception as error:  # noqa: BLE001 - fail closed at COM boundary
                    entry["active_view_association"] = {
                        "status": "unproven", "error_type": type(error).__name__,
                    }
                if entry.get("active_view_association", {}).get("status") != "matched":
                    continue  # Excluded tabs need no Folder.Items calls at all.
                if entry.get("native_view_candidate") is None:
                    continue
            items = window.Document.Folder.Items()
            count = items.Count
            entry["item_count"] = count
            if self._view_probe is None or count <= 32:
                entry.pop("lookup_mode")  # Legacy bounded complete evidence.
                entry["truncated"] = count > 32
                entry["candidates"] = [self._candidate(items.Item(i), i)
                                       for i in range(min(count, 32))]
            elif 0 <= provisional_index < count:
                candidate = self._candidate(items.Item(provisional_index), provisional_index)
                entry["candidates"] = [candidate]
            entry["shell_snapshot_stable"] = items.Count == count
        return {"matching_windows": matches, "windows_truncated": windows.Count > 64}

    @staticmethod
    def _candidate(item, index):
        return {
            "enumeration_index": index, "candidate_path": str(item.Path),
            "is_folder": bool(item.IsFolder), "is_filesystem": bool(item.IsFileSystem),
        }
