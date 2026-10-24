"""Diagnostic evidence only: UIA-to-Shell correspondence is deliberately unproven."""

from pathlib import PureWindowsPath
from time import monotonic

from filewheel.core.models import MouseEvent, TargetResolution
from filewheel.platforms.windows.native import Native


def proven_target_from_evidence(event: MouseEvent, evidence: dict) -> None:
    """G2 experiment seam. Names, selection, enumeration order are never identity.

    Shell automation below enumerates candidates, not pointer targets. No path can
    be emitted until live experiments prove a correspondence with the visual item.
    """
    return None


class ExplorerTargetResolver:
    """Construct, use and release on a single COM-initialized worker thread."""

    def __init__(self, write_record):
        self._native = Native()
        import comtypes.client

        # Generated UIA interfaces provide vtable bindings; Shell uses IDispatch.
        uia = comtypes.client.GetModule("UIAutomationCore.dll")
        self._automation = comtypes.client.CreateObject(
            "{FF48DBA4-60EF-4201-AA87-54103EEF594E}", interface=uia.IUIAutomation
        )
        self._point_type = uia.tagPOINT
        self._shell = comtypes.client.CreateObject("Shell.Application", dynamic=True)
        self._write = write_record

    def close(self) -> None:
        # Release proxies before the owning worker calls CoUninitialize.
        self._automation = None
        self._shell = None

    def resolve(self, event: MouseEvent) -> TargetResolution | None:
        start = monotonic()
        if event.injected or start - event.timestamp > 0.5:
            return None
        n = self._native
        window = n.window_evidence(event.point)
        image = window["process_image"]
        if (
            not image or PureWindowsPath(image).name.casefold() != "explorer.exe"
            or window["class_name"] != "CabinetWClass"
            or window["root_hwnd"] != event.window_id
            or window["foreground_hwnd"] != event.window_id
        ):
            return None  # Do not log unrelated applications or Shell surfaces.
        record = {
            "schema_version": 1, "sequence": event.sequence, "point": event.point,
            "timestamp_monotonic": event.timestamp, "window": window,
            "explorer_view": "unknown", "injected": event.injected,
            "resolved_path": None, "rejection": "mapping_unproven",
        }
        try:
            record["uia_ancestry"] = self._uia_evidence(event, window["pid"])
            record["shell_candidates"] = self._shell_evidence(event.window_id)
            # This intentionally returns None for every evidence combination.
            proven_target_from_evidence(event, record)
        except Exception as error:
            record["rejection"] = "evidence_error"
            record["error_type"] = type(error).__name__  # No arbitrary exception text.
        # A foreground/point-window race must discard payload, not just label it.
        try:
            unchanged = n.window_evidence(event.point) == window
        except Exception:
            unchanged = False
        if not unchanged:
            record.pop("uia_ancestry", None)
            record.pop("shell_candidates", None)
            record["rejection"] = "window_changed"
        record["elapsed_ms"] = round((monotonic() - start) * 1000, 3)
        self._write(record)
        return None

    def _uia_evidence(self, event: MouseEvent, expected_pid: int) -> list[dict]:
        element = self._automation.ElementFromPoint(self._point_type(*event.point))
        walker = self._automation.RawViewWalker
        ancestry = []
        for _ in range(12):
            if not element:
                break
            # Inspect ownership before any names, IDs, bounds or other payload.
            if element.CurrentProcessId != expected_pid:
                raise ValueError("UIA process changed")
            bounds = element.CurrentBoundingRectangle
            ancestry.append({
                "name": str(element.CurrentName)[:512],
                "automation_id": str(element.CurrentAutomationId)[:256],
                "class_name": str(element.CurrentClassName)[:256],
                "control_type": element.CurrentControlType,
                "process_id": element.CurrentProcessId,
                "native_hwnd": element.CurrentNativeWindowHandle,
                "runtime_id": list(element.GetRuntimeId())[:64],
                "bounds": [bounds.left, bounds.top, bounds.right, bounds.bottom],
                "contains_point": (
                    bounds.left <= event.point[0] < bounds.right
                    and bounds.top <= event.point[1] < bounds.bottom
                ),
            })
            # Stop before recording another application's ancestor information.
            if element.CurrentNativeWindowHandle == event.window_id:
                break
            element = walker.GetParentElement(element)
        return ancestry

    def _shell_evidence(self, hwnd: int) -> dict:
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
        return {"matching_windows": matches, "windows_truncated": windows.Count > 64}
