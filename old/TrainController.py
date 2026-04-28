import os, sys, time, json, socket, threading
os.environ['TK_SILENCE_DEPRECATION'] = '1'
import tkinter as tk
from tkinter import ttk

from train_controller_backend import TrainController


#  COLOR PALETTE  –  Red & Black Industrial

C = {
    "bg_dark":    "#0d0d0d",
    "bg_panel":   "#1a1a1a",
    "bg_card":    "#222222",
    "bg_header":  "#1a0000",
    "accent":     "#cc0000",
    "accent2":    "#ff3333",
    "accent_dim": "#660000",
    "ok":         "#00cc44",
    "warn":       "#ff8800",
    "fault":      "#ff2222",
    "text":       "#f0f0f0",
    "text_dim":   "#888888",
    "text_lcd":   "#ff4444",
    "border":     "#3a0000",
    "select":     "#cc0000",
    "deselect":   "#2a2a2a",
    "train_sel":  "#3a0a0a",
}


#  UI HELPER FUNCTIONS


def sep(parent, color=C["border"], pady=4):
    tk.Frame(parent, bg=color, height=1).pack(fill=tk.X, pady=pady)

def card(parent, title="", bg=C["bg_card"], pad=10):
    outer = tk.Frame(parent, bg=C["border"], bd=0)
    outer.pack(fill=tk.X, pady=4, padx=2)
    if title:
        th = tk.Frame(outer, bg=C["accent_dim"])
        th.pack(fill=tk.X)
        tk.Label(th, text=f"  {title.upper()}", bg=C["accent_dim"],
                 fg=C["text"], font=("Courier", 9, "bold"),
                 anchor="w", pady=3).pack(fill=tk.X)
    inner = tk.Frame(outer, bg=bg, padx=pad, pady=pad)
    inner.pack(fill=tk.X)
    return inner

def section_title(parent, text):
    f = tk.Frame(parent, bg=C["bg_panel"])
    f.pack(fill=tk.X, pady=(10, 2))
    tk.Frame(f, bg=C["accent"], width=4).pack(side=tk.LEFT, fill=tk.Y)
    tk.Label(f, text=f"  {text}", bg=C["bg_panel"], fg=C["accent2"],
             font=("Courier", 11, "bold")).pack(side=tk.LEFT, pady=4)

def pill_button(parent, text, command, color=C["accent"], fg="white",
                width=10, font_size=11):
    return tk.Button(parent, text=text, command=command,
                     bg=color, fg=fg, activebackground=C["accent2"],
                     activeforeground="white",
                     font=("Courier", font_size, "bold"),
                     relief=tk.FLAT, bd=0, padx=10, pady=6,
                     cursor="hand2", width=width)



#  MAIN APPLICATION


class TrainControllerApp:

    NUM_TRAINS = 3

    def __init__(self, trains=None, show_test_ui_button=True, ipc_host=None, ipc_port=None):
        if trains is not None:
            self.trains = list(trains)
            self.NUM_TRAINS = len(self.trains)
        else:
            self.trains = [TrainController(i+1) for i in range(self.NUM_TRAINS)]
        self.active = 0
        self.sim_running = False
        self._show_test_ui_button = bool(show_test_ui_button)

        self._ipc_host = ipc_host
        self._ipc_port = int(ipc_port) if ipc_port is not None else None
        self._ipc_sock = None
        self._ipc_send_lock = threading.Lock()
        self._ipc_recv_thread = None
        self._ipc_running = False

        # ── per-train UI state (indexed by train number) ──
        # each list has one entry per train so switching tabs
        # never bleeds one train's state into another
        self.left_door_open  = [False] * self.NUM_TRAINS
        self.right_door_open = [False] * self.NUM_TRAINS
        self.ext_light_on    = [False] * self.NUM_TRAINS
        self.int_light_on    = [False] * self.NUM_TRAINS
        self.svc_brake_on    = [False] * self.NUM_TRAINS   # per-train service brake UI state
        self.ebrake_active   = [False] * self.NUM_TRAINS   # per-train e-brake UI state

        if trains is None:
            # demo data
            self.trains[0].commanded_speed = 30; self.trains[0].passengers = 42
            self.trains[0].next_station    = "CENTRAL"
            self.trains[1].commanded_speed = 25; self.trains[1].passengers = 18
            self.trains[1].next_station    = "OVERBROOK"; self.trains[1].authority = 1200
            self.trains[2].commanded_speed = 0;  self.trains[2].passengers = 0
            self.trains[2].next_station    = "YARD";      self.trains[2].authority = 0

        self._build_root()
        self._build_header()
        self._build_body()
        self._build_status_bar()

        if self._ipc_port is not None:
            self._start_ipc()

        self._refresh_all()

    def _start_ipc(self):
        self._ipc_running = True
        self._ipc_sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self._ipc_sock.connect((self._ipc_host or "127.0.0.1", self._ipc_port))
        self._ipc_sock.setblocking(True)

        def _recv_loop():
            buf = b""
            while self._ipc_running:
                try:
                    chunk = self._ipc_sock.recv(4096)
                    if not chunk:
                        break
                    buf += chunk
                    while b"\n" in buf:
                        line, buf = buf.split(b"\n", 1)
                        if not line:
                            continue
                        try:
                            msg = json.loads(line.decode("utf-8"))
                        except Exception:
                            continue
                        if msg.get("type") != "model":
                            continue
                        train_id = int(msg.get("train_id", self.active + 1))
                        idx = max(0, min(self.NUM_TRAINS - 1, train_id - 1))
                        t = self.trains[idx]
                        # Apply model feedback to controller object.
                        # Only touch plain data fields; Tk widgets update on next refresh tick.
                        if "current_speed" in msg:
                            t.current_speed = float(msg["current_speed"])
                        if "commanded_speed" in msg:
                            t.commanded_speed = float(msg["commanded_speed"])
                        if "speed_limit" in msg:
                            t.speed_limit = float(msg["speed_limit"])
                        if "power_output" in msg:
                            t.power_output = float(msg["power_output"])
                        if "authority" in msg:
                            t.authority = float(msg["authority"])
                        if "distance_travelled_km" in msg:
                            t.distance_travelled_km = float(msg["distance_travelled_km"])
                        if "next_station" in msg:
                            t.next_station = str(msg["next_station"])
                        if "emergency_brake" in msg:
                            t.emergency_brake = bool(msg["emergency_brake"])
                            self.ebrake_active[idx] = bool(t.emergency_brake)
                        if "service_brake" in msg:
                            t.service_brake = bool(msg["service_brake"])
                            self.svc_brake_on[idx] = bool(t.service_brake)
                        for k, attr in [("fault_power", "fault_power"),
                                        ("fault_brake", "fault_brake"),
                                        ("fault_signal", "fault_signal")]:
                            if k in msg:
                                setattr(t, attr, bool(msg[k]))
                except Exception:
                    break

        self._ipc_recv_thread = threading.Thread(target=_recv_loop, daemon=True)
        self._ipc_recv_thread.start()

    def _ipc_send_controller_inputs(self):
        if not self._ipc_sock:
            return
        try:
            with self._ipc_send_lock:
                for t in self.trains:
                    payload = {
                        "type": "controller",
                        "train_id": int(getattr(t, "train_id", 0)) or (self.trains.index(t) + 1),
                        "commanded_speed": float(t.commanded_speed),
                        "speed_limit": float(t.speed_limit),
                        "authority": float(t.authority),
                        "kp": float(t.kp),
                        "ki": float(t.ki),
                        "emergency_brake": bool(t.emergency_brake),
                        "service_brake": bool(t.service_brake),
                        "doors_state": int(t.doors_state),
                        "headlights": bool(t.headlights),
                        "interior_lights": int(t.interior_lights),
                        "cabin_temp": float(t.cabin_temp),
                        "passengers": int(t.passengers),
                        "next_station": str(t.next_station),
                        "fault_power": bool(t.fault_power),
                        "fault_brake": bool(t.fault_brake),
                        "fault_signal": bool(t.fault_signal),
                        "automatic_mode": bool(t.automatic_mode),
                        "manual_speed_target": float(t.manual_speed_target),
                    }
                    data = (json.dumps(payload) + "\n").encode("utf-8")
                    self._ipc_sock.sendall(data)
        except Exception:
            pass

    #  root 

    def _build_root(self):
        self.root = tk.Tk()
        self.root.title("Train Controller  –  PAAC North Shore")
        self.root.configure(bg=C["bg_dark"])
        self.root.geometry("1300x860")
        self.root.minsize(1100, 760)
        self.root.resizable(True, True)

    #  header 

    def _build_header(self):
        hdr = tk.Frame(self.root, bg=C["bg_header"], height=64)
        hdr.pack(fill=tk.X, side=tk.TOP)
        hdr.pack_propagate(False)

        logo_f = tk.Frame(hdr, bg=C["accent"], padx=14)
        logo_f.pack(side=tk.LEFT, fill=tk.Y)
        tk.Label(logo_f, text="TC", bg=C["accent"], fg="white",
                 font=("Courier", 26, "bold")).pack(expand=True)

        tk.Label(hdr, text="  TRAIN CONTROLLER", bg=C["bg_header"],
                 fg="white", font=("Courier", 20, "bold")).pack(side=tk.LEFT, pady=10)
        tk.Label(hdr, text="  PAAC North Shore Extension",
                 bg=C["bg_header"], fg=C["text_dim"],
                 font=("Courier", 10)).pack(side=tk.LEFT, pady=10)

        right = tk.Frame(hdr, bg=C["bg_header"])
        right.pack(side=tk.RIGHT, padx=16, fill=tk.Y)

        self.clock_lbl = tk.Label(right, text="00:00:00", bg=C["bg_header"],
                                   fg=C["accent2"], font=("Courier", 16, "bold"))
        self.clock_lbl.pack(side=tk.TOP, pady=(8, 0))
        if self._show_test_ui_button:
            pill_button(right, "TEST UI", self._open_test_ui,
                        color=C["accent_dim"], font_size=9, width=8).pack(side=tk.TOP, pady=4)

    #  body 

    def _build_body(self):
        body = tk.Frame(self.root, bg=C["bg_dark"])
        body.pack(fill=tk.BOTH, expand=True, padx=10, pady=(6, 0))

        # LEFT panel
        left = tk.Frame(body, bg=C["bg_panel"], width=420)
        left.pack(side=tk.LEFT, fill=tk.Y, padx=(0, 6))
        left.pack_propagate(False)

        self._build_train_tabs(left)

        ctrl_canvas = tk.Canvas(left, bg=C["bg_panel"], highlightthickness=0)
        ctrl_scroll = tk.Scrollbar(left, orient="vertical",
                                    command=ctrl_canvas.yview,
                                    bg=C["bg_panel"], troughcolor=C["bg_dark"])
        ctrl_scroll.pack(side=tk.RIGHT, fill=tk.Y)
        ctrl_canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        ctrl_canvas.configure(yscrollcommand=ctrl_scroll.set)

        self.ctrl_inner = tk.Frame(ctrl_canvas, bg=C["bg_panel"])
        ctrl_canvas.create_window((0, 0), window=self.ctrl_inner, anchor="nw")
        self.ctrl_inner.bind("<Configure>",
            lambda e: ctrl_canvas.configure(scrollregion=ctrl_canvas.bbox("all")))
        ctrl_canvas.bind_all("<MouseWheel>",
            lambda e: ctrl_canvas.yview_scroll(int(-1*(e.delta/120)), "units"))

        self._build_controls(self.ctrl_inner)

        # RIGHT panel
        right = tk.Frame(body, bg=C["bg_panel"])
        right.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

        right_canvas = tk.Canvas(right, bg=C["bg_panel"], highlightthickness=0)
        right_scroll = tk.Scrollbar(right, orient="vertical",
                                    command=right_canvas.yview,
                                    bg=C["bg_panel"], troughcolor=C["bg_dark"])
        right_scroll.pack(side=tk.RIGHT, fill=tk.Y)
        right_canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        right_canvas.configure(yscrollcommand=right_scroll.set)

        self.right_inner = tk.Frame(right_canvas, bg=C["bg_panel"])
        right_canvas.create_window((0, 0), window=self.right_inner, anchor="nw")
        self.right_inner.bind(
            "<Configure>",
            lambda e: right_canvas.configure(scrollregion=right_canvas.bbox("all"))
        )
        right_canvas.bind_all(
            "<MouseWheel>",
            lambda e: right_canvas.yview_scroll(int(-1 * (e.delta / 120)), "units")
        )

        self._build_right(self.right_inner)

    #  train tabs 

    def _build_train_tabs(self, parent):
        tab_f = tk.Frame(parent, bg=C["bg_dark"])
        tab_f.pack(fill=tk.X)
        self.train_tab_btns = []
        for i in range(self.NUM_TRAINS):
            b = tk.Button(tab_f, text=f" Train {i+1} ",
                          bg=C["train_sel"] if i==0 else C["bg_dark"],
                          fg=C["accent2"] if i==0 else C["text_dim"],
                          font=("Courier", 10, "bold"),
                          relief=tk.FLAT, bd=0, pady=8, padx=4,
                          cursor="hand2",
                          command=lambda idx=i: self._select_train(idx))
            b.pack(side=tk.LEFT, expand=True, fill=tk.X)
            self.train_tab_btns.append(b)

        ind_f = tk.Frame(parent, bg=C["bg_dark"], height=4)
        ind_f.pack(fill=tk.X)
        self.train_indicators = []
        for i in range(self.NUM_TRAINS):
            ind = tk.Frame(ind_f, bg=C["accent"] if i==0 else C["bg_dark"], height=4)
            ind.pack(side=tk.LEFT, expand=True, fill=tk.X)
            self.train_indicators.append(ind)

    def _select_train(self, idx):
        self.active = idx
        for i, (b, ind) in enumerate(zip(self.train_tab_btns, self.train_indicators)):
            b.config(bg=C["train_sel"] if i==idx else C["bg_dark"],
                     fg=C["accent2"]   if i==idx else C["text_dim"])
            ind.config(bg=C["accent"] if i==idx else C["bg_dark"])
        # Reload ALL widgets from the newly selected train's stored state
        self._reload_controls_for_active_train()

    def _reload_controls_for_active_train(self):
        """Fully reset every control widget to match the active train's state.
        This prevents any widget state from one train bleeding into another."""
        t   = self.T
        idx = self.active

        # ── e-brake button ──
        if self.ebrake_active[idx]:
            self.ebrake_btn.config(bg="#4a0000",
                text="⚠  E-BRAKE ACTIVE – CLICK TO RELEASE")
            self.ebrake_status.config(text="● ACTIVE", fg=C["fault"])
        else:
            self.ebrake_btn.config(bg=C["accent"],
                text="🚨  EMERGENCY BRAKE")
            self.ebrake_status.config(text="● INACTIVE", fg=C["ok"])

        # ── service brake button ──
        if self.svc_brake_on[idx]:
            self.brake_btn.config(text="  ON  🔴", bg=C["fault"], fg="white")
        else:
            self.brake_btn.config(text="  OFF  ", bg=C["deselect"], fg=C["text_dim"])

        # ── mode buttons ──
        if t.automatic_mode:
            self.mode_btns["Auto"].config(bg="#006600", fg="white")
            self.mode_btns["Manual"].config(bg=C["deselect"], fg=C["text_dim"])
        else:
            self.mode_btns["Manual"].config(bg=C["accent"], fg="white")
            self.mode_btns["Auto"].config(bg=C["deselect"], fg=C["text_dim"])

        # ── doors ──
        self._sync_doors()
        # Driver should not interact with doors in Auto.
        try:
            door_state = "disabled" if t.automatic_mode else "normal"
            self.left_door_btn.config(state=door_state)
            self.right_door_btn.config(state=door_state)
        except Exception:
            pass

        # ── lights ──
        self._sync_lights()

        # ── kp / ki entries ──
        self.kp_entry.delete(0, tk.END)
        self.kp_entry.insert(0, str(t.kp))
        self.kp_disp.config(text=f"= {t.kp}")
        self.ki_entry.delete(0, tk.END)
        self.ki_entry.insert(0, str(t.ki))
        self.ki_disp.config(text=f"= {t.ki}")

    #  left controls 

    def _build_controls(self, parent):

        # 1 ── Emergency Brake
        section_title(parent, "Emergency Brake")
        eb_card = card(parent, bg="#1a0000", pad=12)
        # Fixed-height container so the button never grows vertically
        eb_btn_frame = tk.Frame(eb_card, bg="#1a0000", height=52)
        eb_btn_frame.pack(fill=tk.X)
        eb_btn_frame.pack_propagate(False)   # <-- this is what stops expansion
        self.ebrake_btn = tk.Button(eb_btn_frame,
            text="🚨  EMERGENCY BRAKE",
            font=("Courier", 14, "bold"),
            bg=C["accent"], fg="white",
            activebackground="#ff0000",
            relief=tk.FLAT, bd=0,
            cursor="hand2",
            command=self._on_ebrake)
        self.ebrake_btn.pack(fill=tk.BOTH, expand=True)
        self.ebrake_status = tk.Label(eb_card, text="● INACTIVE",
                                       bg="#1a0000", fg=C["ok"],
                                       font=("Courier", 10, "bold"))
        self.ebrake_status.pack(pady=(6, 0))

        # 2 ── Service Brake
        section_title(parent, "Service Brake")
        brk_card = card(parent, pad=10)
        brk_row = tk.Frame(brk_card, bg=C["bg_card"]); brk_row.pack(fill=tk.X)
        tk.Label(brk_row, text="Service Brake", bg=C["bg_card"],
                 fg=C["text"], font=("Courier", 11)).pack(side=tk.LEFT, padx=4)
        self.brake_btn = tk.Button(brk_row, text="  OFF  ",
                                    font=("Courier", 10, "bold"),
                                    bg=C["deselect"], fg=C["text_dim"],
                                    relief=tk.FLAT, bd=0, padx=10, pady=4,
                                    cursor="hand2", command=self._on_brake)
        self.brake_btn.pack(side=tk.RIGHT)

        # 3 ── Doors  (two independent toggle buttons)
        section_title(parent, "Doors")
        door_card = card(parent, pad=12)

        door_status_row = tk.Frame(door_card, bg=C["bg_card"])
        door_status_row.pack(fill=tk.X, pady=(0, 8))
        tk.Label(door_status_row, text="Current:", bg=C["bg_card"],
                 fg=C["text_dim"], font=("Courier", 9)).pack(side=tk.LEFT)
        self.door_status_lbl = tk.Label(door_status_row, text="🚪  BOTH CLOSED",
                 bg=C["bg_card"], fg=C["ok"], font=("Courier", 10, "bold"))
        self.door_status_lbl.pack(side=tk.LEFT, padx=8)

        door_row = tk.Frame(door_card, bg=C["bg_card"])
        door_row.pack(fill=tk.X)

        self.left_door_btn = tk.Button(door_row,
            text="◀  LEFT DOOR\n🔒  CLOSED",
            font=("Courier", 11, "bold"),
            bg=C["deselect"], fg=C["text_dim"],
            relief=tk.FLAT, bd=0, padx=6, pady=14,
            width=14, cursor="hand2",
            command=self._toggle_left_door)
        self.left_door_btn.pack(side=tk.LEFT, padx=4, expand=True, fill=tk.X)

        self.right_door_btn = tk.Button(door_row,
            text="RIGHT DOOR  ▶\n🔒  CLOSED",
            font=("Courier", 11, "bold"),
            bg=C["deselect"], fg=C["text_dim"],
            relief=tk.FLAT, bd=0, padx=6, pady=14,
            width=14, cursor="hand2",
            command=self._toggle_right_door)
        self.right_door_btn.pack(side=tk.LEFT, padx=4, expand=True, fill=tk.X)

        # 4 ── Lights  (two independent toggle buttons)
        section_title(parent, "Lights")
        light_card = card(parent, pad=12)

        light_status_row = tk.Frame(light_card, bg=C["bg_card"])
        light_status_row.pack(fill=tk.X, pady=(0, 8))
        tk.Label(light_status_row, text="Current:", bg=C["bg_card"],
                 fg=C["text_dim"], font=("Courier", 9)).pack(side=tk.LEFT)
        self.light_status_lbl = tk.Label(light_status_row, text="All OFF",
                 bg=C["bg_card"], fg=C["text_dim"], font=("Courier", 10, "bold"))
        self.light_status_lbl.pack(side=tk.LEFT, padx=8)

        light_row = tk.Frame(light_card, bg=C["bg_card"])
        light_row.pack(fill=tk.X)

        self.ext_light_btn = tk.Button(light_row,
            text="🔦  EXTERNAL\n●  OFF",
            font=("Courier", 11, "bold"),
            bg=C["deselect"], fg=C["text_dim"],
            relief=tk.FLAT, bd=0, padx=6, pady=14,
            width=14, cursor="hand2",
            command=self._toggle_ext_light)
        self.ext_light_btn.pack(side=tk.LEFT, padx=4, expand=True, fill=tk.X)

        self.int_light_btn = tk.Button(light_row,
            text="🏠  INTERNAL\n●  OFF",
            font=("Courier", 11, "bold"),
            bg=C["deselect"], fg=C["text_dim"],
            relief=tk.FLAT, bd=0, padx=6, pady=14,
            width=14, cursor="hand2",
            command=self._toggle_int_light)
        self.int_light_btn.pack(side=tk.LEFT, padx=4, expand=True, fill=tk.X)

        # 5 ── Cabin Temperature (AC)
        section_title(parent, "Cabin Temperature (AC)")
        temp_card = card(parent, pad=10)
        temp_row = tk.Frame(temp_card, bg=C["bg_card"]); temp_row.pack(fill=tk.X)
        tk.Label(temp_row, text="Setpoint (°F):", bg=C["bg_card"],
                 fg=C["text"], font=("Courier", 10)).pack(side=tk.LEFT, padx=4)
        self.temp_lbl = tk.Label(temp_row,
                                 text="70.0",
                                 bg=C["bg_dark"], fg=C["text_lcd"],
                                 font=("Courier", 12, "bold"), width=6)
        self.temp_lbl.pack(side=tk.LEFT, padx=4)
        pill_button(temp_row, "−", lambda: self._nudge_temp(-1.0),
                    width=3, font_size=9).pack(side=tk.LEFT, padx=2)
        pill_button(temp_row, "+", lambda: self._nudge_temp(+1.0),
                    width=3, font_size=9).pack(side=tk.LEFT, padx=2)

        # 6 ── Operation Mode
        section_title(parent, "Operation Mode")
        mode_card = card(parent, pad=10)
        mode_row = tk.Frame(mode_card, bg=C["bg_card"]); mode_row.pack(fill=tk.X)
        self.mode_btns = {}
        for txt, val, col in [("🤖  AUTO","Auto","#006600"),("👤  MANUAL","Manual",C["accent"])]:
            b = tk.Button(mode_row, text=txt,
                          font=("Courier", 11, "bold"),
                          bg=col if val=="Auto" else C["deselect"],
                          fg="white" if val=="Auto" else C["text_dim"],
                          relief=tk.FLAT, bd=0, padx=8, pady=8,
                          cursor="hand2", width=12,
                          command=lambda v=val: self._on_mode(v))
            b.pack(side=tk.LEFT, padx=4, expand=True, fill=tk.X)
            self.mode_btns[val] = b

        # 6 ── Set Speed
        section_title(parent, "Set Speed  (Manual)")
        spd_card = card(parent, pad=10)
        spd_row = tk.Frame(spd_card, bg=C["bg_card"]); spd_row.pack(fill=tk.X)
        tk.Label(spd_row, text="Target (mph):", bg=C["bg_card"],
                 fg=C["text"], font=("Courier", 10)).pack(side=tk.LEFT, padx=4)
        self.manual_spd_var = tk.StringVar(value="0")
        tk.Entry(spd_row, textvariable=self.manual_spd_var,
                 font=("Courier", 12, "bold"), width=6,
                 bg=C["bg_dark"], fg=C["text_lcd"],
                 insertbackground=C["accent"],
                 relief=tk.FLAT, bd=1, justify="center"
                 ).pack(side=tk.LEFT, padx=6)
        pill_button(spd_row, "SET", self._on_set_speed,
                    width=6, font_size=10).pack(side=tk.LEFT)

        # 7 ── Train Engineer (Kp / Ki)
        section_title(parent, "Train Engineer  (Kp / Ki)")
        eng_card = card(parent, pad=10)
        for label, attr_e, attr_d, default, cmd in [
            ("Kp:", "kp_entry", "kp_disp", "10.0",   self._on_kp),
            ("Ki:", "ki_entry", "ki_disp", "8000.0",  self._on_ki),
        ]:
            row = tk.Frame(eng_card, bg=C["bg_card"]); row.pack(fill=tk.X, pady=3)
            tk.Label(row, text=label, bg=C["bg_card"], fg=C["text"],
                     font=("Courier", 10), width=4).pack(side=tk.LEFT)
            ent = tk.Entry(row, font=("Courier", 11, "bold"), width=9,
                           bg=C["bg_dark"], fg=C["text_lcd"],
                           insertbackground=C["accent"],
                           relief=tk.FLAT, bd=1, justify="center")
            ent.insert(0, default)
            ent.pack(side=tk.LEFT, padx=6)
            setattr(self, attr_e, ent)
            pill_button(row, "SET", cmd, width=5, font_size=9).pack(side=tk.LEFT, padx=4)
            disp = tk.Label(row, text=f"= {default}", bg=C["bg_card"],
                             fg=C["ok"], font=("Courier", 9))
            disp.pack(side=tk.LEFT, padx=4)
            setattr(self, attr_d, disp)

        # 8 ── Fault Simulation
        section_title(parent, "Fault Simulation  (Testing)")
        fault_sim = card(parent, pad=10)
        fsrow = tk.Frame(fault_sim, bg=C["bg_card"]); fsrow.pack(fill=tk.X)
        self.pwr_sim_btn = pill_button(fsrow, "⚡ Power",
            lambda: self._sim_fault("power"), color="#994400", width=9, font_size=9)
        self.pwr_sim_btn.pack(side=tk.LEFT, padx=2)
        self.brk_sim_btn = pill_button(fsrow, "🛑 Brake",
            lambda: self._sim_fault("brake"), color="#994400", width=9, font_size=9)
        self.brk_sim_btn.pack(side=tk.LEFT, padx=2)
        self.sig_sim_btn = pill_button(fsrow, "📡 Signal",
            lambda: self._sim_fault("signal"), color="#994400", width=9, font_size=9)
        self.sig_sim_btn.pack(side=tk.LEFT, padx=2)

        # 9 ── Simulation button
        sep(parent)
        sim_f = tk.Frame(parent, bg=C["bg_panel"]); sim_f.pack(fill=tk.X, pady=6, padx=6)
        self.sim_btn = tk.Button(sim_f,
            text="▶  START SIMULATION",
            font=("Courier", 12, "bold"),
            bg="#005500", fg="white",
            activebackground="#008800",
            relief=tk.FLAT, bd=0, pady=10,
            cursor="hand2", command=self._toggle_sim)
        self.sim_btn.pack(fill=tk.X)

    #  right panel 

    def _build_right(self, parent):

        # mini overview strip
        overview = tk.Frame(parent, bg=C["bg_dark"])
        overview.pack(fill=tk.X, pady=(0, 6))
        self.mini_cards = []
        for i in range(self.NUM_TRAINS):
            mc = self._make_mini_card(overview, i)
            mc["frame"].pack(side=tk.LEFT, expand=True, fill=tk.X, padx=3)
            self.mini_cards.append(mc)

        # driver outputs
        section_title(parent, "Driver Outputs Display")
        out_card = tk.Frame(parent, bg=C["bg_card"], pady=10)
        out_card.pack(fill=tk.X, padx=4)
        out_grid = tk.Frame(out_card, bg=C["bg_card"])
        out_grid.pack(fill=tk.X, expand=True, padx=10, pady=6)

        def _out_row(row, label, label_bg, attr, unit=""):
            lf = tk.Frame(out_grid, bg=label_bg, padx=10, pady=8)
            lf.grid(row=row, column=0, padx=6, pady=5, sticky="ew")
            tk.Label(lf, text=label, bg=label_bg, fg="white",
                     font=("Courier", 13, "bold"),
                     anchor="center").pack()
            val_f = tk.Frame(out_grid, bg=C["bg_dark"], padx=4, pady=4)
            val_f.grid(row=row, column=1, padx=6, pady=5, sticky="ew")
            val_lbl = tk.Label(val_f, text="–", bg="#0a0000", fg=C["text_lcd"],
                                font=("Courier", 18, "bold"),
                                anchor="e", padx=10)
            val_lbl.pack(fill=tk.X, expand=True)
            tk.Label(out_grid, text=unit, bg=C["bg_card"],
                     fg=C["text_dim"], font=("Courier", 10)
                     ).grid(row=row, column=2, padx=4)
            setattr(self, attr, val_lbl)

        _out_row(0, "Actual Speed",   "#5a0000",  "disp_actual_spd",  "mph")
        _out_row(1, "Commanded Speed","#3a2000",  "disp_cmd_spd",     "mph")
        _out_row(2, "Speed Limit",    "#3a2000",  "disp_speed_limit", "mph")
        _out_row(3, "Cabin Temp",     "#3a2000",  "disp_temp",        "°F")
        _out_row(4, "Distance",       "#3a3a00",  "disp_distance",    "miles")
        _out_row(5, "Authority",      "#3a3a00",  "disp_authority",   "miles")
        _out_row(6, "Passengers",     "#003050",  "disp_passengers",  "pax")
        _out_row(7, "Next Station",   "#1a1a3a",  "disp_next_station","")
        _out_row(8, "Power Command",  "#003a00",  "disp_power",       "W")
        out_grid.columnconfigure(0, weight=1, uniform="out")
        out_grid.columnconfigure(1, weight=2, uniform="out")
        out_grid.columnconfigure(2, weight=0)

        # fault indicators
        section_title(parent, "Fault Indicators")
        fault_card = card(parent, pad=12)
        fault_row = tk.Frame(fault_card, bg=C["bg_card"]); fault_row.pack(fill=tk.X)
        self.fault_lbls = {}
        for fname in ["Power Fault", "Brake Fault", "Signal Fault"]:
            key = fname.split()[0].lower()
            col = tk.Frame(fault_row, bg=C["bg_card"]); col.pack(side=tk.LEFT, expand=True)
            icon = tk.Label(col, text="●", bg=C["bg_card"], fg=C["text_dim"],
                             font=("Courier", 22, "bold"))
            icon.pack()
            tk.Label(col, text=fname, bg=C["bg_card"], fg=C["text_dim"],
                     font=("Courier", 9)).pack()
            self.fault_lbls[key] = icon

        # system status
        section_title(parent, "System Status")
        stat_card = card(parent, pad=10)
        stat_row = tk.Frame(stat_card, bg=C["bg_card"]); stat_row.pack(fill=tk.X)
        for label, attr in [("Mode","stat_mode"),("Doors","stat_doors"),
                              ("Lights","stat_lights"),("E-Brake","stat_ebrake")]:
            col = tk.Frame(stat_row, bg=C["bg_card"]); col.pack(side=tk.LEFT, expand=True)
            tk.Label(col, text=label, bg=C["bg_card"], fg=C["text_dim"],
                     font=("Courier", 9)).pack()
            # clearer defaults instead of dashes
            if label == "Mode":
                default_text = "AUTO"
            elif label == "Doors":
                default_text = "Closed"
            elif label == "Lights":
                default_text = "Off"
            else:  # E-Brake
                default_text = "OFF"
            lbl = tk.Label(col, text=default_text, bg=C["bg_card"], fg=C["ok"],
                            font=("Courier", 10, "bold"))
            lbl.pack()
            setattr(self, attr, lbl)

        # ads / announcements (match Train Model UI placeholder)
        section_title(parent, "Advertisements")
        ads_card = card(parent, pad=10)
        ads_row = tk.Frame(ads_card, bg=C["bg_card"])
        ads_row.pack(fill=tk.X, padx=6, pady=6)
        ads_lbl = tk.Label(ads_row,
                           text="[ Ad Content Placeholder ]",
                           bg=C["bg_card"], fg=C["accent2"],
                           font=("Courier", 11), anchor="center")
        ads_lbl.pack(fill=tk.X, padx=8, pady=6)

    #  mini card 

    def _make_mini_card(self, parent, idx):
        f = tk.Frame(parent, bg=C["bg_card"], padx=8, pady=8)
        tk.Label(f, text=f"TRAIN {idx+1}", bg=C["bg_card"],
                 fg=C["accent2"], font=("Courier", 9, "bold")).pack(anchor="w")
        spd = tk.Label(f, text="0.0 mph", bg=C["bg_card"],
                       fg=C["text_lcd"], font=("Courier", 11, "bold"))
        spd.pack(anchor="w")
        sta = tk.Label(f, text="YARD", bg=C["bg_card"],
                       fg=C["text_dim"], font=("Courier", 8))
        sta.pack(anchor="w")
        fl = tk.Label(f, text="OK", bg=C["bg_card"], fg=C["ok"],
                      font=("Courier", 8, "bold"))
        fl.pack(anchor="w")
        return {"frame": f, "spd": spd, "sta": sta, "fl": fl}

    #  status bar 

    def _build_status_bar(self):
        bar = tk.Frame(self.root, bg="#0a0000", height=32)
        bar.pack(fill=tk.X, side=tk.BOTTOM)
        bar.pack_propagate(False)
        self.status_lbl = tk.Label(bar, text="●  System Ready  –  Auto Mode",
                                    bg="#0a0000", fg=C["ok"],
                                    font=("Courier", 10, "bold"),
                                    anchor="w", padx=14)
        self.status_lbl.pack(side=tk.LEFT, fill=tk.Y)
        self.status_lbl2 = tk.Label(bar, text="",
                                     bg="#0a0000", fg=C["text_dim"],
                                     font=("Courier", 9), anchor="e", padx=14)
        self.status_lbl2.pack(side=tk.RIGHT, fill=tk.Y)

    #  EVENT HANDLERS
   

    @property
    def T(self): return self.trains[self.active]

    def _set_status(self, msg, color=None):
        self.status_lbl.config(text=f"●  {msg}", fg=color or C["ok"])

    #  Emergency Brake 

    def _on_ebrake(self):
        t = self.T
        if not t.emergency_brake:
            t._activate_ebrake()
            self.ebrake_active[self.active] = True
            self.ebrake_btn.config(bg="#4a0000",
                text="⚠  E-BRAKE ACTIVE  –  CLICK TO RELEASE")
            self.ebrake_status.config(text="● ACTIVE", fg=C["fault"])
            self._set_status("EMERGENCY BRAKE ACTIVE", C["fault"])
        else:
            t.release_ebrake()
            self.ebrake_active[self.active] = bool(t.emergency_brake)
            self.ebrake_btn.config(bg=C["accent"], text="🚨  EMERGENCY BRAKE")
            self.ebrake_status.config(text="● INACTIVE", fg=C["ok"])
            self._set_status("Emergency Brake Released")

    #  Service Brake 

    def _on_brake(self):
        t = self.T
        t.service_brake = not t.service_brake
        self.svc_brake_on[self.active] = bool(t.service_brake)
        if t.service_brake:
            self.brake_btn.config(text="  ON  🔴", bg=C["fault"], fg="white")
            self._set_status("Service Brake Applied", C["warn"])
        else:
            self.brake_btn.config(text="  OFF  ", bg=C["deselect"], fg=C["text_dim"])

    #  Doors 

    def _toggle_left_door(self):
        if not self.T.automatic_mode:
            self.left_door_open[self.active] = not self.left_door_open[self.active]
            self._sync_doors()
        else:
            self._set_status("Doors locked in Auto mode", C["warn"])

    def _toggle_right_door(self):
        if not self.T.automatic_mode:
            self.right_door_open[self.active] = not self.right_door_open[self.active]
            self._sync_doors()
        else:
            self._set_status("Doors locked in Auto mode", C["warn"])

    def _sync_doors(self):
        t   = self.T
        ld  = self.left_door_open[self.active]
        rd  = self.right_door_open[self.active]

        # update controller state
        if   ld and rd: t.doors_state = 3
        elif rd:        t.doors_state = 1
        elif ld:        t.doors_state = 2
        else:           t.doors_state = 0

        # left button
        self.left_door_btn.config(
            bg=C["accent"] if ld else C["deselect"],
            fg="white"     if ld else C["text_dim"],
            text="◀  LEFT DOOR\n🔓  OPEN" if ld else "◀  LEFT DOOR\n🔒  CLOSED")

        # right button
        self.right_door_btn.config(
            bg=C["accent"] if rd else C["deselect"],
            fg="white"     if rd else C["text_dim"],
            text="RIGHT DOOR  ▶\n🔓  OPEN" if rd else "RIGHT DOOR  ▶\n🔒  CLOSED")

        # status label
        if   ld and rd: txt, col = "◀▶  BOTH OPEN",   C["warn"]
        elif ld:        txt, col = "◀  LEFT OPEN",     C["accent"]
        elif rd:        txt, col = "RIGHT OPEN  ▶",    C["accent"]
        else:           txt, col = "🚪  BOTH CLOSED",  C["ok"]
        self.door_status_lbl.config(text=txt, fg=col)

    #  Lights 

    def _toggle_ext_light(self):
        if not self.T.automatic_mode:
            self.ext_light_on[self.active] = not self.ext_light_on[self.active]
            self._sync_lights()
        else:
            self._set_status("Lights locked in Auto mode", C["warn"])

    def _toggle_int_light(self):
        if not self.T.automatic_mode:
            self.int_light_on[self.active] = not self.int_light_on[self.active]
            self._sync_lights()
        else:
            self._set_status("Lights locked in Auto mode", C["warn"])

    def _sync_lights(self):
        t   = self.T
        ext = self.ext_light_on[self.active]
        int_ = self.int_light_on[self.active]

        t.headlights      = ext
        t.interior_lights = 1 if int_ else 0

        self.ext_light_btn.config(
            bg=C["warn"]   if ext  else C["deselect"],
            fg="white"     if ext  else C["text_dim"],
            text="🔦  EXTERNAL\n●  ON" if ext else "🔦  EXTERNAL\n●  OFF")

        self.int_light_btn.config(
            bg="#005588"   if int_ else C["deselect"],
            fg="white"     if int_ else C["text_dim"],
            text="🏠  INTERNAL\n●  ON" if int_ else "🏠  INTERNAL\n●  OFF")

        if   ext and int_: txt, col = "🔦 Ext + 🏠 Int ON", C["warn"]
        elif ext:           txt, col = "🔦  EXTERNAL ON",    C["warn"]
        elif int_:          txt, col = "🏠  INTERNAL ON",    "#5599ff"
        else:               txt, col = "All OFF",            C["text_dim"]
        self.light_status_lbl.config(text=txt, fg=col)

    #  Mode 

    def _on_mode(self, val):
        t = self.T
        if val == "Auto":
            t.set_auto()
            self.mode_btns["Auto"].config(bg="#006600", fg="white")
            self.mode_btns["Manual"].config(bg=C["deselect"], fg=C["text_dim"])
            self._set_status("Auto Mode Active")
        else:
            t.set_manual(t.manual_speed_target)
            self.mode_btns["Manual"].config(bg=C["accent"], fg="white")
            self.mode_btns["Auto"].config(bg=C["deselect"], fg=C["text_dim"])
            self._set_status("Manual Mode Active – set target speed", C["warn"])
        self._ensure_engineer_inputs_enabled()

    #  Set Speed 

    def _on_set_speed(self):
        try:
            spd = float(self.manual_spd_var.get())
            if not (0 <= spd <= 80):
                self._set_status("Speed must be 0–80 mph", C["warn"]); return
            self.mode_btns["Manual"].config(bg=C["accent"], fg="white")
            self.mode_btns["Auto"].config(bg=C["deselect"], fg=C["text_dim"])
            self.T.set_manual(spd)
            self._set_status(f"Manual – target {spd:.1f} mph", C["warn"])
        except ValueError:
            self._set_status("Invalid speed value", C["fault"])

    #  Kp / Ki (always editable) 

    def _ensure_engineer_inputs_enabled(self):
        moving = self.T.current_speed > 0.0
        if moving:
            state = "disabled"
            bg = "#202020"
            fg = C["text_dim"]
        else:
            state = "normal"
            bg = C["bg_dark"]
            fg = C["text_lcd"]
        for w in (self.kp_entry, self.ki_entry):
            w.config(state=state, bg=bg, fg=fg)

    def _nudge_temp(self, delta_f):
        t = self.T
        t.cabin_temp = max(50.0, min(80.0, t.cabin_temp + delta_f))
        self.temp_lbl.config(text=f"{t.cabin_temp:.1f}")
        self._set_status(f"Cabin temperature set to {t.cabin_temp:.1f} °F")

    def _on_kp(self):
        self._ensure_engineer_inputs_enabled()
        try:
            v = float(self.kp_entry.get())
            self.T.kp = v
            self.kp_disp.config(text=f"= {v}", fg=C["ok"])
            self._set_status(f"Kp updated → {v}")
        except ValueError:
            self._set_status("Invalid Kp value", C["fault"])

    def _on_ki(self):
        self._ensure_engineer_inputs_enabled()
        try:
            v = float(self.ki_entry.get())
            self.T.ki = v
            self.ki_disp.config(text=f"= {v}", fg=C["ok"])
            self._set_status(f"Ki updated → {v}")
        except ValueError:
            self._set_status("Invalid Ki value", C["fault"])

    #  Fault simulation 

    def _sim_fault(self, kind):
        t = self.T
        if kind == "power":
            t.set_power_fault(not t.fault_power)
            self.pwr_sim_btn.config(bg=C["fault"] if t.fault_power else "#994400")
        elif kind == "brake":
            t.set_brake_fault(not t.fault_brake)
            self.brk_sim_btn.config(bg=C["fault"] if t.fault_brake else "#994400")
        elif kind == "signal":
            t.set_signal_fault(not t.fault_signal)
            self.sig_sim_btn.config(bg=C["fault"] if t.fault_signal else "#994400")
        if t.any_fault:
            self._set_status(f"FAULT DETECTED on Train {t.train_id}", C["fault"])

    #  CTC inputs 

    def _apply_cmd_spd(self):
        try: self.T.commanded_speed = float(self.ctc_spd.get())
        except ValueError: pass

    def _apply_auth(self):
        try: self.T.authority = float(self.ctc_auth.get())
        except ValueError: pass

    def _apply_pass(self):
        try: self.T.passengers = int(self.ctc_pass.get())
        except ValueError: pass

    def _apply_cur_spd(self):
        try: self.T.current_speed = float(self.ctc_cspe.get())
        except ValueError: pass

    # ── Simulation ───────────────────────────────────────────

    def _toggle_sim(self):
        if self._ipc_port is not None:
            self._set_status("Simulation disabled (integrated mode)", C["warn"])
            return
        self.sim_running = not self.sim_running
        if self.sim_running:
            self.sim_btn.config(text="⏸  STOP SIMULATION", bg=C["accent_dim"])
            self._sim_step()
        else:
            self.sim_btn.config(text="▶  START SIMULATION", bg="#005500")
            self._ensure_engineer_inputs_enabled()

    def _sim_step(self):
        if not self.sim_running: return
        for t in self.trains:
            target = t.commanded_speed if t.automatic_mode else t.manual_speed_target
            if t.emergency_brake and t.current_speed > 0:
                t.current_speed = max(0.0, t.current_speed - 2.0)
            elif t.service_brake and t.current_speed > 0:
                t.current_speed = max(0.0, t.current_speed - 1.0)
            elif t.current_speed < target and not t.emergency_brake and t.authority > 0:
                t.current_speed = min(target, t.current_speed + 0.5)
            t.update(0.1)
        self.root.after(100, self._sim_step)

    
    #  DISPLAY REFRESH
  

    def _refresh_all(self):
        self._refresh_controls()
        self._refresh_mini_cards()
        self._refresh_clock()
        self._ensure_engineer_inputs_enabled()
        self._ipc_send_controller_inputs()
        self.root.after(100, self._refresh_all)

    def _refresh_controls(self):
        t   = self.T
        idx = self.active
        DOOR  = {0:"Closed",1:"Right",2:"Left",3:"Both"}
        light = ("External" if t.headlights else
                 ("Internal" if t.interior_lights else "Off"))

        # Auto door behavior:
        # - In Auto, driver cannot interact with doors (disable buttons).
        # - When stopped at a station, doors open; when departing, doors close.
        try:
            door_state = "disabled" if t.automatic_mode else "normal"
            self.left_door_btn.config(state=door_state)
            self.right_door_btn.config(state=door_state)
        except Exception:
            pass

        if t.automatic_mode:
            try:
                stopped = float(getattr(t, "current_speed", 0.0)) <= 0.1
            except Exception:
                stopped = False
            station = str(getattr(t, "next_station", "") or "").strip()
            at_station = stopped and station and station.upper() not in ("—", "YARD")
            if at_station:
                self.left_door_open[idx] = True
                self.right_door_open[idx] = True
            else:
                # Leaving station (or not at one): keep closed in Auto.
                self.left_door_open[idx] = False
                self.right_door_open[idx] = False

        self.disp_actual_spd.config(text=f"{t.current_speed:.1f}")
        self.disp_cmd_spd.config(text=f"{t.commanded_speed:.1f}")
        self.disp_speed_limit.config(text=f"{t.speed_limit:.1f}")
        self.disp_temp.config(text=f"{t.cabin_temp:.1f}")
        # distance and authority mirrored from the Train Model via backend
        dist_km = getattr(t, "distance_travelled_km", 0.0)
        self.disp_distance.config(text=f"{dist_km * 0.621371:.3f}")
        self.disp_authority.config(text=f"{t.authority*0.000621371:.3f}")
        self.disp_passengers.config(text=str(t.passengers))
        self.disp_next_station.config(text=t.next_station)
        self.disp_power.config(text=f"{t.power_output:,.0f}")

        for key, attr in [("power","fault_power"),
                           ("brake","fault_brake"),
                           ("signal","fault_signal")]:
            self.fault_lbls[key].config(
                fg=C["fault"] if getattr(t, attr) else C["text_dim"])

        self.stat_mode.config(
            text="AUTO" if t.automatic_mode else "MANUAL",
            fg=C["ok"] if t.automatic_mode else C["warn"])
        self.stat_doors.config(
            text=DOOR.get(t.doors_state,"Closed"),
            fg=C["warn"] if t.doors_state else C["ok"])
        self.stat_lights.config(text=light,
            fg=C["warn"] if light!="Off" else C["text_dim"])
        self.stat_ebrake.config(
            text="ACTIVE" if t.emergency_brake else "OFF",
            fg=C["fault"] if t.emergency_brake else C["ok"])

        # Make it obvious whether we're seeing a true fault vs an authority-triggered e-brake.
        if getattr(t, "emergency_brake", False) and not getattr(t, "any_fault", False):
            why = getattr(t, "ebrake_reason", "") or "EMERGENCY"
            self.status_lbl.config(text=f"●  E-BRAKE ACTIVE  –  {why}", fg=C["warn"])
        elif getattr(t, "any_fault", False):
            why = getattr(t, "ebrake_reason", "") or "FAULT"
            self.status_lbl.config(text=f"●  FAULT ACTIVE  –  {why}", fg=C["fault"])

        # ── sync e-brake button to THIS train's stored state ──
        if self.ebrake_active[idx]:
            self.ebrake_btn.config(bg="#4a0000",
                text="⚠  E-BRAKE ACTIVE – CLICK TO RELEASE")
            self.ebrake_status.config(text="● ACTIVE", fg=C["fault"])
        else:
            self.ebrake_btn.config(bg=C["accent"],
                text="🚨  EMERGENCY BRAKE")
            self.ebrake_status.config(text="● INACTIVE", fg=C["ok"])

        # ── sync service brake button to THIS train's stored state ──
        if self.svc_brake_on[idx]:
            self.brake_btn.config(text="  ON  🔴", bg=C["fault"], fg="white")
        else:
            self.brake_btn.config(text="  OFF  ", bg=C["deselect"], fg=C["text_dim"])

        # also catch internally triggered e-brake (e.g. from authority monitor)
        if t.emergency_brake and not self.ebrake_active[idx]:
            self.ebrake_active[idx] = True
            self.ebrake_btn.config(bg="#4a0000",
                text="⚠  E-BRAKE ACTIVE – CLICK TO RELEASE")
            self.ebrake_status.config(text="● ACTIVE", fg=C["fault"])

        # sync door & light buttons
        self._sync_doors()
        self._sync_lights()

        self.status_lbl2.config(
            text=f"Train {t.train_id}  |  "
                 f"Spd {t.current_speed:.1f} mph  |  "
                 f"Auth {t.authority:.0f} m  |  "
                 f"Pwr {t.power_output:,.0f} W")

    def _refresh_mini_cards(self):
        for i, (t, mc) in enumerate(zip(self.trains, self.mini_cards)):
            mc["spd"].config(text=f"{t.current_speed:.1f} mph")
            mc["sta"].config(text=t.next_station)
            is_fault = bool(getattr(t, "any_fault", False))
            is_ebrake = bool(getattr(t, "emergency_brake", False))
            if is_fault:
                label = "⚠ FAULT"
                fg = C["fault"]
                bg = "#1a0000"
            elif is_ebrake:
                label = "⚠ E-BRAKE"
                fg = C["warn"]
                bg = "#1a0000"
            else:
                label = "● OK"
                fg = C["ok"]
                bg = C["bg_card"]
            mc["fl"].config(text=label, fg=fg, bg=bg)
            for w in (mc["frame"], mc["spd"], mc["sta"]):
                w.config(bg=bg)

    def _refresh_clock(self):
        t = time.localtime()
        self.clock_lbl.config(
            text=f"{t.tm_hour:02d}:{t.tm_min:02d}:{t.tm_sec:02d}")

    
    #  TEST UI WINDOW
   

    def _open_test_ui(self):
        win = tk.Toplevel(self.root)
        win.title(f"Test UI – Train {self.active+1}")
        win.configure(bg=C["bg_dark"])
        win.geometry("720x760")

        tk.Label(win, text=f"TEST UI  –  TRAIN {self.active+1}",
                 bg=C["bg_header"], fg=C["accent2"],
                 font=("Courier", 13, "bold"), pady=10
                 ).pack(fill=tk.X)

        body = tk.Frame(win, bg=C["bg_dark"])
        body.pack(fill=tk.BOTH, expand=True, padx=10, pady=8)

        lf = tk.LabelFrame(body, text="  INPUTS", bg=C["bg_panel"],
                            fg=C["accent2"], font=("Courier", 10, "bold"),
                            padx=8, pady=8, relief=tk.FLAT,
                            highlightbackground=C["border"],
                            highlightthickness=1)
        lf.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=(0,5))

        rf = tk.LabelFrame(body, text="  OUTPUTS", bg=C["bg_panel"],
                            fg=C["ok"], font=("Courier", 10, "bold"),
                            padx=8, pady=8, relief=tk.FLAT,
                            highlightbackground=C["border"],
                            highlightthickness=1)
        rf.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=(5,0))

        t = self.T
        DOOR  = {0:"Closed",1:"Right",2:"Left",3:"Both"}
        light = "External" if t.headlights else ("Internal" if t.interior_lights else "Off")

        in_rows = [
            ("─ From Train Model ─",  None),
            ("Commanded Spd (km/hr)", f"{t.commanded_speed*1.60934:.1f}"),
            ("Authority (km)",        f"{t.authority/1000:.3f}"),
            ("Actual Speed (km/hr)",  f"{t.current_speed*1.60934:.1f}"),
            ("Power Fault",           str(t.fault_power)),
            ("Brake Fault",           str(t.fault_brake)),
            ("Signal Fault",          str(t.fault_signal)),
            ("Next Station",          t.next_station),
            ("Passengers",            str(t.passengers)),
            ("─ From Engineer ─",     None),
            ("Kp",                    str(t.kp)),
            ("Ki",                    str(t.ki)),
            ("─ From Driver ─",       None),
            ("Emergency Brake",       str(t.emergency_brake)),
            ("Service Brake",         str(t.service_brake)),
            ("Door State",            DOOR.get(t.doors_state,"Closed")),
            ("Mode",                  "Auto" if t.automatic_mode else "Manual"),
            ("Set Speed (km/hr)",     f"{t.manual_speed_target*1.60934:.0f}"),
            ("Lights",                light),
        ]

        out_rows = [
            ("─ To Driver ─",         None),
            ("Speed Display (km/hr)", f"{t.current_speed*1.60934:.1f}"),
            ("Authority (km)",        f"{t.authority/1000:.3f}"),
            ("Authority (m)",         f"{t.authority:.0f}"),
            ("Next Station",          t.next_station),
            ("Power Command (W)",     f"{t.power_output:,.0f}"),
            ("─ To Train Model ─",    None),
            ("Velocity Cmd (km/hr)",  f"{t.commanded_speed*1.60934:.1f}"),
            ("Door",                  DOOR.get(t.doors_state,"Closed")),
            ("Lights",                light),
            ("Emergency Brake",       str(t.emergency_brake)),
            ("Temperature (°F)",      str(t.cabin_temp)),
            ("Service Brake",         str(t.service_brake)),
        ]

        def _rows(parent, rows, val_bg):
            for lbl, val in rows:
                if val is None:
                    tk.Label(parent, text=lbl, bg=C["accent_dim"],
                             fg="white", font=("Courier", 8, "bold"),
                             anchor="w", padx=4).pack(fill=tk.X, pady=(6,1))
                else:
                    r = tk.Frame(parent, bg=C["bg_panel"]); r.pack(fill=tk.X, pady=1)
                    tk.Label(r, text=lbl, bg=C["bg_panel"], fg=C["text_dim"],
                             font=("Courier", 8), width=22, anchor="w"
                             ).pack(side=tk.LEFT)
                    tk.Label(r, text=f"[{val}]", bg=val_bg, fg=C["text"],
                             font=("Courier", 8, "bold"), width=14,
                             anchor="center", padx=4
                             ).pack(side=tk.RIGHT)

        _rows(lf, in_rows,  "#1a1000")
        _rows(rf, out_rows, "#001a00")

  

    def run(self):
        self.root.mainloop()



if __name__ == "__main__":
    ipc_host = os.environ.get("TRAIN_IPC_HOST")
    ipc_port = os.environ.get("TRAIN_IPC_PORT")
    if ipc_port:
        app = TrainControllerApp(show_test_ui_button=False, ipc_host=ipc_host or "127.0.0.1", ipc_port=int(ipc_port))
    else:
        app = TrainControllerApp()
    app.run()