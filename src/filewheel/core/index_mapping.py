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


def _tab_window_index(windows: list, frame: int, ancestry: list, view: int, tab: int) -> int | None:
    """Choose only a unique native HWND match, with positive exclusion of peers.

    This is diagnostic association, not point-to-item identity. An unknown peer
    cannot be discarded merely because another registration appears to match.
    """
    shell_views = [index for index, node in enumerate(ancestry)
                   if node.get("class_name") == "DUIListView"
                   and node.get("control_type") == 50033]
    if len(shell_views) != 1 or not view < shell_views[0] < tab:
        return None
    view_hwnd = ancestry[shell_views[0]].get("native_hwnd")
    tab_hwnd = ancestry[tab]["native_hwnd"]
    items_hwnd = ancestry[view]["native_hwnd"]
    if not _integer(view_hwnd) or not view_hwnd:
        return None
    matched = []
    for position, entry in enumerate(windows):
        if (not isinstance(entry, dict) or type(entry.get("hwnd")) is not int
                or entry["hwnd"] != frame or entry.get("native_error") is not None):
            return None
        association = entry.get("active_view_association")
        if (
            not isinstance(association, dict)
            or association.get("method") != "active_shell_view_hwnd_chain"
            or association.get("error_type") is not None
            or association.get("tab_hwnd") != tab_hwnd
            or association.get("items_view_hwnd") != items_hwnd
            or not all(_integer(association.get(key)) and association[key]
                       for key in ("tab_hwnd", "items_view_hwnd", "browser_hwnd", "view_hwnd"))
        ):
            return None
        native_match = (association["browser_hwnd"] == tab_hwnd
                        and association["view_hwnd"] == view_hwnd)
        is_matched = association.get("status") == "matched" and native_match
        is_excluded = (
            association.get("status") == "unproven"
            and association["browser_hwnd"] != tab_hwnd
            and association["view_hwnd"] != view_hwnd
            and entry.get("native_view_candidate") is None
        )
        if not is_matched and not is_excluded:
            return None  # Unknown or partially matching relationships cannot be ignored.
        count, candidates = entry.get("item_count"), entry.get("candidates")
        if entry.get("lookup_mode") in ("targeted_index", "grouped_name"):
            # A positively excluded tab has no item enumeration or path lookup.
            if is_excluded:
                if count is not None or candidates != [] or entry.get("truncated") is not False:
                    return None
            elif (not _integer(count) or not isinstance(candidates, list)
                  or len(candidates) != 1 or entry.get("truncated") is not False):
                return None
            if is_matched:
                matched.append(position)
            continue
        if not _integer(count) or (is_matched and count > 32):
            return None
        # A peer is excluded by independent native HWNDs, not its candidate
        # listing. Permit only the collector's exact bounded prefix for it;
        # the chosen registration must still have its complete candidate set.
        expected_count = min(count, 32) if is_excluded else count
        if (entry.get("truncated") is not (count > 32)
                or not isinstance(candidates, list) or len(candidates) != expected_count
                or any(
                    not isinstance(candidate, dict)
                    or not isinstance(candidate.get("candidate_path"), str)
                    or not 1 <= len(candidate["candidate_path"]) <= 2048
                    or type(candidate.get("is_folder")) is not bool
                    or type(candidate.get("is_filesystem")) is not bool
                    for candidate in candidates
                )):
            return None
        indices = [candidate.get("enumeration_index") for candidate in candidates]
        if (any(not _integer(index) for index in indices)
                or sorted(indices) != list(range(expected_count))):
            return None
        if is_matched:
            matched.append(position)
    return matched[0] if len(matched) == 1 else None


def assess_index_mapping(record: dict, *, now: float) -> dict:
    """Return bounded JSON evidence for an index candidate, never a trusted path.

    ``candidate_path`` is copied only from Shell item lookup evidence. ``provisional``
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
            "complete_candidates": False, "candidate_lookup_complete": False, "index_in_range": False,
            "name_corroboration": None, "active_view_associated": False,
            "identity_correspondence": False, "filesystem_identity": False,
            "shell_window_count": None, "selected_shell_window_index": None,
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
        if not isinstance(automation_id, str) or len(automation_id) > 256:
            return reject("invalid_automation_index")
        # Grouped IDs may be local/compound. Preserve the opaque ID for UIA
        # snapshot consistency; only indexed lookups interpret canonical numbers.
        index = (int(automation_id) if re.fullmatch(r"0|[1-9][0-9]{0,9}", automation_id)
                 else None)
        result["candidate_index"] = index
        shell = record["shell_candidates"]
        if not isinstance(shell, dict) or shell.get("windows_truncated") is not False:
            return reject("truncated_shell_windows")
        windows = shell.get("matching_windows")
        if not isinstance(windows, list) or not 1 <= len(windows) <= 64:
            return reject("ambiguous_shell_windows")
        checks["shell_window_count"] = len(windows)
        if len(windows) == 1:
            selected_window = 0
        else:
            selected_window = _tab_window_index(windows, event.window_id, ancestry, view[0], tab[0])
            if selected_window is None:
                return reject("ambiguous_shell_windows")
        checks["selected_shell_window_index"] = selected_window
        shell_window = windows[selected_window]
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
        grouped = shell_window.get("lookup_mode") == "grouped_name"
        targeted = shell_window.get("lookup_mode") in ("targeted_index", "grouped_name")
        if grouped:
            result["candidate_index"] = None  # UIA group IDs are not flat Shell indices.
        if index is None and not grouped:
            return reject("invalid_automation_index")
        if shell_window.get("lookup_mode") not in (None, "targeted_index", "grouped_name"):
            return reject("invalid_lookup_mode")
        if targeted:
            if (_tab_window_index(windows, event.window_id, ancestry, view[0], tab[0])
                    != selected_window or not checks["active_view_associated"]):
                return reject("active_view_mismatch")
            if (shell_window.get("truncated") is not False or not _integer(count)
                    or not isinstance(candidates, list) or len(candidates) != 1
                    or shell_window.get("shell_snapshot_stable") is not True):
                return reject("incomplete_targeted_lookup")
            native = shell_window.get("native_view_candidate")
            if (not isinstance(native, dict) or not _integer(native.get("view_item_count"))
                    or native["view_item_count"] != count):
                return reject("native_count_mismatch")
            candidate = candidates[0]
            if not isinstance(candidate, dict):
                return reject("malformed_evidence")
            if grouped and count < 1:
                return reject("invalid_candidate_index")
            if grouped:
                if candidate.get("lookup_name") != item.get("name") or native.get("index") is not None:
                    return reject("grouped_name_mismatch")
            elif (type(candidate.get("enumeration_index")) is not int
                  or candidate["enumeration_index"] != index):
                return reject("inconsistent_candidate_indices")
        else:
            if (
                shell_window.get("truncated") is not False or not _integer(count)
                or not isinstance(candidates, list) or len(candidates) != count or count > 32
            ):
                return reject("truncated_candidates")
            indices = [candidate.get("enumeration_index") for candidate in candidates]
            if any(not _integer(value) for value in indices) or sorted(indices) != list(range(count)):
                return reject("inconsistent_candidate_indices")
            checks["complete_candidates"] = True
            candidate = next((candidate for candidate in candidates
                              if candidate["enumeration_index"] == index), None)
        if not grouped:
            if not 0 <= index < count:
                return reject("invalid_candidate_index")
            checks["index_in_range"] = True
        checks["candidate_lookup_complete"] = True
        if candidate.get("is_folder") is not False or candidate.get("is_filesystem") is not True:
            return reject("unsupported_shell_object")
        path = _local_file_path(candidate.get("candidate_path"))
        if path is None:
            return reject("unsupported_candidate_path")
        if grouped:
            context = shell_window.get("grouped_context")
            if not isinstance(context, dict) or context.get("method") != "active_folder_exact_name":
                return reject("grouped_context_incomplete")
            parent = _local_file_path(context.get("folder_path"))
            anchor = _local_file_path(context.get("native_anchor_path"))
            if (parent is None or anchor is None or anchor.parent != parent or path.parent != parent
                    or _local_file_path(context.get("native_parent_path")) != parent
                    or context.get("native_anchor_is_filesystem") is not True):
                return reject("grouped_parent_mismatch")
            key = context.get("grouping_key")
            if key == "uia_group":
                groups = [node for node in ancestry[item_index + 1:view[0]]
                          if node.get("control_type") == 50026]
                if not groups or not all(_contains(node.get("bounds"), point) for node in groups):
                    return reject("grouped_context_incomplete")
            elif (not isinstance(key, str)
                  or not re.fullmatch(r"\{[0-9A-Fa-f]{8}(?:-[0-9A-Fa-f]{4}){3}-[0-9A-Fa-f]{12}\}:[0-9]{1,10}", key)
                  or key.lower().startswith("{00000000-0000-0000-0000-000000000000}")):
                return reject("grouped_context_incomplete")
            checks["native_group_parent_match"] = True
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
        if targeted:
            # No global name evidence: hidden/shortened labels must fail closed.
            if name != path.name:
                return reject("ambiguous_display_name")
            ambiguity = shell_window.get("name_ambiguity")
            if (not isinstance(ambiguity, dict)
                    or ambiguity.get("method") != "literal_name_collision_probe"
                    or type(ambiguity.get("query_count")) is not int
                    or ambiguity["query_count"] not in (2, 3)
                    or ambiguity.get("name") != name
                    or _local_file_path(ambiguity.get("candidate_path")) != path):
                return reject("name_ambiguity_unproven")
            if ambiguity.get("status") != "unique":
                return reject("ambiguous_display_name" if ambiguity.get("status") == "ambiguous"
                              else "name_ambiguity_unproven")
        else:
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
        if len(windows) > 1 and native is None:
            return reject("native_checks_incomplete")
        checks["native_index_path_match"] = None
        checks["native_regular_file"] = None
        checks["native_snapshot_stable"] = None
        checks["native_reparse_point"] = None
        checks["native_local_fixed_drive"] = None
        if native is not None:
            if not isinstance(native, dict):
                return reject("malformed_native_evidence")
            native_path = _local_file_path(native.get("candidate_path"))
            matches = native_path == path and (
                native.get("index") is None if grouped
                else _integer(native.get("index")) and native["index"] == index
            )
            checks["native_item_path_match"] = matches
            checks["native_index_path_match"] = None if grouped else matches
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
