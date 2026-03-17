import tkinter as tk
from tkinter import ttk, filedialog, messagebox
import os
import importlib.util

# Import the wayside controller launcher — both files must be in the same folder
from wayside_controller import launch_as_toplevel

# PIL for image loading (pip install pillow if missing)
try:
    from PIL import Image, ImageTk
    PIL_AVAILABLE = True
except ImportError:
    PIL_AVAILABLE = False


class WaysideDashboard(tk.Tk):
    """Wayside Control System Dashboard"""
    
    def __init__(self):
        super().__init__()
        
        # Window configuration
        self.title("Wayside Control System")
        self.geometry("900x700")
        self.configure(bg="white")
        
        # Initialize block information
        self.green_line_blocks = self.initialize_green_line_blocks()
        self.red_line_blocks = self.initialize_red_line_blocks()
        
        # Initialize variables
        self.setup_variables()
        
        # Create UI components
        self.setup_ui()
        
    def initialize_green_line_blocks(self):
        """Initialize Green Line block information"""
        blocks = {}
        
        # Stations
        stations = {
            2: "PIONEER", 9: "EDGEBROOK", 16: "STATION", 22: "STATION",
            31: "SOUTH BANK", 48: "STATION", 57: "YARD", 65: "STATION",
            73: "STATION", 77: "YARD JUNCTION", 105: "STATION", 114: "STATION"
        }
        
        # Junctions
        junctions = [1, 12, 28, 29, 57, 58, 62, 63, 77, 85, 86, 100, 101]
        
        # Crossings
        crossings = [19]
        
        # Initialize all blocks (1-150)
        for i in range(1, 151):
            block_type = "Regular"
            station_name = "N/A"
            has_switch = False
            has_light = False
            has_crossing = False
            
            if i in stations:
                block_type = "Station"
                station_name = stations[i]
            elif i in junctions:
                block_type = "Junction"
                has_switch = True
                has_light = True
            elif i in crossings:
                block_type = "Crossing"
                has_crossing = True
            
            blocks[i] = {
                'type': block_type,
                'station_name': station_name,
                'has_switch': has_switch,
                'has_light': has_light,
                'has_crossing': has_crossing,
                'occupancy': 'Unoccupied',
                'track_fault': 'No Fault',
                'switch_position': 'Position A' if has_switch else 'N/A',
                'light_color': 'Green' if has_light else 'N/A',
                'crossing_status': 'Inactive' if has_crossing else 'N/A',
                'speed_limit': 45,
                'authority': 5.0
            }
        
        return blocks
    
    def initialize_red_line_blocks(self):
        """Initialize Red Line block information"""
        blocks = {}
        
        # Stations
        stations = {
            7: "SHADYSIDE", 16: "HERRON AVE", 21: "SWISSVILLE",
            25: "PENN STATION", 35: "STEEL PLAZA", 45: "FIRST AVE",
            48: "STATION SQUARE"
        }
        
        # Junctions
        junctions = [1, 9, 15, 27, 28, 32, 33, 38, 39, 43, 44, 52, 53, 66, 67, 72, 76]
        
        # Crossings
        crossings = [11, 45, 47]
        
        # Initialize all blocks (1-76)
        for i in range(1, 77):
            block_type = "Regular"
            station_name = "N/A"
            has_switch = False
            has_light = False
            has_crossing = False
            
            if i in stations:
                block_type = "Station"
                station_name = stations[i]
            elif i in junctions:
                block_type = "Junction"
                has_switch = True
                has_light = True
            elif i in crossings:
                block_type = "Crossing"
                has_crossing = True
            
            blocks[i] = {
                'type': block_type,
                'station_name': station_name,
                'has_switch': has_switch,
                'has_light': has_light,
                'has_crossing': has_crossing,
                'occupancy': 'Unoccupied',
                'track_fault': 'No Fault',
                'switch_position': 'Position A' if has_switch else 'N/A',
                'light_color': 'Green' if has_light else 'N/A',
                'crossing_status': 'Inactive' if has_crossing else 'N/A',
                'speed_limit': 40,
                'authority': 4.5
            }
        
        return blocks
        
    def setup_variables(self):
        """Initialize application variables"""
        self.light_color = tk.StringVar(value="Green")
        self.switch_position = tk.StringVar(value="Position A")
        self.crossing_status = tk.StringVar(value="Inactive")
        self.plc_file_path = tk.StringVar(value="")
        self.selected_line = tk.StringVar(value="Select Line")
        self.selected_block = tk.StringVar(value="Select Block")
        
    def setup_ui(self):
        """Create and arrange all UI components"""
        # Header with logo and title
        self.create_header()
        
        # Track visualization area
        self.create_track_area()
        
        # Bottom section with controls and info
        self.create_bottom_section()
        
    def create_header(self):
        """Create header with logo and title"""
        header_frame = tk.Frame(self, bg="#c0c0c0", relief=tk.RAISED, borderwidth=2)
        header_frame.pack(fill=tk.X, padx=10, pady=10)
        
        # Logo placeholder
        logo_label = tk.Label(header_frame, text="Logo", bg="#808080", fg="white", 
                            font=("Arial", 12, "bold"), width=8, height=2, relief=tk.RAISED)
        logo_label.pack(side=tk.LEFT, padx=10, pady=10)
        
        # Title
        title_label = tk.Label(header_frame, text="Wayside Dashboard", 
                             font=("Helvetica", 24, "bold"), bg="#c0c0c0", fg="black")
        title_label.pack(side=tk.LEFT, padx=20, pady=10, expand=True)
        
    def create_track_area(self):
        """Display the Red/Green Line map and the Blue Line map side by side."""
        track_frame = tk.Frame(self, bg="white", relief=tk.SUNKEN, borderwidth=2)
        track_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=5)

        script_dir = os.path.dirname(os.path.abspath(__file__))

        # Left panel — Red & Green Line map
        left_panel = tk.Frame(track_frame, bg="white")
        left_panel.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=(4, 2), pady=4)
        tk.Label(left_panel, text="Red & Green Line",
                 bg="white", fg="#555555",
                 font=("Arial", 8, "bold")).pack(anchor="nw")

        rg_path = os.path.join(script_dir, "Picture1.png")
        if PIL_AVAILABLE and os.path.exists(rg_path):
            self._load_map_image(left_panel, rg_path, key="rg")
        else:
            msg = "Picture1.png not found." if PIL_AVAILABLE else "Install Pillow:  pip install pillow"
            tk.Label(left_panel, text=msg, bg="white", fg="gray",
                     font=("Arial", 9, "italic")).pack(expand=True)

        # Divider
        tk.Frame(track_frame, bg="#cccccc", width=2).pack(side=tk.LEFT, fill=tk.Y, pady=8)

        # Right panel — Blue Line map
        right_panel = tk.Frame(track_frame, bg="white")
        right_panel.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=(2, 4), pady=4)
        tk.Label(right_panel, text="Blue Line",
                 bg="white", fg="#555555",
                 font=("Arial", 8, "bold")).pack(anchor="nw")

        blue_path = os.path.join(script_dir, "blue.png")
        if PIL_AVAILABLE and os.path.exists(blue_path):
            self._load_map_image(right_panel, blue_path, key="blue")
        else:
            msg = "blue.png not found." if PIL_AVAILABLE else "Install Pillow:  pip install pillow"
            tk.Label(right_panel, text=msg, bg="white", fg="gray",
                     font=("Arial", 9, "italic")).pack(expand=True)

    def _load_map_image(self, parent, img_path, key="map"):
        """Load, scale to fit, and display a map image inside parent."""
        canvas = tk.Canvas(parent, bg="white", highlightthickness=0)
        canvas.pack(fill=tk.BOTH, expand=True)

        pil_img = Image.open(img_path)

        # Store per-key so multiple images don't overwrite each other's references
        if not hasattr(self, "_map_store"):
            self._map_store = {}
        self._map_store[key] = {"pil": pil_img, "tk": None}

        def _redraw(event=None, c=canvas, k=key):
            w = c.winfo_width()
            h = c.winfo_height()
            if w < 2 or h < 2:
                return
            img_w, img_h = self._map_store[k]["pil"].size
            scale = min(w / img_w, h / img_h)
            new_w = max(1, int(img_w * scale))
            new_h = max(1, int(img_h * scale))
            resized = self._map_store[k]["pil"].resize((new_w, new_h), Image.LANCZOS)
            self._map_store[k]["tk"] = ImageTk.PhotoImage(resized)
            c.delete("all")
            c.create_image(w // 2, h // 2, anchor="center",
                           image=self._map_store[k]["tk"])

        canvas.bind("<Configure>", _redraw)
        canvas.after(50, _redraw)
            
    def create_bottom_section(self):
        """Create bottom section with controls and information"""
        bottom_frame = tk.Frame(self, bg="white")
        bottom_frame.pack(fill=tk.BOTH, padx=10, pady=10)
        
        # Left side - Controls
        self.create_controls_panel(bottom_frame)
        
        # Right side - Information display
        self.create_info_panel(bottom_frame)
        
        # Bottom - PLC Upload section
        self.create_plc_upload_section(bottom_frame)
        
    def create_controls_panel(self, parent):
        """Create the left control panel"""
        controls_frame = tk.LabelFrame(parent, text="", bg="white", relief=tk.RAISED, 
                                      borderwidth=2, padx=15, pady=15)
        controls_frame.grid(row=0, column=0, sticky="nsew", padx=5, pady=5)
        
        # Separator
        ttk.Separator(controls_frame, orient=tk.HORIZONTAL).pack(fill=tk.X, pady=10)
        
        # Lights dropdown (initially shown)
        self.lights_frame = tk.Frame(controls_frame, bg="white")
        self.lights_frame.pack(anchor="w", pady=5)
        
        tk.Label(self.lights_frame, text="Lights:", bg="white", font=("Arial", 10)).pack(side=tk.LEFT, padx=5)
        
        self.light_menu = ttk.Combobox(self.lights_frame, textvariable=self.light_color, 
                                 values=["Green", "Yellow", "Red"], width=10, state="readonly")
        self.light_menu.pack(side=tk.LEFT, padx=5)
        
        tk.Button(self.lights_frame, text="Apply", width=8,
                 command=self.apply_light_change).pack(side=tk.LEFT, padx=5)
        
        # Switch lane (initially shown)
        self.switch_frame = tk.Frame(controls_frame, bg="white")
        self.switch_frame.pack(anchor="w", pady=5)
        
        tk.Label(self.switch_frame, text="Switch lane:", bg="white", font=("Arial", 10)).pack(side=tk.LEFT, padx=5)
        
        self.switch_dropdown = ttk.Combobox(self.switch_frame, textvariable=self.switch_position,
                                           values=["Position A", "Position B"],
                                           width=10, state="readonly")
        self.switch_dropdown.pack(side=tk.LEFT, padx=5)
        
        tk.Button(self.switch_frame, text="Apply", width=8,
                 command=self.apply_switch_change).pack(side=tk.LEFT, padx=5)
        
        # Crossing controls (initially hidden)
        self.crossing_frame = tk.Frame(controls_frame, bg="white")
        
        tk.Label(self.crossing_frame, text="Crossing:", bg="white", font=("Arial", 10)).pack(side=tk.LEFT, padx=5)
        
        self.crossing_dropdown = ttk.Combobox(self.crossing_frame, textvariable=self.crossing_status,
                                             values=["Active", "Inactive"],
                                             width=10, state="readonly")
        self.crossing_dropdown.pack(side=tk.LEFT, padx=5)
        
        tk.Button(self.crossing_frame, text="Apply", width=8,
                 command=self.apply_crossing_change).pack(side=tk.LEFT, padx=5)
        
        # Initially hide lights and switch controls
        self.lights_frame.pack_forget()
        self.switch_frame.pack_forget()
        
    def create_info_panel(self, parent):
        """Create the right information panel"""
        info_frame = tk.LabelFrame(parent, text="", bg="white", relief=tk.RAISED, 
                                  borderwidth=2, padx=15, pady=15)
        info_frame.grid(row=0, column=1, sticky="nsew", padx=5, pady=5)
        
        self.info_text = """Speed limit (mph) = [Value]
Authority (miles) = [Value]
Track occupancy (bool) = [Value]
Track positions = [Value]
Track states (bool) = [Value]
Crossing states (bool) = [Value]"""
        
        self.info_label = tk.Label(info_frame, text=self.info_text, bg="white", 
                            font=("Arial", 11), justify=tk.LEFT, anchor="w")
        self.info_label.pack(fill=tk.BOTH, expand=True)
        
    def create_plc_upload_section(self, parent):
        """Create PLC file upload section"""
        plc_frame = tk.Frame(parent, bg="white")
        plc_frame.grid(row=1, column=0, columnspan=2, sticky="ew", pady=15)
        
        # Left side - Default settings button
        left_frame = tk.Frame(plc_frame, bg="white")
        left_frame.pack(side=tk.LEFT, padx=20)
        
        tk.Label(left_frame, text="Use default settings", bg="white", 
                font=("Arial", 10)).pack(pady=5)
        
        self.default_btn = tk.Button(left_frame, text="Button", width=10, 
                              command=self.use_default_settings)
        self.default_btn.pack(pady=5)

        # Status label — shown when default settings window is open
        self.default_status_label = tk.Label(
            left_frame,
            text="✔  Default settings are\ncurrently being used",
            bg="white", fg="#2e7d32",
            font=("Arial", 9, "italic"),
            justify=tk.LEFT
        )
        # Not packed yet — shown only when window is open

        # Separator line
        separator = tk.Frame(plc_frame, bg="gray", width=2)
        separator.pack(side=tk.LEFT, fill=tk.Y, padx=20)
        
        # Right side - Upload PLC file
        right_frame = tk.Frame(plc_frame, bg="white")
        right_frame.pack(side=tk.LEFT, padx=20, expand=True)
        
        tk.Label(right_frame, text="Upload PLC file (Python)", bg="white", 
                font=("Arial", 11, "bold")).pack(pady=5)
        
        upload_frame = tk.Frame(right_frame, bg="white")
        upload_frame.pack(pady=5)
        
        file_entry = tk.Entry(upload_frame, textvariable=self.plc_file_path, 
                            width=30, state="readonly")
        file_entry.pack(side=tk.LEFT, padx=5)
        
        self.browse_btn = tk.Button(upload_frame, text="Browse...", width=10, 
                             command=self.browse_file)
        self.browse_btn.pack(side=tk.LEFT, padx=5)

        # Validation error label (shown when browse rejects a file)
        self.browse_error_label = tk.Label(right_frame, text="", bg="white",
                                           fg="#c0392b", font=("Arial", 9, "italic"))
        self.browse_error_label.pack(anchor="w", padx=5)

        # "How does PLC work?" hover-help label
        plc_help_label = tk.Label(right_frame, text="❓ How does PLC work?",
                                  bg="white", fg="#1a6fad",
                                  font=("Arial", 9, "underline"),
                                  cursor="hand2")
        plc_help_label.pack(anchor="w", padx=5, pady=(2, 0))
        plc_help_label.bind("<Button-1>", lambda e: self._show_plc_help())

        self.upload_btn = tk.Button(right_frame, text="Upload", width=10, 
                             command=self.upload_file)
        self.upload_btn.pack(pady=5)

        # Status label shown when PLC window is open
        self.plc_status_label = tk.Label(
            right_frame,
            text="✔  PLC file is currently active",
            bg="white", fg="#2e7d32",
            font=("Arial", 9, "italic"),
            justify=tk.LEFT
        )
        # Not packed yet

        # Attach tooltips (shown only when disabled)
        self._attach_tooltip(self.browse_btn,
            "Unavailable: a controller window is currently open.")
        self._attach_tooltip(self.upload_btn,
            "Unavailable: a controller window is currently open.")
        
        # Configure grid weights
        parent.columnconfigure(0, weight=1)
        parent.columnconfigure(1, weight=1)
    
    # ============ Event Handlers ============
    
    def on_line_selected(self, event=None):
        """Handle line selection"""
        line = self.selected_line.get()
        
        if line == "Green Line":
            blocks = [f"Block {i}" for i in range(1, 151)]
            self.block_dropdown['values'] = ["Select Block"] + blocks
            self.block_dropdown['state'] = "readonly"
        elif line == "Red Line":
            blocks = [f"Block {i}" for i in range(1, 77)]
            self.block_dropdown['values'] = ["Select Block"] + blocks
            self.block_dropdown['state'] = "readonly"
        else:
            self.block_dropdown['state'] = "disabled"
        
        self.selected_block.set("Select Block")
        self.lights_frame.pack_forget()
        self.switch_frame.pack_forget()
        self.crossing_frame.pack_forget()
        self.update_info_display(None)
    
    def on_block_selected(self, event=None):
        """Handle block selection"""
        line = self.selected_line.get()
        block_str = self.selected_block.get()
        
        if line == "Select Line" or block_str == "Select Block":
            return
        
        # Extract block number
        block_num = int(block_str.split()[1])
        
        # Get block info
        if line == "Green Line":
            block_info = self.green_line_blocks.get(block_num)
        else:
            block_info = self.red_line_blocks.get(block_num)
        
        if block_info:
            self.display_block_controls(block_info)
            self.update_info_display(block_info)
    
    def display_block_controls(self, block_info):
        """Show appropriate controls based on block type"""
        # Hide all control frames first
        self.lights_frame.pack_forget()
        self.switch_frame.pack_forget()
        self.crossing_frame.pack_forget()
        
        # Show appropriate controls
        if block_info['has_switch'] and block_info['has_light']:
            # Junction - show switch and light controls
            self.switch_position.set(block_info['switch_position'])
            self.light_color.set(block_info['light_color'])
            self.switch_frame.pack(anchor="w", pady=5)
            self.lights_frame.pack(anchor="w", pady=5)
        elif block_info['has_crossing']:
            # Crossing - show crossing controls
            self.crossing_status.set(block_info['crossing_status'])
            self.crossing_frame.pack(anchor="w", pady=5)
        # Regular blocks and stations show no controls
    
    def update_info_display(self, block_info):
        """Update the information display"""
        if block_info is None:
            info_text = """Speed limit (mph) = [Value]
Authority (miles) = [Value]
Track occupancy (bool) = [Value]
Track positions = [Value]
Track states (bool) = [Value]
Crossing states (bool) = [Value]"""
        else:
            info_text = f"""Speed limit (mph) = {block_info['speed_limit']}
Authority (miles) = {block_info['authority']}
Track occupancy (bool) = {block_info['occupancy']}
Track positions = {block_info['station_name']}
Track states (bool) = {block_info['track_fault']}
Crossing states (bool) = {block_info.get('crossing_status', 'N/A')}"""
        
        self.info_label.config(text=info_text)
    
    def apply_switch_change(self):
        """Apply switch position change"""
        line = self.selected_line.get()
        block_str = self.selected_block.get()
        
        if line == "Select Line" or block_str == "Select Block":
            messagebox.showwarning("Warning", "Please select a line and block first")
            return
        
        block_num = int(block_str.split()[1])
        new_position = self.switch_position.get()
        
        # Update block info
        if line == "Green Line":
            self.green_line_blocks[block_num]['switch_position'] = new_position
        else:
            self.red_line_blocks[block_num]['switch_position'] = new_position
        
        messagebox.showinfo("Success", 
                          f"Switch position updated to {new_position} for Block {block_num}")
    
    def apply_light_change(self):
        """Apply traffic light change"""
        line = self.selected_line.get()
        block_str = self.selected_block.get()
        
        if line == "Select Line" or block_str == "Select Block":
            messagebox.showwarning("Warning", "Please select a line and block first")
            return
        
        block_num = int(block_str.split()[1])
        new_color = self.light_color.get()
        
        # Update block info
        if line == "Green Line":
            self.green_line_blocks[block_num]['light_color'] = new_color
        else:
            self.red_line_blocks[block_num]['light_color'] = new_color
        
        messagebox.showinfo("Success", 
                          f"Traffic light changed to {new_color} for Block {block_num}")
    
    def apply_crossing_change(self):
        """Apply crossing status change"""
        line = self.selected_line.get()
        block_str = self.selected_block.get()
        
        if line == "Select Line" or block_str == "Select Block":
            messagebox.showwarning("Warning", "Please select a line and block first")
            return
        
        block_num = int(block_str.split()[1])
        new_status = self.crossing_status.get()
        
        # Update block info
        if line == "Green Line":
            self.green_line_blocks[block_num]['crossing_status'] = new_status
        else:
            self.red_line_blocks[block_num]['crossing_status'] = new_status
        
        messagebox.showinfo("Success", 
                          f"Crossing status updated to {new_status} for Block {block_num}")
        
    def browse_file(self):
        """Open file browser — validate .py and no spaces in filename."""
        filename = filedialog.askopenfilename(
            title="Select PLC File",
            filetypes=[("Python files", "*.py"), ("All files", "*.*")]
        )
        if not filename:
            return

        basename = os.path.basename(filename)

        # Validate extension
        if not basename.lower().endswith(".py"):
            self.plc_file_path.set("")
            self.browse_error_label.config(
                text="✗  Only .py files are accepted."
            )
            return

        # Validate no spaces in filename
        if " " in basename:
            self.plc_file_path.set("")
            self.browse_error_label.config(
                text="✗  File name cannot contain spaces."
            )
            return

        # File is valid
        self.plc_file_path.set(filename)
        self.browse_error_label.config(text="")
            
    def upload_file(self):
        """Validate PLC file, import it, and open a wayside window using its logic."""
        path = self.plc_file_path.get()
        if not path:
            messagebox.showwarning("Warning", "No file selected. Use Browse to pick a .py file.")
            return

        # Dynamically import the PLC file
        try:
            spec   = importlib.util.spec_from_file_location("plc_module", path)
            module = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(module)
        except Exception as e:
            messagebox.showerror("Import Error",
                f"Could not load the PLC file:\n{e}")
            return

        # Check it defines compute_wayside_outputs
        if not hasattr(module, "compute_wayside_outputs"):
            messagebox.showerror("Missing Function",
                "The PLC file does not define a function named:\n"
                "  compute_wayside_outputs(block_state, block_lengths, "
                "switches_def, crossings_list)\n\n"
                "Please add this function and try again.")
            return

        # All good — open the wayside window with the PLC's compute function
        basename = os.path.basename(path)
        plc_win = launch_as_toplevel(
            self,
            compute_fn=module.compute_wayside_outputs,
            title=f"Wayside Controller – PLC: {basename}"
        )
        self._set_plc_mode(active=True)
        plc_win.protocol("WM_DELETE_WINDOW",
                         lambda: self._on_plc_closed(plc_win))
            
    def use_default_settings(self):
        """Open the Wayside Controller UI in a new window and lock PLC upload."""
        wayside_win = launch_as_toplevel(self)
        self._set_default_mode(active=True)
        wayside_win.protocol("WM_DELETE_WINDOW", lambda: self._on_wayside_closed(wayside_win))

    def _on_wayside_closed(self, win):
        """Called when the Wayside Controller window is closed."""
        win.destroy()
        self._set_default_mode(active=False)

    def _set_default_mode(self, active: bool):
        """Enable or disable default-settings-active state."""
        if active:
            self.default_btn.config(state="disabled", bg="#d0d0d0", fg="#888888")
            self.browse_btn.config(state="disabled", bg="#d0d0d0", fg="#888888")
            self.upload_btn.config(state="disabled", bg="#d0d0d0", fg="#888888")
            self.default_status_label.pack(pady=(0, 4))
        else:
            self.default_btn.config(state="normal", bg="SystemButtonFace", fg="black")
            self.browse_btn.config(state="normal", bg="SystemButtonFace", fg="black")
            self.upload_btn.config(state="normal", bg="SystemButtonFace", fg="black")
            self.default_status_label.pack_forget()

    def _set_plc_mode(self, active: bool):
        """Enable or disable PLC-active state (mirrors _set_default_mode for the PLC side)."""
        if active:
            self.default_btn.config(state="disabled", bg="#d0d0d0", fg="#888888")
            self.browse_btn.config(state="disabled", bg="#d0d0d0", fg="#888888")
            self.upload_btn.config(state="disabled", bg="#d0d0d0", fg="#888888")
            self.plc_status_label.pack(pady=(0, 4))
        else:
            self.default_btn.config(state="normal", bg="SystemButtonFace", fg="black")
            self.browse_btn.config(state="normal", bg="SystemButtonFace", fg="black")
            self.upload_btn.config(state="normal", bg="SystemButtonFace", fg="black")
            self.plc_status_label.pack_forget()

    def _on_plc_closed(self, win):
        """Called when the PLC Wayside Controller window is closed."""
        win.destroy()
        self._set_plc_mode(active=False)

    def _show_plc_help(self):
        popup = tk.Toplevel(self)
        popup.title("How does PLC work?")
        popup.configure(bg="#1e1e1e")
        popup.resizable(False, False)

        tk.Label(popup,
                 text="PLC File — Required Syntax",
                 bg="#007acc", fg="white",
                 font=("Helvetica", 11, "bold"),
                 anchor="w", padx=16, pady=8
                 ).pack(fill="x")

        content = tk.Text(popup,
                          bg="#1e1e1e", fg="#cccccc",
                          font=("Courier", 9),
                          relief="flat",
                          padx=16, pady=12,
                          wrap="none",
                          width=72, height=26,
                          state="normal",
                          cursor="arrow")
        content.pack(fill="both", expand=True)

        content.tag_configure("white",  foreground="#cccccc")
        content.tag_configure("blue",   foreground="#9cdcfe")
        content.tag_configure("green",  foreground="#4ec994")
        content.tag_configure("grey",   foreground="#6a9955")
        content.tag_configure("yellow", foreground="#dcdcaa")
        content.tag_configure("sep",    foreground="#555555")
        content.tag_configure("bold",   font=("Courier", 9, "bold"), foreground="#ffffff")

        def ins(text, tag="white"):
            content.insert("end", text, tag)

        ins("Your PLC file must be a .py file with no spaces in the name.\n")
        ins("It must define exactly this function:\n\n")
        ins("─" * 62 + "\n", "sep")
        ins("\ndef ", "white")
        ins("compute_wayside_outputs", "yellow")
        ins("(\n", "white")
        ins("        block_state,      ", "blue")
        ins("# dict: {block_num: {occupied, cmd_speed, authority}}\n", "grey")
        ins("        block_lengths,    ", "blue")
        ins("# dict: {block_num: length_in_metres}\n", "grey")
        ins("        switches_def,     ", "blue")
        ins("# dict: switch definitions for the line\n", "grey")
        ins("        crossings_list    ", "blue")
        ins("# list: block numbers that have crossings\n", "grey")
        ins("):\n", "white")
        ins("    ", "white")
        ins("# Your custom wayside logic here\n", "grey")
        ins("    return {\n", "white")
        ins("        'switches'", "blue")
        ins(":  {sw_id: ", "white")
        ins("'normal'", "green")
        ins(" or ", "white")
        ins("'reverse'", "green")
        ins("},\n", "white")
        ins("        'signals'", "blue")
        ins(":   {block_num: ", "white")
        ins("'green'", "green")
        ins(", ", "white")
        ins("'yellow'", "yellow")
        ins(", or ", "white")
        ins("'red'", "blue")
        ins("},\n", "white")
        ins("        'crossings'", "blue")
        ins(": {block_num: ", "white")
        ins("'active'", "green")
        ins(" or ", "white")
        ins("'inactive'", "blue")
        ins("},\n", "white")
        ins("        'reach'", "blue")
        ins(":     {},   ", "white")
        ins("# can be empty dict\n", "grey")
        ins("    }\n", "white")
        ins("\n" + "─" * 62 + "\n", "sep")
        ins("\nNotes:\n", "bold")
        ins("  • The function is called on every refresh for each line.\n", "grey")
        ins("  • Empty 'reach' dict disables the authority blue highlight.\n", "grey")
        ins("  • Upload is rejected if this function is missing.\n", "grey")

        content.config(state="disabled")

        tk.Button(popup, text="OK", width=12,
                  bg="#007acc", fg="white",
                  font=("Helvetica", 9, "bold"),
                  relief="flat", padx=6, pady=5,
                  cursor="hand2",
                  activebackground="#005f9e",
                  command=popup.destroy).pack(pady=10)

        popup.update_idletasks()
        pw = popup.winfo_reqwidth()
        ph = popup.winfo_reqheight()
        x = self.winfo_rootx() + (self.winfo_width()  - pw) // 2
        y = self.winfo_rooty() + (self.winfo_height() - ph) // 2
        popup.geometry(f"+{max(0,x)}+{max(0,y)}")
        popup.grab_set()

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
                tk.Label(tw, text=text, bg="#ffffe0", fg="black",
                         font=("Arial", 9), relief="solid", borderwidth=1,
                         padx=6, pady=4, justify=tk.LEFT).pack()
                tip_win.append(tw)

        def on_leave(event):
            for tw in tip_win:
                tw.destroy()
            tip_win.clear()

        widget.bind("<Enter>", on_enter)
        widget.bind("<Leave>", on_leave)


def main():
    """Entry point for the application"""
    app = WaysideDashboard()
    app.mainloop()

if __name__ == "__main__":
    main()
