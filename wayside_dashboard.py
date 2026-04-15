"""
Wayside Control System Dashboard
==================================
The top-level window the programmer interacts with.

Features
--------
- Track map display (Green/Red line image)
- "Open Controller" button  -> live-mode controller window
- "Open Testing"   button  -> testing-mode controller window
- "PLC Manager"    button  -> popup to upload/clear PLC files per wayside
- Button locking: only one controller window can be open at a time
- Hot-swap: PLC uploads and clears take effect on the very next refresh tick

PLC Manager layout (inside the popup):
  Organised by line (Green / Red sections)
  One row per wayside: [name] [file path entry] [Browse] [Upload] [status] [Clear]

Relationship to wayside_controller.py:
  - Imports launch_as_toplevel() and WAYSIDE_CONFIGS / LINE_WAYSIDES
  - Calls controller_frame.set_compute_fn(wid, fn) for hot-swap
"""

import tkinter as tk
from tkinter import ttk, filedialog, messagebox
import os
import importlib.util

from wayside_controller import (
    launch_as_toplevel,
    WAYSIDE_CONFIGS,
    LINE_WAYSIDES,
    C,
)

# SharedState bridge (optional – gracefully absent if run standalone)
try:
    from shared_state import SharedState
    _SHARED_STATE_AVAILABLE = True
except ImportError:
    _SHARED_STATE_AVAILABLE = False

try:
    from PIL import Image, ImageTk
    PIL_AVAILABLE = True
except ImportError:
    PIL_AVAILABLE = False


class WaysideDashboard(tk.Tk):
    """
    Main dashboard window for the Wayside Control System.

    State
    -----
    _plc_state : {wayside_id: {"path": str, "module": module|None, "fn": callable|None,
                               "path_var": tk.StringVar, "status_lbl": tk.Label}}
                 Tracks PLC upload state per wayside.

    _controller_frame : WaysideFrame | None
                 Reference to the open controller frame for hot-swap calls.
    """

    def __init__(self, shared_state=None):
        super().__init__()
        self.title("Wayside Control System")
        self.geometry("1100x720")
        self.configure(bg=C["bg"])
        self.resizable(True, True)

        # SharedState bridge (None when running standalone)
        self._shared = shared_state

        # Initialise block data for the map/info area
        self.green_line_blocks = self._init_green_blocks()
        self.red_line_blocks   = self._init_red_blocks()

        # PLC state per wayside - all start with no PLC uploaded (default logic)
        self._plc_state = {
            wid: {
                "path":       "",
                "module":     None,
                "fn":         None,       # None means use built-in default logic
                "path_var":   tk.StringVar(value=""),
                "status_lbl": None,       # filled in when PLC Manager row is built
                "err_lbl":    None,
            }
            for wid in WAYSIDE_CONFIGS
        }

        # Reference to the currently open WaysideFrame (None when no window is open)
        self._controller_frame = None

        self._setup_ui()

        # Start SharedState polling loop (only when wired to CTC)
        if self._shared is not None:
            self.after(100, self._poll_shared_state)

    # =========================================================================
    # BLOCK DATA INITIALISATION
    # =========================================================================

    def _init_green_blocks(self):
        """Initialise the Green Line block metadata dict (blocks 1-150)."""
        stations  = {2:"PIONEER", 9:"EDGEBROOK", 16:"STATION", 22:"WHITED",
                     31:"SOUTH BANK", 39:"CENTRAL", 48:"INGLEWOOD", 57:"OVERBROOK",
                     65:"GLENBURY", 73:"DORMONT", 77:"MT LEBANON", 88:"POPLAR",
                     96:"CASTLE SHANNON"}
        junctions = {1,12,28,29,57,58,62,63,77,85,86,100,101}
        crossings  = {19}
        blocks = {}
        for i in range(1, 151):
            blocks[i] = {
                "type":            "Station"  if i in stations  else
                                   "Junction" if i in junctions else
                                   "Crossing" if i in crossings else "Regular",
                "station_name":    stations.get(i, "N/A"),
                "has_switch":      i in junctions,
                "has_crossing":    i in crossings,
                "occupancy":       "Unoccupied",
                "track_fault":     "No Fault",
                "switch_position": "Position A" if i in junctions else "N/A",
                "light_color":     "Green"      if i in junctions else "N/A",
                "crossing_status": "Inactive"   if i in crossings else "N/A",
                "speed_limit":     45,
                "authority":       5.0,
            }
        return blocks

    def _init_red_blocks(self):
        """Initialise the Red Line block metadata dict (blocks 1-76)."""
        stations  = {7:"SHADYSIDE", 16:"HERRON AVE", 21:"SWISSVILLE",
                     25:"PENN STATION", 35:"STEEL PLAZA", 45:"FIRST AVE",
                     48:"STATION SQUARE", 60:"SOUTH HILLS JUNCTION"}
        junctions = {1,9,15,27,28,32,33,38,39,43,44,52,53,66,67,72,76}
        crossings  = {11,45,47}
        blocks = {}
        for i in range(1, 77):
            blocks[i] = {
                "type":            "Station"  if i in stations  else
                                   "Junction" if i in junctions else
                                   "Crossing" if i in crossings else "Regular",
                "station_name":    stations.get(i, "N/A"),
                "has_switch":      i in junctions,
                "has_crossing":    i in crossings,
                "occupancy":       "Unoccupied",
                "track_fault":     "No Fault",
                "switch_position": "Position A" if i in junctions else "N/A",
                "light_color":     "Green"      if i in junctions else "N/A",
                "crossing_status": "Inactive"   if i in crossings else "N/A",
                "speed_limit":     40,
                "authority":       4.5,
            }
        return blocks

    # =========================================================================
    # UI SETUP
    # =========================================================================

    def _setup_ui(self):
        """Build the full dashboard: header, footer buttons, map area."""
        self._style_ttk()
        self._build_header()
        self._build_footer()   # footer packed to bottom first so it anchors
        self._build_map_area()

    def _style_ttk(self):
        style = ttk.Style()
        style.theme_use("clam")
        style.configure("TCombobox",
                        fieldbackground=C["card"], background=C["card"],
                        foreground=C["white"], arrowcolor=C["muted"])

    # -- Header ---------------------------------------------------------------

    def _build_header(self):
        hdr = tk.Frame(self, bg=C["header"])
        hdr.pack(fill="x", side="top")

        tk.Frame(hdr, bg=C["accent"], width=5).pack(side="left", fill="y")

        title_block = tk.Frame(hdr, bg=C["header"], padx=20, pady=14)
        title_block.pack(side="left")
        tk.Label(title_block, text="WAYSIDE CONTROL SYSTEM",
                 font=("Helvetica", 18, "bold"),
                 bg=C["header"], fg=C["white"]).pack(anchor="w")
        tk.Label(title_block,
                 text="WG1 · WG2  |  WR1 · WR2",
                 font=("Helvetica", 9),
                 bg=C["header"], fg=C["muted"]).pack(anchor="w")

        status_block = tk.Frame(hdr, bg=C["header"], padx=20)
        status_block.pack(side="right", pady=14)
        for label, color in [("Green Line (WG1 · WG2)", C["green"]),
                              ("Red Line   (WR1 · WR2)", C["red"])]:
            row = tk.Frame(status_block, bg=C["header"])
            row.pack(anchor="e", pady=1)
            tk.Label(row, text="\u25cf", fg=color, bg=C["header"],
                     font=("Helvetica", 10)).pack(side="left")
            tk.Label(row, text=f"  {label}", fg=C["muted"], bg=C["header"],
                     font=("Helvetica", 8)).pack(side="left")

        tk.Frame(self, bg=C["accent"], height=2).pack(fill="x", side="top")

    # -- Map area -------------------------------------------------------------

    def _build_map_area(self):
        outer = tk.Frame(self, bg=C["bg"])
        outer.pack(fill="both", expand=True, padx=12, pady=10)

        script_dir = os.path.dirname(os.path.abspath(__file__))

        rg_card = self._map_card(outer, "RED & GREEN LINE", C["green"])
        rg_card.pack(side="left", fill="both", expand=True)
        rg_path = os.path.join(script_dir, "Picture1.png")
        if PIL_AVAILABLE and os.path.exists(rg_path):
            self._load_map_image(rg_card, rg_path, key="rg")
        else:
            self._map_fallback(rg_card, "Picture1.png")



    def _map_card(self, parent, title, accent_color):
        card = tk.Frame(parent, bg=C["card"], bd=0)
        tk.Frame(card, bg=accent_color, height=3).pack(fill="x")
        title_row = tk.Frame(card, bg=C["card"], pady=6)
        title_row.pack(fill="x", padx=10)
        tk.Label(title_row, text="\u258c " + title,
                 font=("Helvetica", 8, "bold"),
                 bg=C["card"], fg=accent_color).pack(side="left")
        return card

    def _map_fallback(self, parent, filename):
        msg = (f"{filename} not found." if PIL_AVAILABLE
               else "Install Pillow:  pip install pillow")
        tk.Label(parent, text=msg, bg=C["card"], fg=C["muted"],
                 font=("Helvetica", 9, "italic")).pack(expand=True)

    def _load_map_image(self, parent, img_path, key="map"):
        canvas = tk.Canvas(parent, bg=C["card"], highlightthickness=0)
        canvas.pack(fill="both", expand=True, padx=6, pady=(0, 6))
        pil_img = Image.open(img_path)
        if not hasattr(self, "_map_store"):
            self._map_store = {}
        self._map_store[key] = {"pil": pil_img, "tk": None}

        def _redraw(event=None, c=canvas, k=key):
            w, h = c.winfo_width(), c.winfo_height()
            if w < 2 or h < 2:
                return
            iw, ih = self._map_store[k]["pil"].size
            scale  = min(w / iw, h / ih)
            nw, nh = max(1, int(iw * scale)), max(1, int(ih * scale))
            resized = self._map_store[k]["pil"].resize((nw, nh), Image.LANCZOS)
            self._map_store[k]["tk"] = ImageTk.PhotoImage(resized)
            c.delete("all")
            c.create_image(w // 2, h // 2, anchor="center",
                           image=self._map_store[k]["tk"])

        canvas.bind("<Configure>", _redraw)
        canvas.after(50, _redraw)

    # -- Footer ---------------------------------------------------------------

    def _build_footer(self):
        """
        Footer with three buttons:
          Open Controller  |  Open Testing  |  PLC Manager
        """
        tk.Frame(self, bg=C["divider"], height=2).pack(fill="x", side="bottom")

        footer = tk.Frame(self, bg=C["header"])
        footer.pack(fill="x", side="bottom")

        inner = tk.Frame(footer, bg=C["header"])
        inner.pack(fill="x", padx=20, pady=14)

        # -- Open Controller (live mode) --------------------------------------
        live_col = tk.Frame(inner, bg=C["header"])
        live_col.pack(side="left", padx=(0, 16))

        tk.Label(live_col, text="LIVE MODE",
                 font=("Helvetica", 7, "bold"),
                 bg=C["header"], fg=C["yellow"]).pack(anchor="w")

        btn_row = tk.Frame(live_col, bg=C["header"])
        btn_row.pack(anchor="w", pady=(4, 0))

        self.default_btn = tk.Button(
            btn_row, text="Open Controller",
            font=("Helvetica", 9, "bold"),
            bg=C["accent"], fg=C["white"],
            activebackground="#c73652",
            relief="flat", padx=12, pady=6,
            cursor="hand2",
            command=self._open_live,
        )
        self.default_btn.pack(side="left")

        self.live_status_lbl = tk.Label(
            btn_row, text="  Active",
            bg=C["header"], fg=C["green"],
            font=("Helvetica", 9, "italic"),
        )
        # Not packed until a window opens

        tk.Frame(inner, bg=C["divider"], width=2).pack(
            side="left", fill="y", padx=14)

        # -- Open Testing -----------------------------------------------------
        test_col = tk.Frame(inner, bg=C["header"])
        test_col.pack(side="left", padx=(0, 16))

        tk.Label(test_col, text="TESTING MODE",
                 font=("Helvetica", 7, "bold"),
                 bg=C["header"], fg=C["green"]).pack(anchor="w")

        test_row = tk.Frame(test_col, bg=C["header"])
        test_row.pack(anchor="w", pady=(4, 0))

        self.testing_btn = tk.Button(
            test_row, text="Open Testing",
            font=("Helvetica", 9, "bold"),
            bg=C["green"], fg="#000000",
            activebackground="#00a854",
            relief="flat", padx=12, pady=6,
            cursor="hand2",
            command=self._open_testing,
        )
        self.testing_btn.pack(side="left")

        self.test_status_lbl = tk.Label(
            test_row, text="  Active",
            bg=C["header"], fg=C["green"],
            font=("Helvetica", 9, "italic"),
        )

        tk.Frame(inner, bg=C["divider"], width=2).pack(
            side="left", fill="y", padx=14)

        # -- PLC Manager button -----------------------------------------------
        plc_col = tk.Frame(inner, bg=C["header"])
        plc_col.pack(side="left")

        tk.Label(plc_col, text="PLC UPLOAD",
                 font=("Helvetica", 7, "bold"),
                 bg=C["header"], fg=C["blue"]).pack(anchor="w")

        plc_row = tk.Frame(plc_col, bg=C["header"])
        plc_row.pack(anchor="w", pady=(4, 0))

        self.plc_mgr_btn = tk.Button(
            plc_row, text="PLC Manager",
            font=("Helvetica", 9, "bold"),
            bg=C["blue"], fg="#000000",
            activebackground="#39a8d4",
            relief="flat", padx=12, pady=6,
            cursor="hand2",
            command=self._open_plc_manager,
        )
        self.plc_mgr_btn.pack(side="left")

        # PLC syntax help link
        help_lbl = tk.Label(
            inner, text="  How does PLC work?",
            bg=C["header"], fg=C["blue"],
            font=("Helvetica", 8, "underline"),
            cursor="hand2",
        )
        help_lbl.pack(side="left", padx=(16, 0))
        help_lbl.bind("<Button-1>", lambda e: self._show_plc_help())

        # Collect button references for global lock/unlock
        self.ALL_BTNS = ["default_btn", "testing_btn", "plc_mgr_btn"]

        for btn in (self.default_btn, self.testing_btn, self.plc_mgr_btn):
            self._attach_tooltip(btn,
                "Unavailable: a controller window is currently open.")

    # =========================================================================
    # CONTROLLER WINDOW MANAGEMENT
    # =========================================================================

    def _open_live(self):
        """Open a live-mode controller window using current PLC assignments."""
        compute_fns = self._build_compute_fns()
        win = launch_as_toplevel(
            self,
            compute_fns=compute_fns,
            title="Wayside Controller - Live",
            mode="live",
        )
        # Keep a reference to the WaysideFrame for hot-swap calls
        self._controller_frame = win.winfo_children()[0]
        self._lock_all(self.live_status_lbl)
        win.protocol("WM_DELETE_WINDOW",
                     lambda: self._on_window_closed(self.live_status_lbl, win))

    def _open_testing(self):
        """Open a testing-mode controller window using current PLC assignments."""
        compute_fns = self._build_compute_fns()
        win = launch_as_toplevel(
            self,
            compute_fns=compute_fns,
            title="Wayside Controller - Testing",
            mode="testing",
        )
        self._controller_frame = win.winfo_children()[0]
        self._lock_all(self.test_status_lbl)
        win.protocol("WM_DELETE_WINDOW",
                     lambda: self._on_window_closed(self.test_status_lbl, win))

    def _build_compute_fns(self):
        """
        Build the compute_fns dict passed to launch_as_toplevel.
        Waysides with an uploaded PLC use that function;
        waysides with fn=None use the built-in default inside WaysideFrame.
        """
        return {wid: self._plc_state[wid]["fn"] for wid in WAYSIDE_CONFIGS}

    def _on_window_closed(self, status_lbl, win):
        """Called when the programmer closes the controller window."""
        self._controller_frame = None
        self._unlock_all(status_lbl, win)

    # =========================================================================
    # BUTTON LOCKING
    # =========================================================================

    def _lock_all(self, status_lbl=None):
        """Disable all 3 launch buttons while a controller window is open."""
        for attr in self.ALL_BTNS:
            btn = getattr(self, attr)
            btn.config(state="disabled", bg="#2a2a2a", fg="#666666")
        if status_lbl:
            status_lbl.pack(side="left", padx=(8, 0))

    def _unlock_all(self, status_lbl, win):
        """Re-enable all buttons after the controller window is closed."""
        win.destroy()
        self.default_btn.config(state="normal",  bg=C["accent"], fg=C["white"])
        self.testing_btn.config(state="normal",  bg=C["green"],  fg="#000000")
        self.plc_mgr_btn.config(state="normal",  bg=C["blue"],   fg="#000000")
        if status_lbl:
            status_lbl.pack_forget()

    def _attach_tooltip(self, widget, text):
        """Show a tooltip when hovering over a disabled button."""
        tip_win = []

        def on_enter(event):
            if widget["state"] == "disabled":
                x = widget.winfo_rootx() + 20
                y = widget.winfo_rooty() + widget.winfo_height() + 4
                tw = tk.Toplevel(self)
                tw.wm_overrideredirect(True)
                tw.wm_geometry(f"+{x}+{y}")
                tk.Label(tw, text=text, bg="#1e1e1e", fg="#e0e0e0",
                         font=("Helvetica", 8), relief="solid", borderwidth=1,
                         padx=8, pady=4).pack()
                tip_win.append(tw)

        def on_leave(event):
            for tw in tip_win:
                tw.destroy()
            tip_win.clear()

        widget.bind("<Enter>", on_enter)
        widget.bind("<Leave>", on_leave)

    # =========================================================================
    # PLC MANAGER POPUP
    # =========================================================================

    def _open_plc_manager(self):
        """
        Open the PLC Manager modal popup.
        Organised by line; one row per wayside showing:
          [wayside id] [path entry] [Browse] [Upload] [status] [Clear]
        """
        popup = tk.Toplevel(self)
        popup.title("PLC Manager")
        popup.configure(bg=C["bg"])
        popup.resizable(False, False)

        # Title bar
        tk.Label(popup,
                 text="PLC Manager  -  Upload a custom PLC file per wayside",
                 bg=C["card"], fg=C["white"],
                 font=("Helvetica", 11, "bold"),
                 anchor="w", padx=16, pady=10).pack(fill="x")

        tk.Label(popup,
                 text="Waysides with no PLC uploaded run the built-in default logic.",
                 bg=C["bg"], fg=C["muted"],
                 font=("Helvetica", 8, "italic")).pack(anchor="w", padx=16, pady=(6, 2))

        # One section per line, two rows per section (one per wayside)
        for line_name, wid_list in LINE_WAYSIDES.items():
            line_color = WAYSIDE_CONFIGS[wid_list[0]]["color"]

            # Line section header
            sec_hdr = tk.Frame(popup, bg=line_color, pady=3)
            sec_hdr.pack(fill="x", padx=12, pady=(10, 2))
            tk.Label(sec_hdr, text=f"  {line_name} Line",
                     font=("Helvetica", 10, "bold"),
                     bg=line_color, fg="#000000").pack(side="left", padx=8)

            for wid in wid_list:
                self._build_plc_manager_row(popup, wid)

        tk.Button(popup, text="Close",
                  font=("Helvetica", 9, "bold"),
                  bg=C["accent"], fg=C["white"],
                  activebackground="#c73652",
                  relief="flat", padx=16, pady=6,
                  cursor="hand2",
                  command=popup.destroy).pack(pady=12)

        # Centre over dashboard
        popup.update_idletasks()
        pw, ph = popup.winfo_reqwidth(), popup.winfo_reqheight()
        x = self.winfo_rootx() + (self.winfo_width()  - pw) // 2
        y = self.winfo_rooty() + (self.winfo_height() - ph) // 2
        popup.geometry(f"+{max(0,x)}+{max(0,y)}")
        popup.grab_set()   # modal

    def _build_plc_manager_row(self, parent, wid):
        """
        Build one row in the PLC Manager popup for the given wayside.
        Stores references to the status and error labels in _plc_state.
        """
        state = self._plc_state[wid]
        cfg   = WAYSIDE_CONFIGS[wid]

        outer = tk.Frame(parent, bg=C["bg"])
        outer.pack(fill="x", padx=12, pady=2)

        row = tk.Frame(outer, bg=C["panel"])
        row.pack(fill="x")

        # Wayside ID label
        tk.Label(row, text=wid,
                 font=("Helvetica", 9, "bold"),
                 bg=C["panel"], fg=cfg["color"],
                 width=5, anchor="w").pack(side="left", padx=(8, 4))

        # Read-only file path entry
        tk.Entry(row, textvariable=state["path_var"],
                 width=30, state="readonly",
                 bg=C["card"], fg=C["white"],
                 readonlybackground=C["card"],
                 relief="flat",
                 font=("Helvetica", 8)).pack(side="left", ipady=3, padx=(0, 4))

        # Error label for this row (packed below)
        err_lbl = tk.Label(outer, text="",
                           bg=C["bg"], fg="#ff6b6b",
                           font=("Helvetica", 7, "italic"))
        state["err_lbl"] = err_lbl

        # Browse button
        tk.Button(row, text="Browse",
                  font=("Helvetica", 8),
                  bg=C["card"], fg=C["white"],
                  activebackground=C["bg"],
                  relief="flat", padx=8, pady=3,
                  cursor="hand2",
                  command=lambda w=wid, e=err_lbl: self._browse_plc(w, e)
                  ).pack(side="left", padx=(0, 4))

        # Upload button
        tk.Button(row, text="Upload",
                  font=("Helvetica", 8, "bold"),
                  bg=C["blue"], fg="#000000",
                  activebackground="#39a8d4",
                  relief="flat", padx=8, pady=3,
                  cursor="hand2",
                  command=lambda w=wid, e=err_lbl: self._upload_plc(w, e)
                  ).pack(side="left", padx=(0, 6))

        # Status label: "PLC Active" or "Default"
        fn = state["fn"]
        status_lbl = tk.Label(row,
                              text="PLC Active" if fn is not None else "Default",
                              font=("Helvetica", 8, "italic"),
                              bg=C["panel"],
                              fg=C["green"] if fn is not None else C["muted"],
                              width=12, anchor="w")
        status_lbl.pack(side="left", padx=(0, 6))
        state["status_lbl"] = status_lbl

        # Clear button
        tk.Button(row, text="Clear",
                  font=("Helvetica", 8),
                  bg=C["card"], fg=C["muted"],
                  activebackground=C["bg"],
                  relief="flat", padx=6, pady=3,
                  cursor="hand2",
                  command=lambda w=wid: self._clear_plc(w)
                  ).pack(side="left")

        err_lbl.pack(anchor="w", padx=4, pady=(1, 0))

    # =========================================================================
    # PLC FILE VALIDATION, UPLOAD, CLEAR
    # =========================================================================

    def _browse_plc(self, wid, err_lbl):
        """
        Open a file browser for the given wayside.
        Validates extension (.py) and filename (no spaces).
        """
        filename = filedialog.askopenfilename(
            title=f"Select PLC File for {wid}",
            filetypes=[("Python files", "*.py"), ("All files", "*.*")]
        )
        if not filename:
            return

        basename = os.path.basename(filename)

        if not basename.lower().endswith(".py"):
            self._plc_state[wid]["path_var"].set("")
            err_lbl.config(text="Only .py files are accepted.")
            return

        if " " in basename:
            self._plc_state[wid]["path_var"].set("")
            err_lbl.config(text="File name cannot contain spaces.")
            return

        self._plc_state[wid]["path_var"].set(filename)
        err_lbl.config(text="")

    def _upload_plc(self, wid, err_lbl):
        """
        Load the PLC file for the given wayside and hot-swap if the
        controller window is currently open.
        The new function takes effect on the very next _refresh() tick.
        """
        path = self._plc_state[wid]["path_var"].get()
        if not path:
            err_lbl.config(text="No file selected. Use Browse first.")
            return

        module = self._load_plc_module(path)
        if module is None:
            return   # error dialog already shown by _load_plc_module

        fn = module.compute_wayside_outputs
        self._plc_state[wid]["module"] = module
        self._plc_state[wid]["fn"]     = fn

        # Update status label in the PLC Manager row
        status_lbl = self._plc_state[wid].get("status_lbl")
        if status_lbl:
            status_lbl.config(text="PLC Active", fg=C["green"])

        # Hot-swap: update the running controller frame immediately
        if self._controller_frame is not None:
            self._controller_frame.set_compute_fn(wid, fn)

    def _clear_plc(self, wid):
        """
        Clear the uploaded PLC for the given wayside and revert to built-in logic.
        Hot-swaps immediately if a controller window is open.
        """
        self._plc_state[wid]["path_var"].set("")
        self._plc_state[wid]["module"] = None
        self._plc_state[wid]["fn"]     = None

        status_lbl = self._plc_state[wid].get("status_lbl")
        if status_lbl:
            status_lbl.config(text="Default", fg=C["muted"])

        # Hot-swap: pass None so WaysideFrame reverts to compute_wayside_outputs
        if self._controller_frame is not None:
            self._controller_frame.set_compute_fn(wid, None)

    def _load_plc_module(self, path):
        """
        Import a PLC .py file as a Python module.
        Returns the module on success, None on failure.
        Shows error dialogs for import errors and missing function.
        """
        try:
            spec   = importlib.util.spec_from_file_location("plc_module", path)
            module = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(module)
        except Exception as e:
            messagebox.showerror(
                "Import Error",
                f"Could not load the PLC file:\n{e}"
            )
            return None

        if not hasattr(module, "compute_wayside_outputs"):
            messagebox.showerror(
                "Missing Function",
                "The PLC file does not define:\n\n"
                "  compute_wayside_outputs(\n"
                "      block_state, block_lengths,\n"
                "      switches_def, crossings_list,\n"
                "      signal_blocks=None\n"
                "  )\n\nPlease add this function and try again."
            )
            return None

        return module

    # =========================================================================
    # PLC SYNTAX HELP POPUP
    # =========================================================================

    def _show_plc_help(self):
        """Open a scrollable modal popup with the full 6-wayside PLC guide."""
        popup = tk.Toplevel(self)
        popup.title("PLC Programming Guide")
        popup.configure(bg="#1e1e1e")
        popup.resizable(True, True)
        popup.geometry("820x640")

        # ── Title bar ────────────────────────────────────────────────────────
        tk.Label(popup, text="PLC Programming Guide  —  6-Wayside Architecture",
                 bg="#007acc", fg="white",
                 font=("Helvetica", 11, "bold"),
                 anchor="w", padx=16, pady=8).pack(fill="x")

        # ── Scrollable text area ──────────────────────────────────────────────
        frame = tk.Frame(popup, bg="#1e1e1e")
        frame.pack(fill="both", expand=True)

        sb = tk.Scrollbar(frame)
        sb.pack(side="right", fill="y")

        content = tk.Text(frame, bg="#1e1e1e", fg="#cccccc",
                          font=("Courier", 9), relief="flat",
                          padx=18, pady=12, wrap="none",
                          width=96, height=36,
                          yscrollcommand=sb.set,
                          state="normal", cursor="arrow")
        content.pack(side="left", fill="both", expand=True)
        sb.config(command=content.yview)

        # ── Colour tags ───────────────────────────────────────────────────────
        content.tag_configure("h1",     font=("Courier", 10, "bold"), foreground="#ffffff")
        content.tag_configure("h2",     font=("Courier", 9,  "bold"), foreground="#ffffff")
        content.tag_configure("white",  foreground="#cccccc")
        content.tag_configure("blue",   foreground="#9cdcfe")
        content.tag_configure("green",  foreground="#4ec994")
        content.tag_configure("grey",   foreground="#6a9955")
        content.tag_configure("yellow", foreground="#dcdcaa")
        content.tag_configure("orange", foreground="#ce9178")
        content.tag_configure("red",    foreground="#f48771")
        content.tag_configure("purple", foreground="#c586c0")
        content.tag_configure("sep",    foreground="#444444")
        content.tag_configure("tbl",    foreground="#aaaaaa")

        def ins(text, tag="white"):
            content.insert("end", text, tag)

        def sep(char="─", n=88):
            ins(char * n + "\n", "sep")

        def h1(text):
            ins("\n" + text + "\n", "h1")
            sep("═")

        def h2(text):
            ins("\n" + text + "\n", "h2")
            sep()

        # =====================================================================
        # 1. OVERVIEW
        # =====================================================================
        h1("1.  OVERVIEW")
        ins(
            "A PLC (Programmable Logic Controller) file is a Python (.py) script that\n"
            "replaces the built-in wayside logic for one specific wayside section.\n\n"
            "The system has 6 independent waysides.  Each wayside can independently\n"
            "run either the built-in default logic or your custom PLC file.\n\n"
            "Your PLC file is called once per wayside per 100 ms refresh tick in live\n"
            "mode, or once per input change in testing mode.\n"
        )

        # =====================================================================
        # 2. WAYSIDE BLOCK RANGES
        # =====================================================================
        h1("2.  WAYSIDE BLOCK RANGES")
        ins(
            "Each wayside is responsible for a contiguous range of blocks on one line.\n"
            "Your PLC only receives data for blocks in its assigned range.\n\n"
        )
        ins("  Wayside  Line    Blocks       Switches              Crossings\n", "tbl")
        sep("─", 70)
        rows = [
            ("  WG1 ", "Green", "  1 –  75 ", "SW12, SW28, SW57, SW62", "Block 19"),
            ("  WG2 ", "Green", " 76 – 150 ", "SW76, SW85",             "Block 108"),
            ("  WR1 ", "Red  ", "  1 –  38 ", "SW9, SW15, SW27, SW32, SW38", "Block 11"),
            ("  WR2 ", "Red  ", " 39 –  76 ", "SW43, SW52",             "Block 47"),

        ]
        for wid, line, blks, switches, crossings in rows:
            ins(f"  {wid}", "yellow")
            ins(f"   {line}  {blks}   {switches:<26} {crossings}\n", "tbl")
        ins("\n")

        # =====================================================================
        # 3. FILE REQUIREMENTS
        # =====================================================================
        h1("3.  FILE REQUIREMENTS")
        ins(
            "  - File extension must be  "); ins(".py\n", "yellow")
        ins(
            "  - File name must have     "); ins("no spaces\n", "red")
        ins(
            "  - Must define the function "); ins("compute_wayside_outputs", "yellow")
        ins("  (exact name)\n"
            "  - One file per wayside  —  upload separately in PLC Manager\n"
            "  - You may reuse the same file for multiple waysides if the logic is shared\n"
        )

        # =====================================================================
        # 4. FUNCTION SIGNATURE
        # =====================================================================
        h1("4.  FUNCTION SIGNATURE")
        ins("\ndef ", "purple")
        ins("compute_wayside_outputs", "yellow")
        ins("(\n")
        ins("        block_state",    "blue");   ins(",      # dict  — see section 5\n", "grey")
        ins("        block_lengths",  "blue");   ins(",   # dict  — see section 5\n", "grey")
        ins("        switches_def",   "blue");   ins(",   # dict  — see section 5\n", "grey")
        ins("        crossings_list", "blue");   ins(",# list  — see section 5\n", "grey")
        ins("        signal_blocks",  "blue");   ins(" = "); ins("None", "orange")
        ins(",  # set   — see section 6\n", "grey")
        ins("):\n")
        ins("    ...\n")
        ins("    return ", "purple"); ins("{ ... }"); ins("  # see section 7\n\n", "grey")

        # =====================================================================
        # 5. INPUT PARAMETERS
        # =====================================================================
        h1("5.  INPUT PARAMETERS")

        h2("block_state  —  dict[int, dict]")
        ins(
            "  Maps each block number in this wayside's range to its current sensor data.\n\n"
        )
        ins("  block_state = {\n")
        ins("      27", "orange"); ins(": {\n")
        ins("          'occupied'",  "blue"); ins(":  "); ins("True",  "orange"); ins(",   # bool  — from Track Model\n", "grey")
        ins("          'cmd_speed'", "blue"); ins(": "); ins("55.0",  "orange"); ins(",   # float — commanded speed in "); ins("km/h", "red"); ins(" (NOT mph)\n", "grey")
        ins("          'authority'", "blue"); ins(": "); ins("1.2",   "orange"); ins(",   # float — authority in "); ins("km", "red"); ins(" (NOT miles)\n", "grey")
        ins("      },\n")
        ins("      28", "orange"); ins(": { 'occupied': "); ins("False", "orange")
        ins(", 'cmd_speed': "); ins("0.0", "orange"); ins(", 'authority': "); ins("0.0", "orange"); ins(" },\n")
        ins("      ...\n  }\n\n")
        ins("  "); ins("IMPORTANT:", "red")
        ins("  Units are always metric — km/h and km.\n"
            "  The UI displays mph/miles but all logic runs in metric.\n")

        h2("block_lengths  —  dict[int, float]")
        ins(
            "  Maps each block number to its length in metres.\n"
            "  Use this for distance calculations (e.g. authority reach).\n\n"
        )
        ins("  block_lengths = { 27: 50.0, 28: 50.0, 29: 60.0, ... }\n")

        h2("switches_def  —  dict[str, dict]")
        ins(
            "  Defines each switch in this wayside.  Only switches whose host block\n"
            "  falls in this wayside's range are included.\n\n"
        )
        ins("  switches_def = {\n")
        ins("      'SW27'", "orange"); ins(": {\n")
        ins("          'host'",        "blue"); ins(":    "); ins("27", "orange"); ins(",\n")
        ins("          'normal'",      "blue"); ins(":  ("); ins("28", "orange"); ins(", "); ins("'27->28'", "green"); ins("),  # (next_block, label)\n", "grey")
        ins("          'reverse'",     "blue"); ins(": ("); ins("76", "orange"); ins(", "); ins("'27->76'", "green"); ins("),\n")
        ins("          'description'", "blue"); ins(": "); ins("'Blocks 27->28 / 76'", "green"); ins(",\n")
        ins("      },\n      ...\n  }\n")

        h2("crossings_list  —  list[int]")
        ins(
            "  Block numbers of railway crossings in this wayside's range.\n"
            "  May be empty if this wayside has no crossings.\n\n"
        )
        ins("  crossings_list = ["); ins("11", "orange"); ins("]   # or  [] if none\n")

        # =====================================================================
        # 6. SIGNAL BLOCKS
        # =====================================================================
        h1("6.  SIGNAL BLOCKS  (signal_blocks parameter)")
        ins(
            "  signal_blocks is a pre-computed set of block numbers that have\n"
            "  physical signal lights installed in this wayside's section.\n\n"
            "  Blocks ARE in signal_blocks:   return 'green', 'yellow', or 'red'\n"
            "  Blocks NOT in signal_blocks:   return None  (no signal hardware)\n\n"
            "  Signal blocks are automatically calculated as:\n"
            "    - The host block of every switch\n"
            "    - Both branch blocks of every switch\n"
            "    - One block before and after every station\n\n"
        )
        ins("  Example check:\n\n")
        ins("  for blk in block_lengths:\n")
        ins("      if ")
        ins("signal_blocks", "blue"); ins(" is not None and blk not in "); ins("signal_blocks", "blue"); ins(":\n")
        ins("          signals[blk] = "); ins("None", "orange"); ins("   # no hardware here\n", "grey")
        ins("          continue\n")
        ins("      # ... compute signal colour for this block\n", "grey")

        # =====================================================================
        # 7. RETURN VALUE
        # =====================================================================
        h1("7.  RETURN VALUE  —  dict with 4 required keys")

        h2("'switches'  —  dict[str, str]")
        ins(
            "  One entry per switch in switches_def.\n"
            "  Value must be exactly 'normal' or 'reverse'.\n\n"
        )
        ins("  'switches': { 'SW27': "); ins("'normal'", "green")
        ins(", 'SW32': "); ins("'reverse'", "yellow"); ins(", ... }\n")

        h2("'signals'  —  dict[int, str | None]")
        ins(
            "  One entry per block in block_lengths.\n"
            "  Value must be 'green', 'yellow', 'red', or None.\n"
            "  Return None for any block not in signal_blocks.\n\n"
        )
        ins("  'signals': {\n")
        ins("      26", "orange"); ins(": "); ins("'green'",  "green");  ins(",  # clear\n", "grey")
        ins("      27", "orange"); ins(": "); ins("'yellow'", "yellow"); ins(", # caution\n", "grey")
        ins("      28", "orange"); ins(": "); ins("'red'",    "red");    ins(",   # stop\n",  "grey")
        ins("      29", "orange"); ins(": "); ins("None",     "orange"); ins(",    # no signal hardware\n", "grey")
        ins("      ...\n  }\n")

        h2("'crossings'  —  dict[int, str]")
        ins(
            "  One entry per block in crossings_list.\n"
            "  Value must be exactly 'active' or 'inactive'.\n\n"
        )
        ins("  'crossings': { "); ins("11", "orange"); ins(": "); ins("'active'", "orange")
        ins(" }   # or 'inactive'\n")

        h2("'reach'  —  dict[int, set[int]]")
        ins(
            "  Optional.  Maps each occupied block to the set of blocks within its\n"
            "  authority reach.  Used only for the blue highlight in the UI.\n"
            "  Return an empty dict if you don't want to compute reach.\n\n"
        )
        ins("  'reach': { "); ins("27", "orange"); ins(": {"); ins("28", "orange")
        ins(", "); ins("29", "orange"); ins(", "); ins("30", "orange"); ins("} }   # or  {}\n")

        # =====================================================================
        # 8. COMPLETE EXAMPLE
        # =====================================================================
        h1("8.  COMPLETE MINIMAL EXAMPLE")
        ins("\n")
        ins("# myplc_wr1.py  —  minimal PLC for wayside WR1 (Red blocks 1-38)\n", "grey")
        ins("\ndef ", "purple"); ins("compute_wayside_outputs", "yellow")
        ins("(block_state, block_lengths, switches_def,\n"
            "                         crossings_list, signal_blocks=None):\n\n")
        ins("    # --- signals ------------------------------------------------\n", "grey")
        ins("    signals = {}\n")
        ins("    occupied = {b for b, s in block_state.items() if s["); ins("'occupied'", "green"); ins("]}\n")
        ins("    for blk in block_lengths:\n")
        ins("        if signal_blocks is not None and blk not in signal_blocks:\n")
        ins("            signals[blk] = "); ins("None", "orange"); ins("; continue\n")
        ins("        n1, n2 = blk + 1, blk + 2\n")
        ins("        if   n1 in occupied: signals[blk] = "); ins("'red'\n",    "red")
        ins("        elif n2 in occupied: signals[blk] = "); ins("'yellow'\n", "yellow")
        ins("        else:                signals[blk] = "); ins("'green'\n",  "green")

        ins("\n    # --- switches -----------------------------------------------\n", "grey")
        ins("    switches = {sw_id: "); ins("'normal'", "green")
        ins(" for sw_id in switches_def}\n")

        ins("\n    # --- crossings ----------------------------------------------\n", "grey")
        ins("    crossings = {cx: "); ins("'active'", "orange")
        ins(" if cx in occupied else "); ins("'inactive'", "blue")
        ins("\n                 for cx in crossings_list}\n")

        ins("\n    return {\n")
        ins("        "); ins("'switches'",  "blue"); ins(":  switches,\n")
        ins("        "); ins("'signals'",   "blue"); ins(":   signals,\n")
        ins("        "); ins("'crossings'", "blue"); ins(": crossings,\n")
        ins("        "); ins("'reach'",     "blue"); ins(":     {},\n")
        ins("    }\n")

        # =====================================================================
        # 9. COMMON MISTAKES
        # =====================================================================
        h1("9.  COMMON MISTAKES")
        mistakes = [
            ("red",    "Using mph or miles instead of km/h and km in logic."),
            ("red",    "Forgetting to return None for blocks not in signal_blocks."),
            ("red",    "Omitting a switch from the 'switches' return dict."),
            ("red",    "Omitting a block from the 'signals' return dict."),
            ("red",    "Filename contains spaces  (e.g. 'my plc.py' will be rejected)."),
            ("red",    "Wrong function name  (must be exactly compute_wayside_outputs)."),
            ("orange", "Using global block numbers instead of only this wayside's range."),
            ("orange", "Returning 'active' for a crossing block that is not in crossings_list."),
            ("orange", "Not handling the case where block_state[blk] is missing a key."),
        ]
        ins("\n")
        for color, text in mistakes:
            ins("  [!] ", color); ins(text + "\n", "white")

        ins("\n")
        sep("─")
        ins("  Upload your .py file in PLC Manager.  "
            "Each wayside gets its own upload slot.\n", "grey")
        ins("  Changes hot-swap into the running controller within one refresh tick.\n", "grey")

        content.config(state="disabled")

        # ── OK button ────────────────────────────────────────────────────────
        tk.Button(popup, text="Close Guide",
                  font=("Helvetica", 9, "bold"),
                  bg="#007acc", fg="white",
                  activebackground="#005f9e",
                  relief="flat", padx=16, pady=6,
                  cursor="hand2",
                  command=popup.destroy).pack(pady=10)

        # Centre over dashboard
        popup.update_idletasks()
        pw, ph = popup.winfo_reqwidth(), popup.winfo_reqheight()
        x = self.winfo_rootx() + (self.winfo_width()  - pw) // 2
        y = self.winfo_rooty() + (self.winfo_height() - ph) // 2
        popup.geometry(f"+{max(0,x)}+{max(0,y)}")
        popup.grab_set()


# =============================================================================

def main():
    app = WaysideDashboard()
    app.mainloop()


if __name__ == "__main__":
    main()

# =============================================================================
# SharedState integration – appended by merger
# =============================================================================

def _wd_poll_shared_state(self):
    """
    Called every 100 ms via tkinter after().

    CTC -> Wayside:
      - Block occupancy / speed / authority  -> WaysideFrame.receive_live_data()
      - Switch/signal overrides from CTC maintenance -> applied to WaysideFrame

    Wayside -> CTC:
      - Computed signals, switches, crossings -> SharedState.push_wayside_outputs()
      - Switch-change events (delta only)     -> SharedState.push_switch_event()
    """
    if self._shared is None:
        return

    from wayside_controller import C, SIG_COLOR, LINE_WAYSIDES

    # ── CTC block data -> Wayside ─────────────────────────────────────────────
    new_ctc = self._shared.poll_ctc_data()
    if new_ctc and self._controller_frame is not None:
        for line_name, block_data in new_ctc.items():
            # Must run even when block_data is {} — CTC uses an empty dict as a
            # full snapshot (no trains on that line); skipping falsy {} left stale
            # occupancies and never cleared the wayside panel.
            if not isinstance(block_data, dict):
                block_data = {}
            self._controller_frame.receive_live_data(line_name, block_data)

    # ── CTC maintenance state -> Wayside ─────────────────────────────────────
    # If CTC puts a line into maintenance, toggle the matching wayside line too
    new_maint = self._shared.poll_ctc_maintenance()
    if new_maint and self._controller_frame is not None:
        cf = self._controller_frame
        for line_name, active in new_maint.items():
            # Check whether the wayside line is already in the target state
            wid_list = LINE_WAYSIDES.get(line_name, [])
            if not wid_list:
                continue
            currently_on = cf.waysides[wid_list[0]].get("maintenance", False)
            if active != currently_on:
                # _toggle_maintenance flips the state; only call it when it differs
                cf._toggle_maintenance(line_name)

    # ── CTC maintenance overrides -> Wayside ──────────────────────────────────
    new_overrides = self._shared.poll_ctc_overrides()
    if new_overrides and self._controller_frame is not None:
        cf = self._controller_frame
        for line_name, ov in new_overrides.items():
            # Apply switch overrides: find the matching wayside and set the
            # override_var so the next _refresh() picks it up
            for sw_id, position in ov.get("switch_overrides", {}).items():
                for wid in LINE_WAYSIDES.get(line_name, []):
                    ws = cf.waysides.get(wid, {})
                    entry = ws.get("sw_labels", {}).get(sw_id)
                    if entry:
                        pos_lbl, route_lbl, override_var, override_btn = entry
                        override_var.set(position)
                        override_btn.config(
                            text="Set NORMAL" if position == "reverse" else "Set REVERSE"
                        )
            # Apply signal overrides
            for blk_str, color in ov.get("signal_overrides", {}).items():
                blk = int(blk_str) if not isinstance(blk_str, int) else blk_str
                for wid in LINE_WAYSIDES.get(line_name, []):
                    ws = cf.waysides.get(wid, {})
                    entry = ws.get("sig_labels", {}).get(blk)
                    if entry:
                        dot, cell, num_lbl, override_var, cycle_btn, spd_lbl = entry
                        override_var.set(color)
                        cycle_btn.config(
                            text=color[:1].upper(),
                            fg=SIG_COLOR.get(color, C["muted"])
                        )
        cf._refresh()

    # ── Wayside outputs -> CTC ────────────────────────────────────────────────
    if self._controller_frame is not None:
        cf = self._controller_frame
        inv_sig = {v: k for k, v in SIG_COLOR.items()}

        outputs_by_line = {}
        prev_switches = getattr(self, "_prev_switch_states", {})
        new_prev = {}

        for wid, ws in cf.waysides.items():
            line = ws.get("line", "")
            if line not in outputs_by_line:
                outputs_by_line[line] = {"signals": {}, "switches": {}, "crossings": {}}

            # Signals
            for blk, entry in ws.get("sig_labels", {}).items():
                dot, cell, num_lbl, override_var, cycle_btn, spd_lbl = entry
                if ws.get("maintenance"):
                    sig = override_var.get()
                else:
                    sig = inv_sig.get(dot.cget("fg"))
                outputs_by_line[line]["signals"][blk] = sig

            # Switches — detect changes and queue events
            for sw_id, entry in ws.get("sw_labels", {}).items():
                pos_lbl, route_lbl, override_var, _ = entry
                pos = (override_var.get() if ws.get("maintenance")
                       else pos_lbl.cget("text").lower())
                outputs_by_line[line]["switches"][sw_id] = pos

                key = (line, sw_id)
                new_prev[key] = pos
                old_pos = prev_switches.get(key)
                if old_pos is not None and old_pos != pos:
                    self._shared.push_switch_event(line, sw_id, old_pos, pos)

            # Crossings
            for cx, lbl in ws.get("cx_labels", {}).items():
                state = "active" if lbl.cget("text") == "ACTIVE" else "inactive"
                outputs_by_line[line]["crossings"][cx] = state

        # Save switch state snapshot for next cycle's delta detection
        self._prev_switch_states = {**prev_switches, **new_prev}

        for line_name, outputs in outputs_by_line.items():
            self._shared.push_wayside_outputs(line_name, outputs)

    # Reschedule
    self.after(100, self._poll_shared_state)


# Monkey-patch onto WaysideDashboard
WaysideDashboard._poll_shared_state = _wd_poll_shared_state


def main(shared_state=None):
    """
    Launch the Wayside Dashboard.

    Parameters
    ----------
    shared_state : SharedState | None
        Pass the SharedState instance when running alongside the CTC.
        Pass None (default) to run the dashboard standalone.
    """
    app = WaysideDashboard(shared_state=shared_state)
    app.mainloop()
