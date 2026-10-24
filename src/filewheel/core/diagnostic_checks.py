"""Portable provenance classification for diagnostic counts, never path resolution."""

from pathlib import PureWindowsPath

from filewheel.core.models import MouseEvent


def explorer_rejection(event: MouseEvent, window: dict) -> str | None:
    image = window.get("process_image")
    if not image:
        return "process_unavailable"
    if PureWindowsPath(image).name.casefold() != "explorer.exe":
        return "non_explorer_process"
    if window.get("class_name") != "CabinetWClass":
        return "unsupported_explorer_surface"
    if (
        window.get("root_hwnd") != event.window_id
        or window.get("foreground_hwnd") != event.window_id
    ):
        return "window_mismatch"
    return None
