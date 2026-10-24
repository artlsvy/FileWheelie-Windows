"""Diagnostic evidence only: UIA-to-Shell correspondence is deliberately unproven."""

from collections import Counter
from time import monotonic

from filewheel.core.diagnostic_checks import explorer_rejection
from filewheel.core.index_mapping import assess_index_mapping
from filewheel.core.models import MouseEvent, TargetResolution
from filewheel.platforms.windows.native import Native


def proven_target_from_evidence(event: MouseEvent, evidence: dict) -> None:
    """G2 experiment seam. Names, selection, enumeration order are never identity.

    Shell automation below enumerates candidates, not pointer targets. No path can
    be emitted until live experiments prove a correspondence with the visual item.
    """
    return


class ExplorerTargetResolver:
    """Own UIA on MTA; optional Shell STA exchanges only diagnostic DTOs."""

    def __init__(self, write_record, *, dry_run_mapping: bool = False):
        self._native = Native()
        import comtypes.client

        # Generated UIA interfaces provide vtable bindings; Shell uses IDispatch.
        uia = comtypes.client.GetModule("UIAutomationCore.dll")
        self._automation = comtypes.client.CreateObject(
            "{FF48DBA4-60EF-4201-AA87-54103EEF594E}", interface=uia.IUIAutomation
        )
        self._point_type = uia.tagPOINT
        self._selection_type = uia.IUIAutomationSelectionItemPattern
        self._write = write_record
        self.counts = Counter()
        self._dry_run_mapping = dry_run_mapping
        from filewheel.platforms.windows.shell_evidence import ShellEvidenceCollector

        self._shell_worker = None
        self._shell_collector = None
        if dry_run_mapping:
            from filewheel.platforms.windows.shell_worker import ShellStaWorker

            self._shell_worker = ShellStaWorker(lambda: ShellEvidenceCollector(native_probe=True))
        else:
            self._shell_collector = ShellEvidenceCollector()

    def close(self) -> None:
        # Release proxies before the owning worker calls CoUninitialize.
        self._automation = None
        if self._shell_collector is not None:
            self._shell_collector.close()
            self._shell_collector = None
        if self._shell_worker is not None:
            if not self._shell_worker.close():
                raise TimeoutError("Shell STA worker did not exit")
            self._shell_worker = None

    def resolve(self, event: MouseEvent) -> TargetResolution | None:
        start = monotonic()
        self.counts["resolver_calls"] += 1
        if event.injected:
            self.counts["injected"] += 1
            return None
        if start - event.timestamp > 0.5:
            self.counts["stale_event"] += 1
            return None
        n = self._native
        window = n.window_evidence(event.point)
        rejection = explorer_rejection(event, window)
        if rejection is not None:
            self.counts[rejection] += 1
            return None  # Do not log unrelated applications or Shell surfaces.
        self.counts["explorer_accepted"] += 1
        record = {
            "schema_version": 1, "sequence": event.sequence, "point": event.point,
            "timestamp_monotonic": event.timestamp, "window": window,
            "explorer_view": "unknown", "injected": event.injected,
            "resolved_path": None, "rejection": "mapping_unproven",
        }
        try:
            record["uia_ancestry"] = self._uia_evidence(event, window["pid"])
            if getattr(self, "_dry_run_mapping", False):
                record["shell_candidates"] = self._shell_evidence(
                    event.window_id, record["uia_ancestry"]
                )
                again = self._uia_evidence(event, window["pid"])
                # Selection is diagnostic only and may change under native Mouse3.
                def identity_snapshot(ancestry):
                    return [{k: v for k, v in row.items() if k != "selection_snapshot"}
                            for row in ancestry]

                record["snapshot_stable"] = (
                    identity_snapshot(again) == identity_snapshot(record["uia_ancestry"])
                )
                record["mapping"] = assess_index_mapping(record, now=monotonic())
                record["rejection"] = record["mapping"]["rejection"]
            else:
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
            record.pop("mapping", None)
            record["rejection"] = "window_changed"
        record["elapsed_ms"] = round((monotonic() - start) * 1000, 3)
        self._write(record)
        self.counts["records_written"] += 1
        self.counts[record["rejection"]] += 1
        return None

    def _selection_evidence(self, element) -> dict:
        """Snapshot only; never call Select/AddToSelection/RemoveFromSelection."""
        try:
            pattern = element.GetCurrentPattern(10010)  # UIA_SelectionItemPatternId
            if not pattern:
                return {"is_selected": None, "status": "unavailable"}
            selected = pattern.QueryInterface(self._selection_type).CurrentIsSelected
            return {"is_selected": bool(selected), "status": "observed"}
        except Exception:
            return {"is_selected": None, "status": "unavailable_or_error"}

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
            if element.CurrentControlType == 50007:  # UIA_ListItemControlTypeId
                ancestry[-1]["selection_snapshot"] = self._selection_evidence(element)
            # Stop before recording another application's ancestor information.
            if element.CurrentNativeWindowHandle == event.window_id:
                break
            element = walker.GetParentElement(element)
        return ancestry

    def _shell_evidence(self, hwnd: int, ancestry: list[dict] | None = None) -> dict:
        if self._shell_worker is not None:
            return self._shell_worker.collect(hwnd, ancestry)
        return self._shell_collector.collect(hwnd, ancestry)
