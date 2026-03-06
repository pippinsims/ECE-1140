import os, sys, math, time
os.environ['TK_SILENCE_DEPRECATION'] = '1'
import tkinter as tk
from tkinter import ttk, font as tkfont


#  COLOR PALETTE  –  Red & Black Industrial

C = {
    "bg_dark":    "#0d0d0d",   # main background
    "bg_panel":   "#1a1a1a",   # panel background
    "bg_card":    "#222222",   # card / inner box
    "bg_header":  "#1a0000",   # header strip
    "accent":     "#cc0000",   # primary red
    "accent2":    "#ff3333",   # bright red (hover / active)
    "accent_dim": "#660000",   # dim red
    "ok":         "#00cc44",   # green for good states
    "warn":       "#ff8800",   # orange warning
    "fault":      "#ff2222",   # fault red (bright)
    "text":       "#f0f0f0",   # primary text
    "text_dim":   "#888888",   # secondary text
    "text_lcd":   "#ff4444",   # lcd-style value color
    "border":     "#3a0000",   # panel border
    "select":     "#cc0000",   # selected button
    "deselect":   "#2a2a2a",   # unselected button
    "train_sel":  "#3a0a0a",   # selected train tab
}


#  TRAIN CONTROLLER LOGIC


class TrainController:
    def __init__(self, train_id=1):
        self.train_id             = train_id
        self.current_speed        = 0.0    # mph
        self.commanded_speed      = 0.0    # mph
        self.speed_limit          = 30.0   # mph
        self.authority            = 500.0  # meters
        self.kp                   = 10.0
        self.ki                   = 8000.0
        self.power_output         = 0.0    # Watts
        self.uk                   = 0.0
        self.prev_error           = 0.0
        self.prev_uk              = 0.0
        self.emergency_brake      = False
        self.service_brake        = False
        self.MAX_POWER            = 120_000
        self.SERVICE_DECEL        = 1.2
        self.EMERGENCY_DECEL      = 2.73
        self.fault_power          = False
        self.fault_brake          = False
        self.fault_signal         = False
        self.automatic_mode       = True
        self.doors_state          = 0      # 0=closed,1=right,2=left,3=both
        self.headlights           = False
        self.interior_lights      = 0
        self.cabin_temp           = 70
        self.passengers           = 0
        self.next_station         = "YARD"
        self.driver_power_req     = 0
        self.manual_speed_target  = 0.0

  

    def _stop_dist(self, decel):
        v = self.current_speed * 0.44704
        return (v**2 / (2*decel) + v*0.1) if decel > 0 else 0.0

    def monitor(self):
        svc = self._stop_dist(self.SERVICE_DECEL)
        emg = self._stop_dist(self.EMERGENCY_DECEL)

        if 5 <= self.authority <= emg:
            self._activate_ebrake(); return
        if self.authority <= svc or (self.authority < 0 and self.current_speed > 0):
            self.service_brake = True; self.driver_power_req = 0; return
        if self.current_speed > self.speed_limit:
            self.service_brake = True; self.driver_power_req = 0; return
        if self.current_speed > self.commanded_speed:
            self.service_brake = True; self.driver_power_req = 0; return

        if self.automatic_mode:
            if self.current_speed < self.commanded_speed and self.current_speed < self.speed_limit:
                self.driver_power_req = (25 if self.authority<=50 else 50 if self.authority<=60 else 100)
                self.service_brake = False
            else:
                self.driver_power_req = 0; self.service_brake = False

    def calc_power(self, dt):
        if self.emergency_brake or self.service_brake:
            self.power_output = 0; self.uk = 0; return 0.0
        if self.driver_power_req == 0:
            self.power_output = 0; return 0.0
        cmd_v = (self.commanded_speed if self.automatic_mode else self.manual_speed_target) * 0.44704
        err   = cmd_v - self.current_speed * 0.44704
        self.uk = self.prev_uk + (dt/2)*(err + self.prev_error)
        pwr = (self.kp*err + self.ki*self.uk) * (self.driver_power_req/100.0)
        self.prev_error = err; self.prev_uk = self.uk
        self.power_output = max(0.0, min(float(self.MAX_POWER), pwr))
        return self.power_output

    def update_auth(self, dt):
        if self.current_speed > 0:
            self.authority -= self.current_speed * 0.00044704 * dt * 1000

    def update(self, dt):
        self.monitor(); self.calc_power(dt); self.update_auth(dt)

    #  failures 

    def _activate_ebrake(self):
        self.emergency_brake = True; self.power_output = 0
        self.driver_power_req = 0; self.service_brake = False

    def release_ebrake(self):
        if not (self.fault_power or self.fault_brake or self.fault_signal):
            self.emergency_brake = False

    def set_power_fault(self, v):
        self.fault_power = v
        if v: self._activate_ebrake()

    def set_brake_fault(self, v):
        self.fault_brake = v
        if v: self._activate_ebrake()

    def set_signal_fault(self, v):
        self.fault_signal = v
        if v: self._activate_ebrake()

    #  non-vital 

    def set_doors(self, s):
        if self.current_speed == 0: self.doors_state = s

    def set_lights(self, mode):
        if   mode == "Off":      self.headlights = False; self.interior_lights = 0
        elif mode == "External": self.headlights = True;  self.interior_lights = 0
        elif mode == "Internal": self.headlights = False; self.interior_lights = 1

    def set_auto(self): self.automatic_mode = True
    def set_manual(self, spd):
        self.automatic_mode = False; self.manual_speed_target = spd; self.driver_power_req = 50

    @property
    def any_fault(self): return self.fault_power or self.fault_brake or self.fault_signal



#  UI HELPER WIDGETS


def sep(parent, color=C["border"], pady=4):
    f = tk.Frame(parent, bg=color, height=1)
    f.pack(fill=tk.X, pady=pady)

def card(parent, title="", bg=C["bg_card"], pad=10):
    outer = tk.Frame(parent, bg=C["border"], bd=0)
    outer.pack(fill=tk.X, pady=4, padx=2)
    if title:
        th = tk.Frame(outer, bg=C["accent_dim"])
        th.pack(fill=tk.X)
        tk.Label(th, text=f"  {title.upper()}", bg=C["accent_dim"],
                 fg=C["text"], font=("Courier", 9, "bold"), anchor="w",
                 pady=3).pack(fill=tk.X)
    inner = tk.Frame(outer, bg=bg, padx=pad, pady=pad)
    inner.pack(fill=tk.X)
    return inner

def lcd_label(parent, width=12, font_size=20):
    """Red LCD-style value display."""
    lbl = tk.Label(parent, text="0", bg="#0a0000", fg=C["text_lcd"],
                   font=("Courier", font_size, "bold"),
                   width=width, anchor="e", padx=8, pady=4,
                   relief=tk.FLAT, bd=0)
    return lbl

def section_title(parent, text):
    f = tk.Frame(parent, bg=C["bg_panel"])
    f.pack(fill=tk.X, pady=(10, 2))
    tk.Frame(f, bg=C["accent"], width=4).pack(side=tk.LEFT, fill=tk.Y)
    tk.Label(f, text=f"  {text}", bg=C["bg_panel"], fg=C["accent2"],
             font=("Courier", 11, "bold")).pack(side=tk.LEFT, pady=4)


def pill_button(parent, text, command, color=C["accent"], fg="white",
                width=10, font_size=11):
    btn = tk.Button(parent, text=text, command=command,
                    bg=color, fg=fg, activebackground=C["accent2"],
                    activeforeground="white",
                    font=("Courier", font_size, "bold"),
                    relief=tk.FLAT, bd=0, padx=10, pady=6,
                    cursor="hand2", width=width)
    return btn


def toggle_group(parent, options, command, bg_sel=C["accent"],
                 bg_desel=C["deselect"], font_size=10):
    """Radio-style toggle button group. Returns (frame, var, buttons_dict)."""
    var  = tk.StringVar(value=options[0][1])
    btns = {}
    frm  = tk.Frame(parent, bg=C["bg_card"])

    def _click(val):
        var.set(val)
        for v, b in btns.items():
            b.config(bg=bg_sel if v==val else bg_desel,
                     fg="white" if v==val else C["text_dim"])
        command(val)

    for txt, val in options:
        b = tk.Button(frm, text=txt,
                      bg=bg_sel if val==options[0][1] else bg_desel,
                      fg="white" if val==options[0][1] else C["text_dim"],
                      font=("Courier", font_size, "bold"),
                      relief=tk.FLAT, bd=0, padx=8, pady=5,
                      cursor="hand2",
                      command=lambda v=val: _click(v))
        b.pack(side=tk.LEFT, padx=2)
        btns[val] = b
    return frm, var, btns


def fault_badge(parent, text):
    lbl = tk.Label(parent, text=f"● {text}", bg=C["bg_card"],
                   fg=C["text_dim"], font=("Courier", 11, "bold"),
                   padx=8, pady=4)
    return lbl



#  MAIN APPLICATION


class TrainControllerApp:

    NUM_TRAINS = 3

    def __init__(self):
        # Create 3 independent controllers
        self.trains   = [TrainController(i+1) for i in range(self.NUM_TRAINS)]
        self.active   = 0          # index of currently viewed train
        self.sim_running = False

        # Pre-set demo data so UI looks alive on launch
        self.trains[0].commanded_speed = 30; self.trains[0].passengers = 42
        self.trains[0].next_station    = "CENTRAL"
        self.trains[1].commanded_speed = 25; self.trains[1].passengers = 18
        self.trains[1].next_station    = "OVERBROOK"; self.trains[1].authority = 1200
        self.trains[2].commanded_speed = 0;  self.trains[2].passengers = 0
        self.trains[2].next_station    = "YARD"; self.trains[2].authority = 0

        self._build_root()
        self._build_header()
        self._build_body()
        self._build_status_bar()
        self._refresh_all()

    #  root window 

    def _build_root(self):
        self.root = tk.Tk()
        self.root.title("Train Controller  –  PAAC North Shore")
        self.root.configure(bg=C["bg_dark"])
        self.root.geometry("1300x860")
        self.root.minsize(1100, 760)
        # custom title bar feel with resizable
        self.root.resizable(True, True)

    #  header 

    def _build_header(self):
        hdr = tk.Frame(self.root, bg=C["bg_header"], height=64)
        hdr.pack(fill=tk.X, side=tk.TOP)
        hdr.pack_propagate(False)

        # Logo block
        logo_f = tk.Frame(hdr, bg=C["accent"], padx=14, pady=0)
        logo_f.pack(side=tk.LEFT, fill=tk.Y)
        tk.Label(logo_f, text="TC", bg=C["accent"], fg="white",
                 font=("Courier", 26, "bold")).pack(expand=True)

        # Title
        tk.Label(hdr, text="  TRAIN CONTROLLER", bg=C["bg_header"],
                 fg="white", font=("Courier", 20, "bold")).pack(side=tk.LEFT, pady=10)
        tk.Label(hdr, text="  PAAC North Shore Extension",
                 bg=C["bg_header"], fg=C["text_dim"],
                 font=("Courier", 10)).pack(side=tk.LEFT, pady=10)

        # Right side – clock & test UI button
        right = tk.Frame(hdr, bg=C["bg_header"])
        right.pack(side=tk.RIGHT, padx=16, fill=tk.Y)

        self.clock_lbl = tk.Label(right, text="00:00:00", bg=C["bg_header"],
                                   fg=C["accent2"], font=("Courier", 16, "bold"))
        self.clock_lbl.pack(side=tk.TOP, pady=(8, 0))

        pill_button(right, "TEST UI", self._open_test_ui,
                    color=C["accent_dim"], font_size=9, width=8
                    ).pack(side=tk.TOP, pady=4)

    #  body 

    def _build_body(self):
        body = tk.Frame(self.root, bg=C["bg_dark"])
        body.pack(fill=tk.BOTH, expand=True, padx=10, pady=(6, 0))

        # ── LEFT PANEL ──
        left = tk.Frame(body, bg=C["bg_panel"], width=420)
        left.pack(side=tk.LEFT, fill=tk.Y, padx=(0, 6))
        left.pack_propagate(False)

        # Train selector tabs
        self._build_train_tabs(left)

        # Scrollable controls area
        ctrl_canvas = tk.Canvas(left, bg=C["bg_panel"], highlightthickness=0)
        ctrl_scroll = tk.Scrollbar(left, orient="vertical", command=ctrl_canvas.yview,
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

        # ── RIGHT PANEL ──
        right = tk.Frame(body, bg=C["bg_panel"])
        right.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        self._build_right(right)

    #  train selector tabs 

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

        # thin status indicators under tabs
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
        self._refresh_controls()

    #  left controls 

    def _build_controls(self, parent):

        #  Emergency Brake 
        section_title(parent, "Emergency Brake")
        eb_card = card(parent, bg="#1a0000", pad=12)
        self.ebrake_btn = tk.Button(eb_card,
            text="🚨  EMERGENCY BRAKE",
            font=("Courier", 14, "bold"),
            bg=C["accent"], fg="white",
            activebackground="#ff0000",
            relief=tk.FLAT, bd=0, pady=14,
            cursor="hand2",
            command=self._on_ebrake)
        self.ebrake_btn.pack(fill=tk.X)
        self.ebrake_status = tk.Label(eb_card, text="● INACTIVE",
                                       bg="#1a0000", fg=C["ok"],
                                       font=("Courier", 10, "bold"))
        self.ebrake_status.pack(pady=(6, 0))

        #  Service Brake 
        section_title(parent, "Service Brake")
        brk_card = card(parent, pad=10)
        brk_row = tk.Frame(brk_card, bg=C["bg_card"])
        brk_row.pack(fill=tk.X)
        tk.Label(brk_row, text="Service Brake", bg=C["bg_card"],
                 fg=C["text"], font=("Courier", 11)).pack(side=tk.LEFT, padx=4)
        self.brake_btn = tk.Button(brk_row, text="  OFF  ",
                                    font=("Courier", 10, "bold"),
                                    bg=C["deselect"], fg=C["text_dim"],
                                    relief=tk.FLAT, bd=0, padx=10, pady=4,
                                    cursor="hand2", command=self._on_brake)
        self.brake_btn.pack(side=tk.RIGHT)

        #  Doors 
        section_title(parent, "Doors")
        door_card = card(parent, pad=12)

        # Status indicator
        door_status_row = tk.Frame(door_card, bg=C["bg_card"])
        door_status_row.pack(fill=tk.X, pady=(0, 8))
        tk.Label(door_status_row, text="Current:", bg=C["bg_card"],
                 fg=C["text_dim"], font=("Courier", 9)).pack(side=tk.LEFT)
        self.door_status_lbl = tk.Label(door_status_row, text="🚪  CLOSED",
                 bg=C["bg_card"], fg=C["ok"],
                 font=("Courier", 10, "bold"))
        self.door_status_lbl.pack(side=tk.LEFT, padx=8)

        # Big clear door buttons in a 2x2 grid
        self.door_var = tk.StringVar(value="0")
        self.door_btns = {}
        door_grid = tk.Frame(door_card, bg=C["bg_card"])
        door_grid.pack(fill=tk.X)

        door_defs = [
            ("🚪\nCLOSED",  "0",  0, 0, C["ok"]),
            ("◀  LEFT\nOPEN", "2",  0, 1, C["accent"]),
            ("RIGHT ▶\nOPEN", "1",  1, 0, C["accent"]),
            ("◀  BOTH  ▶\nOPEN",  "3",  1, 1, C["warn"]),
        ]
        for txt, val, row, col, active_col in door_defs:
            btn = tk.Button(door_grid, text=txt,
                            font=("Courier", 10, "bold"),
                            bg=active_col if val == "0" else C["deselect"],
                            fg="white",
                            relief=tk.FLAT, bd=0,
                            padx=6, pady=10,
                            width=12, cursor="hand2",
                            command=lambda v=val: self._on_door(v))
            btn.grid(row=row, column=col, padx=4, pady=4, sticky="ew")
            self.door_btns[val] = btn
        door_grid.columnconfigure(0, weight=1)
        door_grid.columnconfigure(1, weight=1)

        #  Lights 
        section_title(parent, "Lights")
        light_card = card(parent, pad=12)

        # Status indicator
        light_status_row = tk.Frame(light_card, bg=C["bg_card"])
        light_status_row.pack(fill=tk.X, pady=(0, 8))
        tk.Label(light_status_row, text="Current:", bg=C["bg_card"],
                 fg=C["text_dim"], font=("Courier", 9)).pack(side=tk.LEFT)
        self.light_status_lbl = tk.Label(light_status_row, text="💡  OFF",
                 bg=C["bg_card"], fg=C["text_dim"],
                 font=("Courier", 10, "bold"))
        self.light_status_lbl.pack(side=tk.LEFT, padx=8)

        # Three big light buttons side by side
        self.light_var = tk.StringVar(value="Off")
        self.light_btns = {}
        light_row = tk.Frame(light_card, bg=C["bg_card"])
        light_row.pack(fill=tk.X)

        light_defs = [
            ("💡\nOFF",       "Off",      C["deselect"], C["text_dim"]),
            ("🔦\nEXTERNAL",  "External", C["warn"],     "white"),
            ("🏠\nINTERNAL",  "Internal", "#005588",     "white"),
        ]
        for txt, val, active_col, active_fg in light_defs:
            is_sel = (val == "Off")
            btn = tk.Button(light_row, text=txt,
                            font=("Courier", 10, "bold"),
                            bg=C["deselect"] if not is_sel else "#333333",
                            fg=C["text_dim"] if not is_sel else "white",
                            relief=tk.FLAT, bd=0,
                            padx=6, pady=10,
                            width=10, cursor="hand2",
                            command=lambda v=val, ac=active_col, af=active_fg:
                                self._on_light(v, ac, af))
            btn.pack(side=tk.LEFT, padx=4, expand=True, fill=tk.X)
            self.light_btns[val] = (btn, active_col, active_fg)

        #  Operation Mode 
        section_title(parent, "Operation Mode")
        mode_card = card(parent, pad=10)
        mode_opts = [("🤖  AUTO","Auto"),("👤  MANUAL","Manual")]
        self.mode_frm, self.mode_var, self.mode_btns = toggle_group(
            mode_card, mode_opts, self._on_mode, bg_sel="#006600")
        self.mode_frm.pack(fill=tk.X)

        #  Set Speed 
        section_title(parent, "Set Speed  (Manual)")
        spd_card = card(parent, pad=10)
        spd_row = tk.Frame(spd_card, bg=C["bg_card"]); spd_row.pack(fill=tk.X)
        tk.Label(spd_row, text="Target (mph):", bg=C["bg_card"],
                 fg=C["text"], font=("Courier", 10)).pack(side=tk.LEFT, padx=4)
        self.manual_spd_var = tk.StringVar(value="0")
        spd_e = tk.Entry(spd_row, textvariable=self.manual_spd_var,
                          font=("Courier", 12, "bold"), width=6,
                          bg=C["bg_dark"], fg=C["text_lcd"],
                          insertbackground=C["accent"],
                          relief=tk.FLAT, bd=1, justify="center")
        spd_e.pack(side=tk.LEFT, padx=6)
        pill_button(spd_row, "SET", self._on_set_speed,
                    width=6, font_size=10).pack(side=tk.LEFT)

        #  Train Engineer 
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

        #  Fault Simulation 
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

        # ── CTC / Testing Inputs 
        section_title(parent, "CTC / Testing Inputs")
        ctc_card = card(parent, pad=10)

        for label, attr, default, cmd in [
            ("Cmd Speed (mph):", "ctc_spd",  "30",  self._apply_cmd_spd),
            ("Authority (m):",   "ctc_auth", "500", self._apply_auth),
            ("Passengers:",      "ctc_pass", "0",   self._apply_pass),
            ("Sim Speed (mph):", "ctc_cspe", "0",   self._apply_cur_spd),
        ]:
            row = tk.Frame(ctc_card, bg=C["bg_card"]); row.pack(fill=tk.X, pady=3)
            tk.Label(row, text=label, bg=C["bg_card"], fg=C["text_dim"],
                     font=("Courier", 9), width=18, anchor="w").pack(side=tk.LEFT)
            ent = tk.Entry(row, font=("Courier", 10), width=7,
                           bg=C["bg_dark"], fg=C["text_lcd"],
                           insertbackground=C["accent"],
                           relief=tk.FLAT, bd=1, justify="center")
            ent.insert(0, default)
            ent.pack(side=tk.LEFT, padx=4)
            setattr(self, attr, ent)
            pill_button(row, "▶", cmd, width=3, font_size=9).pack(side=tk.LEFT)

        #  Simulation 
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

        #  TOP: per-train mini overview strip 
        overview = tk.Frame(parent, bg=C["bg_dark"])
        overview.pack(fill=tk.X, pady=(0, 6))
        self.mini_cards = []
        for i in range(self.NUM_TRAINS):
            mc = self._make_mini_card(overview, i)
            mc["frame"].pack(side=tk.LEFT, expand=True, fill=tk.X, padx=3)
            self.mini_cards.append(mc)

        #  MAIN OUTPUTS 
        section_title(parent, "Driver Outputs Display")
        out_card = tk.Frame(parent, bg=C["bg_card"], pady=10)
        out_card.pack(fill=tk.X, padx=4)

        out_grid = tk.Frame(out_card, bg=C["bg_card"]); out_grid.pack(padx=10, pady=6)

        def _out_row(row, label, label_bg, attr, unit=""):
            lf = tk.Frame(out_grid, bg=label_bg, padx=10, pady=8)
            lf.grid(row=row, column=0, padx=6, pady=5, sticky="ew")
            tk.Label(lf, text=label, bg=label_bg, fg="white",
                     font=("Courier", 13, "bold"), width=14,
                     anchor="center").pack()
            val_f = tk.Frame(out_grid, bg=C["bg_dark"], padx=4, pady=4)
            val_f.grid(row=row, column=1, padx=6, pady=5, sticky="ew")
            val_lbl = tk.Label(val_f, text="–", bg="#0a0000", fg=C["text_lcd"],
                                font=("Courier", 18, "bold"), width=14,
                                anchor="e", padx=10)
            val_lbl.pack()
            unit_lbl = tk.Label(out_grid, text=unit, bg=C["bg_card"],
                                 fg=C["text_dim"], font=("Courier", 10))
            unit_lbl.grid(row=row, column=2, padx=4)
            setattr(self, attr, val_lbl)

        _out_row(0, "Actual Speed",   "#5a0000",  "disp_actual_spd",  "mph")
        _out_row(1, "Set Speed",      "#3a2000",  "disp_set_spd",     "mph")
        _out_row(2, "Authority",      "#3a3a00",  "disp_authority",   "miles")
        _out_row(3, "Passengers",     "#003050",  "disp_passengers",  "pax")
        _out_row(4, "Next Station",   "#1a1a3a",  "disp_next_station","")
        _out_row(5, "Power Command",  "#003a00",  "disp_power",       "W")

        out_grid.columnconfigure(0, weight=1)
        out_grid.columnconfigure(1, weight=1)

        #  FAULT INDICATORS 
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

        #  SYSTEM STATUS 
        section_title(parent, "System Status")
        stat_card = card(parent, pad=10)
        stat_row = tk.Frame(stat_card, bg=C["bg_card"]); stat_row.pack(fill=tk.X)

        for label, attr in [("Mode","stat_mode"), ("Doors","stat_doors"),
                              ("Lights","stat_lights"), ("E-Brake","stat_ebrake")]:
            col = tk.Frame(stat_row, bg=C["bg_card"]); col.pack(side=tk.LEFT, expand=True)
            tk.Label(col, text=label, bg=C["bg_card"], fg=C["text_dim"],
                     font=("Courier", 9)).pack()
            lbl = tk.Label(col, text="–", bg=C["bg_card"], fg=C["ok"],
                            font=("Courier", 10, "bold"))
            lbl.pack()
            setattr(self, attr, lbl)

    #  mini train card 

    def _make_mini_card(self, parent, idx):
        f = tk.Frame(parent, bg=C["bg_card"], relief=tk.FLAT, bd=0, padx=8, pady=8)
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
                                    font=("Courier", 10, "bold"), anchor="w", padx=14)
        self.status_lbl.pack(side=tk.LEFT, fill=tk.Y)
        self.status_lbl2 = tk.Label(bar, text="",
                                     bg="#0a0000", fg=C["text_dim"],
                                     font=("Courier", 9), anchor="e", padx=14)
        self.status_lbl2.pack(side=tk.RIGHT, fill=tk.Y)

    #  event handlers 

    @property
    def T(self): return self.trains[self.active]

    def _set_status(self, msg, color=None):
        self.status_lbl.config(text=f"●  {msg}",
                                fg=color or C["ok"])

    def _on_ebrake(self):
        t = self.T
        if not t.emergency_brake:
            t._activate_ebrake()
            self.ebrake_btn.config(bg="#4a0000",
                text="⚠  E-BRAKE ACTIVE  –  CLICK TO RELEASE")
            self.ebrake_status.config(text="● ACTIVE", fg=C["fault"])
            self._set_status("EMERGENCY BRAKE ACTIVE", C["fault"])
        else:
            t.release_ebrake()
            self.ebrake_btn.config(bg=C["accent"], text="🚨  EMERGENCY BRAKE")
            self.ebrake_status.config(text="● INACTIVE", fg=C["ok"])
            self._set_status("Emergency Brake Released")

    def _on_brake(self):
        t = self.T
        t.service_brake = not t.service_brake
        if t.service_brake:
            self.brake_btn.config(text="  ON  🔴", bg=C["fault"], fg="white")
            self._set_status("Service Brake Applied", C["warn"])
        else:
            self.brake_btn.config(text="  OFF  ", bg=C["deselect"], fg=C["text_dim"])

    def _on_door(self, val):
        t = self.T
        if not t.automatic_mode:
            t.set_doors(int(val))
            # Update button highlights
            door_labels = {"0":"🚪  CLOSED","1":"RIGHT OPEN","2":"LEFT OPEN","3":"BOTH OPEN"}
            door_colors = {"0": C["ok"], "1": C["accent"], "2": C["accent"], "3": C["warn"]}
            for v, btn in self.door_btns.items():
                if v == val:
                    btn.config(bg=door_colors[v], fg="white")
                else:
                    btn.config(bg=C["deselect"], fg=C["text_dim"])
            self.door_status_lbl.config(
                text=f"🚪  {door_labels.get(val,'CLOSED')}",
                fg=C["ok"] if val=="0" else C["accent"])
            self.door_var.set(val)
        else:
            # Reset all to closed
            for v, btn in self.door_btns.items():
                btn.config(bg=C["ok"] if v=="0" else C["deselect"],
                           fg="white" if v=="0" else C["text_dim"])
            self.door_var.set("0")
            self.door_status_lbl.config(text="🚪  CLOSED", fg=C["ok"])
            self._set_status("Doors locked in Auto mode", C["warn"])

    def _on_light(self, val, active_col=None, active_fg=None):
        t = self.T
        if not t.automatic_mode:
            t.set_lights(val)
            # Update button highlights
            for v, (btn, ac, af) in self.light_btns.items():
                if v == val:
                    btn.config(bg=ac, fg=af)
                else:
                    btn.config(bg=C["deselect"], fg=C["text_dim"])
            light_icons = {"Off":"💡  OFF", "External":"🔦  EXTERNAL", "Internal":"🏠  INTERNAL"}
            light_colors = {"Off": C["text_dim"], "External": C["warn"], "Internal": "#5599ff"}
            self.light_status_lbl.config(
                text=light_icons.get(val, "💡  OFF"),
                fg=light_colors.get(val, C["text_dim"]))
            self.light_var.set(val)
        else:
            for v, (btn, ac, af) in self.light_btns.items():
                btn.config(bg=C["deselect"] if v!="Off" else "#333333",
                           fg=C["text_dim"] if v!="Off" else "white")
            self.light_var.set("Off")
            self.light_status_lbl.config(text="💡  OFF", fg=C["text_dim"])
            self._set_status("Lights locked in Auto mode", C["warn"])

    def _on_mode(self, val):
        t = self.T
        if val == "Auto":
            t.set_auto()
            self._set_status("Auto Mode Active")
        else:
            t.set_manual(t.manual_speed_target)
            self._set_status("Manual Mode Active – set target speed", C["warn"])
        # Kp / Ki are ALWAYS kept enabled regardless of mode or motion
        self._ensure_engineer_inputs_enabled()

    def _on_set_speed(self):
        try:
            spd = float(self.manual_spd_var.get())
            if not (0 <= spd <= 80):
                self._set_status("Speed must be 0–80 mph", C["warn"]); return
            self.mode_btns["Manual"].config(bg=C["accent"], fg="white")
            self.mode_btns["Auto"].config(bg=C["deselect"], fg=C["text_dim"])
            self.mode_var.set("Manual")
            self.T.set_manual(spd)
            self._set_status(f"Manual – target {spd:.1f} mph", C["warn"])
        except ValueError:
            self._set_status("Invalid speed value", C["fault"])

    def _ensure_engineer_inputs_enabled(self):
        """Kp and Ki must ALWAYS be editable — even while train is moving."""
        for widget in (self.kp_entry, self.ki_entry):
            widget.config(state="normal",
                          bg=C["bg_dark"], fg=C["text_lcd"],
                          disabledbackground=C["bg_dark"])

    def _on_kp(self):
        self._ensure_engineer_inputs_enabled()   # safety: re-enable before reading
        try:
            v = float(self.kp_entry.get())
            self.T.kp = v
            self.kp_disp.config(text=f"= {v}", fg=C["ok"])
            self._set_status(f"Kp updated → {v}")
        except ValueError:
            self._set_status("Invalid Kp value", C["fault"])

    def _on_ki(self):
        self._ensure_engineer_inputs_enabled()   # safety: re-enable before reading
        try:
            v = float(self.ki_entry.get())
            self.T.ki = v
            self.ki_disp.config(text=f"= {v}", fg=C["ok"])
            self._set_status(f"Ki updated → {v}")
        except ValueError:
            self._set_status("Invalid Ki value", C["fault"])

    def _sim_fault(self, kind):
        t = self.T
        if kind == "power":
            t.set_power_fault(not t.fault_power)
            active = t.fault_power
            self.pwr_sim_btn.config(bg=C["fault"] if active else "#994400")
        elif kind == "brake":
            t.set_brake_fault(not t.fault_brake)
            active = t.fault_brake
            self.brk_sim_btn.config(bg=C["fault"] if active else "#994400")
        elif kind == "signal":
            t.set_signal_fault(not t.fault_signal)
            active = t.fault_signal
            self.sig_sim_btn.config(bg=C["fault"] if active else "#994400")
        if t.any_fault:
            self._set_status(f"FAULT DETECTED on Train {t.train_id}", C["fault"])

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

    def _toggle_sim(self):
        self.sim_running = not self.sim_running
        if self.sim_running:
            self.sim_btn.config(text="⏸  STOP SIMULATION", bg=C["accent_dim"])
            self._sim_step()
        else:
            self.sim_btn.config(text="▶  START SIMULATION", bg="#005500")
        self._ensure_engineer_inputs_enabled()   # re-enable after sim stops

    #  simulation 

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

    #  refresh all displays 

    def _refresh_all(self):
        self._refresh_controls()
        self._refresh_mini_cards()
        self._refresh_clock()
        self._ensure_engineer_inputs_enabled()   # called every 100ms – Kp/Ki ALWAYS editable
        self.root.after(100, self._refresh_all)

    def _refresh_controls(self):
        t = self.T
        DOOR = {0:"Closed",1:"Right",2:"Left",3:"Both"}
        light = ("External" if t.headlights else ("Internal" if t.interior_lights else "Off"))

        # outputs
        self.disp_actual_spd.config(   text=f"{t.current_speed:.1f}")
        self.disp_set_spd.config(
            text=f"{t.commanded_speed:.1f}" if t.automatic_mode
            else f"{t.manual_speed_target:.1f}  ✎")
        auth_mi = t.authority * 0.000621371
        self.disp_authority.config(    text=f"{auth_mi:.3f}")
        self.disp_passengers.config(   text=str(t.passengers))
        self.disp_next_station.config( text=t.next_station)
        self.disp_power.config(        text=f"{t.power_output:,.0f}")

        # faults
        for key, attr in [("power","fault_power"),("brake","fault_brake"),("signal","fault_signal")]:
            active = getattr(t, attr)
            self.fault_lbls[key].config(
                fg=C["fault"] if active else C["text_dim"])

        # status row
        self.stat_mode.config(
            text="AUTO" if t.automatic_mode else "MANUAL",
            fg=C["ok"] if t.automatic_mode else C["warn"])
        self.stat_doors.config(
            text=DOOR.get(t.doors_state,"Closed"),
            fg=C["warn"] if t.doors_state else C["ok"])
        self.stat_lights.config(text=light,
            fg=C["warn"] if light!="Off" else C["text_dim"])

        # keep door & light button highlights in sync with controller state
        dv = str(t.doors_state)
        door_colors = {"0": C["ok"], "1": C["accent"], "2": C["accent"], "3": C["warn"]}
        for v, btn in self.door_btns.items():
            btn.config(bg=door_colors[v] if v==dv else C["deselect"],
                       fg="white" if v==dv else C["text_dim"])
        door_labels = {"0":"🚪  CLOSED","1":"RIGHT OPEN","2":"LEFT OPEN","3":"BOTH OPEN"}
        self.door_status_lbl.config(
            text=door_labels.get(dv,"🚪  CLOSED"),
            fg=C["ok"] if dv=="0" else C["accent"])

        lv = light
        light_icons  = {"Off":"💡  OFF","External":"🔦  EXTERNAL","Internal":"🏠  INTERNAL"}
        light_colors_map = {"Off":C["text_dim"],"External":C["warn"],"Internal":"#5599ff"}
        for v, (btn, ac, af) in self.light_btns.items():
            btn.config(bg=ac if v==lv else C["deselect"],
                       fg=af if v==lv else C["text_dim"])
        self.light_status_lbl.config(
            text=light_icons.get(lv,"💡  OFF"),
            fg=light_colors_map.get(lv, C["text_dim"]))
        self.stat_ebrake.config(
            text="ACTIVE" if t.emergency_brake else "OFF",
            fg=C["fault"] if t.emergency_brake else C["ok"])

        # sync e-brake button if triggered internally
        if t.emergency_brake and "RELEASE" not in self.ebrake_btn.cget("text"):
            self.ebrake_btn.config(bg="#4a0000",
                text="⚠  E-BRAKE ACTIVE  –  CLICK TO RELEASE")
            self.ebrake_status.config(text="● ACTIVE", fg=C["fault"])

        # secondary status
        self.status_lbl2.config(
            text=f"Train {t.train_id}  |  "
                 f"Spd {t.current_speed:.1f} mph  |  "
                 f"Auth {t.authority:.0f} m  |  "
                 f"Pwr {t.power_output:,.0f} W")

    def _refresh_mini_cards(self):
        for i, (t, mc) in enumerate(zip(self.trains, self.mini_cards)):
            mc["spd"].config(text=f"{t.current_speed:.1f} mph")
            mc["sta"].config(text=t.next_station)
            if t.any_fault or t.emergency_brake:
                mc["fl"].config(text="⚠ FAULT", fg=C["fault"])
                mc["frame"].config(bg="#1a0000")
                mc["spd"].config(bg="#1a0000")
                mc["sta"].config(bg="#1a0000")
                mc["fl"].config(bg="#1a0000")
            else:
                mc["fl"].config(text="● OK", fg=C["ok"])
                mc["frame"].config(bg=C["bg_card"])
                mc["spd"].config(bg=C["bg_card"])
                mc["sta"].config(bg=C["bg_card"])
                mc["fl"].config(bg=C["bg_card"])

    def _refresh_clock(self):
        t = time.localtime()
        self.clock_lbl.config(
            text=f"{t.tm_hour:02d}:{t.tm_min:02d}:{t.tm_sec:02d}")

    #  test UI 

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

        # left inputs, right outputs
        lf = tk.LabelFrame(body, text="  INPUTS", bg=C["bg_panel"],
                            fg=C["accent2"], font=("Courier", 10, "bold"),
                            padx=8, pady=8, relief=tk.FLAT,
                            highlightbackground=C["border"], highlightthickness=1)
        lf.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=(0,5))

        rf = tk.LabelFrame(body, text="  OUTPUTS", bg=C["bg_panel"],
                            fg=C["ok"], font=("Courier", 10, "bold"),
                            padx=8, pady=8, relief=tk.FLAT,
                            highlightbackground=C["border"], highlightthickness=1)
        rf.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=(5,0))

        t = self.T
        DOOR = {0:"Closed",1:"Right",2:"Left",3:"Both"}
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
                             font=("Courier", 8, "bold"), width=14, anchor="center",
                             relief=tk.FLAT, padx=4
                             ).pack(side=tk.RIGHT)

        _rows(lf, in_rows,  "#1a1000")
        _rows(rf, out_rows, "#001a00")

    #  run 

    def run(self):
        self.root.mainloop()



if __name__ == "__main__":
    app = TrainControllerApp()
    app.run()