# ai was used to help with code development.

import sys
import os
import json
import socket
import subprocess
import atexit
from PyQt5.QtWidgets import QApplication
from PyQt5.QtCore import QTimer

from train_backend import TrainSystem
from train_frontend_main import TrainControlUI
from train_frontend_test import TrainModelTestUI


NUM_TRAINS = 3  # should match TrainControllerApp.NUM_TRAINS


def main():
    app = QApplication(sys.argv)  # to allow app to run

    # create separate backend + UI for each train
    systems = {}
    model_uis = []
    test_uis = []
    for train_id in range(1, NUM_TRAINS + 1):
        system = TrainSystem()
        systems[train_id] = system
        ui = TrainControlUI(trainModel=system.model)
        ui.setWindowTitle(f"Train Model – Train {train_id}")
        ui.show()
        model_uis.append(ui)

        # launch a test UI for this train model
        test = TrainModelTestUI(trainModel=system.model)
        test.setWindowTitle(f"Train Model Test – Train {train_id}")
        test.show()
        test_uis.append(test)

    # Train Controller (Tkinter) UI runs in a separate process to avoid
    # PyQt + Tkinter event-loop/GIL crashes on Windows.
    server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server.bind(("127.0.0.1", 0))
    server.listen(1)
    server.setblocking(False)
    port = server.getsockname()[1]

    env = os.environ.copy()
    env["TRAIN_IPC_HOST"] = "127.0.0.1"
    env["TRAIN_IPC_PORT"] = str(port)

    controller_proc = subprocess.Popen([sys.executable, "TrainController.py"], env=env)

    def _cleanup():
        try:
            controller_proc.terminate()
        except Exception:
            pass

    atexit.register(_cleanup)

    # artificial timer was made to simulate time so speed, accel, etc. could change as time passes
    simTimer = QTimer()

    conn = None
    recv_buf = ""

    def onTick():
        nonlocal conn, recv_buf

        if conn is None:
            try:
                conn, _ = server.accept()
                conn.setblocking(False)
            except BlockingIOError:
                conn = None
            except Exception:
                conn = None

        if conn is not None:
            # Read controller inputs (non-blocking, newline-delimited JSON).
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
                train_id = int(msg.get("train_id", 1))
                system = systems.get(train_id)
                if system is None:
                    continue
                c = system.controller
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

        # advance all trains' backends
        for system in systems.values():
            system.tick()

        # Send model feedback back to controller UI for each train
        if conn is not None:
            try:
                for train_id, system in systems.items():
                    feedback = {
                        "type": "model",
                        "train_id": int(train_id),
                        "current_speed": float(system.controller.current_speed),
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

    simTimer.timeout.connect(onTick)
    simTimer.start(100)  # 100 ms matches samplePeriodSec in the backend

    sys.exit(app.exec_())


if __name__ == "__main__":
    main()

