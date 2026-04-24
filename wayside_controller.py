"""
Wayside Controller – Train Control System
==========================================
6-Wayside Architecture:

  Green Line (150 blocks):  WG1 = blocks  1–75   | WG2 = blocks  76–150
  Red   Line  (76 blocks):  WR1 = blocks  1–38   | WR2 = blocks  39–76

Each wayside owns its own block range, switches, and crossings.
Each wayside can independently run either the built-in default logic
or a user-supplied PLC compute function.

Inputs (per block, from Track Model & CTC):
  - Occupied        (bool)   from Track Model
  - Commanded Speed (km/h)   from CTC
  - Authority       (km)     from CTC

Outputs (computed by each wayside's logic):
  - Signal state per block   (green / yellow / red / None)
  - Switch position           (normal / reverse)
  - Crossing state            (active / inactive)

Authority logic:
  BFS forward from the occupied block, accumulating block lengths (m),
  until cumulative distance >= authority (km to m). The set of reachable
  blocks drives signal, switch, and crossing decisions.
"""

import tkinter as tk
from tkinter import ttk

# =============================================================================
# TRACK DATA  -  Block lengths, switches, crossings, stations, speed limits
# =============================================================================

# -- Green Line ---------------------------------------------------------------
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

# Switch definitions:
#   host    = block the switch lives on
#   normal  = (next_block, display_label) when switch is in NORMAL position
#   reverse = (next_block, display_label) when switch is in REVERSE position
GREEN_SWITCHES = {
    "SW12": {"host":12, "normal":(13,"12->13"),  "reverse":(1, "1->13"),    "description":"Blocks 1/12 -> 13"},
    "SW28": {"host":28, "normal":(29,"28->29"),  "reverse":(150,"150->28"), "description":"Blocks 28 / 150"},
    "SW57": {"host":57, "normal":(58,"57->58(Yard)"), "reverse":(0,"57->Depot"),  "description":"Yard Switch at 57 (enters yard at 58)"},
    "SW62": {"host":62, "normal":(63,"62->63"),        "reverse":(0,"62->Depot"),  "description":"Yard Switch at 62 (exits yard to 63)"},
    "SW76": {"host":76, "normal":(77,"76->77"),  "reverse":(101,"77->101"), "description":"Blocks 76->77 / 101"},
    "SW85": {"host":85, "normal":(86,"85->86"),  "reverse":(100,"100->85"), "description":"Blocks 85 / 100"},
}

GREEN_CROSSINGS = [19, 108]   # block numbers with railway crossings

GREEN_STATIONS = {2,9,16,22,31,39,48,57,65,73,77,88,96}

GREEN_SPEED_LIMITS = {
    1:45,2:45,3:45,4:45,5:45,6:45,7:45,8:45,9:45,10:45,
    11:45,12:45,13:70,14:70,15:70,16:70,17:60,18:60,19:60,20:60,
    21:70,22:70,23:70,24:70,25:70,26:70,27:30,28:30,29:30,30:30,
    31:30,32:30,33:30,34:30,35:30,36:30,37:30,38:30,39:30,40:30,
    41:30,42:30,43:30,44:30,45:30,46:30,47:30,48:30,49:30,50:30,
    51:30,52:30,53:30,54:30,55:30,56:30,57:30,58:30,59:30,60:30,
    61:30,62:30,63:70,64:70,65:70,66:70,67:40,68:40,69:40,70:40,
    71:40,72:40,73:40,74:40,75:40,76:40,77:70,78:70,79:70,80:70,
    81:70,82:70,83:70,84:70,85:70,86:25,87:25,88:25,89:25,90:25,
    91:25,92:25,93:25,94:25,95:25,96:25,97:25,98:25,99:25,100:25,
    101:26,102:28,103:28,104:28,105:28,106:28,107:28,108:28,109:28,110:30,
    111:30,112:30,113:30,114:30,115:30,116:30,117:15,118:15,119:15,120:15,
    121:15,122:20,123:20,124:20,125:20,126:20,127:20,128:20,129:20,130:20,
    131:20,132:20,133:20,134:20,135:20,136:20,137:20,138:20,139:20,140:20,
    141:20,142:20,143:20,144:20,145:20,146:20,147:20,148:20,149:20,150:20,
}

# -- Red Line -----------------------------------------------------------------
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

RED_SWITCHES = {
    "SW9":  {"host":9,  "normal":(10,"9->10"),  "reverse":(0,"Yard"),    "description":"Yard Switch at 9"},
    "SW15": {"host":15, "normal":(16,"15->16"), "reverse":(1,"1->16"),   "description":"Blocks 1/15 -> 16"},
    "SW27": {"host":27, "normal":(28,"27->28"), "reverse":(76,"27->76"), "description":"Blocks 27->28 / 76"},
    "SW32": {"host":32, "normal":(33,"32->33"), "reverse":(72,"33->72"), "description":"Blocks 32/72 -> 33"},
    "SW38": {"host":38, "normal":(39,"38->39"), "reverse":(71,"38->71"), "description":"Blocks 38/71 -> 39"},
    "SW43": {"host":43, "normal":(44,"43->44"), "reverse":(67,"44->67"), "description":"Blocks 43/67 -> 44"},
    "SW52": {"host":52, "normal":(53,"52->53"), "reverse":(66,"52->66"), "description":"Blocks 52->53 / 66"},
}

RED_CROSSINGS = [11, 47]

RED_STATIONS = {7,16,21,25,35,45,48,60}

RED_SPEED_LIMITS = {
    1:40,2:40,3:40,4:40,5:40,6:40,7:40,8:40,9:40,10:40,
    11:40,12:40,13:40,14:40,15:40,16:40,17:55,18:70,19:70,20:70,
    21:55,22:55,23:55,24:70,25:70,26:70,27:70,28:70,29:70,30:70,
    31:70,32:70,33:70,34:70,35:70,36:70,37:70,38:70,39:70,40:70,
    41:70,42:70,43:70,44:70,45:70,46:70,47:70,48:70,49:60,50:60,
    51:55,52:55,53:55,54:55,55:55,56:55,57:55,58:55,59:55,60:55,
    61:55,62:55,63:55,64:55,65:55,66:55,67:55,68:55,69:55,70:55,
    71:55,72:55,73:55,74:55,75:55,76:55,
}

# Blue Line removed


# =============================================================================
# WAYSIDE CONFIGURATION  -  Single source of truth for all 6 waysides
# =============================================================================
# WAYSIDE_CONFIGS is keyed by wayside ID: WG1, WG2, WR1, WR2.
# Each entry provides all the static data a wayside sub-tab needs.
# The dashboard and WaysideFrame both import from this dict.

def _slice(full_dict, block_range):
    """Return only the entries from full_dict whose keys are in block_range."""
    return {b: v for b, v in full_dict.items() if b in block_range}

def _slice_switches(switches_def, block_range):
    """Return only the switches whose host block falls within block_range."""
    return {sid: sw for sid, sw in switches_def.items()
            if sw["host"] in block_range}

def _slice_crossings(crossings_list, block_range):
    """Return only the crossing blocks that fall within block_range."""
    return [cx for cx in crossings_list if cx in block_range]


# Block ranges for each of the 6 waysides
# Wayside 1 on each line owns the boundary switch (host at the split point)
WG1_BLOCKS = range(1,  76)   # Green: blocks  1-75   owns SW12, SW28, SW57, SW62
WG2_BLOCKS = range(76, 151)  # Green: blocks 76-150  owns SW76, SW85
WR1_BLOCKS = range(1,  39)   # Red:   blocks  1-38   owns SW9, SW15, SW27, SW32, SW38
WR2_BLOCKS = range(39, 77)   # Red:   blocks 39-76   owns SW43, SW52



def compute_signal_blocks(stations, switches_def, block_lengths):
    """
    Return the set of blocks that should have physical signals:
      - Switch host block + both branch blocks get signals
      - The block immediately before and after every station gets a signal

    Blocks NOT in this set get signal = None (no physical signal exists there).
    The result is intersected with block_lengths to exclude out-of-range blocks.
    """
    signal_blocks = set()

    # Every switch: host and both branch blocks get signals
    for sw in switches_def.values():
        signal_blocks.add(sw["host"])
        n = sw["normal"][0]
        r = sw["reverse"][0]
        if n > 0: signal_blocks.add(n)
        if r > 0: signal_blocks.add(r)

    # Station neighbours: one block before and after each station
    all_blocks = set(block_lengths.keys())
    for st in stations:
        if (st - 1) in all_blocks: signal_blocks.add(st - 1)
        if (st + 1) in all_blocks: signal_blocks.add(st + 1)

    # Only return blocks that actually exist in this wayside's block range
    return signal_blocks & all_blocks


# Pre-compute signal block sets for every wayside at module load time
_WG1_SB = compute_signal_blocks(
    GREEN_STATIONS, _slice_switches(GREEN_SWITCHES, WG1_BLOCKS),
    _slice(GREEN_BLOCK_LENGTHS, WG1_BLOCKS))
_WG2_SB = compute_signal_blocks(
    GREEN_STATIONS, _slice_switches(GREEN_SWITCHES, WG2_BLOCKS),
    _slice(GREEN_BLOCK_LENGTHS, WG2_BLOCKS))
_WR1_SB = compute_signal_blocks(
    RED_STATIONS, _slice_switches(RED_SWITCHES, WR1_BLOCKS),
    _slice(RED_BLOCK_LENGTHS, WR1_BLOCKS))
_WR2_SB = compute_signal_blocks(
    RED_STATIONS, _slice_switches(RED_SWITCHES, WR2_BLOCKS),
    _slice(RED_BLOCK_LENGTHS, WR2_BLOCKS))



# WAYSIDE_CONFIGS - single source of truth imported by WaysideFrame and WaysideDashboard
WAYSIDE_CONFIGS = {
    "WG1": {
        "line":          "Green",
        "label":         "WG1  (Blocks 1-75)",
        "color":         "#00d26a",
        "blocks":        set(WG1_BLOCKS),
        "block_lengths": _slice(GREEN_BLOCK_LENGTHS, WG1_BLOCKS),
        "speed_limits":  _slice(GREEN_SPEED_LIMITS,  WG1_BLOCKS),
        "switches":      _slice_switches(GREEN_SWITCHES, WG1_BLOCKS),
        "crossings":     _slice_crossings(GREEN_CROSSINGS, WG1_BLOCKS),
        "signal_blocks": _WG1_SB,
    },
    "WG2": {
        "line":          "Green",
        "label":         "WG2  (Blocks 76-150)",
        "color":         "#00d26a",
        "blocks":        set(WG2_BLOCKS),
        "block_lengths": _slice(GREEN_BLOCK_LENGTHS, WG2_BLOCKS),
        "speed_limits":  _slice(GREEN_SPEED_LIMITS,  WG2_BLOCKS),
        "switches":      _slice_switches(GREEN_SWITCHES, WG2_BLOCKS),
        "crossings":     _slice_crossings(GREEN_CROSSINGS, WG2_BLOCKS),
        "signal_blocks": _WG2_SB,
    },
    "WR1": {
        "line":          "Red",
        "label":         "WR1  (Blocks 1-38)",
        "color":         "#ff4757",
        "blocks":        set(WR1_BLOCKS),
        "block_lengths": _slice(RED_BLOCK_LENGTHS, WR1_BLOCKS),
        "speed_limits":  _slice(RED_SPEED_LIMITS,  WR1_BLOCKS),
        "switches":      _slice_switches(RED_SWITCHES, WR1_BLOCKS),
        "crossings":     _slice_crossings(RED_CROSSINGS, WR1_BLOCKS),
        "signal_blocks": _WR1_SB,
    },
    "WR2": {
        "line":          "Red",
        "label":         "WR2  (Blocks 39-76)",
        "color":         "#ff4757",
        "blocks":        set(WR2_BLOCKS),
        "block_lengths": _slice(RED_BLOCK_LENGTHS, WR2_BLOCKS),
        "speed_limits":  _slice(RED_SPEED_LIMITS,  WR2_BLOCKS),
        "switches":      _slice_switches(RED_SWITCHES, WR2_BLOCKS),
        "crossings":     _slice_crossings(RED_CROSSINGS, WR2_BLOCKS),
        "signal_blocks": _WR2_SB,
    },

}

# Ordered wayside IDs per line - used to build line tabs in the correct order
LINE_WAYSIDES = {
    "Green": ["WG1", "WG2"],
    "Red":   ["WR1", "WR2"],

}

# O(1) routing lookup: (line_name, block_number) -> wayside_id
# Used by receive_live_data to route incoming blocks without scanning all waysides
BLOCK_TO_WAYSIDE = {}
for _wid, _cfg in WAYSIDE_CONFIGS.items():
    for _blk in _cfg["blocks"]:
        BLOCK_TO_WAYSIDE[(_cfg["line"], _blk)] = _wid


# =============================================================================
# CORE WAYSIDE LOGIC  -  BFS authority reach + signal / switch / crossing
# =============================================================================

def build_switch_map(switches):
    """
    Build a block-graph adjacency dict used by the BFS authority reach.
    Returns {host_block: [normal_branch_block, reverse_branch_block]}.
    Blocks not in this dict default to [block+1] (simple sequential track).
    """
    m = {}
    for sw in switches.values():
        h = sw["host"]
        n = sw["normal"][0]
        r = sw["reverse"][0]
        m[h] = [b for b in {n, r} if b > 0]
    return m


def authority_reach(start_block, authority_km, block_lengths, switch_map):
    """
    BFS forward from start_block accumulating block length in metres.
    Returns the set of blocks the train is cleared to enter.

    A block is included as soon as the train begins to enter it
    (dist_so_far < authority before entering that block).
    Both switch branches are explored so the reach covers all possible paths.

    Parameters
    ----------
    start_block  : first block to enter (usually occupied_block + 1)
    authority_km : authority in kilometres
    block_lengths: {block_num: length_in_metres}
    switch_map   : output of build_switch_map()
    """
    auth_m = authority_km * 1000.0
    if auth_m <= 0:
        return set()

    reached = set()
    # Queue entries: (block_number, metres_consumed_before_entering_this_block)
    queue   = [(start_block, 0.0)]
    visited = set()

    while queue:
        blk, dist_so_far = queue.pop(0)
        if blk in visited or blk <= 0:
            continue
        visited.add(blk)

        if dist_so_far >= auth_m:
            # Already over budget before even entering this block - skip it
            continue

        reached.add(blk)

        dist_end = dist_so_far + block_lengths.get(blk, 50)
        if dist_end >= auth_m:
            # Authority exhausted inside this block - don't walk further
            continue

        # Walk into next block(s); switch hosts fan out to both branches
        for nxt in switch_map.get(blk, [blk + 1]):
            if nxt > 0 and nxt not in visited:
                queue.append((nxt, dist_end))

    return reached


def compute_wayside_outputs(block_state, block_lengths, switches_def,
                             crossings_list, signal_blocks=None):
    """
    Compute signal, switch, and crossing states for ONE wayside's block range.

    Parameters
    ----------
    block_state   : {blk: {"occupied": bool,
                            "cmd_speed": float (km/h),
                            "authority": float (km)}}
    block_lengths : {blk: length_in_metres}
    switches_def  : switch definitions dict (only for this wayside)
    crossings_list: list of crossing block numbers (only for this wayside)
    signal_blocks : set of blocks with physical signals.
                    Blocks not in this set get signal=None.
                    Pass None to give all blocks a signal (backwards compat).

    Returns
    -------
    {
      "switches"  : {sw_id: "normal" | "reverse"},
      "signals"   : {blk:   "green" | "yellow" | "red" | None},
      "crossings" : {blk:   "active" | "inactive"},
      "reach"     : {train_blk: set_of_reached_blocks}
    }

    NOTE FOR PLC AUTHORS:
      Only return signal colours for blocks in signal_blocks.
      Return None for any block not in signal_blocks.
    """
    sw_map = build_switch_map(switches_def)

    # -- Authority reach per occupied block -----------------------------------
    # BFS starts from the block AHEAD of each train's current position
    reach_map = {}
    for blk, st in block_state.items():
        if st["occupied"]:
            reach_map[blk] = authority_reach(
                blk + 1, st["authority"], block_lengths, sw_map)

    all_reach = set().union(*reach_map.values()) if reach_map else set()
    occupied  = {b for b, s in block_state.items() if s["occupied"]}

    # -- Signal logic ---------------------------------------------------------
    signals = {}
    for blk in block_lengths:
        # No physical signal at this block - return None
        if signal_blocks is not None and blk not in signal_blocks:
            signals[blk] = None
            continue

        st        = block_state.get(blk, {})
        is_occ    = st.get("occupied", False)
        cmd_speed = st.get("cmd_speed", 0.0)
        authority = st.get("authority", 0.0)
        next1, next2 = blk + 1, blk + 2

        if is_occ:
            # Train on this block: signal based on clear distance ahead
            if next1 in occupied:
                sig = "red"                         # immediate block blocked
            elif authority <= 0 or cmd_speed == 0:
                sig = "red"                         # no authority / no speed
            else:
                len1   = block_lengths.get(next1, 50)
                len2   = block_lengths.get(next2, 50)
                auth_m = authority * 1000
                if auth_m < len1:
                    sig = "red"                     # cannot clear next block
                elif next2 in occupied or auth_m < (len1 + len2):
                    sig = "yellow"                  # cleared one block, not two
                else:
                    sig = "green"                   # two clear blocks ahead
        else:
            # No train here: signal based on occupancy of next two blocks
            if next1 in occupied:
                sig = "red"
            elif next2 in occupied:
                sig = "yellow"
            else:
                sig = "green"

        signals[blk] = sig

    # -- Switch logic ---------------------------------------------------------
    switch_states = {}
    for sw_id, sw in switches_def.items():
        host     = sw["host"]
        norm_blk = sw["normal"][0]
        rev_blk  = sw["reverse"][0]

        if host in occupied:
            # SAFETY RULE: never flip a switch while a train is on the host block
            switch_states[sw_id] = "normal"
            continue

        # Skip reverse routing for one-way exit switches whose reverse branch
        # points backward (rev_blk <= host) or is a self-loop (rev_blk == host).
        # These are yard-exit style switches (e.g. SW62) where there is no
        # meaningful alternate forward route — always keep them normal.
        if rev_blk <= host:
            switch_states[sw_id] = "normal"
            continue

        # Reverse only to let a merging train through; normal in all other cases
        # (covers: nobody on either branch, both branches occupied, only normal occupied)
        if rev_blk in occupied and norm_blk not in occupied:
            switch_states[sw_id] = "reverse"
        else:
            switch_states[sw_id] = "normal"

    # -- Crossing logic -------------------------------------------------------
    crossing_states = {}
    for cx in crossings_list:
        on_crossing = cx in occupied
        # Approaching: train one block before with authority reaching the crossing
        approaching = (cx - 1) in occupied and cx in all_reach
        crossing_states[cx] = "active" if (on_crossing or approaching) else "inactive"

    return {
        "switches":  switch_states,
        "signals":   signals,
        "crossings": crossing_states,
        "reach":     reach_map,
    }


# =============================================================================
# UNIT CONVERSION HELPERS
# =============================================================================

KMH_TO_MPH  = 0.621371
KM_TO_MILES = 0.621371

def kmh_to_mph(v):   return v * KMH_TO_MPH
def mph_to_kmh(v):   return v * (1.0 / KMH_TO_MPH)
def km_to_miles(v):  return v * KM_TO_MILES
def miles_to_km(v):  return v * (1.0 / KM_TO_MILES)


# =============================================================================
# COLOUR PALETTE  -  shared across controller and dashboard
# =============================================================================

C = {
    "bg":      "#1a1a2e",
    "panel":   "#16213e",
    "card":    "#0f3460",
    "header":  "#0d2137",
    "accent":  "#e94560",
    "green":   "#00d26a",
    "yellow":  "#ffd700",
    "red":     "#ff4757",
    "orange":  "#ff6b35",
    "blue":    "#4fc3f7",
    "white":   "#e0e0e0",
    "muted":   "#8899aa",
    "reach":   "#1d4e6b",
    "divider": "#1e2d45",
    "occupied":"#7c2d00",
}

SIG_COLOR = {"green": C["green"], "yellow": C["yellow"], "red": C["red"]}


# =============================================================================
# WAYSIDEFRAME  -  Full 6-wayside controller UI as an embeddable tk.Frame
# =============================================================================

class WaysideFrame(tk.Frame):
    """
    Full wayside controller UI hosting all 6 waysides in one window.

    Layout
    ------
    Header bar  (title + mode badge)
    Outer Notebook with 2 line tabs  (Green | Red)
      Each line tab:
        Maintenance toggle bar  (shared by both waysides on the line)
        Inner Notebook with 2 sub-tabs  (WG1|WG2 etc.)
          Each sub-tab:
            Sub-tab header  (block range label + PLC/Default badge)
            PanedWindow
              Left  = block inputs (occupied, cmd speed, authority)
              Right = computed outputs (signals, switches, crossings)

    Parameters
    ----------
    parent      : parent tk widget
    compute_fns : {wayside_id: callable} - optional per-wayside PLC functions.
                  Missing waysides use the built-in compute_wayside_outputs.
                  Hot-swap at runtime via set_compute_fn().
    mode        : "live" | "testing"
                  live    - inputs locked, 100 ms polling loop active
                  testing - inputs editable, no polling
    """

    def __init__(self, parent, compute_fns=None, mode="live", **kwargs):
        super().__init__(parent, bg=C["bg"], **kwargs)

        self._mode         = mode
        self._testing_mode = (mode == "testing")
        self._live_job     = None   # handle for the after() polling job

        # One compute function per wayside; unspecified ones use built-in logic
        self._compute_fns = {}
        for wid in WAYSIDE_CONFIGS:
            fn = (compute_fns or {}).get(wid)
            self._compute_fns[wid] = fn if fn is not None else compute_wayside_outputs

        # Input widget references for global lock/unlock: {wid: [(cb, sp_spd, sp_auth)]}
        self._input_widgets = {wid: [] for wid in WAYSIDE_CONFIGS}

        # Per-wayside runtime state dict - populated during _build_ui
        # Each entry starts as a copy of its static WAYSIDE_CONFIGS entry,
        # then gains UI-specific keys: block_vars, sw_labels, sig_labels,
        # cx_labels, plc_badge, maintenance, maint_btn, maint_banner
        self.waysides = {}
        for wid, cfg in WAYSIDE_CONFIGS.items():
            self.waysides[wid] = dict(cfg)
            self.waysides[wid].update({
                "block_vars":  {},    # {blk: {occupied, cmd_speed, authority}} (tk vars)
                "sw_labels":   {},    # {sw_id: (pos_lbl, route_lbl, override_var, override_btn)}
                "sig_labels":  {},    # {blk: (dot, cell, num_lbl, override_var, cycle_btn, spd_lbl)}
                "cx_labels":   {},    # {cx: label_widget}
                "plc_badge":   None,  # tk.Label showing "PLC" or "Default"
                "maintenance": False,
                "maint_btn":   None,  # shared with the other wayside on the same line
                "maint_banner":None,
            })

        self._build_ui()
        self._refresh()
        self._apply_mode()

    # =========================================================================
    # PUBLIC API  -  called by the dashboard
    # =========================================================================

    def set_compute_fn(self, wayside_id, fn):
        """
        Hot-swap the compute function for one specific wayside.
        The new function takes effect on the very next _refresh() call,
        which happens within 100 ms in live mode or immediately in testing mode.

        Parameters
        ----------
        wayside_id : "WG1" | "WG2" | "WR1" | "WR2"
        fn         : callable with the same signature as compute_wayside_outputs,
                     or None to revert to the built-in default logic.
        """
        self._compute_fns[wayside_id] = (
            fn if fn is not None else compute_wayside_outputs
        )
        # Update the PLC/Default badge on the sub-tab header
        badge = self.waysides[wayside_id].get("plc_badge")
        if badge:
            if fn is not None:
                badge.config(text="● PLC", fg=C["yellow"])
            else:
                badge.config(text="● Default", fg=C["muted"])

    def receive_live_data(self, line_name, block_data):
        """
        Push live block data from the CTC/Track Model into the input fields.
        Automatically routes each block to the correct wayside by looking up
        (line_name, block_number) in BLOCK_TO_WAYSIDE.

        Parameters
        ----------
        line_name  : "Green" | "Red"
        block_data : {block_num: {"occupied": bool,
                                  "cmd_speed": float,  # km/h (metric)
                                  "authority": float}} # km  (metric)

        All incoming data should be in metric units (km/h, km).
        Conversion to imperial (mph, miles) for the UI happens here.
        """
        # Accept live pushes in both modes. In integrated runs, operators may
        # open the testing view while still expecting CTC-fed values to update.

        # Full snapshot: CTC only lists occupied blocks. Clear any block on this
        # line that is missing from the payload (otherwise old occupancies linger).
        def _norm_blk(k):
            if isinstance(k, str) and k.isdigit():
                return int(k)
            return k

        incoming = {_norm_blk(k) for k in block_data.keys()}
        for _wid, ws in self.waysides.items():
            if ws.get("line") != line_name:
                continue
            for blk, bvars in ws.get("block_vars", {}).items():
                if _norm_blk(blk) not in incoming:
                    try:
                        bvars["occupied"].set(False)
                        bvars["cmd_speed"].set(0.0)
                        bvars["authority"].set(0.0)
                    except (KeyError, tk.TclError):
                        pass

        for blk, data in block_data.items():
            blk_n = _norm_blk(blk)
            # O(1) lookup - no loop needed to find which wayside owns this block
            wid = BLOCK_TO_WAYSIDE.get((line_name, blk_n))
            if wid is None:
                continue   # block not in any known wayside for this line

            bvars = self.waysides[wid]["block_vars"].get(blk_n)
            if bvars is None:
                continue

            bvars["occupied"].set(bool(data.get("occupied", False)))
            # Convert km/h -> mph and km -> miles for display
            bvars["cmd_speed"].set(
                round(kmh_to_mph(float(data.get("cmd_speed", 0.0))), 1))
            bvars["authority"].set(
                round(km_to_miles(float(data.get("authority", 0.0))), 3))

        self._refresh()

    # =========================================================================
    # UI CONSTRUCTION
    # =========================================================================

    def _build_ui(self):
        """Build the header bar and the outer 3-line notebook."""
        # -- Header bar -------------------------------------------------------
        hdr = tk.Frame(self, bg=C["header"], pady=8)
        hdr.pack(fill="x")

        tk.Label(hdr, text="WAYSIDE CONTROLLER",
                 font=("Helvetica", 18, "bold"),
                 bg=C["header"], fg=C["white"]).pack(side="left", padx=20)

        tk.Label(hdr, text="WG1 · WG2  |  WR1 · WR2",
                 font=("Helvetica", 10),
                 bg=C["header"], fg=C["muted"]).pack(side="left", padx=8)

        # Fixed mode badge - no toggle, mode is set when the window opens
        if self._mode == "testing":
            badge_text = "  TESTING MODE"
            badge_bg   = C["green"]; badge_fg = "#000000"
        else:
            badge_text = "  LIVE MODE"
            badge_bg   = C["yellow"]; badge_fg = "#000000"

        tk.Label(hdr, text=badge_text,
                 font=("Helvetica", 9, "bold"),
                 bg=badge_bg, fg=badge_fg,
                 padx=12, pady=5).pack(side="right", padx=20)

        if self._mode == "live":
            tk.Label(hdr,
                     text="  Receiving data from CTC & Track Model every 100 ms",
                     font=("Helvetica", 8, "italic"),
                     bg=C["header"], fg=C["yellow"]).pack(side="right", padx=6)

        # -- Configure notebook styles ----------------------------------------
        style = ttk.Style()
        style.theme_use("clam")
        style.configure("TNotebook",     background=C["bg"],   borderwidth=0)
        style.configure("TNotebook.Tab", background=C["card"], foreground=C["white"],
                        padding=[12, 5], font=("Helvetica", 10, "bold"))
        style.map("TNotebook.Tab", background=[("selected", C["accent"])])
        style.configure("Vertical.TScrollbar",
                        background=C["card"], troughcolor=C["bg"])

        # -- Outer notebook: one tab per line ---------------------------------
        outer_nb = ttk.Notebook(self)
        outer_nb.pack(fill="both", expand=True, padx=8, pady=8)

        for line_name in ["Green", "Red"]:
            line_frame = tk.Frame(outer_nb, bg=C["bg"])
            outer_nb.add(line_frame, text=f"  {line_name} Line  ")
            self._build_line_tab(line_frame, line_name)

    def _build_line_tab(self, parent, line_name):
        """
        Build one line tab.
        Contains a shared maintenance bar for the whole line
        and an inner notebook with one sub-tab per wayside.
        """
        wid_list   = LINE_WAYSIDES[line_name]
        line_color = WAYSIDE_CONFIGS[wid_list[0]]["color"]

        # -- Shared maintenance toggle bar (both waysides on this line) -------
        # bd=0 and highlightthickness=0 prevent border artifacts on Windows
        maint_bar = tk.Frame(parent, bg=C["bg"], pady=4,
                             borderwidth=0, highlightthickness=0)
        maint_bar.pack(fill="x", padx=6)
        maint_bar.pack_propagate(True)

        maint_btn = tk.Button(
            maint_bar,
            text="  Maintenance Mode: OFF",
            font=("Helvetica", 9, "bold"),
            bg=C["card"], fg=C["muted"],
            activebackground=C["card"],
            relief="flat", bd=0, padx=10, pady=5,
            cursor="hand2",
            command=lambda ln=line_name: self._toggle_maintenance(ln),
        )
        maint_btn.pack(side="left")

        # Warning banner - only visible when maintenance is ON
        maint_banner = tk.Label(
            maint_bar,
            text="    Manual override active - computed values paused",
            font=("Helvetica", 8, "italic"),
            bg=C["bg"], fg=C["orange"],
        )
        # Not packed yet; packed by _toggle_maintenance when turned ON

        # Store the shared maintenance widgets on both waysides of this line
        for wid in wid_list:
            self.waysides[wid]["maint_btn"]    = maint_btn
            self.waysides[wid]["maint_banner"] = maint_banner

        # -- Inner notebook: one sub-tab per wayside --------------------------
        inner_nb = ttk.Notebook(parent)
        inner_nb.pack(fill="both", expand=True, padx=4, pady=4)

        for wid in wid_list:
            sub_frame = tk.Frame(inner_nb, bg=C["bg"],
                                 borderwidth=0, highlightthickness=0)
            inner_nb.add(sub_frame, text=f"  {wid}  ")
            self._build_wayside_subtab(sub_frame, wid)

    def _build_wayside_subtab(self, parent, wid):
        """
        Build one wayside sub-tab.
        Contains a header row, then a PanedWindow with:
          left pane  = block inputs
          right pane = computed outputs
        """
        ws  = self.waysides[wid]
        cfg = WAYSIDE_CONFIGS[wid]
        lc  = cfg["color"]

        # -- Sub-tab header (block range + PLC/Default badge) -----------------
        sub_hdr = tk.Frame(parent, bg=C["panel"], pady=4)
        sub_hdr.pack(fill="x", padx=4, pady=(4, 0))

        tk.Label(sub_hdr, text=cfg["label"],
                 font=("Helvetica", 10, "bold"),
                 bg=C["panel"], fg=lc).pack(side="left", padx=12)

        plc_badge = tk.Label(sub_hdr, text="● Default",
                             font=("Helvetica", 8),
                             bg=C["panel"], fg=C["muted"])
        plc_badge.pack(side="right", padx=12)
        ws["plc_badge"] = plc_badge

        # -- Left / right paned layout ----------------------------------------
        pw = tk.PanedWindow(parent, orient="horizontal",
                            bg=C["bg"], sashwidth=5)
        pw.pack(fill="both", expand=True, padx=4, pady=4)

        left  = tk.Frame(pw, bg=C["bg"], borderwidth=0, highlightthickness=0)
        right = tk.Frame(pw, bg=C["bg"], borderwidth=0, highlightthickness=0)
        pw.add(left,  minsize=480)
        pw.add(right, minsize=440)

        self._section_label(left,  "INPUTS  -  Track Model & CTC", lc)
        self._make_scrollable(left, self._build_block_inputs, wid, lc)

        self._section_label(right, "OUTPUTS  -  Computed by Wayside", lc)
        self._make_scrollable(right, self._build_outputs_panel, wid, lc)

    # -- Layout helpers -------------------------------------------------------

    def _section_label(self, parent, text, color):
        """Coloured section header bar."""
        f = tk.Frame(parent, bg=color, pady=3)
        f.pack(fill="x", padx=4, pady=(4, 2))
        tk.Label(f, text=text,
                 font=("Helvetica", 9, "bold"),
                 bg=color, fg="#000000").pack(padx=8)

    def _make_scrollable(self, parent, builder_fn, *args):
        """
        Wrap builder_fn in a vertically scrollable canvas.
        Windows-safe: forces scrollregion sync on every scroll event,
        binds MouseWheel on all child widgets, and eliminates border/highlight
        artifacts that cause widget overlap on Windows GDI repaints.
        """
        canvas = tk.Canvas(parent, bg=C["bg"],
                           highlightthickness=0, borderwidth=0)
        sb = ttk.Scrollbar(parent, orient="vertical",
                           command=canvas.yview,
                           style="Vertical.TScrollbar")
        canvas.configure(yscrollcommand=sb.set)
        sb.pack(side="right", fill="y")
        canvas.pack(fill="both", expand=True)

        frame = tk.Frame(canvas, bg=C["bg"], borderwidth=0, highlightthickness=0)
        win   = canvas.create_window((0, 0), window=frame, anchor="nw")

        def _update_scrollregion(event=None):
            canvas.configure(scrollregion=canvas.bbox("all"))
            canvas.update_idletasks()

        def _update_width(event):
            canvas.itemconfig(win, width=event.width)
            _update_scrollregion()

        def _on_mousewheel(event):
            canvas.yview_scroll(-1 * (event.delta // 120), "units")
            _update_scrollregion()

        def _bind_mousewheel(widget):
            """Recursively bind MouseWheel to every child widget."""
            widget.bind("<MouseWheel>", _on_mousewheel)
            for child in widget.winfo_children():
                _bind_mousewheel(child)

        frame.bind("<Configure>", _update_scrollregion)
        canvas.bind("<Configure>", _update_width)
        canvas.bind("<MouseWheel>", _on_mousewheel)
        canvas.bind("<Enter>", lambda e: canvas.focus_set())

        builder_fn(frame, *args)

        # Bind mousewheel on all children after they are built
        _bind_mousewheel(frame)
        # Force an initial scrollregion calculation
        canvas.after(50, _update_scrollregion)

    def _card(self, parent, title):
        """Return the inner frame of a titled card panel."""
        outer = tk.Frame(parent, bg=C["bg"], pady=3)
        outer.pack(fill="x", padx=4, pady=4)
        tk.Label(outer, text=title,
                 font=("Helvetica", 9, "bold"),
                 bg=C["bg"], fg=C["white"]).pack(anchor="w", padx=4)
        inner = tk.Frame(outer, bg=C["card"], padx=6, pady=6)
        inner.pack(fill="x")
        return inner

    # =========================================================================
    # BLOCK INPUT PANEL
    # =========================================================================

    def _build_block_inputs(self, parent, wid, lc):
        """
        Build one input row per block in this wayside's range.
        Columns: Block | Speed limit (mph) | Occupied | Cmd Speed (mph) | Authority (miles)
        Input widgets are locked in live mode and unlocked in testing mode.
        """
        ws = self.waysides[wid]

        # Column headers
        hdr = tk.Frame(parent, bg=C["panel"])
        hdr.pack(fill="x", padx=4, pady=(4, 0))
        for txt, w in [("Block", 14), ("Spd Limit\n(mph)", 10),
                       ("Occupied", 9), ("Cmd Speed\n(mph)", 12),
                       ("Authority\n(miles)", 11)]:
            tk.Label(hdr, text=txt,
                     font=("Helvetica", 8, "bold"),
                     bg=C["panel"], fg=C["muted"],
                     width=w, anchor="center").pack(side="left", padx=2, pady=3)

        for blk in sorted(ws["block_lengths"].keys()):
            is_sw  = any(sw["host"] == blk for sw in ws["switches"].values())
            is_cx  = blk in ws["crossings"]
            tag    = " [SW]" if is_sw else (" [CX]" if is_cx else "")
            fg     = C["orange"] if is_cx else (C["yellow"] if is_sw else C["white"])
            row_bg = C["panel"] if blk % 2 == 0 else C["card"]

            spd_mph = kmh_to_mph(ws["speed_limits"].get(blk, 0))

            row = tk.Frame(parent, bg=row_bg,
                          borderwidth=0, highlightthickness=0)
            row.pack(fill="x", padx=4, pady=1)

            tk.Label(row, text=f"{blk}{tag}",
                     font=("Helvetica", 8), bg=row_bg, fg=fg,
                     width=14, anchor="w").pack(side="left", padx=3)
            tk.Label(row, text=f"{spd_mph:.0f}",
                     font=("Helvetica", 8), bg=row_bg, fg=C["muted"],
                     width=10, anchor="center").pack(side="left", padx=2)

            occ_var   = tk.BooleanVar(value=False)
            speed_var = tk.DoubleVar(value=0.0)   # UI in mph
            auth_var  = tk.DoubleVar(value=0.0)   # UI in miles

            cb = tk.Checkbutton(row, variable=occ_var,
                                bg=row_bg, fg=lc,
                                activebackground=row_bg,
                                selectcolor=row_bg,
                                command=self._refresh)
            cb.pack(side="left", padx=10)

            spinboxes = []
            for var, hi, inc, fmt in [(speed_var, 150, 5,    "%.0f"),
                                       (auth_var,  62,  0.05, "%.2f")]:
                sp = tk.Spinbox(row, from_=0, to=hi,
                                increment=inc, textvariable=var,
                                format=fmt, width=8,
                                font=("Helvetica", 8),
                                bg=C["bg"], fg=C["white"],
                                buttonbackground=C["card"],
                                command=self._refresh)
                sp.pack(side="left", padx=5)
                sp.bind("<Return>",   lambda e: self._refresh())
                sp.bind("<FocusOut>", lambda e: self._refresh())
                spinboxes.append(sp)

            # Save refs so _set_inputs_locked can find all widgets for this wayside
            self._input_widgets[wid].append((cb, spinboxes[0], spinboxes[1]))

            # block_vars stores tk vars (UI uses imperial; logic uses metric via conversion)
            ws["block_vars"][blk] = {
                "occupied":       occ_var,
                "cmd_speed":      speed_var,   # mph in UI
                "authority":      auth_var,    # miles in UI
                "row":            row,
                "row_default_bg": row_bg,
            }

    # =========================================================================
    # OUTPUT PANEL
    # =========================================================================

    def _build_outputs_panel(self, parent, wid, lc):
        """
        Build the outputs panel for one wayside showing:
          - Switch states with manual override buttons (hidden until maintenance ON)
          - Signal grid with cycle buttons (hidden until maintenance ON)
          - Crossing states
        """
        ws = self.waysides[wid]

        # -- Switch states ----------------------------------------------------
        sw_card = self._card(parent, "Switch States")
        for sw_id, sw in ws["switches"].items():
            row = tk.Frame(sw_card, bg=C["card"])
            row.pack(fill="x", pady=2, padx=4)

            tk.Label(row, text=f"{sw_id}  -  {sw['description']}",
                     font=("Helvetica", 9), bg=C["card"], fg=C["muted"],
                     width=34, anchor="w").pack(side="left")

            pos_lbl = tk.Label(row, text="NORMAL",
                               font=("Helvetica", 9, "bold"),
                               bg=C["card"], fg=C["green"], width=9)
            pos_lbl.pack(side="left", padx=4)

            route_lbl = tk.Label(row, text=sw["normal"][1],
                                 font=("Helvetica", 8),
                                 bg=C["card"], fg=C["muted"], width=14)
            route_lbl.pack(side="left")

            # Override button (hidden until maintenance ON)
            override_var = tk.StringVar(value="normal")
            override_btn = tk.Button(
                row, text="Set REVERSE",
                font=("Helvetica", 8),
                bg=C["panel"], fg=C["yellow"],
                activebackground=C["panel"],
                relief="flat", padx=6, pady=2,
                cursor="hand2",
            )
            override_btn.config(
                command=lambda sid=sw_id, w=wid, v=override_var, b=override_btn:
                    self._toggle_switch_override(sid, w, v, b)
            )
            # Packed by _set_override_widgets_visible when maintenance turns ON

            ws["sw_labels"][sw_id] = (pos_lbl, route_lbl, override_var, override_btn)

        # -- Signal grid ------------------------------------------------------
        sig_card = self._card(
            parent,
            "Signal States  (dot colour = signal)"
        )
        grid = tk.Frame(sig_card, bg=C["card"])
        grid.pack(fill="both", expand=True, padx=4, pady=4)
        COLS = 10   # number of block cells per row in the grid

        for i, blk in enumerate(sorted(ws["block_lengths"].keys())):
            r, c = divmod(i, COLS)
            cell = tk.Frame(grid, bg=C["bg"], bd=1, relief="solid")
            cell.grid(row=r, column=c, padx=2, pady=2, sticky="nsew")
            grid.columnconfigure(c, weight=1)

            num_lbl = tk.Label(cell, text=str(blk),
                               font=("Helvetica", 7),
                               bg=C["bg"], fg=C["muted"])
            num_lbl.pack()

            dot = tk.Label(cell, text="●",
                           font=("Helvetica", 12),
                           bg=C["bg"], fg=C["muted"])
            dot.pack()

            spd_mph = kmh_to_mph(ws["speed_limits"].get(blk, 0))
            spd_lbl = tk.Label(cell, text=f"{spd_mph:.0f}mph",
                               font=("Helvetica", 6),
                               bg=C["bg"], fg=C["muted"])
            spd_lbl.pack()

            # Cycle button for maintenance mode signal override (hidden by default)
            override_var = tk.StringVar(value="green")
            cycle_btn = tk.Button(
                cell, text="",
                font=("Helvetica", 6),
                bg=C["bg"], fg=C["muted"],
                activebackground=C["bg"],
                relief="flat", padx=0, pady=0,
                cursor="hand2", width=4,
            )
            cycle_btn.config(
                command=lambda b=blk, w=wid, v=override_var:
                    self._cycle_signal_override(b, w, v)
            )
            # Packed by _set_override_widgets_visible when maintenance turns ON

            ws["sig_labels"][blk] = (dot, cell, num_lbl, override_var, cycle_btn, spd_lbl)

        # -- Crossing states --------------------------------------------------
        cx_card = self._card(parent, "Railway Crossing States")
        if ws["crossings"]:
            for cx in ws["crossings"]:
                row = tk.Frame(cx_card, bg=C["card"])
                row.pack(fill="x", pady=2, padx=4)
                tk.Label(row, text=f"Block {cx}  Railway Crossing",
                         font=("Helvetica", 9), bg=C["card"], fg=C["muted"],
                         width=28, anchor="w").pack(side="left")
                lbl = tk.Label(row, text="INACTIVE",
                               font=("Helvetica", 10, "bold"),
                               bg=C["card"], fg=C["green"], width=14)
                lbl.pack(side="left", padx=6)
                ws["cx_labels"][cx] = lbl
        else:
            tk.Label(cx_card,
                     text="No crossings in this wayside section.",
                     font=("Helvetica", 8, "italic"),
                     bg=C["card"], fg=C["muted"]).pack(padx=4, pady=4)

        # -- Legend -----------------------------------------------------------
        leg = tk.Frame(parent, bg=C["bg"])
        leg.pack(fill="x", padx=6, pady=(4, 2))
        tk.Label(leg, text="Legend:",
                 font=("Helvetica", 8, "bold"),
                 bg=C["bg"], fg=C["muted"]).pack(side="left")
        for txt, col in [(" Green=clear",   C["green"]),
                         (" Yellow=caution", C["yellow"]),
                         (" Red=stop",       C["red"]),
                         (" -No signal",     C["muted"]),
                         (" Occupied",       C["occupied"])]:
            tk.Label(leg, text=txt,
                     font=("Helvetica", 8),
                     bg=C["bg"], fg=col).pack(side="left")

    # =========================================================================
    # REFRESH  -  Recompute and update all 6 waysides
    # =========================================================================

    def _refresh(self, *_):
        """
        Recompute outputs for every wayside and update ONLY widgets whose
        displayed value has actually changed since the last refresh.

        Switch labels, signal dots, and crossing labels each carry a
        _cache dict keyed by (wid, id) that stores the last-rendered
        value.  A .config() call is only issued when the new value
        differs from the cache, eliminating the per-tick full repaint
        that was corrupting the layout.

        Called every 1 s in live mode (via _schedule_live_poll) or
        immediately on any input change in testing mode.
        """
        # Initialise render caches on first call
        if not hasattr(self, "_sw_cache"):
            self._sw_cache  = {}   # (wid, sw_id) -> last rendered pos
            self._sig_cache = {}   # (wid, blk)   -> (bg, sig_text, sig_fg, sig_font)
            self._cx_cache  = {}   # (wid, cx)    -> last rendered state

        for wid, ws in self.waysides.items():
            # -- Gather block_state from UI vars ------------------------------
            block_state = {}
            for blk, bvars in ws["block_vars"].items():
                try:
                    speed_mph  = float(bvars["cmd_speed"].get())
                    auth_miles = float(bvars["authority"].get())
                except (tk.TclError, ValueError):
                    speed_mph, auth_miles = 0.0, 0.0
                block_state[blk] = {
                    "occupied":  bvars["occupied"].get(),
                    "cmd_speed": mph_to_kmh(speed_mph),
                    "authority": miles_to_km(auth_miles),
                }

            # -- Run this wayside's compute function --------------------------
            result = self._compute_fns[wid](
                block_state,
                ws["block_lengths"],
                ws["switches"],
                ws["crossings"],
                ws.get("signal_blocks"),
            )

            occupied_blks = {b for b, s in block_state.items() if s["occupied"]}
            in_maint      = ws["maintenance"]

            # -- Recolor input rows when occupancy changes --------------------
            if not hasattr(self, "_row_cache"):
                self._row_cache = {}
            for blk, bvars in ws["block_vars"].items():
                is_occ    = blk in occupied_blks
                cache_key = (wid, blk)
                if self._row_cache.get(cache_key) == is_occ:
                    continue
                self._row_cache[cache_key] = is_occ
                row_widget = bvars.get("row")
                new_bg     = C["occupied"] if is_occ else bvars.get("row_default_bg", C["panel"])
                if row_widget:
                    row_widget.config(bg=new_bg)
                    for child in row_widget.winfo_children():
                        try:
                            child.config(bg=new_bg)
                        except tk.TclError:
                            pass

            # -- Update switch labels (only on change) ------------------------
            for sw_id, computed_pos in result["switches"].items():
                entry = ws["sw_labels"].get(sw_id)
                if not entry:
                    continue
                pos_lbl, route_lbl, override_var, _ = entry
                sw  = ws["switches"][sw_id]
                pos = override_var.get() if in_maint else computed_pos

                cache_key = (wid, sw_id)
                if self._sw_cache.get(cache_key) == pos:
                    continue   # nothing changed — skip the .config() calls

                self._sw_cache[cache_key] = pos
                if pos == "normal":
                    pos_lbl.config(text="NORMAL",  fg=C["green"])
                    route_lbl.config(text=sw["normal"][1],  fg=C["muted"])
                else:
                    pos_lbl.config(text="REVERSE", fg=C["yellow"])
                    route_lbl.config(text=sw["reverse"][1], fg=C["yellow"])

            # -- Update signal grid (only on change) --------------------------
            for blk, computed_sig in result["signals"].items():
                entry = ws["sig_labels"].get(blk)
                if not entry:
                    continue
                dot, cell, num_lbl, override_var, cycle_btn, spd_lbl = entry
                is_occ = blk in occupied_blks

                # Determine desired background
                if is_occ:
                    bg = C["occupied"]
                else:
                    bg = C["bg"]

                # Determine desired dot appearance
                if computed_sig is None:
                    sig_text  = "—"
                    sig_fg    = C["muted"]
                    sig_font  = ("Helvetica", 10)
                else:
                    sig       = override_var.get() if in_maint else computed_sig
                    sig_text  = "●"
                    sig_fg    = SIG_COLOR.get(sig, C["muted"])
                    sig_font  = ("Helvetica", 12)

                cache_key  = (wid, blk)
                cached_val = self._sig_cache.get(cache_key)
                new_val    = (bg, sig_text, sig_fg, sig_font)

                if cached_val == new_val:
                    continue   # nothing changed — skip all .config() calls

                self._sig_cache[cache_key] = new_val

                # Apply background to all four cell widgets
                for w in (cell, dot, num_lbl, spd_lbl):
                    w.config(bg=bg)

                dot.config(text=sig_text, fg=sig_fg, font=sig_font)

            # -- Update crossing labels (only on change) ----------------------
            for cx, state in result["crossings"].items():
                lbl = ws["cx_labels"].get(cx)
                if not lbl:
                    continue
                cache_key = (wid, cx)
                if self._cx_cache.get(cache_key) == state:
                    continue   # nothing changed

                self._cx_cache[cache_key] = state
                lbl.config(
                    text="ACTIVE"   if state == "active"   else "INACTIVE",
                    fg  =C["orange"] if state == "active"  else C["green"]
                )

    # =========================================================================
    # MODE MANAGEMENT
    # =========================================================================

    def _apply_mode(self):
        """
        Apply the current mode globally across all 6 waysides.
        Testing -> unlock all inputs, stop live polling.
        Live    -> lock all inputs, start 100 ms polling.
        """
        if self._testing_mode:
            if self._live_job is not None:
                self.after_cancel(self._live_job)
                self._live_job = None
            self._set_inputs_locked(False)
        else:
            self._set_inputs_locked(True)
            self._schedule_live_poll()

    def _set_inputs_locked(self, locked):
        """Lock or unlock all block input widgets across all 6 waysides."""
        state  = "disabled" if locked else "normal"
        txt_fg = C["muted"] if locked else C["white"]
        for wid, widgets in self._input_widgets.items():
            for cb, sp_spd, sp_auth in widgets:
                cb.config(state=state)
                sp_spd.config(state=state, fg=txt_fg)
                sp_auth.config(state=state, fg=txt_fg)

    # =========================================================================
    # LIVE POLLING
    # =========================================================================

    def _schedule_live_poll(self):
        """Reschedule the live data poll 100 ms from now."""
        if not self._testing_mode:
            self._poll_live_data()
            self._live_job = self.after(1000, self._schedule_live_poll)

    def _poll_live_data(self):
        """
        Stub called every 100 ms in live mode.
        Replace with a real CTC / Track Model data fetch when ready.

        Example (once CTC is connected):
            for line in ["Green", "Red"]:
                data = ctc_module.get_block_states(line)
                self.receive_live_data(line, data)
        """
        pass   # <- connect your CTC / Track Model here

    # =========================================================================
    # MAINTENANCE MODE
    # =========================================================================

    def _toggle_maintenance(self, line_name):
        """
        Toggle maintenance mode ON/OFF for an entire line.
        Both waysides on the line share the same maintenance state.

        When turned ON:
          - Override vars are seeded from the current computed state
          - Override buttons become visible on all switch and signal cells
          - Outputs are driven by override vars instead of compute function

        When turned OFF:
          - Override buttons are hidden
          - Outputs return to the compute function's results
        """
        wid_list = LINE_WAYSIDES[line_name]

        # All waysides on this line share the same maintenance flag
        new_val = not self.waysides[wid_list[0]]["maintenance"]
        for wid in wid_list:
            self.waysides[wid]["maintenance"] = new_val

        # maint_btn and maint_banner are shared widgets (same object on both waysides)
        btn    = self.waysides[wid_list[0]]["maint_btn"]
        banner = self.waysides[wid_list[0]]["maint_banner"]

        if new_val:
            btn.config(text="  Maintenance Mode: ON",
                       bg=C["orange"], fg="#000000")
            banner.pack(side="left", padx=10)
            # Seed override vars from current computed state for a smooth transition
            for wid in wid_list:
                self._seed_overrides(wid)
        else:
            btn.config(text="  Maintenance Mode: OFF",
                       bg=C["card"], fg=C["muted"])
            banner.pack_forget()

        for wid in wid_list:
            self._set_override_widgets_visible(wid, new_val)

        self._refresh()

    def _seed_overrides(self, wid):
        """
        Run compute_fn once and copy the results into the override tk.StringVars.
        This ensures that when maintenance turns ON, the override buttons start
        from the last computed value rather than arbitrary defaults.
        """
        ws = self.waysides[wid]
        block_state = {}
        for blk, bvars in ws["block_vars"].items():
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

        result = self._compute_fns[wid](
            block_state, ws["block_lengths"],
            ws["switches"], ws["crossings"],
            ws.get("signal_blocks"),
        )

        for sw_id, pos in result["switches"].items():
            entry = ws["sw_labels"].get(sw_id)
            if entry:
                _, _, override_var, override_btn = entry
                override_var.set(pos)
                override_btn.config(
                    text="Set NORMAL" if pos == "reverse" else "Set REVERSE"
                )

        for blk, sig in result["signals"].items():
            if sig is None:
                continue   # skip blocks with no physical signal
            entry = ws["sig_labels"].get(blk)
            if entry:
                _, _, _, override_var, cycle_btn, _ = entry
                override_var.set(sig)
                cycle_btn.config(text=sig[:1].upper(),
                                 fg=SIG_COLOR.get(sig, C["muted"]))

    def _set_override_widgets_visible(self, wid, visible):
        """Pack or forget all manual override widgets for one wayside."""
        ws = self.waysides[wid]

        for sw_id, entry in ws["sw_labels"].items():
            _, _, _, override_btn = entry
            if visible:
                override_btn.pack(side="left", padx=(8, 0))
            else:
                override_btn.pack_forget()

        for blk, entry in ws["sig_labels"].items():
            _, _, _, _, cycle_btn, _ = entry
            if visible:
                cycle_btn.pack()
            else:
                cycle_btn.pack_forget()

    # =========================================================================
    # MANUAL OVERRIDE ACTIONS
    # =========================================================================

    def _toggle_switch_override(self, sw_id, wid, override_var, btn):
        """
        Flip the manual switch override between normal and reverse.
        Called when the programmer clicks a switch override button
        while maintenance mode is ON.
        """
        new_pos = "reverse" if override_var.get() == "normal" else "normal"
        override_var.set(new_pos)
        btn.config(text="Set NORMAL" if new_pos == "reverse" else "Set REVERSE")
        self._refresh()

    def _cycle_signal_override(self, blk, wid, override_var):
        """
        Step the manual signal override one step forward in the cycle:
            green -> yellow -> red -> green
        Called when the programmer clicks a signal cycle button
        while maintenance mode is ON.
        """
        cycle   = ["green", "yellow", "red"]
        current = override_var.get()
        if current not in cycle:
            current = "green"
        next_sig = cycle[(cycle.index(current) + 1) % len(cycle)]
        override_var.set(next_sig)

        # Update the cycle button appearance
        entry = self.waysides[wid]["sig_labels"].get(blk)
        if entry:
            _, _, _, _, cycle_btn, _ = entry
            cycle_btn.config(text=next_sig[:1].upper(),
                             fg=SIG_COLOR.get(next_sig, C["muted"]))
        self._refresh()


# =============================================================================
# STANDALONE LAUNCHER  -  used when running wayside_controller.py directly
# =============================================================================

class WaysideApp(tk.Tk):
    """Thin wrapper that runs WaysideFrame as a standalone application."""
    def __init__(self):
        super().__init__()
        self.title("Wayside Controller - 6 Wayside Architecture")
        self.geometry("1400x860")
        self.configure(bg=C["bg"])
        self.resizable(True, True)
        WaysideFrame(self, mode="testing").pack(fill="both", expand=True)


def launch_as_toplevel(parent, compute_fns=None, title=None, mode="live"):
    """
    Open the Wayside Controller as a child Toplevel window.

    Parameters
    ----------
    parent      : parent tk widget (the WaysideDashboard)
    compute_fns : {wayside_id: callable} - optional per-wayside PLC functions.
                  Missing waysides use built-in compute_wayside_outputs.
    title       : window title string
    mode        : "live" | "testing"

    Returns
    -------
    tk.Toplevel  containing the WaysideFrame
    """
    win = tk.Toplevel(parent)
    win.title(title or "Wayside Controller")
    win.geometry("1400x860")
    win.configure(bg=C["bg"])
    win.resizable(True, True)
    WaysideFrame(win, compute_fns=compute_fns, mode=mode).pack(fill="both", expand=True)
    return win


if __name__ == "__main__":
    WaysideApp().mainloop()
