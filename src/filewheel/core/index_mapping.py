"""Assess an Explorer index hypothesis for diagnostics, never for trusted routing.

UIA AutomationId and Shell Folder.Items indices have no proven correspondence.
Even a structurally consistent assessment remains provisional: this module never
creates TargetResolution or accepts caller-provided 'verified' identity flags.
"""

import math
import re
from pathlib import PureWindowsPath

from filewheel.core.diagnostic_checks import explorer_rejection
from filewheel.core.models import MouseEvent


def _number(value) -> bool:
    return type(value) in (int, float) and math.isfinite(value)


def _integer(value) -> bool:
    return type(value) is int and value >= 0


def _contains(bounds, point) -> bool:
    return (
        isinstance(bounds, (list, tuple)) and len(bounds) == 4
        and all(_number(value) for value in bounds)
        and bounds[0] < bounds[2] and bounds[1] < bounds[3]
        and bounds[0] <= point[0] < bounds[2]
        and bounds[1] <= point[1] < bounds[3]
    )


def _local_file_path(value) -> PureWindowsPath | None:
    if not isinstance(value, str) or not value or len(value) > 2048:
        return None
    if any(part in (".", "..") for part in value.replace("/", "\\").split("\\")):
        return None
    path = PureWindowsPath(value)
    if not path.is_absolute() or not re.fullmatch(r"[A-Za-z]:", path.drive):
        return None
    if any(
        part in (".", "..") or part.endswith((".", " "))
        or any(character in part for character in '\x00:*?"<>|')
        or any(ord(character) < 32 for character in part)
        or re.fullmatch(r"(?i)(CON|PRN|AUX|NUL|COM[1-9]|LPT[1-9])(?:\..*)?", part)
        for part in path.parts[1:]
    ):
        return None
    return path if len(path.parts) > 1 else None


def assess_index_mapping(record: dict, *, now: float) -> dict:
    """Return bounded JSON evidence for an index candidate, never a trusted path.

    ``candidate_path`` is copied only from Shell enumeration. ``provisional``
    means basic consistency checks passed, not that the click's identity is
    established. Collection timestamps are monotonic within the captured run;
    replay callers must use that run's clock domain, not their current uptime.
    """
    result = {
        "status": "rejected", "rejection": "malformed_evidence",
        "candidate_path": None, "candidate_index": None, "hovered_item": None,
        "checks": {
            "explorer_provenance": False, "fresh": False,
            "geometry_valid": False, "ancestry_provenance": False,
            "complete_candidates": False, "index_in_range": False,
            "name_corroboration": None, "active_view_associated": False,
            "identity_correspondence": False, "filesystem_identity": False,
        },
    }
    checks = result["checks"]

    def reject(reason):
        result["rejection"] = reason
        return result

    try:
        if (not isinstance(record, dict) or type(record.get("schema_version")) is not int
                or record["schema_version"] != 1):
            return result
        point = record["point"]
        timestamp = record["timestamp_monotonic"]
        window = record["window"]
        if (
            not isinstance(point, (list, tuple)) or len(point) != 2
            or not all(_number(value) for value in point)
            or not isinstance(window, dict)
            or not _integer(window.get("foreground_hwnd"))
            or window["foreground_hwnd"] == 0
            or not _integer(window.get("pid")) or window["pid"] == 0
            or not _integer(record.get("sequence"))
            or not _number(timestamp) or not _number(now)
            or record.get("injected") is not False
        ):
            return result
        event = MouseEvent(record["sequence"], tuple(point), timestamp,
                           window["foreground_hwnd"])
        rejection = explorer_rejection(event, window)
        if rejection:
            return reject(rejection)
        checks["explorer_provenance"] = True
        if not 0 <= now - timestamp <= 0.5:
            return reject("stale_evidence")
        if record.get("rejection") in ("window_changed", "evidence_error"):
            return reject(record["rejection"])
        if record.get("uia_recheck_unchanged") is False:
            return reject("uia_changed")
        if record.get("snapshot_stable") is False:
            return reject("snapshot_changed")
        checks["fresh"] = True
        ancestry = record["uia_ancestry"]
        if not isinstance(ancestry, list) or not 1 <= len(ancestry) <= 12:
            return reject("invalid_ancestry")
        if any(not isinstance(item, dict) or item.get("process_id") != window["pid"]
               for item in ancestry):
            return reject("uia_process_mismatch")
        hits = [(index, item) for index, item in enumerate(ancestry)
                if item.get("class_name") == "UIItem" and item.get("control_type") == 50007]
        if len(hits) != 1:
            return reject("non_file_element" if not hits else "ambiguous_uia_item")
        item_index, item = hits[0]
        result["hovered_item"] = {
            "name": str(item.get("name", ""))[:512],
            "automation_id": str(item.get("automation_id", ""))[:256],
            "bounds": None,
        }
        if not _contains(item.get("bounds"), point):
            return reject("invalid_geometry")
        result["hovered_item"]["bounds"] = list(item["bounds"])
        checks["geometry_valid"] = True
        view = [index for index, node in enumerate(ancestry)
                if node.get("class_name") == "UIItemsView" and node.get("control_type") == 50008]
        tab = [index for index, node in enumerate(ancestry)
               if node.get("class_name") == "ShellTabWindowClass"]
        root = ancestry[-1]
        if (
            len(view) != 1 or len(tab) != 1 or not item_index < view[0] < tab[0] < len(ancestry) - 1
            or root.get("class_name") != "CabinetWClass"
            or root.get("native_hwnd") != event.window_id
            or not _integer(ancestry[view[0]].get("native_hwnd"))
            or not ancestry[view[0]]["native_hwnd"]
            or not _integer(ancestry[tab[0]].get("native_hwnd"))
            or not ancestry[tab[0]]["native_hwnd"]
            or not all(_contains(ancestry[index].get("bounds"), point)
                       for index in (view[0], tab[0], len(ancestry) - 1))
        ):
            return reject("invalid_view_ancestry")
        checks["ancestry_provenance"] = True
        automation_id = item.get("automation_id")
        if not isinstance(automation_id, str) or not re.fullmatch(r"0|[1-9][0-9]{0,9}", automation_id):
            return reject("invalid_automation_index")
        index = int(automation_id)
        result["candidate_index"] = index
        shell = record["shell_candidates"]
        if not isinstance(shell, dict) or shell.get("windows_truncated") is not False:
            return reject("truncated_shell_windows")
        windows = shell.get("matching_windows")
        if not isinstance(windows, list) or len(windows) != 1:
            return reject("ambiguous_shell_windows")
        shell_window = windows[0]
        if shell_window.get("hwnd") != event.window_id:
            return reject("shell_window_mismatch")
        if shell_window.get("native_error") is not None:
            return reject(
                "native_view_index_or_size"
                if shell_window["native_error"] == "view_index_or_size"
                else "native_probe_error"
            )
        association = shell_window.get("active_view_association", {})
        if not isinstance(association, dict):
            return reject("invalid_view_association")
        if association.get("error_type") is not None:
            return reject("native_probe_error")
        association_status = association.get("status", "unproven")
        if association_status not in ("matched", "unproven"):
            return reject("ambiguous_active_view")
        if association_status == "matched":
            if (
                association.get("items_view_hwnd") != ancestry[view[0]]["native_hwnd"]
                or association.get("tab_hwnd") != ancestry[tab[0]]["native_hwnd"]
                or not _integer(association.get("view_hwnd"))
                or not association["view_hwnd"]
                or not _integer(association.get("browser_hwnd"))
                or not association["browser_hwnd"]
            ):
                return reject("active_view_mismatch")
            checks["active_view_associated"] = True
        candidates = shell_window.get("candidates")
        count = shell_window.get("item_count")
        if (
            shell_window.get("truncated") is not False or not _integer(count)
            or not isinstance(candidates, list) or len(candidates) != count
            or count > 32
        ):
            return reject("truncated_candidates")
        indices = [candidate.get("enumeration_index") for candidate in candidates]
        if any(not _integer(value) for value in indices) or sorted(indices) != list(range(count)):
            return reject("inconsistent_candidate_indices")
        checks["complete_candidates"] = True
        if not 0 <= index < count:
            return reject("invalid_candidate_index")
        checks["index_in_range"] = True
        candidate = next(candidate for candidate in candidates
                         if candidate["enumeration_index"] == index)
        if candidate.get("is_folder") is not False or candidate.get("is_filesystem") is not True:
            return reject("unsupported_shell_object")
        path = _local_file_path(candidate.get("candidate_path"))
        if path is None:
            return reject("unsupported_candidate_path")
        name = item.get("name")
        if not isinstance(name, str) or not name or len(name) > 512:
            return reject("invalid_uia_name")
        display_name = candidate.get("display_name")
        if display_name is not None:
            if not isinstance(display_name, str) or not display_name or name != display_name:
                return reject("inconsistent_names")
            checks["name_corroboration"] = True
        elif name == path.name:
            checks["name_corroboration"] = True
        elif name == path.stem:
            checks["name_corroboration"] = None  # Hidden extension is not identity.
        else:
            return reject("inconsistent_names")
        name_matches = 0
        for other in candidates:
            other_path = _local_file_path(other.get("candidate_path"))
            if other.get("display_name") is not None:
                name_matches += other["display_name"] == name
            elif other_path is not None:
                name_matches += name in (other_path.name, other_path.stem)
        if name_matches > 1:
            return reject("ambiguous_display_name")
        native = shell_window.get("native_view_candidate")
        checks["native_index_path_match"] = None
        checks["native_regular_file"] = None
        checks["native_snapshot_stable"] = None
        checks["native_reparse_point"] = None
        checks["native_local_fixed_drive"] = None
        if native is not None:
            if not isinstance(native, dict):
                return reject("malformed_native_evidence")
            native_path = _local_file_path(native.get("candidate_path"))
            matches = _integer(native.get("index")) and native["index"] == index and native_path == path
            checks["native_index_path_match"] = matches
            if not matches:
                return reject("native_candidate_mismatch")
            regular = native.get("exists_regular_file")
            checks["native_regular_file"] = regular if type(regular) is bool else None
            stable = native.get("snapshot_stable")
            checks["native_snapshot_stable"] = stable if type(stable) is bool else None
            reparse = native.get("is_reparse_point")
            checks["native_reparse_point"] = reparse if type(reparse) is bool else None
            local_drive = native.get("local_fixed_drive")
            checks["native_local_fixed_drive"] = (
                local_drive if type(local_drive) is bool else None
            )
            if local_drive is False:
                return reject("unsupported_native_drive")
            if regular is False:
                return reject("native_file_missing_or_not_regular")
            if native.get("is_filesystem") is not True or native.get("is_folder") is not False:
                return reject("unsupported_native_object")
            if reparse is True:
                return reject("native_reparse_point")
            if stable is False:
                return reject("native_snapshot_changed")
            if any(type(value) is not bool for value in (regular, stable, reparse, local_drive)):
                return reject("native_checks_incomplete")
        result["candidate_path"] = str(path)
        result["status"] = "provisional"
        result["rejection"] = (
            "identity_correspondence_unproven" if checks["active_view_associated"]
            else "active_view_unproven"
        )
        return result
    except (KeyError, TypeError, ValueError, AttributeError, OverflowError):
        return reject("malformed_evidence")
