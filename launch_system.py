"""
launch_system.py — single entry point for the full integrated stack
===================================================================
Starts in one process (one QApplication):

  • Central Traffic Control (PyQt6)
  • Train Track Model + Train Model UIs (PyQt6)
  • Train Controller backend + Train Controller UI subprocess (socket IPC)

Starts in a daemon thread:

  • Wayside Dashboard (tkinter), wired via SharedState like ``launcher.py``

Run:

    py -3 launch_system.py

Windows are tiled so the CTC is not covered by the track or train model UIs.
The Default Green ``T-01``…``T-10`` simulation is hidden on the CTC diagram and
wayside so only the three physical trains (``Train-1``…``Train-3``) match the
train controller / train models. All three start at the **Green yard** (block 57).
Use **manual dispatch** from the yard; only **one train at a time** receives
movement (train 2 after train 1 has left the yard, then train 3). Use the
**Train** and **Destination** columns for progress. Physics uses the CTC speed
slider scale (default 10 = 0.1 s/tick).
"""

from __future__ import annotations

import atexit
import copy
import importlib
import json
import os
import socket
import subprocess
import sys
import threading

from PyQt6.QtCore import QTimer
from PyQt6.QtGui import QColor, QGuiApplication, QPalette
from PyQt6.QtWidgets import QApplication

from ctc_ui import GREEN_LINE_BLOCKS, MainWindow
from shared_state import SharedState
from train_backend import TrainSystem, kmhToMph, samplePeriodSec
from train_frontend_main import TrainControlUI

import track_model

NUM_TRAINS = 3
# Green Line yard (matches ``GREEN_STATION_TO_START["Yard"]`` in ``ctc_ui``).
GREEN_YARD_BLOCK_NUM = 57

def _green_section_for_block(bn: int) -> str:
    for sec, blks in GREEN_LINE_BLOCKS.items():
        if any(b[0] == bn for b in blks):
            return sec
    return "A"

def _motion_allowed(ctc_win: MainWindow) -> bool:
    """True when the user has started manual dispatch or the default Green sim."""
    ext = getattr(ctc_win, "_external_trains", {}) or {}
    if any(str(k).startswith("Manual-") for k in ext): return True
    if any(str(k).startswith("Train-") for k in ext): return True
    if getattr(ctc_win, "_sim_running", False):
        if getattr(ctc_win, "_sim_schedule", None) == "Default Green":
            return True
    return False

def _tile_windows(ctc_win: MainWindow, track_window, model_uis: list) -> None:
    """Avoid stacking every window at (0,0), which hides the CTC and train UIs."""
    screen = QGuiApplication.primaryScreen()
    if screen is None:
        ctc_win.raise_()
        ctc_win.activateWindow()
        return
    avail = screen.availableGeometry()
    ctc_win.resize(min(1400, avail.width() - 80), min(900, avail.height() - 80))
    ctc_win.move(avail.left() + 24, avail.top() + 24)
    ctc_win.show()
    fg = ctc_win.frameGeometry()
    tw = track_window.frameGeometry().width() or 720
    tx = min(fg.right() + 12, avail.right() - tw - 16)
    track_window.move(max(avail.left(), tx), fg.top())
    track_window.show()
    base_y = min(fg.bottom() + 12, avail.bottom() - 260)
    for i, ui in enumerate(model_uis):
        ui.move(fg.left() + 40 + i * 36, base_y + i * 32)
        ui.show()
    ctc_win.raise_()
    ctc_win.activateWindow()


def _place_model_ui(ctc_win: MainWindow, ui, idx: int) -> None:
    """Place a newly spawned Train Model UI near the CTC."""
    try:
        fg = ctc_win.frameGeometry()
        screen = QGuiApplication.primaryScreen()
        if screen is None:
            ui.move(fg.left() + 40 + idx * 36, fg.bottom() + 12 + idx * 32)
        else:
            avail = screen.availableGeometry()
            base_y = min(fg.bottom() + 12, avail.bottom() - 260)
            ui.move(fg.left() + 40 + idx * 36, base_y + idx * 32)
    except Exception:
        pass
    ui.show()


def _run_wayside(state: SharedState) -> None:
    from wayside_dashboard import WaysideDashboard

    app = WaysideDashboard(shared_state=state)
    app.mainloop()


def _lookup_block_data(green_ctc: dict, bn: int):
    return green_ctc.get(bn) or green_ctc.get(str(bn))


def _lookup_signal(signals: dict, bn: int):
    return signals.get(bn) if signals.get(bn) is not None else signals.get(str(bn))


def _apply_signal(cmd_kmh: float, auth_km: float, sig) -> tuple[float, float]:
    if sig is None:
        return cmd_kmh, auth_km
    s = str(sig).lower()
    if s == "red":
        return 0.0, 0.0
    if s == "yellow":
        return max(0.0, cmd_kmh * 0.5), auth_km
    return cmd_kmh, auth_km


def _sync_track_model_switches(track_map, switch_states: dict, switch_defs: dict) -> None:
    """
    Mirror wayside/track-controller switch states into the Track Model.

    switch_states: {sw_id: "normal"|"reverse"}
    switch_defs: wayside_controller.GREEN_SWITCHES/RED_SWITCHES dict with {"host": block_num, ...}
    """
    if not switch_states or not switch_defs:
        return
    # Avoid console spam: only print when a state actually changes.
    if not hasattr(track_map, "_integrated_last_switch_state"):
        try:
            track_map._integrated_last_switch_state = {}
        except Exception:
            pass
    last_state = getattr(track_map, "_integrated_last_switch_state", {}) or {}

    def _parse_int(x):
        try:
            return int(x)
        except Exception:
            return None

    for sw_id, pos in switch_states.items():
        sw = switch_defs.get(sw_id)
        if not sw:
            continue
        try:
            host_bn = int(sw.get("host", -1))
        except Exception:
            continue
        if host_bn <= 0:
            continue
        host_b = track_map.block(host_bn)
        if host_b is None or not hasattr(host_b, "switch_state"):
            continue
        # Choose the Track Model's switch_state based on which option matches the
        # desired next-block from the wayside (do not assume normal=0/reverse=1).
        try:
            desired_next = sw.get("reverse")[0] if str(pos).lower() == "reverse" else sw.get("normal")[0]
            desired_next_i = _parse_int(desired_next)
            if desired_next_i is None:
                continue
            opt1 = getattr(host_b, "first_switch_option", lambda: ())()
            opt2 = getattr(host_b, "second_switch_option", lambda: ())()
            opt1_i = [_parse_int(v) for v in opt1]
            opt2_i = [_parse_int(v) for v in opt2]
            # Identify the physical switch by its option-set so we can mirror
            # state onto every Track Model "switch block" that represents it.
            host_opt_set = frozenset([x for x in (opt1_i + opt2_i) if x is not None])
            if desired_next_i in opt1_i:
                new_state = 0
            elif desired_next_i in opt2_i:
                new_state = 1
            else:
                # Fallback: keep existing state
                continue

            # Collect all affected Track Model blocks (host + any mirror blocks).
            affected: list = [host_b]

            # Mirror onto any other switch blocks that share the same options.
            try:
                for b in getattr(track_map, "blocks", []) or []:
                    if b is host_b:
                        continue
                    if not hasattr(b, "switch_state"):
                        continue
                    try:
                        b_opt1 = getattr(b, "first_switch_option", lambda: ())()
                        b_opt2 = getattr(b, "second_switch_option", lambda: ())()
                        b_opt1_i = [_parse_int(v) for v in b_opt1]
                        b_opt2_i = [_parse_int(v) for v in b_opt2]
                        b_opt_set = frozenset([x for x in (b_opt1_i + b_opt2_i) if x is not None])
                    except Exception:
                        continue
                    if b_opt_set == host_opt_set:
                        affected.append(b)
            except Exception:
                pass

            # Apply + print changes.
            changed_blocks: list[int] = []
            for b in affected:
                try:
                    bn = int(getattr(b, "num", -1))
                except Exception:
                    bn = -1
                prev = last_state.get(bn)
                if prev != new_state:
                    try:
                        b.switch_state = new_state
                    except Exception:
                        pass
                    last_state[bn] = new_state
                    if bn >= 0:
                        changed_blocks.append(bn)

            if changed_blocks:
                try:
                    print(
                        f"[WS→TM] {sw_id} pos={str(pos).lower()} host={host_bn} "
                        f"desired_next={desired_next_i} switch_state={new_state} -> blocks={sorted(changed_blocks)}"
                    )
                except Exception:
                    pass
        except Exception:
            pass


def main() -> None:
    state = SharedState()
    threading.Thread(
        target=_run_wayside,
        args=(state,),
        daemon=True,
        name="WaysideThread",
    ).start()

    app = QApplication(sys.argv)
    app.setApplicationName("Integrated Train System")
    app.setStyle("Fusion")
    light = QPalette()
    light.setColor(QPalette.ColorRole.Window, QColor(255, 255, 255))
    light.setColor(QPalette.ColorRole.WindowText, QColor(0, 0, 0))
    light.setColor(QPalette.ColorRole.Base, QColor(240, 240, 240))
    light.setColor(QPalette.ColorRole.AlternateBase, QColor(225, 225, 225))
    light.setColor(QPalette.ColorRole.Text, QColor(0, 0, 0))
    light.setColor(QPalette.ColorRole.ButtonText, QColor(0, 0, 0))
    light.setColor(QPalette.ColorRole.BrightText, QColor(0, 0, 0))
    light.setColor(QPalette.ColorRole.Button, QColor(225, 225, 225))
    light.setColor(QPalette.ColorRole.Highlight, QColor(74, 111, 165))
    light.setColor(QPalette.ColorRole.HighlightedText, QColor(255, 255, 255))
    app.setPalette(light)

    ctc_win = MainWindow(shared_state=state)
    # Only the three physical trains appear on the CTC / wayside (not T-01…T-10).
    ctc_win._integrated_hide_schedule_trains = True
    ctc_win._integrated_sim_clock_from_launcher = True
    # One simulation tick in ``on_tick`` so inject → poll order is guaranteed.
    if hasattr(ctc_win, "_train_timer"):
        ctc_win._train_timer.stop()

    track_window = track_model.make_widget()
    track_map = track_window.tkm

    #do not create trains at launch. Spawn only when CTC creates a Manual-* dispatch.
    track_map.trains = []

    yard_block = track_map.block(GREEN_YARD_BLOCK_NUM)

    train_models: dict[int, TrainSystem] = {}
    model_uis: dict[int, TrainControlUI] = {}
    dispatched: list[str] = []
    # manually_dispatched_ids: dict[str, int] = {}

    _tile_windows(ctc_win, track_window, [])

    server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server.bind(("127.0.0.1", 0))
    server.listen(1)
    server.setblocking(False)
    port = server.getsockname()[1]

    env = os.environ.copy()
    env["TRAIN_IPC_HOST"] = "127.0.0.1"
    env["TRAIN_IPC_PORT"] = str(port)

    controller_proc = None
    controller_script = os.path.join(
        os.path.dirname(os.path.abspath(__file__)), "TrainController.py"
    )
    if os.path.exists(controller_script):
        controller_proc = subprocess.Popen([sys.executable, controller_script], env=env)

    def _cleanup() -> None:
        if controller_proc is not None:
            try:
                controller_proc.terminate()
            except Exception:
                pass

    atexit.register(_cleanup)

    conn = None
    recv_buf = ""
    last_authority_block: dict[int, tuple] = {}
    # Keep train motion smooth across block boundaries even when CTC snapshot doesn't contain the next block yet.
    _last_cmd_kmh: dict[int, float] = {}
    _last_auth_km: dict[int, float] = {}
    # Station dwell + destination hold
    _last_block_seen: dict[int, int] = {}
    _dwell_remaining_sec: dict[int, float] = {}
    _dest_hold_on: set[int] = set()

    def on_tick() -> None:
        nonlocal conn, recv_buf

        try:
            slider = float(ctc_win.speed_slider.value())
        except Exception:
            slider = 10.0
        slider = max(1.0, min(100.0, slider))
        # Match CTC schedule scaling: schedule adds ``slider`` sim-seconds per tick;
        # physics uses the same factor relative to nominal slider=10 → dt=0.1 s.
        physics_dt = samplePeriodSec * (slider / 10.0)

        if getattr(ctc_win, "_sim_running", False):
            try:
                ctc_win._sim_time_sec += slider
            except Exception:
                pass

        #spawn train_models on CTC manual dispatch (max NUM_TRAINS)
        ext = copy.deepcopy(ctc_win._external_trains)
        for new_dispatch in [k for k in list(ext.keys()) if k.startswith("Manual-")]:
            #cannot dispatch same train twice, or dispatch too many trains
            if new_dispatch in dispatched or len(dispatched) >= NUM_TRAINS: continue
            
            print("DISPATCHING NEW TRAIN")
            # Apply switch states ONCE at dispatch time (before the train moves).
            # Do not rely on the wayside GUI thread timing to publish outputs in time.
            try:
                from wayside_controller import (
                    compute_wayside_outputs,
                    GREEN_BLOCK_LENGTHS,
                    GREEN_SWITCHES as _WS_GREEN_SWITCHES,
                    GREEN_CROSSINGS,
                )
                # Build a one-shot CTC-style payload with occupancy for the new train's origin.
                info:dict = ext.get(new_dispatch, {})
                b_id = int(info.get("block", yard_block.num))
                green_payload: dict[int, dict] = {}
                for _sec, blks in (GREEN_LINE_BLOCKS or {}).items():
                    for inf0 in blks:
                        try:
                            bn0 = int(inf0[0])
                        except Exception:
                            continue
                        try:
                            cmd0 = float(inf0[3])
                        except Exception:
                            cmd0 = 0.0
                        try:
                            auth_km0 = float(inf0[1]) / 1000.0
                        except Exception:
                            auth_km0 = 0.0
                        green_payload[bn0] = {
                            "occupied": (bn0 == b_id),
                            "cmd_speed": cmd0,
                            "authority": auth_km0,
                        }
                ws_out = compute_wayside_outputs(
                    green_payload,
                    GREEN_BLOCK_LENGTHS,
                    _WS_GREEN_SWITCHES,
                    GREEN_CROSSINGS,
                    signal_blocks=None,
                )
                _sync_track_model_switches(track_map, ws_out.get("switches", {}), _WS_GREEN_SWITCHES)
            except Exception:
                pass

            new_t_id = len(dispatched) + 1

            #instantiate train model
            system = TrainSystem()
            train_models[new_t_id] = system
            ui = TrainControlUI(trainModel=system.model)
            ui.setWindowTitle(f"Train Model - Train {new_t_id}")
            model_uis[new_t_id] = ui
            _place_model_ui(ctc_win, ui, new_t_id - 1)

            #spawn at the requested origin block on CTC (default is yard)
            info:dict = ext.pop(new_dispatch)
            b_id = int(info.get("block", yard_block.num))

            # track_model.Train placed at spawnpoint, will display on next tick
            t = track_model.Train(new_t_id, track_map)
            t.block = track_map.block(b_id)
            track_map.trains.append(t)

            # Push occupancy/cmd/auth snapshot to SharedState ONCE per dispatch so
            # the wayside computes and publishes switch states for the new train.
            try:
                occupied_blocks = set()
                for tr0 in getattr(track_map, "trains", []) or []:
                    try:
                        occupied_blocks.add(int(tr0.block.num))
                    except Exception:
                        pass

                green_payload: dict[int, dict] = {}
                for _sec, blks in (GREEN_LINE_BLOCKS or {}).items():
                    for inf0 in blks:
                        try:
                            bn0 = int(inf0[0])
                        except Exception:
                            continue
                        try:
                            cmd0 = float(inf0[3])
                        except Exception:
                            cmd0 = 0.0
                        try:
                            auth_km0 = float(inf0[1]) / 1000.0
                        except Exception:
                            auth_km0 = 0.0
                        green_payload[bn0] = {
                            "occupied": (bn0 in occupied_blocks),
                            "cmd_speed": cmd0,
                            "authority": auth_km0,
                        }
                state.push_ctc_data("Green", green_payload)
                state.push_ctc_data("Red", {})
            except Exception:
                pass

            # Move Manual-* to Train-*,
            ext[f"Train-{new_t_id}"] = {
                **(ext.get(f"Train-{new_t_id}", {}) or {}),
                "line"      : info.get("line", "Green Line"),
                "section"   : info.get("section", _green_section_for_block(b_id)),
                "block"     : b_id,
                "origin"    : info.get("origin"),
                "dest"      : info.get("dest"),
                "dest_block": info.get("dest_block"),
                "arrival"   : info.get("arrival"),
            }
        ctc_win._external_trains = ext

        # Update physical Train-* positions in the CTC table.
        for i, tr in enumerate(track_map.trains):
            tid = f"Train-{i + 1}"
            bn = tr.block.num
            sec = _green_section_for_block(bn)
            prev = ctc_win._external_trains.get(tid, {})
            ctc_win._external_trains[tid] = {
                **prev,
                "line": "Green Line",
                "section": sec,
                "block": bn,
            }
        ctc_win._poll_active_trains()

        # Note: SharedState inputs for the wayside (occupancy/cmd/auth) are pushed
        # only on DISPATCH (see dispatch loop above), not every tick as trains move.

        green_ctc = state.get_ctc_block_data("Green")
        green_ws = state.get_wayside_outputs("Green")
        ws_blocks = (green_ws or {}).get("blocks", {}) if isinstance(green_ws, dict) else {}

        # Keep Track Model per-block cmd/auth fields up-to-date for the block-info textbox.
        # Prefer track-controller channel; fall back to CTC snapshot.
        try:
            src = ws_blocks if ws_blocks else green_ctc
            for b in getattr(track_map, "blocks", []) or []:
                try:
                    bn = int(getattr(b, "num", 0))
                except Exception:
                    continue
                bd = _lookup_block_data(src, bn)
                if not bd:
                    continue
                try:
                    b.speed = float(bd.get("cmd_speed", getattr(b, "speed", 0.0) or 0.0))
                except Exception:
                    pass
                try:
                    b.authority = float(bd.get("authority", getattr(b, "authority", 0.0) or 0.0))
                except Exception:
                    pass
        except Exception:
            pass
        # Keep Track Model switches aligned with wayside outputs continuously.
        try:
            from wayside_controller import GREEN_SWITCHES as _WS_GREEN_SWITCHES

            ws_switches = (green_ws or {}).get("switches", {}) if isinstance(green_ws, dict) else {}
            _sync_track_model_switches(track_map, ws_switches, _WS_GREEN_SWITCHES)
            for it in getattr(track_map, "items", []) or []:
                try:
                    it.update()
                except Exception:
                    pass
        except Exception:
            pass
        signals = (green_ws or {}).get("signals", {})
        allow_motion = _motion_allowed(ctc_win)

        for ti, tr in enumerate(track_map.trains, start=1):
            bn = tr.block.num
            # Prefer the track-controller (wayside) channel for cmd/auth.
            bd = _lookup_block_data(ws_blocks, bn) or _lookup_block_data(green_ctc, bn)
            sig = _lookup_signal(signals, bn)
            if allow_motion and bd:
                cmd = float(bd.get("cmd_speed", 0.0))
                auth = float(bd.get("authority", 0.0))
                # CTC often omits or zeros cmd for a block until the next refresh; keep
                # motion smooth when we still have authority (real stops use auth=0 or signals).
                if cmd <= 0.0 and auth > 0.0:
                    cmd = float(_last_cmd_kmh.get(ti, 0.0))
                if auth <= 0.0 and cmd > 0.0:
                    la = float(_last_auth_km.get(ti, 0.0))
                    if la > 0.0:
                        auth = la
                try:
                    lim = float(getattr(tr.block, "speed_limit", 0.0) or 0.0)
                    if lim > 0.0:
                        cmd = min(cmd, lim)
                except Exception:
                    pass
            elif allow_motion:
                # Carry forward last commanded speed/authority instead of dropping to 0
                # at each new block, and clamp to the local speed limit.
                cmd = float(_last_cmd_kmh.get(ti, 0.0))
                auth = float(_last_auth_km.get(ti, 0.0))
                try:
                    lim = float(getattr(tr.block, "speed_limit", 0.0) or 0.0)
                    if lim > 0.0:
                        cmd = min(cmd, lim)
                except Exception:
                    pass
            else:
                cmd = 0.0
                auth = 0.0
            cmd, auth = _apply_signal(cmd, auth, sig)
            tr.integrated_cmd_kmh = cmd
            tr.integrated_auth_km = auth
            _last_cmd_kmh[ti] = float(cmd)
            _last_auth_km[ti] = float(auth)

        for train_id, system in train_models.items():
            idx = train_id - 1
            m = system.model
            td = track_map.get_train_track_data(idx)
            if td:
                cur_block = td.get("block_num", -1)
                block_authority = td["authority_km"]
                m.commandedSpeedKmh = td["commanded_speed_kmh"]
                prev = last_authority_block.get(train_id)
                if (
                    prev is None
                    or prev[0] != cur_block
                    or prev[1] != block_authority
                ):
                    # Wayside authority often changes discretely per block; a downward jump
                    # makes the controller think authority vanished and zeros traction for a tick.
                    # On block change: never shrink commanded authority below what the model
                    # already holds (unless the track explicitly commands 0).
                    try:
                        inc_m = float(block_authority)
                    except Exception:
                        inc_m = 0.0
                    if prev is not None and prev[0] != cur_block:
                        try:
                            cur_m = float(m.commandedAuthorityKm)
                        except Exception:
                            cur_m = 0.0
                        if inc_m <= 0.0:
                            m.commandedAuthorityKm = inc_m
                        else:
                            m.commandedAuthorityKm = max(cur_m, inc_m)
                    else:
                        m.commandedAuthorityKm = block_authority
                    last_authority_block[train_id] = (cur_block, block_authority)
                m.trackGradePercent = td["track_grade_percent"]
                m.speedLimitKmh = td["speed_limit_kmh"]
                m.beaconData = td["beacon_data"]
                m.isRailBroken = td["rail_broken"]
                m.isTrackCircuitFailed = td["circuit_failed"]
                m.isTrackPowerLost = td["power_lost"]
                m.boardingPassengerCount = td["boarding_passengers"]

        if conn is None:
            try:
                conn, _ = server.accept()
                conn.setblocking(False)
            except BlockingIOError:
                pass
            except Exception:
                pass

        if conn is not None:
            while True:
                try:
                    data = conn.recv(4096)
                    if not data:
                        conn.close()
                        conn = None
                        break
                    recv_buf += data.decode("utf-8", errors="ignore")
                except BlockingIOError:
                    break
                except Exception:
                    try:
                        conn.close()
                    except Exception:
                        pass
                    conn = None
                    break

            while conn is not None and "\n" in recv_buf:
                line, recv_buf = recv_buf.split("\n", 1)
                if not line.strip():
                    continue
                try:
                    msg = json.loads(line)
                except Exception:
                    continue
                if msg.get("type") != "controller":
                    continue
                tid = int(msg.get("train_id", 1))
                sys_obj = train_models.get(tid)
                if sys_obj is None:
                    continue
                c = sys_obj.controller
                for k, cast in [
                    ("commanded_speed", float),
                    ("speed_limit", float),
                    ("authority", float),
                    ("kp", float),
                    ("ki", float),
                    ("manual_speed_target", float),
                ]:
                    if k in msg:
                        try:
                            setattr(c, k, cast(msg[k]))
                        except Exception:
                            pass
                for k in [
                    "emergency_brake",
                    "service_brake",
                    "headlights",
                    "fault_power",
                    "fault_brake",
                    "fault_signal",
                    "automatic_mode",
                ]:
                    if k in msg:
                        try:
                            setattr(c, k, bool(msg[k]))
                        except Exception:
                            pass
                if "interior_lights" in msg:
                    try:
                        c.interior_lights = int(msg["interior_lights"])
                    except Exception:
                        pass
                if "doors_state" in msg:
                    try:
                        c.doors_state = int(msg["doors_state"])
                    except Exception:
                        pass
                if "cabin_temp" in msg:
                    try:
                        c.cabin_temp = float(msg["cabin_temp"])
                    except Exception:
                        pass
                if "passengers" in msg:
                    try:
                        c.passengers = int(msg["passengers"])
                    except Exception:
                        pass
                if "next_station" in msg:
                    try:
                        c.next_station = str(msg["next_station"])
                    except Exception:
                        pass

        for system in train_models.values():
            system.tick(dt=physics_dt)

        for train_id, system in train_models.items():
            track_map.set_train_speed(train_id - 1, system.model.currentSpeedKmh)

        track_map.update(physics_dt)

        # Apply station dwell + destination hold AFTER the Track Model advances blocks,
        # so we don't miss stations/destination when multiple blocks are traversed in one tick.
        for ti, tr in enumerate(track_map.trains, start=1):
            try:
                cur_bn = int(tr.block.num)
            except Exception:
                continue

            # Destination hold
            try:
                dest_bn = ctc_win._external_trains.get(f"Train-{ti}", {}).get("dest_block")
                if dest_bn is not None and int(dest_bn) == cur_bn:
                    _dest_hold_on.add(ti)
            except Exception:
                pass

            if ti in _dest_hold_on:
                try:
                    tr.speed = 0.0
                except Exception:
                    pass
                try:
                    sys_obj = train_models.get(ti)
                    if sys_obj is not None:
                        sys_obj.controller.service_brake = True
                except Exception:
                    pass
                continue

            # Station dwell (1s) on entry
            prev_bn = int(_last_block_seen.get(ti, -1))
            if cur_bn != prev_bn:
                _last_block_seen[ti] = cur_bn
                try:
                    if hasattr(tr.block, "is_station") and tr.block.is_station():
                        _dwell_remaining_sec[ti] = 1.0
                except Exception:
                    pass

            rem = float(_dwell_remaining_sec.get(ti, 0.0))
            if rem > 0.0:
                _dwell_remaining_sec[ti] = max(0.0, rem - float(physics_dt))
                try:
                    tr.speed = 0.0
                except Exception:
                    pass
                try:
                    sys_obj = train_models.get(ti)
                    if sys_obj is not None:
                        sys_obj.controller.service_brake = True
                except Exception:
                    pass
            else:
                # release dwell brake if we applied it
                try:
                    sys_obj = train_models.get(ti)
                    if sys_obj is not None and getattr(sys_obj.controller, "service_brake", False):
                        sys_obj.controller.service_brake = False
                except Exception:
                    pass
        try:
            track_model.ui.update()
            if track_window.testui.myscroll.isVisible():
                track_window.testui.update()
        except Exception:
            pass

        if conn is not None:
            try:
                for train_id, system in train_models.items():
                    m = system.model
                    feedback = {
                        "type": "model",
                        "train_id": int(train_id),
                        "current_speed": float(system.controller.current_speed),
                        "commanded_speed": float(kmhToMph(m.commandedSpeedKmh)),
                        "speed_limit": float(kmhToMph(m.speedLimitKmh)),
                        "power_output": float(system.controller.power_output),
                        "authority": float(system.controller.authority),
                        "distance_travelled_km": float(
                            getattr(system.controller, "distance_travelled_km", 0.0)
                        ),
                        "emergency_brake": bool(system.controller.emergency_brake),
                        "service_brake": bool(system.controller.service_brake),
                        "fault_power": bool(system.controller.fault_power),
                        "fault_brake": bool(system.controller.fault_brake),
                        "fault_signal": bool(system.controller.fault_signal),
                        "next_station": str(system.controller.next_station),
                    }
                    conn.sendall((json.dumps(feedback) + "\n").encode("utf-8"))
            except Exception:
                try:
                    conn.close()
                except Exception:
                    pass
                conn = None

    sim_timer = QTimer()
    sim_timer.timeout.connect(on_tick)
    sim_timer.start(100)

    sys.exit(app.exec())

if __name__ == "__main__":
    main()
