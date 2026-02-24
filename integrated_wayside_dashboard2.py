import tkinter as tk
from tkinter import ttk, filedialog, messagebox

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
                'maintenance': 'Inactive',
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
                'maintenance': 'Inactive',
                'switch_position': 'Position A' if has_switch else 'N/A',
                'light_color': 'Green' if has_light else 'N/A',
                'crossing_status': 'Inactive' if has_crossing else 'N/A',
                'speed_limit': 40,
                'authority': 4.5
            }
        
        return blocks
        
    def setup_variables(self):
        """Initialize application variables"""
        self.maintenance_mode = tk.BooleanVar(value=False)
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
        """Create the track visualization area"""
        track_frame = tk.Frame(self, bg="white", relief=tk.SUNKEN, borderwidth=2)
        track_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=5)
        
        # Green line (top track)
        green_canvas = tk.Canvas(track_frame, bg="white", height=80, highlightthickness=1, 
                                highlightbackground="green")
        green_canvas.pack(fill=tk.X, padx=5, pady=5)
        self.draw_track_line(green_canvas, "green")
        
        # Red line (bottom track)
        red_canvas = tk.Canvas(track_frame, bg="white", height=80, highlightthickness=1, 
                              highlightbackground="red")
        red_canvas.pack(fill=tk.X, padx=5, pady=5)
        self.draw_track_line(red_canvas, "red")
        
    def draw_track_line(self, canvas, color):
        """Draw a track line with stations and switches"""
        canvas.update_idletasks()
        width = canvas.winfo_width() if canvas.winfo_width() > 1 else 800
        height = canvas.winfo_height() if canvas.winfo_height() > 1 else 80
        
        y_main = height // 2
        
        # Draw main horizontal line
        canvas.create_line(20, y_main, width - 20, y_main, fill=color, width=2, arrow=tk.LAST)
        
        # Draw stations (small circles along the line)
        num_stations = 12
        for i in range(num_stations):
            x = 20 + (width - 40) * i / (num_stations - 1)
            canvas.create_oval(x-4, y_main-4, x+4, y_main+4, fill=color, outline=color)
            
        # Draw a switch/junction area (example)
        switch_x = width // 2
        if color == "green":
            # Upper junction
            canvas.create_line(switch_x, y_main, switch_x, y_main - 25, fill=color, width=2)
            canvas.create_line(switch_x, y_main - 25, switch_x + 80, y_main - 25, 
                             fill=color, width=2, arrow=tk.LAST)
            canvas.create_rectangle(switch_x - 15, y_main - 10, switch_x + 15, y_main + 10, 
                                  fill="lightblue", outline=color, width=2)
        else:
            # Lower junction
            canvas.create_line(switch_x - 100, y_main, switch_x - 100, y_main + 25, 
                             fill=color, width=2)
            canvas.create_line(switch_x - 100, y_main + 25, switch_x, y_main + 25, 
                             fill=color, width=2, arrow=tk.LAST)
            
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
        
        # Maintenance mode toggle
        maintenance_frame = tk.Frame(controls_frame, bg="white")
        maintenance_frame.pack(anchor="w", pady=5)
        
        tk.Label(maintenance_frame, text="Maintenance mode", bg="white", 
            font=("Arial", 10)).pack(side=tk.LEFT, padx=5)
        
        # Toggle switch with ON/OFF text
        self.toggle_btn = tk.Checkbutton(maintenance_frame, variable=self.maintenance_mode,
                       bg="lightgray", activebackground="lightgray",
                       selectcolor="lightgreen", width=6, indicatoron=False,
                       text="OFF", relief=tk.RAISED, borderwidth=2,
                       command=self.on_maintenance_toggle)
        self.toggle_btn.pack(side=tk.LEFT, padx=5)
        
        # Block selection section (initially hidden)
        self.block_selection_frame = tk.Frame(controls_frame, bg="white")
        
        # Line selection
        line_frame = tk.Frame(self.block_selection_frame, bg="white")
        line_frame.pack(anchor="w", pady=5)
        
        tk.Label(line_frame, text="Line:", bg="white", font=("Arial", 10)).pack(side=tk.LEFT, padx=5)
        
        self.line_dropdown = ttk.Combobox(line_frame, textvariable=self.selected_line,
                                         values=["Select Line", "Green Line", "Red Line"],
                                         width=12, state="readonly")
        self.line_dropdown.pack(side=tk.LEFT, padx=5)
        self.line_dropdown.bind('<<ComboboxSelected>>', self.on_line_selected)
        
        # Block selection
        block_frame = tk.Frame(self.block_selection_frame, bg="white")
        block_frame.pack(anchor="w", pady=5)
        
        tk.Label(block_frame, text="Block:", bg="white", font=("Arial", 10)).pack(side=tk.LEFT, padx=5)
        
        self.block_dropdown = ttk.Combobox(block_frame, textvariable=self.selected_block,
                                          width=12, state="disabled")
        self.block_dropdown.pack(side=tk.LEFT, padx=5)
        self.block_dropdown.bind('<<ComboboxSelected>>', self.on_block_selected)
        
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
        
        default_btn = tk.Button(left_frame, text="Button", width=10, 
                              command=self.use_default_settings)
        default_btn.pack(pady=5)
        
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
        
        browse_btn = tk.Button(upload_frame, text="Browse...", width=10, 
                             command=self.browse_file)
        browse_btn.pack(side=tk.LEFT, padx=5)
        
        upload_btn = tk.Button(right_frame, text="Upload", width=10, 
                             command=self.upload_file)
        upload_btn.pack(pady=5)
        
        # Configure grid weights
        parent.columnconfigure(0, weight=1)
        parent.columnconfigure(1, weight=1)
    
    # ============ Event Handlers ============
    
    def on_maintenance_toggle(self):
        """Handle maintenance mode toggle"""
        if self.maintenance_mode.get():
            self.toggle_btn.config(text="ON")
            # Show block selection
            self.block_selection_frame.pack(anchor="w", pady=10, before=self.lights_frame.master.children['!separator'])
        else:
            self.toggle_btn.config(text="OFF")
            # Hide block selection and controls
            self.block_selection_frame.pack_forget()
            self.lights_frame.pack_forget()
            self.switch_frame.pack_forget()
            self.crossing_frame.pack_forget()
            
            # Reset selections
            self.selected_line.set("Select Line")
            self.selected_block.set("Select Block")
            self.block_dropdown['state'] = 'disabled'
            self.update_info_display(None)
    
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
        """Open file browser to select PLC file"""
        filename = filedialog.askopenfilename(
            title="Select PLC File",
            filetypes=[("Python files", "*.py"), ("All files", "*.*")]
        )
        if filename:
            self.plc_file_path.set(filename)
            
    def upload_file(self):
        """Handle PLC file upload"""
        if self.plc_file_path.get():
            print(f"Uploading file: {self.plc_file_path.get()}")
            messagebox.showinfo("Success", "PLC file uploaded successfully")
        else:
            messagebox.showwarning("Warning", "No file selected")
            
    def use_default_settings(self):
        """Load default settings"""
        print("Loading default settings...")
        messagebox.showinfo("Info", "Default settings loaded")

def main():
    """Entry point for the application"""
    app = WaysideDashboard()
    app.mainloop()

if __name__ == "__main__":
    main()
