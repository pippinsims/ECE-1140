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
    _plc_state : {wayside_id: {"path": str, "fn": callable|None,
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
        print("[wayside-dashboard] _open_live() called")
        compute_fns = self._build_compute_fns()
        try:
            win = launch_as_toplevel(
                self,
                compute_fns=compute_fns,
                title="Wayside Controller - Live",
                mode="live",
            )
            # Keep a reference to the WaysideFrame for hot-swap calls
            self._controller_frame = win.winfo_children()[0]
            print(f"[wayside-dashboard] _open_live() SUCCESS — controller_frame set, type={type(self._controller_frame).__name__}")
        except Exception as e:
            import traceback
            print(f"[wayside-dashboard] _open_live() FAILED: {type(e).__name__}: {e}")
            traceback.print_exc()
            return
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
        Validates extension (.plc) and filename (no spaces).
        """
        filename = filedialog.askopenfilename(
            title=f"Select PLC File for {wid}",
            filetypes=[("PLC rule files", "*.plc"), ("All files", "*.*")]
        )
        if not filename:
            return

        basename = os.path.basename(filename)

        if not basename.lower().endswith(".plc"):
            self._plc_state[wid]["path_var"].set("")
            err_lbl.config(text="Only .plc files are accepted.")
            return

        if " " in basename:
            self._plc_state[wid]["path_var"].set("")
            err_lbl.config(text="File name cannot contain spaces.")
            return

        self._plc_state[wid]["path_var"].set(filename)
        err_lbl.config(text="")

    def _upload_plc(self, wid, err_lbl):
        """
        Load the .plc rule file for the given wayside and hot-swap if the
        controller window is currently open.
        The new function takes effect on the very next _refresh() tick.
        """
        path = self._plc_state[wid]["path_var"].get()
        if not path:
            err_lbl.config(text="No file selected. Use Browse first.")
            return

        fn = self._load_plc_file(path)
        if fn is None:
            return   # error dialog already shown by _load_plc_file

        self._plc_state[wid]["fn"] = fn

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
        self._plc_state[wid]["fn"]     = None

        status_lbl = self._plc_state[wid].get("status_lbl")
        if status_lbl:
            status_lbl.config(text="Default", fg=C["muted"])

        # Hot-swap: pass None so WaysideFrame reverts to compute_wayside_outputs
        if self._controller_frame is not None:
            self._controller_frame.set_compute_fn(wid, None)

    def _load_plc_file(self, path):
        """
        Read a .plc rule file, parse it, and return a compute function.
        Returns the compute function on success, None on failure.
        Shows error dialogs for read or parse errors.
        """
        try:
            with open(path, "r", encoding="utf-8") as fh:
                text = fh.read()
        except Exception as e:
            messagebox.showerror(
                "File Read Error",
                f"Could not read the PLC file:\n{e}"
            )
            return None

        try:
            from wayside_controller import parse_plc_rules, make_plc_compute_fn
            rules = parse_plc_rules(text)
        except ValueError as e:
            messagebox.showerror(
                "PLC Syntax Error",
                f"The PLC file has a syntax error:\n\n{e}\n\n"
                "Click the 'How does PLC work?' link for the rule format."
            )
            return None
        except Exception as e:
            messagebox.showerror(
                "PLC Load Error",
                f"Unexpected error loading the PLC file:\n{e}"
            )
            return None

        if not rules:
            messagebox.showerror(
                "Empty PLC File",
                "The PLC file contains no rules.\n\n"
                "Add at least one rule like:\n"
                "  sig[77] = red IF occ[78]"
            )
            return None

        return make_plc_compute_fn(rules)

    # =========================================================================
    # PLC SYNTAX HELP POPUP
    # =========================================================================

    def _show_plc_help(self):
        """Open a scrollable modal popup with the PLC rule format guide."""
        popup = tk.Toplevel(self)
        popup.title("PLC Programming Guide")
        popup.configure(bg="#1e1e1e")
        popup.resizable(True, True)
        popup.geometry("820x640")

        # Title bar
        tk.Label(popup, text="PLC Programming Guide  -  Rule File Format",
                 bg="#007acc", fg="white",
                 font=("Helvetica", 11, "bold"),
                 anchor="w", padx=16, pady=8).pack(fill="x")

        # Scrollable text area
        frame = tk.Frame(popup, bg="#1e1e1e")
        frame.pack(fill="both", expand=True)

        sb = tk.Scrollbar(frame)
        sb.pack(side="right", fill="y")

        content = tk.Text(frame, bg="#1e1e1e", fg="#cccccc",
                          font=("Courier", 9), relief="flat",
                          padx=18, pady=12, wrap="word",
                          width=96, height=36,
                          yscrollcommand=sb.set,
                          state="normal", cursor="arrow")
        content.pack(side="left", fill="both", expand=True)
        sb.config(command=content.yview)

        content.tag_configure("h1",     font=("Courier", 10, "bold"), foreground="#ffffff")
        content.tag_configure("h2",     font=("Courier", 9,  "bold"), foreground="#ffffff")
        content.tag_configure("white",  foreground="#cccccc")
        content.tag_configure("blue",   foreground="#9cdcfe")
        content.tag_configure("green",  foreground="#4ec994")
        content.tag_configure("grey",   foreground="#6a9955")
        content.tag_configure("yellow", foreground="#dcdcaa")
        content.tag_configure("orange", foreground="#ce9178")
        content.tag_configure("red",    foreground="#f48771")
        content.tag_configure("sep",    foreground="#444444")

        def ins(text, tag="white"):
            content.insert("end", text, tag)

        def sep(char="-", n=88):
            ins(char * n + "\n", "sep")

        def h1(text):
            ins("\n" + text + "\n", "h1")
            sep("=")

        def h2(text):
            ins("\n" + text + "\n", "h2")
            sep()

        h1("1.  OVERVIEW")
        ins(
            "A PLC file is a plain-text rule file (.plc) that lets you override\n"
            "individual signal aspects with custom logic.  The wayside computes\n"
            "all signals normally, then your rules override specific signals\n"
            "based on conditions you write.\n\n"
            "Each wayside (WG1, WG2, WR1, WR2) can independently load its own\n"
            "PLC file, or run on the built-in default logic.  Hot-swap is\n"
            "supported -- new rules take effect on the next 100 ms refresh tick.\n"
        )

        h1("2.  RULE FILE FORMAT")
        ins(
            "Each non-blank, non-comment line is one rule:\n\n"
        )
        ins("    sig[", "white")
        ins("N", "blue")
        ins("] = ", "white")
        ins("COLOR", "yellow")
        ins(" IF ", "white")
        ins("CONDITION", "green")
        ins("\n\n")
        ins(
            "Where:\n"
            "  N         = block number  (must be inside this wayside's range)\n"
            "  COLOR     = green | yellow | red\n"
            "  CONDITION = a Boolean expression using occ[N], reach[N],\n"
            "              AND, OR, NOT, and parentheses\n\n"
            "Comments start with # and are ignored.  Blank lines are ignored.\n"
        )

        h1("3.  AVAILABLE PRIMITIVES")
        ins("  occ[N]\n", "blue")
        ins("    True if block N is currently occupied by a train.\n\n")
        ins("  reach[N]\n", "blue")
        ins(
            "    True if block N is within any train's authority reach\n"
            "    (i.e. some train has been granted authority to traverse it).\n\n"
        )
        ins("  AND, OR, NOT\n", "yellow")
        ins(
            "    Boolean combinators.  Case-insensitive.  Use parentheses\n"
            "    to control precedence:\n"
            "        (occ[10] OR occ[11]) AND NOT occ[15]\n"
        )

        h1("4.  EXAMPLES")
        h2("Hold block 77 red while N section is occupied")
        ins("    sig[77] = red IF occ[78] OR occ[79] OR occ[80]\n", "green")

        h2("Yellow approach to an occupied block")
        ins("    sig[15] = yellow IF occ[17]\n", "green")
        ins("    sig[15] = red    IF occ[16]\n", "green")
        ins(
            "\n"
            "Note: rules are evaluated TOP-TO-BOTTOM, last match wins.  Place\n"
            "the most restrictive rule LAST so it overrides any earlier rule.\n"
        )

        h2("Use authority reach to extend yellow further")
        ins("    sig[40] = yellow IF reach[45] AND NOT occ[42]\n", "green")
        ins("    sig[40] = red    IF occ[42]\n", "green")

        h2("Comment lines and blank lines")
        ins("    # Hold block 28 red whenever a train is approaching from F\n", "grey")
        ins("    sig[28] = red IF occ[20] OR occ[21]\n", "green")
        ins("\n")
        ins("    # The line above is more restrictive than default, applied last.\n", "grey")

        h1("5.  HOW RULES INTERACT WITH DEFAULT LOGIC")
        ins(
            "The wayside ALWAYS runs the built-in compute first.  This sets a\n"
            "default colour for every signal block.  Your PLC rules then run\n"
            "in order; each matching rule overrides the signal it names.\n\n"
            "Blocks NOT mentioned in any rule keep their default colour.\n"
            "If multiple rules name the same block, the LAST matching rule wins.\n\n"
            "Switches, crossings, and reach are NOT affected by PLC rules --\n"
            "they are always computed by the built-in logic.\n"
        )

        h1("6.  COMMON ERRORS")
        ins("Unknown identifier in condition\n", "red")
        ins(
            "  Only occ[N], reach[N], AND, OR, NOT, parentheses, and the\n"
            "  literals True / False are accepted.  Anything else is rejected\n"
            "  with a line number for easy location.\n\n"
        )
        ins("Unrecognised rule format\n", "red")
        ins(
            "  Each rule MUST follow:\n"
            "      sig[N] = COLOR IF CONDITION\n"
            "  Missing IF, missing brackets, or wrong COLOR will all error.\n\n"
        )
        ins("Empty PLC file\n", "red")
        ins(
            "  A .plc file must contain at least one rule.  An empty file\n"
            "  is rejected so you do not accidentally disable the wayside.\n"
        )

        h1("7.  COMPLETE EXAMPLE FILE")
        sep()
        ins("# wg2_simple.plc -- holds N section red during reverse traffic\n\n", "grey")
        ins("# Block 77 stays red whenever any N-section block is occupied\n", "grey")
        ins("sig[77] = red IF occ[78] OR occ[79] OR occ[80] OR occ[81]\n", "green")
        ins("sig[77] = red IF occ[82] OR occ[83] OR occ[84] OR occ[85]\n", "green")
        ins("\n")
        ins("# Block 76 also turns red as an approach warning\n", "grey")
        ins("sig[76] = red IF reach[77]\n", "green")
        ins("\n")
        ins("# Yellow approach signal at block 75 when 76 is the next stop\n", "grey")
        ins("sig[75] = yellow IF occ[76]\n", "green")
        sep()

        # Lock content (read-only) but keep colour visible
        content.config(state="disabled")

        # OK button
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

    # ── DIAGNOSTIC ────────────────────────────────────────────────────────────
    if not hasattr(self, "_diag_tick_count"):
        self._diag_tick_count = 0
    self._diag_tick_count += 1
    if self._diag_tick_count % 50 == 1:   # print every 5 seconds (50 * 100ms)
        cf_status = "SET" if self._controller_frame is not None else "NONE"
        print(f"[wayside-poll] tick #{self._diag_tick_count} controller_frame={cf_status}")
        if self._controller_frame is not None:
            try:
                wsids = list(self._controller_frame.waysides.keys())
                print(f"[wayside-poll]   waysides loaded: {wsids}")
            except Exception as e:
                print(f"[wayside-poll]   waysides access ERROR: {e}")
    # ──────────────────────────────────────────────────────────────────────────

    from wayside_controller import C, SIG_COLOR, LINE_WAYSIDES

    # ── CTC block data + Track Model occupancy -> Wayside ────────────────────
    # CTC provides cmd_speed and authority but always sets occupied=False
    # (it doesn't track real occupancy). The Track Model pushes the
    # authoritative occupancy. Merge them before passing to the wayside.
    new_ctc = self._shared.poll_ctc_data()
    new_track = self._shared.poll_track_occupancy()

    # Cache the latest of each so we always have something to merge
    if new_track is not None:
        self._last_track_occ = new_track
    if new_ctc is not None:
        self._last_ctc_data = new_ctc

    last_track = getattr(self, "_last_track_occ", {"Green": {}, "Red": {}})
    last_ctc   = getattr(self, "_last_ctc_data",  {"Green": {}, "Red": {}})

    if (new_ctc or new_track) and self._controller_frame is not None:
        for line_name in ("Green", "Red"):
            ctc_blocks   = last_ctc.get(line_name, {}) or {}
            track_blocks = last_track.get(line_name, {}) or {}

            # Merge: union of all block keys, occupancy from track, cmd/auth from CTC
            all_blocks = set(ctc_blocks.keys()) | set(track_blocks.keys())
            merged: dict = {}
            for bn in all_blocks:
                ctc_entry = ctc_blocks.get(bn, {}) if isinstance(ctc_blocks.get(bn), dict) else {}
                merged[bn] = {
                    "occupied":  bool(track_blocks.get(bn, False)),
                    "cmd_speed": float(ctc_entry.get("cmd_speed", 0.0)),
                    "authority": float(ctc_entry.get("authority", 0.0)),
                }
            self._controller_frame.receive_live_data(line_name, merged)

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
                        override_var = entry[3]
                        cycle_btn    = entry[4]
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
                dot          = entry[0]
                override_var = entry[3]
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
