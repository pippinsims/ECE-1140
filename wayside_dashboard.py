import tkinter as tk
from tkinter import ttk, filedialog, messagebox
import os
import importlib.util

from wayside_controller import launch_as_toplevel

try:
    from PIL import Image, ImageTk
    PIL_AVAILABLE = True
except ImportError:
    PIL_AVAILABLE = False

# ── Colour palette (mirrors wayside controller) ───────────────────────────────
C = {
    "bg":      "#1a1a2e",
    "panel":   "#16213e",
    "card":    "#0f3460",
    "header":  "#0d2137",
    "accent":  "#e94560",
    "green":   "#00d26a",
    "red":     "#ff4757",
    "blue":    "#4fc3f7",
    "yellow":  "#ffd700",
    "orange":  "#ff6b35",
    "white":   "#e0e0e0",
    "muted":   "#8899aa",
    "divider": "#1e2d45",
}


class WaysideDashboard(tk.Tk):
    """Wayside Control System Dashboard"""

    def __init__(self):
        super().__init__()
        self.title("Wayside Control System")
        self.geometry("1100x720")
        self.configure(bg=C["bg"])
        self.resizable(True, True)

        self.green_line_blocks = self.initialize_green_line_blocks()
        self.red_line_blocks   = self.initialize_red_line_blocks()
        self.setup_variables()
        self.setup_ui()

    # ── Block data ─────────────────────────────────────────────────────────────

    def initialize_green_line_blocks(self):
        blocks   = {}
        stations = {2:"PIONEER",9:"EDGEBROOK",16:"STATION",22:"STATION",
                    31:"SOUTH BANK",48:"STATION",57:"YARD",65:"STATION",
                    73:"STATION",77:"YARD JUNCTION",105:"STATION",114:"STATION"}
        junctions = [1,12,28,29,57,58,62,63,77,85,86,100,101]
        crossings = [19]
        for i in range(1, 151):
            is_st = i in stations
            is_jn = i in junctions
            is_cx = i in crossings
            blocks[i] = {
                'type':           "Station" if is_st else ("Junction" if is_jn else ("Crossing" if is_cx else "Regular")),
                'station_name':   stations.get(i, "N/A"),
                'has_switch':     is_jn,
                'has_light':      is_jn,
                'has_crossing':   is_cx,
                'occupancy':      'Unoccupied',
                'track_fault':    'No Fault',
                'switch_position':'Position A' if is_jn else 'N/A',
                'light_color':    'Green'      if is_jn else 'N/A',
                'crossing_status':'Inactive'   if is_cx else 'N/A',
                'speed_limit':    45,
                'authority':      5.0,
            }
        return blocks

    def initialize_red_line_blocks(self):
        blocks   = {}
        stations = {7:"SHADYSIDE",16:"HERRON AVE",21:"SWISSVILLE",
                    25:"PENN STATION",35:"STEEL PLAZA",45:"FIRST AVE",
                    48:"STATION SQUARE"}
        junctions = [1,9,15,27,28,32,33,38,39,43,44,52,53,66,67,72,76]
        crossings = [11,45,47]
        for i in range(1, 77):
            is_st = i in stations
            is_jn = i in junctions
            is_cx = i in crossings
            blocks[i] = {
                'type':           "Station" if is_st else ("Junction" if is_jn else ("Crossing" if is_cx else "Regular")),
                'station_name':   stations.get(i, "N/A"),
                'has_switch':     is_jn,
                'has_light':      is_jn,
                'has_crossing':   is_cx,
                'occupancy':      'Unoccupied',
                'track_fault':    'No Fault',
                'switch_position':'Position A' if is_jn else 'N/A',
                'light_color':    'Green'      if is_jn else 'N/A',
                'crossing_status':'Inactive'   if is_cx else 'N/A',
                'speed_limit':    40,
                'authority':      4.5,
            }
        return blocks

    # ── Variables ──────────────────────────────────────────────────────────────

    def setup_variables(self):
        self.light_color      = tk.StringVar(value="Green")
        self.switch_position  = tk.StringVar(value="Position A")
        self.crossing_status  = tk.StringVar(value="Inactive")
        self.plc_file_path      = tk.StringVar(value="")
        self.plc_test_file_path = tk.StringVar(value="")
        self.selected_line    = tk.StringVar(value="Select Line")
        self.selected_block   = tk.StringVar(value="Select Block")

    # ── UI ─────────────────────────────────────────────────────────────────────

    def setup_ui(self):
        self._style_ttk()
        self.create_header()
        self.create_footer()   # footer packed before map so it anchors to bottom
        self.create_map_area()

    def _style_ttk(self):
        style = ttk.Style()
        style.theme_use("clam")
        style.configure("TCombobox",
                        fieldbackground=C["card"],
                        background=C["card"],
                        foreground=C["white"],
                        arrowcolor=C["muted"],
                        bordercolor=C["divider"],
                        lightcolor=C["card"],
                        darkcolor=C["card"])
        style.map("TCombobox", fieldbackground=[("readonly", C["card"])])

    # ── Header ─────────────────────────────────────────────────────────────────

    def create_header(self):
        hdr = tk.Frame(self, bg=C["header"])
        hdr.pack(fill="x", side="top")

        # Left accent bar
        tk.Frame(hdr, bg=C["accent"], width=5).pack(side="left", fill="y")

        # Title block
        title_block = tk.Frame(hdr, bg=C["header"], padx=20, pady=14)
        title_block.pack(side="left")
        tk.Label(title_block, text="WAYSIDE CONTROL SYSTEM",
                 font=("Helvetica", 18, "bold"),
                 bg=C["header"], fg=C["white"]).pack(anchor="w")
        tk.Label(title_block, text="Green Line  \u00b7  Red Line  \u00b7  Blue Line",
                 font=("Helvetica", 9),
                 bg=C["header"], fg=C["muted"]).pack(anchor="w")

        # Right side status dots
        status_block = tk.Frame(hdr, bg=C["header"], padx=20)
        status_block.pack(side="right", pady=14)
        for label, color in [("Green Line", C["green"]),
                              ("Red Line",   C["red"]),
                              ("Blue Line",  C["blue"])]:
            row = tk.Frame(status_block, bg=C["header"])
            row.pack(anchor="e", pady=1)
            tk.Label(row, text="\u25cf", fg=color, bg=C["header"],
                     font=("Helvetica", 10)).pack(side="left")
            tk.Label(row, text=f"  {label}", fg=C["muted"], bg=C["header"],
                     font=("Helvetica", 8)).pack(side="left")

        # Accent underline
        tk.Frame(self, bg=C["accent"], height=2).pack(fill="x", side="top")

    # ── Map area ───────────────────────────────────────────────────────────────

    def create_map_area(self):
        outer = tk.Frame(self, bg=C["bg"])
        outer.pack(fill="both", expand=True, padx=12, pady=10)

        script_dir = os.path.dirname(os.path.abspath(__file__))

        # Red & Green card
        rg_card = self._map_card(outer, "RED & GREEN LINE", C["green"])
        rg_card.pack(side="left", fill="both", expand=True, padx=(0, 6))
        rg_path = os.path.join(script_dir, "Picture1.png")
        if PIL_AVAILABLE and os.path.exists(rg_path):
            self._load_map_image(rg_card, rg_path, key="rg")
        else:
            self._map_fallback(rg_card, "Picture1.png")

        # Blue card
        blue_card = self._map_card(outer, "BLUE LINE", C["blue"])
        blue_card.pack(side="left", fill="both", expand=True, padx=(6, 0))
        blue_path = os.path.join(script_dir, "blue.png")
        if PIL_AVAILABLE and os.path.exists(blue_path):
            self._load_map_image(blue_card, blue_path, key="blue")
        else:
            self._map_fallback(blue_card, "blue.png")

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
        msg = f"{filename} not found." if PIL_AVAILABLE else "Install Pillow:  pip install pillow"
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
            w = c.winfo_width()
            h = c.winfo_height()
            if w < 2 or h < 2:
                return
            img_w, img_h = self._map_store[k]["pil"].size
            scale  = min(w / img_w, h / img_h)
            new_w  = max(1, int(img_w * scale))
            new_h  = max(1, int(img_h * scale))
            resized = self._map_store[k]["pil"].resize((new_w, new_h), Image.LANCZOS)
            self._map_store[k]["tk"] = ImageTk.PhotoImage(resized)
            c.delete("all")
            c.create_image(w // 2, h // 2, anchor="center",
                           image=self._map_store[k]["tk"])

        canvas.bind("<Configure>", _redraw)
        canvas.after(50, _redraw)

    # ── Footer ─────────────────────────────────────────────────────────────────

    def create_footer(self):
        """Two-column footer: Live Mode (left) | Testing Mode (right)."""
        tk.Frame(self, bg=C["divider"], height=2).pack(fill="x", side="bottom")

        footer = tk.Frame(self, bg=C["header"])
        footer.pack(fill="x", side="bottom")

        inner = tk.Frame(footer, bg=C["header"])
        inner.pack(fill="x", padx=16, pady=12)

        # ── LEFT COLUMN: LIVE MODE ─────────────────────────────────────
        live_col = tk.Frame(inner, bg=C["header"])
        live_col.pack(side="left", fill="x", expand=True)

        tk.Label(live_col, text="LIVE MODE",
                 font=("Helvetica", 7, "bold"),
                 bg=C["header"], fg=C["yellow"]).pack(anchor="w")

        live_row1 = tk.Frame(live_col, bg=C["header"])
        live_row1.pack(anchor="w", pady=(4, 0))

        # Open Controller button
        self.default_btn = tk.Button(
            live_row1, text="Open Controller",
            font=("Helvetica", 9, "bold"),
            bg=C["accent"], fg=C["white"],
            activebackground="#c73652",
            relief="flat", padx=12, pady=5,
            cursor="hand2",
            command=self.use_default_settings,
        )
        self.default_btn.pack(side="left")
        self.default_status_label = tk.Label(
            live_row1, text="  ✔  Active",
            bg=C["header"], fg=C["green"],
            font=("Helvetica", 9, "italic"),
        )

        # PLC Live row
        live_row2 = tk.Frame(live_col, bg=C["header"])
        live_row2.pack(anchor="w", pady=(6, 0))

        tk.Label(live_row2, text="PLC:",
                 font=("Helvetica", 8),
                 bg=C["header"], fg=C["muted"]).pack(side="left", padx=(0, 4))

        self.plc_live_entry = tk.Entry(
            live_row2, textvariable=self.plc_file_path,
            width=26, state="readonly",
            bg=C["card"], fg=C["white"],
            readonlybackground=C["card"],
            relief="flat", font=("Helvetica", 8),
        )
        self.plc_live_entry.pack(side="left", ipady=3, padx=(0, 4))

        self.browse_btn = tk.Button(
            live_row2, text="Browse…",
            font=("Helvetica", 8),
            bg=C["card"], fg=C["white"],
            activebackground=C["panel"],
            relief="flat", padx=8, pady=3,
            cursor="hand2", command=self.browse_file,
        )
        self.browse_btn.pack(side="left", padx=(0, 4))

        self.upload_btn = tk.Button(
            live_row2, text="Upload & Run",
            font=("Helvetica", 8, "bold"),
            bg=C["blue"], fg="#000000",
            activebackground="#39a8d4",
            relief="flat", padx=10, pady=3,
            cursor="hand2", command=self.upload_file,
        )
        self.upload_btn.pack(side="left", padx=(0, 6))

        self.plc_status_label = tk.Label(
            live_row2, text="✔  PLC Active",
            bg=C["header"], fg=C["green"],
            font=("Helvetica", 8, "italic"),
        )

        # Browse error for live PLC
        self.browse_error_label = tk.Label(
            live_col, text="",
            bg=C["header"], fg="#ff6b6b",
            font=("Helvetica", 8, "italic"),
        )
        self.browse_error_label.pack(anchor="w", pady=(2, 0))

        # PLC help link
        help_lbl = tk.Label(
            live_col, text="❓ How does PLC work?",
            bg=C["header"], fg=C["blue"],
            font=("Helvetica", 8, "underline"),
            cursor="hand2",
        )
        help_lbl.pack(anchor="w")
        help_lbl.bind("<Button-1>", lambda e: self._show_plc_help())

        # ── VERTICAL DIVIDER ───────────────────────────────────────────
        tk.Frame(inner, bg=C["divider"], width=2).pack(
            side="left", fill="y", padx=20)

        # ── RIGHT COLUMN: TESTING MODE ─────────────────────────────────
        test_col = tk.Frame(inner, bg=C["header"])
        test_col.pack(side="left", fill="x", expand=True)

        tk.Label(test_col, text="TESTING MODE",
                 font=("Helvetica", 7, "bold"),
                 bg=C["header"], fg=C["green"]).pack(anchor="w")

        test_row1 = tk.Frame(test_col, bg=C["header"])
        test_row1.pack(anchor="w", pady=(4, 0))

        # Open Testing window button
        self.testing_btn = tk.Button(
            test_row1, text="Open Testing",
            font=("Helvetica", 9, "bold"),
            bg=C["green"], fg="#000000",
            activebackground="#00a854",
            relief="flat", padx=12, pady=5,
            cursor="hand2",
            command=self.use_testing_mode,
        )
        self.testing_btn.pack(side="left")
        self.testing_status_label = tk.Label(
            test_row1, text="  ✔  Active",
            bg=C["header"], fg=C["green"],
            font=("Helvetica", 9, "italic"),
        )

        # PLC Testing row
        test_row2 = tk.Frame(test_col, bg=C["header"])
        test_row2.pack(anchor="w", pady=(6, 0))

        tk.Label(test_row2, text="PLC:",
                 font=("Helvetica", 8),
                 bg=C["header"], fg=C["muted"]).pack(side="left", padx=(0, 4))

        self.plc_test_entry = tk.Entry(
            test_row2, textvariable=self.plc_test_file_path,
            width=26, state="readonly",
            bg=C["card"], fg=C["white"],
            readonlybackground=C["card"],
            relief="flat", font=("Helvetica", 8),
        )
        self.plc_test_entry.pack(side="left", ipady=3, padx=(0, 4))

        self.browse_test_btn = tk.Button(
            test_row2, text="Browse…",
            font=("Helvetica", 8),
            bg=C["card"], fg=C["white"],
            activebackground=C["panel"],
            relief="flat", padx=8, pady=3,
            cursor="hand2", command=self.browse_test_file,
        )
        self.browse_test_btn.pack(side="left", padx=(0, 4))

        self.upload_test_btn = tk.Button(
            test_row2, text="Test PLC",
            font=("Helvetica", 8, "bold"),
            bg=C["orange"], fg="#000000",
            activebackground="#cc5500",
            relief="flat", padx=10, pady=3,
            cursor="hand2", command=self.upload_test_file,
        )
        self.upload_test_btn.pack(side="left", padx=(0, 6))

        self.plc_test_status_label = tk.Label(
            test_row2, text="✔  PLC Testing Active",
            bg=C["header"], fg=C["green"],
            font=("Helvetica", 8, "italic"),
        )

        self.browse_test_error_label = tk.Label(
            test_col, text="",
            bg=C["header"], fg="#ff6b6b",
            font=("Helvetica", 8, "italic"),
        )
        self.browse_test_error_label.pack(anchor="w", pady=(2, 0))

        # Tooltips for all 6 buttons
        _tip = "Unavailable: a controller window is currently open."
        for btn in (self.default_btn, self.browse_btn, self.upload_btn,
                    self.testing_btn, self.browse_test_btn, self.upload_test_btn):
            self._attach_tooltip(btn, _tip)

    # ── Event handlers  ─────────────────────────────────────────────────────────

    def on_line_selected(self, event=None):
        pass

    def on_block_selected(self, event=None):
        pass

    def display_block_controls(self, block_info):
        pass

    def update_info_display(self, block_info):
        pass

    def apply_switch_change(self):
        pass

    def apply_light_change(self):
        pass

    def apply_crossing_change(self):
        pass

    def browse_file(self):
        """Browse for live PLC file."""
        filename = filedialog.askopenfilename(
            title="Select PLC File (Live)",
            filetypes=[("Python files", "*.py"), ("All files", "*.*")]
        )
        if not filename:
            return
        basename = os.path.basename(filename)
        if not basename.lower().endswith(".py"):
            self.plc_file_path.set("")
            self.browse_error_label.config(text="✗  Only .py files are accepted.")
            return
        if " " in basename:
            self.plc_file_path.set("")
            self.browse_error_label.config(text="✗  File name cannot contain spaces.")
            return
        self.plc_file_path.set(filename)
        self.browse_error_label.config(text="")

    def browse_test_file(self):
        """Browse for testing PLC file."""
        filename = filedialog.askopenfilename(
            title="Select PLC File (Testing)",
            filetypes=[("Python files", "*.py"), ("All files", "*.*")]
        )
        if not filename:
            return
        basename = os.path.basename(filename)
        if not basename.lower().endswith(".py"):
            self.plc_test_file_path.set("")
            self.browse_test_error_label.config(text="✗  Only .py files are accepted.")
            return
        if " " in basename:
            self.plc_test_file_path.set("")
            self.browse_test_error_label.config(text="✗  File name cannot contain spaces.")
            return
        self.plc_test_file_path.set(filename)
        self.browse_test_error_label.config(text="")

    def _load_plc_module(self, path):
        """Import a PLC .py file and return the module, or None on failure."""
        try:
            spec   = importlib.util.spec_from_file_location("plc_module", path)
            module = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(module)
        except Exception as e:
            messagebox.showerror("Import Error", f"Could not load the PLC file:\n{e}")
            return None
        if not hasattr(module, "compute_wayside_outputs"):
            messagebox.showerror("Missing Function",
                "The PLC file does not define a function named:\n"
                "  compute_wayside_outputs(block_state, block_lengths, "
                "switches_def, crossings_list)\n\n"
                "Please add this function and try again.")
            return None
        return module

    def upload_file(self):
        """Validate live PLC file and open a live controller window with it."""
        path = self.plc_file_path.get()
        if not path:
            messagebox.showwarning("Warning", "No file selected. Use Browse to pick a .py file.")
            return
        module = self._load_plc_module(path)
        if module is None:
            return
        basename = os.path.basename(path)
        win = launch_as_toplevel(
            self,
            compute_fn=module.compute_wayside_outputs,
            title=f"Wayside Controller – PLC Live: {basename}",
            mode="live",
        )
        self._lock_all(status_widget=self.plc_status_label)
        win.protocol("WM_DELETE_WINDOW", lambda: self._unlock_all(self.plc_status_label, win))

    def upload_test_file(self):
        """Validate testing PLC file and open a testing controller window with it."""
        path = self.plc_test_file_path.get()
        if not path:
            messagebox.showwarning("Warning", "No file selected. Use Browse to pick a .py file.")
            return
        module = self._load_plc_module(path)
        if module is None:
            return
        basename = os.path.basename(path)
        win = launch_as_toplevel(
            self,
            compute_fn=module.compute_wayside_outputs,
            title=f"Wayside Controller – PLC Testing: {basename}",
            mode="testing",
        )
        self._lock_all(status_widget=self.plc_test_status_label)
        win.protocol("WM_DELETE_WINDOW", lambda: self._unlock_all(self.plc_test_status_label, win))

    def use_default_settings(self):
        """Open a live (default logic) controller window."""
        win = launch_as_toplevel(self, mode="live",
                                 title="Wayside Controller – Live")
        self._lock_all(status_widget=self.default_status_label)
        win.protocol("WM_DELETE_WINDOW",
                     lambda: self._unlock_all(self.default_status_label, win))

    def use_testing_mode(self):
        """Open a testing (default logic) controller window."""
        win = launch_as_toplevel(self, mode="testing",
                                 title="Wayside Controller – Testing")
        self._lock_all(status_widget=self.testing_status_label)
        win.protocol("WM_DELETE_WINDOW",
                     lambda: self._unlock_all(self.testing_status_label, win))

    # ── Unified lock / unlock ──────────────────────────────────────────────────

    ALL_BTNS = ("default_btn", "testing_btn",
                "browse_btn", "upload_btn",
                "browse_test_btn", "upload_test_btn")

    def _attach_tooltip(self, widget, text):
        """Show a tooltip on hover only when the widget is disabled."""
        tip_win = []
        def on_enter(event):
            if widget["state"] == "disabled":
                x = widget.winfo_rootx() + 20
                y = widget.winfo_rooty() + widget.winfo_height() + 4
                tw = tk.Toplevel(self)
                tw.wm_overrideredirect(True)
                tw.wm_geometry(f"+{x}+{y}")
                tk.Label(
                    tw, text=text, bg="#1e1e1e", fg="#e0e0e0",
                    font=("Helvetica", 8), relief="solid", borderwidth=1,
                    padx=8, pady=4).pack()
                tip_win.append(tw)
        def on_leave(event):
            for tw in tip_win: tw.destroy()
            tip_win.clear()
        widget.bind("<Enter>", on_enter)
        widget.bind("<Leave>", on_leave)

    def _lock_all(self, status_widget=None):
        """Disable every launch button and show the active status label."""
        for attr in self.ALL_BTNS:
            btn = getattr(self, attr)
            btn.config(state="disabled", bg="#2a2a2a", fg="#666666")
        if status_widget:
            status_widget.pack(side="left", padx=(8, 0))

    def _unlock_all(self, status_widget, win):
        """Re-enable all buttons and hide the status label."""
        win.destroy()
        self.default_btn.config(state="normal",  bg=C["accent"],  fg=C["white"])
        self.testing_btn.config(state="normal",  bg=C["green"],   fg="#000000")
        self.browse_btn.config(state="normal",   bg=C["card"],    fg=C["white"])
        self.upload_btn.config(state="normal",   bg=C["blue"],    fg="#000000")
        self.browse_test_btn.config(state="normal", bg=C["card"], fg=C["white"])
        self.upload_test_btn.config(state="normal", bg=C["orange"], fg="#000000")
        if status_widget:
            status_widget.pack_forget()

    # Keep old method names as aliases so nothing breaks
    def _on_wayside_closed(self, win):
        win.destroy()

    def _set_default_mode(self, active):
        pass

    def _set_plc_mode(self, active):
        pass

    def _on_plc_closed(self, win):
        win.destroy()

def main():
    app = WaysideDashboard()
    app.mainloop()

if __name__ == "__main__":
    main()
