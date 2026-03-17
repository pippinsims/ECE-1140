"""
Wayside Controller – Train Control System
Green Line (blocks 1–150) and Red Line (blocks 1–76)

Inputs  (per block, from Track Model & CTC):
  - Occupied          (bool)     from Track Model
  - Commanded Speed   (km/h)     from CTC
  - Authority         (km)       from CTC  ← distance the train is cleared to travel

Outputs (computed by Wayside):
  - Signal light state per block  (GREEN / YELLOW / RED)
  - Switch position per switch    (NORMAL / REVERSE)
  - Railway crossing state        (ACTIVE / INACTIVE)

Authority logic:
  Starting from the train's current (occupied) block, the wayside walks forward
  through the sequential block graph, accumulating block lengths (m), until
  the cumulative distance exceeds authority (km -> m).  The set of blocks still
  within authority is the "movement authority reach" and drives signal/switch logic.
"""

import tkinter as tk
from tkinter import ttk

# ─────────────────────────────────────────────────────────────────────────────
# TRACK DATA
# ─────────────────────────────────────────────────────────────────────────────

GREEN_BLOCK_LENGTHS = {
    1:100,2:100,3:100,4:100,5:100,6:100,7:100,8:100,9:100,10:100,
    11:100,12:100,13:150,14:150,15:150,16:150,17:150,18:150,19:150,20:150,
    21:300,22:300,23:300,24:300,25:200,26:100,27:50,28:50,29:50,30:50,
    31:50,32:50,33:50,34:50,35:50,36:50,37:50,38:50,39:50,40:50,
    41:50,42:50,43:50,44:50,45:50,46:50,47:50,48:50,49:50,50:50,
    51:50,52:50,53:50,54:50,55:50,56:50,57:50,58:50,59:50,60:50,
    61:50,62:50,63:100,64:100,65:200,66:200,67:100,68:100,69:100,70:100,
    71:100,72:100,73:100,74:100,75:100,76:100,77:300,78:300,79:300,80:300,
    81:300,82:300,83:300,84:300,85:300,86:100,87:86.6,88:100,89:75,90:75,
    91:75,92:75,93:75,94:75,95:75,96:75,97:75,98:75,99:75,100:75,
    101:35,102:100,103:100,104:80,105:100,106:100,107:90,108:100,109:100,110:100,
    111:100,112:100,113:100,114:162,115:100,116:100,117:50,118:50,119:40,120:50,
    121:50,122:50,123:50,124:50,125:50,126:50,127:50,128:50,129:50,130:50,
    131:50,132:50,133:50,134:50,135:50,136:50,137:50,138:50,139:50,140:50,
    141:50,142:50,143:50,144:50,145:50,146:50,147:50,148:184,149:40,150:35,
}

RED_BLOCK_LENGTHS = {
    1:50,2:50,3:50,4:50,5:50,6:50,7:75,8:75,9:75,10:75,
    11:75,12:75,13:70,14:60,15:60,16:50,17:200,18:400,19:400,20:200,
    21:100,22:100,23:100,24:50,25:50,26:50,27:50,28:50,29:60,30:60,
    31:50,32:50,33:50,34:50,35:50,36:50,37:50,38:50,39:50,40:60,
    41:60,42:50,43:50,44:50,45:50,46:75,47:75,48:75,49:50,50:50,
    51:50,52:43.2,53:50,54:50,55:75,56:75,57:75,58:75,59:75,60:75,
    61:75,62:75,63:75,64:75,65:75,66:75,67:50,68:50,69:50,70:50,
    71:50,72:50,73:50,74:50,75:50,76:50,
}

# Switch definitions
# host    : block the switch lives on
# normal  : (next_block, display_label) in NORMAL position
# reverse : (next_block, display_label) in REVERSE position
GREEN_SWITCHES = {
    "SW12": {"host":12,  "normal":(13,"12->13"),   "reverse":(1, "1->13"),    "description":"Blocks 1/12 -> 13"},
    "SW28": {"host":28,  "normal":(29,"28->29"),   "reverse":(150,"150->28"), "description":"Blocks 28 / 150"},
    "SW57": {"host":57,  "normal":(58,"57->Yard"),  "reverse":(58,"Yard->57"), "description":"Yard Switch at 57"},
    "SW62": {"host":62,  "normal":(63,"Yard->63"),  "reverse":(62,"62<-Yard"), "description":"Yard Switch at 62/63"},
    "SW76": {"host":76,  "normal":(77,"76->77"),   "reverse":(101,"77->101"), "description":"Blocks 76->77 / 101"},
    "SW85": {"host":85,  "normal":(86,"85->86"),   "reverse":(100,"100->85"), "description":"Blocks 85 / 100"},
}
RED_SWITCHES = {
    "SW9":  {"host":9,  "normal":(10,"9->10"),   "reverse":(0, "Yard"),   "description":"Yard Switch at 9"},
    "SW15": {"host":15, "normal":(16,"15->16"),  "reverse":(1, "1->16"),  "description":"Blocks 1/15 -> 16"},
    "SW27": {"host":27, "normal":(28,"27->28"),  "reverse":(76,"27->76"), "description":"Blocks 27->28 / 76"},
    "SW32": {"host":32, "normal":(33,"32->33"),  "reverse":(72,"33->72"), "description":"Blocks 32/72 -> 33"},
    "SW38": {"host":38, "normal":(39,"38->39"),  "reverse":(71,"38->71"), "description":"Blocks 38/71 -> 39"},
    "SW43": {"host":43, "normal":(44,"43->44"),  "reverse":(67,"44->67"), "description":"Blocks 43/67 -> 44"},
    "SW52": {"host":52, "normal":(53,"52->53"),  "reverse":(66,"52->66"), "description":"Blocks 52->53 / 66"},
}

GREEN_CROSSINGS = [19, 108]
RED_CROSSINGS   = [11, 47]

BLUE_BLOCK_LENGTHS = {
    1:50, 2:50, 3:50, 4:50, 5:50,
    6:50, 7:50, 8:50, 9:50, 10:50,
    11:50, 12:50, 13:50, 14:50, 15:50,
}

BLUE_SWITCHES = {
    "SW5": {"host":5, "normal":(6, "5->6"), "reverse":(11, "5->11"),
            "description":"Blocks 5->6 (Branch B) / 5->11 (Branch C)"},
}

BLUE_CROSSINGS = [3]


# ─────────────────────────────────────────────────────────────────────────────
# AUTHORITY -> BLOCK REACH  (BFS over block graph)
# ─────────────────────────────────────────────────────────────────────────────

def build_switch_map(switches):
    """Return {host_block: [reachable_block, ...]} for both switch positions."""
    m = {}
    for sw in switches.values():
        h = sw["host"]
        n = sw["normal"][0]
        r = sw["reverse"][0]
        branches = [b for b in {n, r} if b > 0]
        m[h] = branches
    return m


def authority_reach(start_block, authority_km, block_lengths, switch_map):
    """
    BFS forward from start_block, accumulating block length in metres.
    Returns set of block numbers the train is cleared to enter given authority_km.
    Both switch branches are explored so reach covers all possible paths.
    """
    auth_m = authority_km * 1000.0
    if auth_m <= 0:
        return set()

    reached = set()
    # queue: (block_number, metres_consumed_reaching_this_block)
    queue = [(start_block, 0.0)]
    visited = set()

    while queue:
        blk, dist_so_far = queue.pop(0)
        if blk in visited or blk <= 0:
            continue
        visited.add(blk)

        blk_len  = block_lengths.get(blk, 50)
        dist_end = dist_so_far + blk_len   # distance after traversing this block

        if dist_so_far >= auth_m:
            # We've already exceeded authority before even entering this block
            continue

        reached.add(blk)

        if dist_end >= auth_m:
            continue   # authority exhausted inside this block; don't walk further

        # Walk into next block(s)
        nexts = switch_map.get(blk, [blk + 1])
        for nxt in nexts:
            if nxt > 0 and nxt not in visited:
                queue.append((nxt, dist_end))

    return reached


# ─────────────────────────────────────────────────────────────────────────────
# WAYSIDE LOGIC
# ─────────────────────────────────────────────────────────────────────────────

def compute_wayside_outputs(block_state, block_lengths, switches_def, crossings_list):
    """
    block_state: {blk: {"occupied": bool, "cmd_speed": float, "authority": float (km)}}

    Returns:
      "switches":  {sw_id: "normal"|"reverse"}
      "signals":   {blk: "green"|"yellow"|"red"}
      "crossings": {blk: "active"|"inactive"}
      "reach":     {train_blk: set_of_blocks}
    """
    sw_map = build_switch_map(switches_def)

    # ── Authority reach per occupied block ─────────────────────────────────
    reach_map = {}
    for blk, st in block_state.items():
        if st["occupied"]:
            reach_map[blk] = authority_reach(
                blk + 1,         # start walking from the block AHEAD of the train
                st["authority"],
                block_lengths,
                sw_map,
            )

    all_reach   = set().union(*reach_map.values()) if reach_map else set()
    occupied    = {b for b, s in block_state.items() if s["occupied"]}

    # ── Signal logic ───────────────────────────────────────────────────────
    # For each block, determine the appropriate signal based on:
    #   1. Immediate safety  (next block occupied?)
    #   2. Authority reach   (does a train's authority extend through here?)
    signals = {}
    for blk in block_lengths:
        st        = block_state.get(blk, {})
        is_occ    = st.get("occupied", False)
        cmd_speed = st.get("cmd_speed", 0.0)
        authority = st.get("authority", 0.0)

        next1 = blk + 1
        next2 = blk + 2

        if is_occ:
            # Signal for the TRAIN currently on this block
            if next1 in occupied:
                sig = "red"
            elif authority <= 0 or cmd_speed == 0:
                sig = "red"
            else:
                # How many metres of authority remain past this block?
                len1 = block_lengths.get(next1, 50)
                len2 = block_lengths.get(next2, 50)
                auth_m = authority * 1000
                if auth_m < len1:
                    sig = "red"
                elif next2 in occupied or auth_m < (len1 + len2):
                    sig = "yellow"
                else:
                    sig = "green"
        else:
            # Unoccupied — show approach signal
            if next1 in occupied:
                sig = "red"
            elif next2 in occupied:
                sig = "yellow"
            else:
                sig = "green"

        signals[blk] = sig

    # ── Switch logic ───────────────────────────────────────────────────────
    switch_states = {}
    for sw_id, sw in switches_def.items():
        host     = sw["host"]
        norm_blk = sw["normal"][0]
        rev_blk  = sw["reverse"][0]

        if host in occupied:
            # Never flip under a train
            switch_states[sw_id] = "normal"
            continue

        # Count trains whose authority reach covers each branch
        norm_count = sum(1 for s in reach_map.values() if norm_blk in s)
        rev_count  = sum(1 for s in reach_map.values() if rev_blk  in s)

        # Is a train already on a branch and needs to merge?
        rev_occ  = rev_blk  in occupied
        norm_occ = norm_blk in occupied

        if rev_occ and not norm_occ:
            switch_states[sw_id] = "reverse"
        elif rev_count > norm_count and rev_count > 0:
            switch_states[sw_id] = "reverse"
        else:
            switch_states[sw_id] = "normal"

    # ── Railway crossing logic ─────────────────────────────────────────────
    crossing_states = {}
    for cx in crossings_list:
        cx_occ    = cx in occupied
        # Approaching: train on previous block with authority that reaches the crossing
        approach  = (cx - 1) in occupied and cx in all_reach
        crossing_states[cx] = "active" if (cx_occ or approach) else "inactive"

    return {
        "switches":  switch_states,
        "signals":   signals,
        "crossings": crossing_states,
        "reach":     reach_map,
    }


# ─────────────────────────────────────────────────────────────────────────────
# COLOUR PALETTE
# ─────────────────────────────────────────────────────────────────────────────

C = {
    "bg":     "#1a1a2e",
    "panel":  "#16213e",
    "card":   "#0f3460",
    "accent": "#e94560",
    "green":  "#00d26a",
    "yellow": "#ffd700",
    "red":    "#ff4757",
    "orange": "#ff6b35",
    "blue":   "#4fc3f7",
    "white":  "#e0e0e0",
    "muted":  "#8899aa",
    "header": "#0d2137",
    "reach":  "#1d4e6b",
}
SIG_COLOR = {"green": C["green"], "yellow": C["yellow"], "red": C["red"]}





# ─────────────────────────────────────────────────────────────────────────────
# EMBEDDABLE FRAME  (all UI/logic in a tk.Frame so it can live in any window)
# ─────────────────────────────────────────────────────────────────────────────

class WaysideFrame(tk.Frame):
    """
    The full wayside controller UI packaged as a Frame.
    Can be embedded inside any tk.Tk, tk.Toplevel, or another Frame.
    """
    def __init__(self, parent, compute_fn=None, mode="live", **kwargs):
        """
        mode : "live"    — locked inputs, live polling, no toggle button
               "testing" — editable inputs, no polling, no toggle button
        """
        super().__init__(parent, bg=C["bg"], **kwargs)
        self._compute_fn   = compute_fn if compute_fn is not None else compute_wayside_outputs
        self._mode         = mode                   # "live" or "testing"
        self._testing_mode = (mode == "testing")    # True if testing window
        self._live_job     = None
        self._input_widgets = {"Green": [], "Red": [], "Blue": []}

        self.lines = {
            "Green": {
                "block_lengths": GREEN_BLOCK_LENGTHS,
                "switches":      GREEN_SWITCHES,
                "crossings":     GREEN_CROSSINGS,
                "color":         C["green"],
                "block_vars":    {},
                "sw_labels":     {},   # {sw_id: (pos_lbl, route_lbl, override_var, override_btn)}
                "sig_labels":    {},   # {blk: (dot, cell, num_lbl, override_var, cycle_btn)}
                "cx_labels":     {},
                "maintenance":   False,
                "maint_btn":     None,
                "maint_banner":  None,
            },
            "Red": {
                "block_lengths": RED_BLOCK_LENGTHS,
                "switches":      RED_SWITCHES,
                "crossings":     RED_CROSSINGS,
                "color":         C["red"],
                "block_vars":    {},
                "sw_labels":     {},
                "sig_labels":    {},
                "cx_labels":     {},
                "maintenance":   False,
                "maint_btn":     None,
                "maint_banner":  None,
            },
            "Blue": {
                "block_lengths": BLUE_BLOCK_LENGTHS,
                "switches":      BLUE_SWITCHES,
                "crossings":     BLUE_CROSSINGS,
                "color":         C["blue"],
                "block_vars":    {},
                "sw_labels":     {},
                "sig_labels":    {},
                "cx_labels":     {},
                "maintenance":   False,
                "maint_btn":     None,
                "maint_banner":  None,
            },
        }

        self._build_ui()
        self._refresh()
        # Apply initial state (testing ON by default)
        self._apply_testing_mode()

    # ── All UI/logic methods are identical to WaysideApp, using self (a Frame) ──

    def _build_ui(self):
        hdr = tk.Frame(self, bg=C["header"], pady=10)
        hdr.pack(fill="x")
        tk.Label(hdr, text="WAYSIDE CONTROLLER",
                 font=("Helvetica", 20, "bold"), bg=C["header"], fg=C["white"]).pack(side="left", padx=20)
        tk.Label(hdr, text="Green Line  |  Red Line  |  Blue Line",
                 font=("Helvetica", 12), bg=C["header"], fg=C["muted"]).pack(side="left", padx=8)

        # Mode badge — fixed label showing live or testing, no toggle
        if self._mode == "testing":
            badge_text  = "🧪  TESTING MODE"
            badge_bg    = C["green"]
            badge_fg    = "#000000"
        else:
            badge_text  = "📡  LIVE MODE"
            badge_bg    = C["yellow"]
            badge_fg    = "#000000"

        tk.Label(hdr, text=badge_text,
                 font=("Helvetica", 9, "bold"),
                 bg=badge_bg, fg=badge_fg,
                 padx=12, pady=5).pack(side="right", padx=20)

        self._test_banner = tk.Label(
            hdr,
            text="  Receiving data from CTC & Track Model every 1s",
            font=("Helvetica", 8, "italic"),
            bg=C["header"], fg=C["yellow"],
        )
        if self._mode == "live":
            self._test_banner.pack(side="right", padx=6)

        style = ttk.Style()
        style.theme_use("clam")
        style.configure("TNotebook",     background=C["bg"],   borderwidth=0)
        style.configure("TNotebook.Tab", background=C["card"], foreground=C["white"],
                        padding=[14, 6], font=("Helvetica", 11, "bold"))
        style.map("TNotebook.Tab", background=[("selected", C["accent"])])
        style.configure("Vertical.TScrollbar", background=C["card"], troughcolor=C["bg"])

        nb = ttk.Notebook(self)
        nb.pack(fill="both", expand=True, padx=8, pady=8)

        for name in ["Green", "Red", "Blue"]:
            frame = tk.Frame(nb, bg=C["bg"])
            nb.add(frame, text=f"  {name} Line  ")
            self._build_line_tab(frame, name)

    def _build_line_tab(self, parent, name):
        lc   = self.lines[name]["color"]
        line = self.lines[name]

        pw = tk.PanedWindow(parent, orient="horizontal", bg=C["bg"], sashwidth=5)
        pw.pack(fill="both", expand=True)
        left  = tk.Frame(pw, bg=C["bg"])
        right = tk.Frame(pw, bg=C["bg"])
        pw.add(left,  minsize=560)
        pw.add(right, minsize=500)

        # ── Left: inputs ──────────────────────────────────────────────
        self._section_label(left, "INPUTS  —  Track Model  &  CTC", lc)
        self._make_scrollable(left, self._build_block_inputs, name, lc)

        # ── Right: maintenance toggle bar (always visible, above scroll) ──
        self._section_label(right, "OUTPUTS  —  Computed by Wayside", lc)

        maint_bar = tk.Frame(right, bg=C["bg"], pady=4)
        maint_bar.pack(fill="x", padx=6)

        maint_btn = tk.Button(
            maint_bar,
            text="🔧  Maintenance Mode: OFF",
            font=("Helvetica", 9, "bold"),
            bg=C["card"], fg=C["muted"],
            activebackground=C["card"],
            relief="flat", bd=0, padx=10, pady=5,
            cursor="hand2",
            command=lambda n=name: self._toggle_maintenance(n),
        )
        maint_btn.pack(side="left")

        # Banner shown when maintenance is ON
        maint_banner = tk.Label(
            maint_bar,
            text="  ⚠  Manual override active — computed values are paused",
            font=("Helvetica", 8, "italic"),
            bg=C["bg"], fg=C["orange"],
        )
        # Not packed until maintenance is on

        line["maint_btn"]    = maint_btn
        line["maint_banner"] = maint_banner

        self._make_scrollable(right, self._build_outputs_panel, name, lc)

    def _section_label(self, parent, text, color):
        f = tk.Frame(parent, bg=color, pady=4)
        f.pack(fill="x", padx=4, pady=(6, 2))
        tk.Label(f, text=text, font=("Helvetica", 10, "bold"),
                 bg=color, fg="#000").pack(padx=10)

    def _make_scrollable(self, parent, builder_fn, *args):
        canvas = tk.Canvas(parent, bg=C["bg"], highlightthickness=0)
        sb     = ttk.Scrollbar(parent, orient="vertical", command=canvas.yview,
                               style="Vertical.TScrollbar")
        canvas.configure(yscrollcommand=sb.set)
        sb.pack(side="right", fill="y")
        canvas.pack(fill="both", expand=True)
        frame = tk.Frame(canvas, bg=C["bg"])
        win   = canvas.create_window((0, 0), window=frame, anchor="nw")
        frame.bind("<Configure>", lambda e: canvas.configure(scrollregion=canvas.bbox("all")))
        canvas.bind("<Configure>", lambda e: canvas.itemconfig(win, width=e.width))
        canvas.bind("<MouseWheel>",
                    lambda e: canvas.yview_scroll(-1*(e.delta//120), "units"))
        builder_fn(frame, *args)

    def _build_block_inputs(self, parent, name, lc):
        line = self.lines[name]
        hdr  = tk.Frame(parent, bg=C["panel"])
        hdr.pack(fill="x", padx=4, pady=(4, 0))
        for txt, w in [("Block", 14), ("Length (m)", 10), ("Occupied", 9),
                       ("Cmd Speed\n(km/h)", 12), ("Authority\n(km)", 11)]:
            tk.Label(hdr, text=txt, font=("Helvetica", 8, "bold"), bg=C["panel"],
                     fg=C["muted"], width=w, anchor="center").pack(side="left", padx=2, pady=3)

        for blk in sorted(line["block_lengths"].keys()):
            blk_len = line["block_lengths"][blk]
            is_sw   = any(sw["host"] == blk for sw in line["switches"].values())
            is_cx   = blk in line["crossings"]
            tag     = " [SW]" if is_sw else (" [CX]" if is_cx else "")
            fg      = C["orange"] if is_cx else (C["yellow"] if is_sw else C["white"])
            row_bg  = C["panel"] if blk % 2 == 0 else C["card"]

            row = tk.Frame(parent, bg=row_bg)
            row.pack(fill="x", padx=4, pady=1)

            tk.Label(row, text=f"{blk}{tag}", font=("Helvetica", 8),
                     bg=row_bg, fg=fg, width=14, anchor="w").pack(side="left", padx=3)
            tk.Label(row, text=f"{blk_len:.0f}", font=("Helvetica", 8),
                     bg=row_bg, fg=C["muted"], width=10, anchor="center").pack(side="left", padx=2)

            occ_var   = tk.BooleanVar(value=False)
            speed_var = tk.DoubleVar(value=0.0)
            auth_var  = tk.DoubleVar(value=0.0)

            cb = tk.Checkbutton(row, variable=occ_var, bg=row_bg, fg=lc,
                                activebackground=row_bg, selectcolor=row_bg,
                                command=self._refresh)
            cb.pack(side="left", padx=10)

            spinboxes = []
            for var, hi, inc, fmt in [(speed_var, 200, 5, "%.0f"),
                                       (auth_var,  100, 0.05, "%.2f")]:
                sp = tk.Spinbox(row, from_=0, to=hi, increment=inc, textvariable=var,
                                format=fmt, width=8, font=("Helvetica", 8),
                                bg=C["bg"], fg=C["white"], buttonbackground=C["card"],
                                command=self._refresh)
                sp.pack(side="left", padx=5)
                sp.bind("<Return>",   lambda e: self._refresh())
                sp.bind("<FocusOut>", lambda e: self._refresh())
                spinboxes.append(sp)

            # Store widget references so we can lock/unlock them
            self._input_widgets[name].append((cb, spinboxes[0], spinboxes[1]))

            line["block_vars"][blk] = {
                "occupied":  occ_var,
                "cmd_speed": speed_var,
                "authority": auth_var,
            }

    def _build_outputs_panel(self, parent, name, lc):
        line = self.lines[name]

        # ── Switch States ─────────────────────────────────────────────
        sw_card = self._card(parent, "Switch States")
        for sw_id, sw in line["switches"].items():
            row = tk.Frame(sw_card, bg=C["card"])
            row.pack(fill="x", pady=2, padx=4)
            tk.Label(row, text=f"{sw_id}  —  {sw['description']}", font=("Helvetica", 9),
                     bg=C["card"], fg=C["muted"], width=34, anchor="w").pack(side="left")

            pos_lbl   = tk.Label(row, text="NORMAL", font=("Helvetica", 9, "bold"),
                                 bg=C["card"], fg=C["green"], width=9)
            pos_lbl.pack(side="left", padx=4)
            route_lbl = tk.Label(row, text=sw["normal"][1], font=("Helvetica", 8),
                                 bg=C["card"], fg=C["muted"], width=14)
            route_lbl.pack(side="left")

            # Manual override toggle button (hidden until maintenance ON)
            override_var = tk.StringVar(value="normal")
            override_btn = tk.Button(
                row,
                text="▶ Set REVERSE",
                font=("Helvetica", 8),
                bg=C["panel"], fg=C["yellow"],
                activebackground=C["panel"],
                relief="flat", padx=6, pady=2,
                cursor="hand2",
            )
            # Wire command after creation so we can reference the button itself
            override_btn.config(
                command=lambda sid=sw_id, n=name, v=override_var, b=override_btn:
                    self._toggle_switch_override(sid, n, v, b)
            )
            # Not packed yet — shown only in maintenance mode

            line["sw_labels"][sw_id] = (pos_lbl, route_lbl, override_var, override_btn)

        # ── Signal States ─────────────────────────────────────────────
        sig_card = self._card(parent, "Signal States per Block  "
                              "(dot colour = signal;  blue background = within authority reach)")
        grid = tk.Frame(sig_card, bg=C["card"])
        grid.pack(fill="both", expand=True, padx=4, pady=4)
        cols = 10
        SIG_CYCLE = ["green", "yellow", "red"]   # manual cycle order

        for i, blk in enumerate(sorted(line["block_lengths"].keys())):
            r, c = divmod(i, cols)
            cell = tk.Frame(grid, bg=C["bg"], bd=1, relief="solid")
            cell.grid(row=r, column=c, padx=2, pady=2, sticky="nsew")
            grid.columnconfigure(c, weight=1)
            num_lbl = tk.Label(cell, text=str(blk), font=("Helvetica", 7),
                               bg=C["bg"], fg=C["muted"])
            num_lbl.pack()
            dot = tk.Label(cell, text="●", font=("Helvetica", 12),
                           bg=C["bg"], fg=C["muted"])
            dot.pack()

            # Cycle button — clicking steps green→yellow→red→green
            override_var = tk.StringVar(value="green")
            cycle_btn = tk.Button(
                cell,
                text="",          # will show current value in maintenance mode
                font=("Helvetica", 6),
                bg=C["bg"], fg=C["muted"],
                activebackground=C["bg"],
                relief="flat", padx=0, pady=0,
                cursor="hand2",
                width=4,
            )
            cycle_btn.config(
                command=lambda b=blk, n=name, v=override_var:
                    self._cycle_signal_override(b, n, v)
            )
            # Not packed yet

            line["sig_labels"][blk] = (dot, cell, num_lbl, override_var, cycle_btn)

        # ── Railway Crossing States ───────────────────────────────────
        cx_card = self._card(parent, "Railway Crossing States")
        for cx in line["crossings"]:
            row = tk.Frame(cx_card, bg=C["card"])
            row.pack(fill="x", pady=2, padx=4)
            tk.Label(row, text=f"Block {cx}  Railway Crossing",
                     font=("Helvetica", 9), bg=C["card"], fg=C["muted"],
                     width=28, anchor="w").pack(side="left")
            lbl = tk.Label(row, text="INACTIVE", font=("Helvetica", 10, "bold"),
                           bg=C["card"], fg=C["green"], width=14)
            lbl.pack(side="left", padx=6)
            line["cx_labels"][cx] = lbl

        leg = tk.Frame(parent, bg=C["bg"])
        leg.pack(fill="x", padx=6, pady=(6, 2))
        tk.Label(leg, text="Legend:", font=("Helvetica", 8, "bold"),
                 bg=C["bg"], fg=C["muted"]).pack(side="left")
        for txt, col in [("  Green = clear", C["green"]), ("  Yellow = caution", C["yellow"]),
                         ("  Red = stop", C["red"]), ("  Blue bg = within authority", C["reach"])]:
            tk.Label(leg, text=txt, font=("Helvetica", 8), bg=C["bg"], fg=col).pack(side="left")

    def _card(self, parent, title):
        outer = tk.Frame(parent, bg=C["bg"], pady=3)
        outer.pack(fill="x", padx=4, pady=4)
        tk.Label(outer, text=title, font=("Helvetica", 9, "bold"),
                 bg=C["bg"], fg=C["white"]).pack(anchor="w", padx=4)
        inner = tk.Frame(outer, bg=C["card"], padx=6, pady=6)
        inner.pack(fill="x")
        return inner

    def _refresh(self, *_):
        for name, line in self.lines.items():
            block_state = {}
            for blk, bvars in line["block_vars"].items():
                try:
                    speed = float(bvars["cmd_speed"].get())
                    auth  = float(bvars["authority"].get())
                except (tk.TclError, ValueError):
                    speed, auth = 0.0, 0.0
                block_state[blk] = {
                    "occupied":  bvars["occupied"].get(),
                    "cmd_speed": speed,
                    "authority": auth,
                }

            result = self._compute_fn(
                block_state, line["block_lengths"],
                line["switches"], line["crossings"],
            )

            all_reach = set().union(*result["reach"].values()) if result["reach"] else set()
            in_maintenance = line["maintenance"]

            # ── Switches ───────────────────────────────────────────────
            for sw_id, pos in result["switches"].items():
                sw    = line["switches"][sw_id]
                entry = line["sw_labels"].get(sw_id)
                if not entry:
                    continue
                pos_lbl, route_lbl, override_var, override_btn = entry

                if in_maintenance:
                    # Use the manual override value, not the computed one
                    pos = override_var.get()

                if pos == "normal":
                    pos_lbl.config(text="NORMAL",  fg=C["green"])
                    route_lbl.config(text=sw["normal"][1],  fg=C["muted"])
                else:
                    pos_lbl.config(text="REVERSE", fg=C["yellow"])
                    route_lbl.config(text=sw["reverse"][1], fg=C["yellow"])

            # ── Signals ────────────────────────────────────────────────
            for blk, sig in result["signals"].items():
                entry = line["sig_labels"].get(blk)
                if not entry:
                    continue
                dot, cell, num_lbl, override_var, cycle_btn = entry

                if in_maintenance:
                    sig = override_var.get()

                dot.config(fg=SIG_COLOR.get(sig, C["muted"]))
                # Suppress authority reach highlight in maintenance mode (less confusing)
                bg = (C["reach"] if blk in all_reach else C["bg"]) if not in_maintenance else C["bg"]
                cell.config(bg=bg)
                dot.config(bg=bg)
                num_lbl.config(bg=bg)

            # ── Crossings ──────────────────────────────────────────────
            for cx, state in result["crossings"].items():
                lbl = line["cx_labels"].get(cx)
                if lbl:
                    if state == "active":
                        lbl.config(text="ACTIVE",   fg=C["orange"])
                    else:
                        lbl.config(text="INACTIVE", fg=C["green"])

    # ── Testing mode helpers ──────────────────────────────────────────────────

    def _apply_testing_mode(self):
        """Lock/unlock inputs based on current mode. No toggle button anymore."""
        if self._testing_mode:
            if self._live_job is not None:
                self.after_cancel(self._live_job)
                self._live_job = None
            self._set_inputs_locked(False)
        else:
            self._set_inputs_locked(True)
            self._schedule_live_poll()

    def _set_inputs_locked(self, locked):
        """Enable or disable all block input widgets across both lines."""
        state = "disabled" if locked else "normal"
        cb_state = "disabled" if locked else "normal"
        dim_fg  = C["muted"]
        norm_fg = C["white"]
        for name, widgets in self._input_widgets.items():
            for cb, sp_speed, sp_auth in widgets:
                cb.config(state=cb_state)
                for sp in (sp_speed, sp_auth):
                    sp.config(state=state,
                              fg=dim_fg if locked else norm_fg)

    def _schedule_live_poll(self):
        """Schedule the next live data push in 1 second."""
        if not self._testing_mode:
            self._poll_live_data()
            self._live_job = self.after(1000, self._schedule_live_poll)

    def _poll_live_data(self):
        """
        Called every second in Live Mode.
        Push incoming CTC + Track Model data into the block input vars.

        ── HOW TO CONNECT YOUR CTC & TRACK MODEL ──────────────────────────
        Call  self.receive_live_data(line_name, block_data)  from your
        external modules, where:

            line_name  : "Green" or "Red"
            block_data : dict  {block_num: {
                                    "occupied":  bool,
                                    "cmd_speed": float,   # km/h from CTC
                                    "authority": float,   # km  from CTC
                                }}

        This method is the stub — replace the pass below with your data
        fetch once CTC and Track Model are ready.
        ────────────────────────────────────────────────────────────────────
        """
        # ── STUB: replace with real CTC / Track Model data fetch ──────────
        # Example:
        #   for line_name in ["Green", "Red"]:
        #       data = ctc_module.get_block_states(line_name)
        #       self.receive_live_data(line_name, data)
        pass

    def receive_live_data(self, line_name, block_data):
        """
        Push live block data into the input fields and trigger a refresh.
        Called by CTC / Track Model integration.

        Parameters
        ----------
        line_name  : "Green" or "Red"
        block_data : {block_num: {"occupied": bool,
                                  "cmd_speed": float,
                                  "authority": float}}
        """
        if self._testing_mode:
            return  # ignore live pushes while in testing mode

        line = self.lines.get(line_name)
        if not line:
            return

        for blk, data in block_data.items():
            bvars = line["block_vars"].get(blk)
            if not bvars:
                continue
            bvars["occupied"].set(bool(data.get("occupied", False)))
            bvars["cmd_speed"].set(float(data.get("cmd_speed", 0.0)))
            bvars["authority"].set(float(data.get("authority", 0.0)))

        self._refresh()

    # ── Maintenance mode helpers ───────────────────────────────────────────

    def _toggle_maintenance(self, name):
        """Toggle maintenance mode on/off for one line."""
        line = self.lines[name]
        line["maintenance"] = not line["maintenance"]
        on = line["maintenance"]

        btn     = line["maint_btn"]
        banner  = line["maint_banner"]

        if on:
            btn.config(text="🔧  Maintenance Mode: ON",
                       bg=C["orange"], fg="#000000")
            banner.pack(side="left", padx=10)
            # Seed override vars from the current computed state so toggles start correct
            self._seed_overrides(name)
        else:
            btn.config(text="🔧  Maintenance Mode: OFF",
                       bg=C["card"], fg=C["muted"])
            banner.pack_forget()

        # Show/hide interactive override widgets on switches and signals
        self._set_override_widgets_visible(name, on)
        self._refresh()

    def _seed_overrides(self, name):
        """Copy the current computed outputs into the override vars."""
        line = self.lines[name]
        block_state = {}
        for blk, bvars in line["block_vars"].items():
            try:
                speed = float(bvars["cmd_speed"].get())
                auth  = float(bvars["authority"].get())
            except (tk.TclError, ValueError):
                speed, auth = 0.0, 0.0
            block_state[blk] = {
                "occupied":  bvars["occupied"].get(),
                "cmd_speed": speed,
                "authority": auth,
            }
        result = self._compute_fn(
            block_state, line["block_lengths"],
            line["switches"], line["crossings"],
        )
        for sw_id, pos in result["switches"].items():
            entry = line["sw_labels"].get(sw_id)
            if entry:
                _, _, override_var, override_btn = entry
                override_var.set(pos)
                label = "▶ Set NORMAL" if pos == "reverse" else "▶ Set REVERSE"
                override_btn.config(text=label)

        for blk, sig in result["signals"].items():
            entry = line["sig_labels"].get(blk)
            if entry:
                _, _, _, override_var, cycle_btn = entry
                override_var.set(sig)
                cycle_btn.config(text=sig[:1].upper(),
                                 fg=SIG_COLOR.get(sig, C["muted"]))

    def _set_override_widgets_visible(self, name, visible):
        """Pack or forget all manual override buttons for a line."""
        line = self.lines[name]
        for sw_id, entry in line["sw_labels"].items():
            _, _, override_var, override_btn = entry
            if visible:
                override_btn.pack(side="left", padx=(8, 0))
            else:
                override_btn.pack_forget()

        for blk, entry in line["sig_labels"].items():
            _, _, _, override_var, cycle_btn = entry
            if visible:
                cycle_btn.pack()
            else:
                cycle_btn.pack_forget()

    def _toggle_switch_override(self, sw_id, name, override_var, btn):
        """Flip the manual switch override between normal and reverse."""
        current = override_var.get()
        new_pos = "reverse" if current == "normal" else "normal"
        override_var.set(new_pos)
        btn.config(text="▶ Set NORMAL" if new_pos == "reverse" else "▶ Set REVERSE")
        self._refresh()

    def _cycle_signal_override(self, blk, name, override_var):
        """Step the manual signal override: green → yellow → red → green."""
        cycle = ["green", "yellow", "red"]
        current = override_var.get()
        next_sig = cycle[(cycle.index(current) + 1) % len(cycle)]
        override_var.set(next_sig)
        # Update the cycle button label and colour
        entry = self.lines[name]["sig_labels"].get(blk)
        if entry:
            _, _, _, _, cycle_btn = entry
            cycle_btn.config(text=next_sig[:1].upper(),
                             fg=SIG_COLOR.get(next_sig, C["muted"]))
        self._refresh()


# ─────────────────────────────────────────────────────────────────────────────
# STANDALONE LAUNCHER  (used when running wayside_controller.py directly)
# ─────────────────────────────────────────────────────────────────────────────

class WaysideApp(tk.Tk):
    """Thin wrapper that hosts WaysideFrame as a standalone application."""
    def __init__(self):
        super().__init__()
        self.title("Wayside Controller – Green & Red Lines")
        self.geometry("1300x840")
        self.configure(bg=C["bg"])
        self.resizable(True, True)
        WaysideFrame(self).pack(fill="both", expand=True)


def launch_as_toplevel(parent, compute_fn=None, title=None, mode="live"):
    """
    Open the Wayside Controller as a child Toplevel.
    mode: "live" or "testing"
    """
    win = tk.Toplevel(parent)
    win.title(title or "Wayside Controller – Green & Red Lines")
    win.geometry("1300x840")
    win.configure(bg=C["bg"])
    win.resizable(True, True)
    WaysideFrame(win, compute_fn=compute_fn, mode=mode).pack(fill="both", expand=True)
    return win


# ─────────────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    WaysideApp().mainloop()
