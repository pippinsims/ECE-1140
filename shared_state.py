"""
shared_state.py  –  Thread-safe bridge between CTC (PyQt6) and Wayside (tkinter)
==================================================================================

Both GUIs run in separate threads with separate event loops.
This module provides the ONLY shared data structure between them.

Data flows (every 100 ms)
--------------------------

CTC -> Wayside
  push_ctc_data()        block occupancy, commanded speed, authority
  push_ctc_overrides()   manual switch/signal overrides set in CTC maintenance mode

Wayside -> CTC
  push_wayside_outputs() computed signals, switch positions, crossing states
  push_switch_events()   switch-state-change events for CTC info-box messages

Version counters on every channel mean poll_*() returns None when nothing
has changed, keeping the 100 ms loops cheap.
"""

import threading
from typing import Dict, Any, List, Optional


LineData  = Dict[int, Dict[str, Any]]
WOutputs  = Dict[str, Any]
Overrides = Dict[str, Any]


class SharedState:
    """Single shared-state object. Create one instance and pass to both windows."""

    def __init__(self):
        self._lock = threading.Lock()

        # CTC -> Wayside: block data
        self._ctc_data: Dict[str, LineData] = {"Green": {}, "Red": {}}
        self._ctc_version: int = 0
        self._ctc_seen_by_wayside: int = -1

        # CTC -> Wayside: maintenance overrides
        # {line: {"switch_overrides": {sw_id: "normal"|"reverse"},
        #         "signal_overrides": {block_num: "green"|"yellow"|"red"}}}
        self._ctc_overrides: Dict[str, Overrides] = {
            "Green": {"switch_overrides": {}, "signal_overrides": {}},
            "Red":   {"switch_overrides": {}, "signal_overrides": {}},
        }
        self._ctc_override_version: int = 0
        self._ctc_override_seen_by_wayside: int = -1

        # Wayside -> CTC: computed outputs
        self._wayside_outputs: Dict[str, WOutputs] = {"Green": {}, "Red": {}}
        self._wayside_version: int = 0
        self._wayside_seen_by_ctc: int = -1

        # CTC -> Wayside: maintenance state per line
        self._ctc_maintenance: Dict[str, bool] = {"Green": False, "Red": False}
        self._ctc_maintenance_version: int = 0
        self._ctc_maintenance_seen_by_wayside: int = -1

        # Wayside -> CTC: switch-change event queue
        # Each entry: {"line": str, "sw_id": str, "old": str, "new": str}
        self._switch_events: List[Dict[str, str]] = []
        self._switch_event_version: int = 0
        self._switch_event_seen_by_ctc: int = -1

    # =========================================================================
    # CTC -> Wayside: block data
    # =========================================================================

    def push_ctc_data(self, line: str, block_data: LineData) -> None:
        """CTC pushes current block occupancy / speed / authority.
        block_data: {block_num: {"occupied": bool, "cmd_speed": float (km/h),
                                  "authority": float (km)}}
        """
        with self._lock:
            self._ctc_data[line] = dict(block_data)
            self._ctc_version += 1

    def poll_ctc_data(self) -> Optional[Dict[str, LineData]]:
        """Wayside polls every 100ms. Returns {line: block_data} if new, else None."""
        with self._lock:
            if self._ctc_version == self._ctc_seen_by_wayside:
                return None
            self._ctc_seen_by_wayside = self._ctc_version
            return {line: dict(data) for line, data in self._ctc_data.items()}

    # =========================================================================
    # CTC -> Wayside: maintenance overrides
    # =========================================================================

    def push_ctc_switch_override(self, line: str, sw_id: str, position: str) -> None:
        """CTC calls this when user changes a switch in maintenance mode.
        position: "normal" | "reverse"
        """
        with self._lock:
            self._ctc_overrides[line]["switch_overrides"][sw_id] = position
            self._ctc_override_version += 1

    def push_ctc_signal_override(self, line: str, block: int, color: str) -> None:
        """CTC calls this when user changes a signal in maintenance mode.
        color: "green" | "yellow" | "red"
        """
        with self._lock:
            self._ctc_overrides[line]["signal_overrides"][block] = color
            self._ctc_override_version += 1

    def clear_ctc_override(self, line: str, sw_id: str = None, block: int = None) -> None:
        """CTC calls this when maintenance is turned OFF.
        Pass neither sw_id nor block to clear ALL overrides on the line.
        """
        with self._lock:
            if sw_id is None and block is None:
                self._ctc_overrides[line] = {
                    "switch_overrides": {},
                    "signal_overrides": {},
                }
            elif sw_id is not None:
                self._ctc_overrides[line]["switch_overrides"].pop(sw_id, None)
            else:
                self._ctc_overrides[line]["signal_overrides"].pop(block, None)
            self._ctc_override_version += 1

    def poll_ctc_overrides(self) -> Optional[Dict[str, Overrides]]:
        """Wayside polls every 100ms. Returns override dict if new, else None."""
        with self._lock:
            if self._ctc_override_version == self._ctc_override_seen_by_wayside:
                return None
            self._ctc_override_seen_by_wayside = self._ctc_override_version
            return {
                line: {
                    "switch_overrides": dict(ov["switch_overrides"]),
                    "signal_overrides": dict(ov["signal_overrides"]),
                }
                for line, ov in self._ctc_overrides.items()
            }

    # =========================================================================
    # Wayside -> CTC: computed outputs
    # =========================================================================

    def push_wayside_outputs(self, line: str, outputs: WOutputs) -> None:
        """Wayside pushes computed signals, switch positions, crossing states.
        outputs: {"signals": {blk: color|None},
                  "switches": {sw_id: "normal"|"reverse"},
                  "crossings": {blk: "active"|"inactive"}}
        """
        with self._lock:
            self._wayside_outputs[line] = dict(outputs)
            self._wayside_version += 1

    def poll_wayside_outputs(self) -> Optional[Dict[str, WOutputs]]:
        """CTC polls every 100ms. Returns {line: outputs} if new, else None."""
        with self._lock:
            if self._wayside_version == self._wayside_seen_by_ctc:
                return None
            self._wayside_seen_by_ctc = self._wayside_version
            return {line: dict(data) for line, data in self._wayside_outputs.items()}

    # =========================================================================
    # Wayside -> CTC: switch-change event queue
    # =========================================================================

    def push_switch_event(self, line: str, sw_id: str,
                           old_pos: str, new_pos: str) -> None:
        """Wayside calls this whenever a switch changes state (computed or manual).
        Events are queued; CTC drains them all on the next poll.
        """
        with self._lock:
            self._switch_events.append({
                "line":  line,
                "sw_id": sw_id,
                "old":   old_pos,
                "new":   new_pos,
            })
            self._switch_event_version += 1

    def poll_switch_events(self) -> Optional[List[Dict[str, str]]]:
        """CTC polls every 100ms. Returns list of change dicts and clears queue, else None."""
        with self._lock:
            if self._switch_event_version == self._switch_event_seen_by_ctc:
                return None
            self._switch_event_seen_by_ctc = self._switch_event_version
            events = list(self._switch_events)
            self._switch_events.clear()
            return events

    # =========================================================================
    # Convenience
    # =========================================================================


    # =========================================================================
    # CTC -> Wayside: maintenance state
    # =========================================================================

    def push_ctc_maintenance(self, line: str, active: bool) -> None:
        """CTC calls this when maintenance is toggled ON or OFF for a block on a line.
        active=True means at least one block on that line is in CTC maintenance mode.
        """
        with self._lock:
            self._ctc_maintenance[line] = active
            self._ctc_maintenance_version += 1

    def poll_ctc_maintenance(self) -> "Optional[Dict[str, bool]]":
        """Wayside polls every 100ms.
        Returns {line: bool} if state changed since last poll, else None."""
        with self._lock:
            if self._ctc_maintenance_version == self._ctc_maintenance_seen_by_wayside:
                return None
            self._ctc_maintenance_seen_by_wayside = self._ctc_maintenance_version
            return dict(self._ctc_maintenance)

    def snapshot(self) -> Dict[str, Any]:
        """Full snapshot for debugging."""
        with self._lock:
            return {
                "ctc_data":        {l: dict(d) for l, d in self._ctc_data.items()},
                "ctc_overrides":   {l: dict(o) for l, o in self._ctc_overrides.items()},
                "ctc_maintenance":  dict(self._ctc_maintenance),
                "wayside_outputs": {l: dict(d) for l, d in self._wayside_outputs.items()},
                "switch_events":   list(self._switch_events),
            }

    def get_ctc_block_data(self, line: str) -> LineData:
        """Latest CTC block payload for ``line`` (copy). Does not affect wayside polling."""
        with self._lock:
            return dict(self._ctc_data.get(line, {}))

    def get_wayside_outputs(self, line: str) -> WOutputs:
        """Latest wayside outputs for ``line`` (copy). Does not affect CTC polling."""
        with self._lock:
            return dict(self._wayside_outputs.get(line, {}))
