
#COMPLETE TRAIN CONTROLLER SYSTEM WITH TEST UI



import os
os.environ['TK_SILENCE_DEPRECATION'] = '1'

import tkinter as tk
from tkinter import ttk
import math



# TRAIN CONTROLLER LOGIC (The Brain)


class TrainController:
    
    
    def __init__(self):
        #  VITAL PARAMETERS 
        # Speed and Authority
        self.current_speed = 0.0  # mph
        self.commanded_speed = 0.0  # mph
        self.speed_limit = 30.0  # mph
        self.authority = 0.0  # meters (distance allowed to travel)
        
        # Power Control (PI Controller)
        self.kp = 10.0  # Proportional gain
        self.ki = 8000.0  # Integral gain
        self.power_output = 0.0  # Watts (max 120,000W)
        self.uk = 0.0  # Integral term accumulator
        self.prev_error = 0.0  # Previous velocity error
        self.prev_uk = 0.0  # Previous integral term
        
        # Braking
        self.emergency_brake_active = False
        self.service_brake_active = False
        
        # Safety Limits
        self.MAX_POWER = 120000  # Watts
        self.SERVICE_BRAKE_DECEL = 1.2  # m/s^2
        self.EMERGENCY_BRAKE_DECEL = 2.73  # m/s^2
        
        #  FAILURE MODES 
        self.power_failure = False
        self.brake_failure = False
        self.signal_pickup_failure = False
        
        #  OPERATION MODE 
        self.automatic_mode = True  # True = Auto, False = Manual
        
        #  NON-VITAL PARAMETERS 
        self.doors_state = 0  # 0=closed, 1=right, 2=left, 3=both
        self.headlights_on = False
        self.interior_lights = 0  # 0=off, 1=on, 2=dimmed
        self.cabin_temperature = 70
        self.passengers = 0
        self.next_station = "YARD"
        self.announcement = ""
        
        # Driver Input
        self.driver_power_request = 0  # 0-100%
        self.manual_speed_setpoint = 0  # For manual mode
        
        # Timing
        self.prev_time = 0
    
    
    
    # VITAL FUNCTIONS - Speed and Authority Control
    
    
    def calculate_stopping_distance(self, deceleration):
        
        velocity_ms = self.current_speed * 0.44704  # mph to m/s
        reaction_distance = velocity_ms * 0.1  # Reaction time buffer
        
        if deceleration > 0:
            stopping_distance = (velocity_ms ** 2) / (2 * deceleration)
        else:
            stopping_distance = 0
        
        return stopping_distance + reaction_distance
    
    def monitor_speed_and_authority(self):
        
        # Calculate stopping distances
        service_stop_dist = self.calculate_stopping_distance(self.SERVICE_BRAKE_DECEL)
        emergency_stop_dist = self.calculate_stopping_distance(self.EMERGENCY_BRAKE_DECEL)
        
        # CRITICAL: Emergency brake if we can't stop in time
        if self.authority <= emergency_stop_dist and self.authority >= 5:
            self.activate_emergency_brake()
            return
        
        # Service brake if approaching authority limit
        if self.authority <= service_stop_dist or (self.authority < 0 and self.current_speed > 0):
            self.service_brake_active = True
            self.driver_power_request = 0
            return
        
        # VITAL: Enforce speed limit (ALWAYS, regardless of mode)
        if self.current_speed > self.speed_limit:
            self.service_brake_active = True
            self.driver_power_request = 0
            return
        
        # VITAL: Don't exceed commanded speed
        if self.current_speed > self.commanded_speed:
            self.service_brake_active = True
            self.driver_power_request = 0
            return
        
        # In automatic mode, regulate to commanded speed
        if self.automatic_mode:
            if self.current_speed < self.commanded_speed and self.current_speed < self.speed_limit:
                # Adjust power based on authority remaining
                if self.authority <= 50:
                    self.driver_power_request = 25
                elif self.authority > 60:
                    self.driver_power_request = 100
                else:
                    self.driver_power_request = 50
                self.service_brake_active = False
            elif self.current_speed >= self.commanded_speed or self.current_speed >= self.speed_limit:
                self.driver_power_request = 0
                self.service_brake_active = False
    
    def calculate_power_command(self, dt_seconds):
        
        # If any brake is active, no power
        if self.emergency_brake_active or self.service_brake_active:
            self.power_output = 0
            self.uk = 0  # Reset integral term
            return 0
        
        # If driver requests no power
        if self.driver_power_request == 0:
            self.power_output = 0
            return 0
        
        # Calculate velocity error (convert mph to m/s)
        if self.automatic_mode:
            cmd_velocity_ms = self.commanded_speed * 0.44704
        else:
            # In manual mode, use manual setpoint
            cmd_velocity_ms = self.manual_speed_setpoint * 0.44704
        
        cur_velocity_ms = self.current_speed * 0.44704
        error = cmd_velocity_ms - cur_velocity_ms
        
        # PI Control with trapezoidal integration
        self.uk = self.prev_uk + (dt_seconds / 2) * (error + self.prev_error)
        
        # Calculate power: P = Kp * e + Ki * uk
        power_calc = (self.kp * error + self.ki * self.uk) * (self.driver_power_request / 100.0)
        
        # Save for next iteration
        self.prev_error = error
        self.prev_uk = self.uk
        
        # Apply power limits
        if power_calc > self.MAX_POWER:
            power_calc = self.MAX_POWER
        elif power_calc < 0:
            power_calc = 0
        
        self.power_output = power_calc
        return power_calc
    
    def update_authority_by_distance(self, dt_seconds):
        
        if self.current_speed > 0:
            velocity_m_per_ms = self.current_speed * 0.00044704
            distance_traveled = velocity_m_per_ms * (dt_seconds * 1000)
            self.authority -= distance_traveled
    
    
   
    # VITAL FUNCTIONS - Failure Handling
    
    
    def activate_emergency_brake(self):
       # Activate emergency brake - highest priority safety
        self.emergency_brake_active = True
        self.power_output = 0
        self.driver_power_request = 0
        self.service_brake_active = False
        print("EMERGENCY BRAKE ACTIVATED BY SYSTEM!")
    
    def release_emergency_brake(self):
        #Release emergency brake (only if safe)
        if not (self.power_failure or self.brake_failure or self.signal_pickup_failure):
            self.emergency_brake_active = False
            print(" Emergency Brake Released")
    
    def handle_power_failure(self, failed):
        #Response to power system failure
        self.power_failure = failed
        if failed:
            print("POWER FAILURE DETECTED!")
            self.activate_emergency_brake()
        else:
            print(" Power restored")
    
    def handle_brake_failure(self, failed):
        #Response to brake system failure
        self.brake_failure = failed
        if failed:
            print("BRAKE FAILURE DETECTED!")
            self.activate_emergency_brake()
        else:
            print(" Brakes restored")
    
    def handle_signal_failure(self, failed):
        #Response to signal pickup failure
        self.signal_pickup_failure = failed
        if failed:
            print("SIGNAL PICKUP FAILURE DETECTED!")
            self.activate_emergency_brake()
        else:
            print(" Signal restored")
    
    
   
    # NON-VITAL FUNCTIONS
   
    
    def set_doors(self, door_state):
       # Control doors (only when stopped)
        if self.current_speed == 0:
            self.doors_state = door_state
            print(f"Doors: {door_state}")
        else:
            print("Cannot open doors while moving!")
    
    def set_lights(self, light_mode):
        #Control lights
        if light_mode == "Off":
            self.headlights_on = False
            self.interior_lights = 0
        elif light_mode == "External":
            self.headlights_on = True
            self.interior_lights = 0
        elif light_mode == "Internal":
            self.headlights_on = False
            self.interior_lights = 1
        print(f"Lights: {light_mode}")
    
    
    
    # MODE CONTROL
    
    
    def set_automatic_mode(self):
       # Switch to automatic mode
        self.automatic_mode = True
        print(" Automatic Mode Activated")
    
    def set_manual_mode(self, manual_speed):
        #Switch to manual mode with speed setpoint
        self.automatic_mode = False
        self.manual_speed_setpoint = manual_speed
        self.driver_power_request = 50
        print(f" Manual Mode Activated - Target Speed: {manual_speed} mph")
    
    
    
    # MAIN UPDATE LOOP
    
    
    def update(self, dt_seconds):
       # Main update function - called every simulation cycle
        self.monitor_speed_and_authority()
        power = self.calculate_power_command(dt_seconds)
        self.update_authority_by_distance(dt_seconds)
        
        return {
            'power': power,
            'service_brake': self.service_brake_active,
            'emergency_brake': self.emergency_brake_active
        }



# TEST UI - Real-time Monitor


class TrainControllerTestUI:
    #Test UI showing all inputs and outputs in real-time
    
    def __init__(self, controller, parent_window):
        
       # Initialize Test UI
        #controller = the TrainController object to monitor
        #parent_window = the main Tk window
        
        self.controller = controller
        self.edit_mode = False  # False = Live Mode, True = Edit Mode
        
        # Create test window
        self.window = tk.Toplevel(parent_window)
        self.window.title("Train Controller Test UI - LIVE MODE")
        self.window.geometry("650x800")
        self.window.configure(bg='#e0e0e0')
        
        self.create_test_ui()
        self.start_monitoring()
    
    def create_test_ui(self):
        #Create the test UI layout
        
        # Title Bar
        title_bar = tk.Frame(self.window, bg='gray', height=50)
        title_bar.pack(fill=tk.X)
        
        # Title
        title = tk.Label(title_bar, text="Train Controller Test UI", 
                        font=('Arial', 16, 'bold'), bg='gray', fg='white')
        title.pack(side=tk.LEFT, padx=15, pady=10)
        
        # Mode Toggle Button
        self.mode_btn = tk.Button(title_bar, text="Switch to EDIT Mode", 
                                 command=self.toggle_mode,
                                 bg='#90EE90', font=('Arial', 11, 'bold'),
                                 relief=tk.RAISED, bd=3, width=18)
        self.mode_btn.pack(side=tk.RIGHT, padx=15, pady=10)
        
        # Main container
        main = tk.Frame(self.window, bg='#e0e0e0')
        main.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        
        #  LEFT SIDE: INPUTS 
        left_frame = tk.LabelFrame(main, text="Inputs", font=('Arial', 13, 'bold'), 
                                   bg='white', padx=10, pady=10, relief=tk.RIDGE, bd=3)
        left_frame.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=(0, 5))
        
        # Input data structure: (label_text, key_name, editable)
        input_data = [
            ("--- From Train Model ---", "header", False),
            ("Commanded Speed (km/hr)", "cmd_speed_kmh", True),
            ("Commanded Authority (km)", "cmd_authority_km", True),
            ("Current Position (km)", "current_pos", False),
            ("Emergency Brake (bool)", "emergency_brake_in", False),
            ("Actual Speed (km/hr)", "actual_speed", True),
            ("Power Fault (bool)", "power_fault", True),
            ("Engine fault (bool)", "engine_fault", False),
            ("Brake Fault (bool)", "brake_fault", True),
            ("Track Power Fault (bool)", "track_power_fault", False),
            ("Next Station (string)", "next_station", True),
            ("Passenger count (integer)", "passenger_count", True),
            ("", "spacer", False),
            ("--- From Train Engineer ---", "header", False),
            ("Kp (Double)", "kp_value", True),
            ("Ki (Double)", "ki_value", True),
            ("", "spacer", False),
            ("--- From Driver ---", "header", False),
            ("Emergency Brake (bool)", "driver_ebrake", False),
            ("Brake (bool)", "driver_brake", False),
            ("Door(Left/right) (bool)", "door_state", False),
            ("Mode (bool)", "mode", False),
            ("Speed (km/hr)", "driver_speed", False),
            ("Light(External/Internal) (bool)", "light_state", False),
        ]
        
        self.input_labels = {}
        self.input_entries = {}  # For edit mode
        
        for text, key, editable in input_data:
            if key == "header":
                # Section header
                tk.Label(left_frame, text=text, font=('Arial', 9, 'bold'), 
                        bg='#c0c0c0', anchor='w', padx=5, relief=tk.RAISED).pack(fill=tk.X, pady=(8, 2))
            elif key == "spacer":
                # Blank space
                tk.Frame(left_frame, height=3, bg='white').pack()
            else:
                # Data row
                row = tk.Frame(left_frame, bg='white')
                row.pack(fill=tk.X, pady=1)
                
                tk.Label(row, text=text, font=('Arial', 8), bg='white', 
                        anchor='w', width=28).pack(side=tk.LEFT, padx=3)
                
                # Value label (for Live mode)
                value_label = tk.Label(row, text="[0]", font=('Arial', 8, 'bold'), 
                                      bg='#ffffcc', fg='black', width=14, 
                                      relief=tk.SUNKEN, bd=1)
                value_label.pack(side=tk.RIGHT, padx=3)
                self.input_labels[key] = value_label
                
                # Entry box (for Edit mode - hidden initially)
                if editable:
                    value_entry = tk.Entry(row, font=('Arial', 8), width=14,
                                          bg='white', fg='black', insertbackground='black',
                                          relief=tk.SUNKEN, bd=1, justify='center')
                    self.input_entries[key] = (value_entry, editable)
        
        #  RIGHT SIDE: OUTPUTS 
        right_frame = tk.LabelFrame(main, text="Outputs", font=('Arial', 13, 'bold'), 
                                    bg='white', padx=10, pady=10, relief=tk.RIDGE, bd=3)
        right_frame.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=(5, 0))
        
        # Output data structure
        output_data = [
            ("--- To Driver ---", "header"),
            ("Speed Display (km/hr)", "speed_display"),
            ("Authority Display (km)", "authority_display_km"),
            ("Authority Display (m)", "authority_display_m"),
            ("Next station", "next_station_out"),
            ("", "spacer"),
            ("--- To Train Model ---", "header"),
            ("Velocity Command (km/hr)", "velocity_cmd"),
            ("Door (Left/right) (bool)", "door_output"),
            ("Lights (External/Internal) (bool)", "lights_output"),
            ("Emergency Brake (bool)", "ebrake_output"),
            ("Temperature (F)", "temp_output"),
            ("Brake (bool)", "brake_output"),
        ]
        
        self.output_labels = {}
        
        for text, key in output_data:
            if key == "header":
                tk.Label(right_frame, text=text, font=('Arial', 9, 'bold'), 
                        bg='#c0c0c0', anchor='w', padx=5, relief=tk.RAISED).pack(fill=tk.X, pady=(8, 2))
            elif key == "spacer":
                tk.Frame(right_frame, height=3, bg='white').pack()
            else:
                row = tk.Frame(right_frame, bg='white')
                row.pack(fill=tk.X, pady=1)
                
                tk.Label(row, text=text, font=('Arial', 8), bg='white', 
                        anchor='w', width=28).pack(side=tk.LEFT, padx=3)
                
                value_label = tk.Label(row, text="[0]", font=('Arial', 8, 'bold'), 
                                      bg='#ccffcc', fg='black', width=14, 
                                      relief=tk.SUNKEN, bd=1)
                value_label.pack(side=tk.RIGHT, padx=3)
                
                self.output_labels[key] = value_label
        
        # Apply/Revert buttons (for Edit mode - hidden initially)
        self.edit_buttons_frame = tk.Frame(self.window, bg='#e0e0e0')
        
        tk.Button(self.edit_buttons_frame, text="✓ Apply Changes", 
                 command=self.apply_changes, bg='#90EE90', 
                 font=('Arial', 12, 'bold'), width=20).pack(side=tk.LEFT, padx=10)
        
        tk.Button(self.edit_buttons_frame, text="✗ Revert Changes", 
                 command=self.revert_changes, bg='#ffcccc', 
                 font=('Arial', 12, 'bold'), width=20).pack(side=tk.LEFT, padx=10)
    
    def toggle_mode(self):
        #Toggle between Live and Edit modes
        self.edit_mode = not self.edit_mode
        
        if self.edit_mode:
            # Switch to EDIT MODE
            self.window.title("Train Controller Test UI - EDIT MODE")
            self.mode_btn.config(text="Switch to LIVE Mode", bg='#ffcccc')
            
            # Show entry boxes, hide labels
            for key, (entry, editable) in self.input_entries.items():
                if editable and key in self.input_labels:
                    # Hide label
                    self.input_labels[key].pack_forget()
                    # Show entry with current value
                    current_text = self.input_labels[key].cget('text')
                    entry.delete(0, tk.END)
                    entry.insert(0, current_text.strip('[]'))
                    entry.pack(side=tk.RIGHT, padx=3)
            
            # Show Apply/Revert buttons
            self.edit_buttons_frame.pack(pady=10)
            
            print("EDIT MODE: You can now modify values")
            
        else:
            # Switch to LIVE MODE
            self.window.title("Train Controller Test UI - LIVE MODE")
            self.mode_btn.config(text="Switch to EDIT Mode", bg='#90EE90')
            
            # Show labels, hide entry boxes
            for key, (entry, editable) in self.input_entries.items():
                entry.pack_forget()
                if key in self.input_labels:
                    self.input_labels[key].pack(side=tk.RIGHT, padx=3)
            
            # Hide Apply/Revert buttons
            self.edit_buttons_frame.pack_forget()
            
            print("LIVE MODE: Monitoring values in real-time")
    
    def apply_changes(self):
        #Apply changes from Edit mode to controller
        try:
            # Apply Commanded Speed
            if 'cmd_speed_kmh' in self.input_entries:
                entry, _ = self.input_entries['cmd_speed_kmh']
                speed_kmh = float(entry.get())
                self.controller.commanded_speed = speed_kmh / 1.60934  # Convert back to mph
                print(f" Commanded Speed: {self.controller.commanded_speed:.1f} mph")
            
            # Apply Authority
            if 'cmd_authority_km' in self.input_entries:
                entry, _ = self.input_entries['cmd_authority_km']
                auth_km = float(entry.get())
                self.controller.authority = auth_km * 1000  # Convert back to meters
                print(f" Authority: {self.controller.authority:.0f} meters")
            
            # Apply Actual Speed
            if 'actual_speed' in self.input_entries:
                entry, _ = self.input_entries['actual_speed']
                speed_kmh = float(entry.get())
                self.controller.current_speed = speed_kmh / 1.60934  # Convert to mph
                print(f" Current Speed: {self.controller.current_speed:.1f} mph")
            
            # Apply Kp
            if 'kp_value' in self.input_entries:
                entry, _ = self.input_entries['kp_value']
                self.controller.kp = float(entry.get())
                print(f" Kp: {self.controller.kp}")
            
            # Apply Ki
            if 'ki_value' in self.input_entries:
                entry, _ = self.input_entries['ki_value']
                self.controller.ki = float(entry.get())
                print(f" Ki: {self.controller.ki}")
            
            # Apply Passengers
            if 'passenger_count' in self.input_entries:
                entry, _ = self.input_entries['passenger_count']
                self.controller.passengers = int(entry.get())
                print(f" Passengers: {self.controller.passengers}")
            
            # Apply Next Station
            if 'next_station' in self.input_entries:
                entry, _ = self.input_entries['next_station']
                self.controller.next_station = entry.get()
                print(f" Next Station: {self.controller.next_station}")
            
            # Apply Power Fault
            if 'power_fault' in self.input_entries:
                entry, _ = self.input_entries['power_fault']
                value = entry.get().lower()
                if value in ['true', '1', 'yes']:
                    self.controller.handle_power_failure(True)
                else:
                    self.controller.handle_power_failure(False)
            
            # Apply Brake Fault
            if 'brake_fault' in self.input_entries:
                entry, _ = self.input_entries['brake_fault']
                value = entry.get().lower()
                if value in ['true', '1', 'yes']:
                    self.controller.handle_brake_failure(True)
                else:
                    self.controller.handle_brake_failure(False)
            
            print("All changes applied!")
            
        except ValueError as e:
            print(f" Error applying changes: {e}")
            print(" Some values may be invalid. Check your inputs.")
    
    def revert_changes(self):
        #Revert all changes - reload from controller
        print("Changes reverted - showing current values")
        # Just update the display - it will reload from controller
        self.update_values()
        
        # Main container
        main = tk.Frame(self.window, bg='#e0e0e0')
        main.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        
        #  LEFT SIDE: INPUTS 
        left_frame = tk.LabelFrame(main, text="Inputs", font=('Arial', 13, 'bold'), 
                                   bg='white', padx=10, pady=10, relief=tk.RIDGE, bd=3)
        left_frame.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=(0, 5))
        
        # Input data structure: (label_text, key_name)
        input_data = [
            ("--- From Train Model ---", "header"),
            ("Commanded Speed (km/hr)", "cmd_speed_kmh"),
            ("Commanded Authority (km)", "cmd_authority_km"),
            ("Current Position (km)", "current_pos"),
            ("Emergency Brake (bool)", "emergency_brake_in"),
            ("Actual Speed (km/hr)", "actual_speed"),
            ("Power Fault (bool)", "power_fault"),
            ("Engine fault (bool)", "engine_fault"),
            ("Brake Fault (bool)", "brake_fault"),
            ("Track Power Fault (bool)", "track_power_fault"),
            ("Next Station (string)", "next_station"),
            ("Passenger count (integer)", "passenger_count"),
            ("", "spacer"),
            ("--- From Train Engineer ---", "header"),
            ("Kp (Double)", "kp_value"),
            ("Ki (Double)", "ki_value"),
            ("", "spacer"),
            ("--- From Driver ---", "header"),
            ("Emergency Brake (bool)", "driver_ebrake"),
            ("Brake (bool)", "driver_brake"),
            ("Door(Left/right) (bool)", "door_state"),
            ("Mode (bool)", "mode"),
            ("Speed (km/hr)", "driver_speed"),
            ("Light(External/Internal) (bool)", "light_state"),
        ]
        
        self.input_labels = {}
        
        for text, key in input_data:
            if key == "header":
                # Section header
                tk.Label(left_frame, text=text, font=('Arial', 9, 'bold'), 
                        bg='#c0c0c0', anchor='w', padx=5, relief=tk.RAISED).pack(fill=tk.X, pady=(8, 2))
            elif key == "spacer":
                # Blank space
                tk.Frame(left_frame, height=3, bg='white').pack()
            else:
                # Data row
                row = tk.Frame(left_frame, bg='white')
                row.pack(fill=tk.X, pady=1)
                
                tk.Label(row, text=text, font=('Arial', 8), bg='white', 
                        anchor='w', width=28).pack(side=tk.LEFT, padx=3)
                
                value_label = tk.Label(row, text="[0]", font=('Arial', 8, 'bold'), 
                                      bg='#ffffcc', fg='black', width=14, 
                                      relief=tk.SUNKEN, bd=1)
                value_label.pack(side=tk.RIGHT, padx=3)
                
                self.input_labels[key] = value_label
        
        #  RIGHT SIDE: OUTPUTS 
        right_frame = tk.LabelFrame(main, text="Outputs", font=('Arial', 13, 'bold'), 
                                    bg='white', padx=10, pady=10, relief=tk.RIDGE, bd=3)
        right_frame.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=(5, 0))
        
        # Output data structure
        output_data = [
            ("--- To Driver ---", "header"),
            ("Speed Display (km/hr)", "speed_display"),
            ("Authority Display (km)", "authority_display_km"),
            ("Authority Display (m)", "authority_display_m"),
            ("Next station", "next_station_out"),
            ("", "spacer"),
            ("--- To Train Model ---", "header"),
            ("Velocity Command (km/hr)", "velocity_cmd"),
            ("Door (Left/right) (bool)", "door_output"),
            ("Lights (External/Internal) (bool)", "lights_output"),
            ("Emergency Brake (bool)", "ebrake_output"),
            ("Temperature (F)", "temp_output"),
            ("Brake (bool)", "brake_output"),
        ]
        
        self.output_labels = {}
        
        for text, key in output_data:
            if key == "header":
                tk.Label(right_frame, text=text, font=('Arial', 9, 'bold'), 
                        bg='#c0c0c0', anchor='w', padx=5, relief=tk.RAISED).pack(fill=tk.X, pady=(8, 2))
            elif key == "spacer":
                tk.Frame(right_frame, height=3, bg='white').pack()
            else:
                row = tk.Frame(right_frame, bg='white')
                row.pack(fill=tk.X, pady=1)
                
                tk.Label(row, text=text, font=('Arial', 8), bg='white', 
                        anchor='w', width=28).pack(side=tk.LEFT, padx=3)
                
                value_label = tk.Label(row, text="[0]", font=('Arial', 8, 'bold'), 
                                      bg='#ccffcc', fg='black', width=14, 
                                      relief=tk.SUNKEN, bd=1)
                value_label.pack(side=tk.RIGHT, padx=3)
                
                self.output_labels[key] = value_label
    
    def start_monitoring(self):
        #Start monitoring and updating values
        self.update_values()
    
    def update_values(self):
        #Update all displayed values from controller
        
        try:
            #  UPDATE INPUTS 
            
            # From Train Model
            self.input_labels['cmd_speed_kmh'].config(
                text=f"[{self.controller.commanded_speed * 1.60934:.1f}]")
            
            self.input_labels['cmd_authority_km'].config(
                text=f"[{self.controller.authority / 1000:.3f}]")
            
            self.input_labels['current_pos'].config(text="[0]")
            
            self.input_labels['emergency_brake_in'].config(
                text=f"[{str(self.controller.emergency_brake_active)}]")
            
            self.input_labels['actual_speed'].config(
                text=f"[{self.controller.current_speed * 1.60934:.1f}]")
            
            self.input_labels['power_fault'].config(
                text=f"[{str(self.controller.power_failure)}]")
            
            self.input_labels['engine_fault'].config(text="[False]")
            
            self.input_labels['brake_fault'].config(
                text=f"[{str(self.controller.brake_failure)}]")
            
            self.input_labels['track_power_fault'].config(text="[False]")
            
            self.input_labels['next_station'].config(
                text=f"[{self.controller.next_station}]")
            
            self.input_labels['passenger_count'].config(
                text=f"[{self.controller.passengers}]")
            
            # From Train Engineer
            self.input_labels['kp_value'].config(
                text=f"[{self.controller.kp:.1f}]")
            
            self.input_labels['ki_value'].config(
                text=f"[{self.controller.ki:.1f}]")
            
            # From Driver
            self.input_labels['driver_ebrake'].config(
                text=f"[{str(self.controller.emergency_brake_active)}]")
            
            self.input_labels['driver_brake'].config(
                text=f"[{str(self.controller.service_brake_active)}]")
            
            # Door state
            door_states = {0: "[Closed]", 1: "[Right]", 2: "[Left]", 3: "[Both]"}
            self.input_labels['door_state'].config(
                text=door_states.get(self.controller.doors_state, "[Closed]"))
            
            # Mode
            mode_text = "[manual]" if not self.controller.automatic_mode else "[auto]"
            self.input_labels['mode'].config(text=mode_text)
            
            # Driver speed
            self.input_labels['driver_speed'].config(
                text=f"[{self.controller.manual_speed_setpoint * 1.60934:.0f}]")
            
            # Light state
            light_text = "[Off]"
            if self.controller.headlights_on:
                light_text = "[External]"
            elif self.controller.interior_lights > 0:
                light_text = "[Internal]"
            self.input_labels['light_state'].config(text=light_text)
            
            #  UPDATE OUTPUTS 
            
            # To Driver
            self.output_labels['speed_display'].config(
                text=f"[{self.controller.current_speed * 1.60934:.0f}]")
            
            self.output_labels['authority_display_km'].config(
                text=f"[{self.controller.authority / 1000:.2f}]")
            
            self.output_labels['authority_display_m'].config(
                text=f"[{self.controller.authority:.0f}]")
            
            self.output_labels['next_station_out'].config(
                text=f"[{self.controller.next_station}]")
            
            # To Train Model
            self.output_labels['velocity_cmd'].config(
                text=f"[{self.controller.commanded_speed * 1.60934:.1f}]")
            
            self.output_labels['door_output'].config(
                text=door_states.get(self.controller.doors_state, "[Closed]"))
            
            self.output_labels['lights_output'].config(text=light_text)
            
            self.output_labels['ebrake_output'].config(
                text=f"[{str(self.controller.emergency_brake_active)}]")
            
            self.output_labels['temp_output'].config(
                text=f"[{self.controller.cabin_temperature}]")
            
            self.output_labels['brake_output'].config(
                text=f"[{str(self.controller.service_brake_active)}]")
            
        except:
            pass  # Ignore errors if window is closing
        
        # Schedule next update (100ms)
        try:
            self.window.after(100, self.update_values)
        except:
            pass
    
    def show(self):
        #Show the test window
        self.window.deiconify()
    
    def hide(self):
        #"""Hide the test window
        self.window.withdraw()



# USER INTERFACE (Tkinter GUI)


class TrainControllerUI:
    #Complete User Interface with Controller Integration
    
    def __init__(self):
        # Create the controller
        self.controller = TrainController()
        
        # Main window
        self.root = tk.Tk()
        self.root.title("Train Controller")
        self.root.geometry("1400x800")
        self.root.configure(bg='#f0f0f0')
        
        self.simulation_running = False
        self.test_ui = None  # Will hold Test UI when created
        
        self.create_ui()
        self.start_update_loop()
    
    def create_ui(self):
        #Create complete UI
        
        #  HEADER 
        header = tk.Frame(self.root, bg='#808080', height=60)
        header.pack(fill=tk.X, side=tk.TOP)
        
        logo_label = tk.Label(header, text="Logo", font=('Arial', 18, 'bold'), 
                             bg='#d3d3d3', width=10, relief=tk.RAISED, bd=3)
        logo_label.pack(side=tk.LEFT, padx=10, pady=10)
        
        title_label = tk.Label(header, text="Train Controller", font=('Arial', 22, 'bold'), 
                              bg='#808080', fg='white')
        title_label.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=20)
        
        # TEST UI BUTTON in header
        test_ui_btn = tk.Button(header, text="📊 Open Test UI", 
                               command=self.open_test_ui, 
                               bg='#ffffaa', font=('Arial', 12, 'bold'),
                               relief=tk.RAISED, bd=3, width=15)
        test_ui_btn.pack(side=tk.RIGHT, padx=10, pady=10)
        
        #  MAIN CONTAINER 
        main_container = tk.Frame(self.root, bg='#f0f0f0')
        main_container.pack(fill=tk.BOTH, expand=True, padx=15, pady=15)
        
        #  LEFT SIDE 
        left_frame = tk.Frame(main_container, bg='#f0f0f0', width=600)
        left_frame.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=(0, 10))
        
        # Driver Inputs Section
        driver_inputs = tk.LabelFrame(left_frame, text="Driver Inputs Buttons", 
                                     font=('Arial', 15, 'bold'), bg='white', 
                                     padx=25, pady=25, relief=tk.RIDGE, bd=3)
        driver_inputs.pack(fill=tk.BOTH, expand=True)
        
        # 1. EMERGENCY BRAKE
        self.ebrake_btn = tk.Button(
            driver_inputs,
            text="Emergency Brake",
            font=('Arial', 18, 'bold'),
            bg='#ffb3ba',
            fg='#8b0000',
            command=self.on_emergency_brake,
            height=2,
            relief=tk.RAISED,
            bd=4
        )
        self.ebrake_btn.pack(fill=tk.X, pady=(0, 15))
        
        # 2. BRAKE TOGGLE
        brake_container = tk.Frame(driver_inputs, bg='#c0c0c0', relief=tk.RAISED, bd=3)
        brake_container.pack(fill=tk.X, pady=15)
        
        tk.Label(brake_container, text="Brake", font=('Arial', 16, 'bold'), 
                bg='#c0c0c0').pack(side=tk.LEFT, padx=20, pady=15)
        
        self.brake_var = tk.IntVar(value=0)
        self.brake_toggle = tk.Checkbutton(
            brake_container,
            text="●",
            variable=self.brake_var,
            command=self.on_brake_toggle,
            font=('Arial', 20, 'bold'),
            bg='#808080',
            selectcolor='#303030',
            indicatoron=False,
            width=4,
            height=1,
            relief=tk.RAISED,
            bd=3
        )
        self.brake_toggle.pack(side=tk.RIGHT, padx=20, pady=10)
        
        # 3. DOORS
        doors_container = tk.Frame(driver_inputs, bg='white', relief=tk.RIDGE, bd=2)
        doors_container.pack(fill=tk.X, pady=15)
        
        tk.Label(doors_container, text="Doors", font=('Arial', 15, 'bold'), 
                bg='white').pack(pady=5)
        
        doors_buttons = tk.Frame(doors_container, bg='white')
        doors_buttons.pack(pady=5)
        
        self.door_var = tk.StringVar(value="Closed")
        self.door_closed_btn = tk.Radiobutton(doors_buttons, text="Closed", variable=self.door_var, value="Closed", 
                      command=self.on_door_change, bg='#add8e6', font=('Arial', 12, 'bold'), 
                      indicatoron=False, width=10, height=2, relief=tk.RAISED, bd=2)
        self.door_closed_btn.pack(side=tk.LEFT, padx=3)
        
        self.door_left_btn = tk.Radiobutton(doors_buttons, text="Left", variable=self.door_var, value="Left", 
                      command=self.on_door_change, bg='white', font=('Arial', 12), 
                      indicatoron=False, width=10, height=2, relief=tk.RAISED, bd=2)
        self.door_left_btn.pack(side=tk.LEFT, padx=3)
        
        self.door_right_btn = tk.Radiobutton(doors_buttons, text="Right", variable=self.door_var, value="Right", 
                      command=self.on_door_change, bg='white', font=('Arial', 12), 
                      indicatoron=False, width=10, height=2, relief=tk.RAISED, bd=2)
        self.door_right_btn.pack(side=tk.LEFT, padx=3)
        
        # 4. LIGHT
        light_container = tk.Frame(driver_inputs, bg='white', relief=tk.RIDGE, bd=2)
        light_container.pack(fill=tk.X, pady=15)
        
        tk.Label(light_container, text="Light", font=('Arial', 15, 'bold'), 
                bg='white').pack(pady=5)
        
        light_buttons = tk.Frame(light_container, bg='white')
        light_buttons.pack(pady=5)
        
        self.light_var = tk.StringVar(value="Off")
        self.light_off_btn = tk.Radiobutton(light_buttons, text="Off", variable=self.light_var, value="Off", 
                      command=self.on_light_change, bg='#add8e6', font=('Arial', 12, 'bold'), 
                      indicatoron=False, width=10, height=2, relief=tk.RAISED, bd=2)
        self.light_off_btn.pack(side=tk.LEFT, padx=3)
        
        self.light_ext_btn = tk.Radiobutton(light_buttons, text="External", variable=self.light_var, value="External", 
                      command=self.on_light_change, bg='white', font=('Arial', 12), 
                      indicatoron=False, width=10, height=2, relief=tk.RAISED, bd=2)
        self.light_ext_btn.pack(side=tk.LEFT, padx=3)
        
        self.light_int_btn = tk.Radiobutton(light_buttons, text="Internal", variable=self.light_var, value="Internal", 
                      command=self.on_light_change, bg='white', font=('Arial', 12), 
                      indicatoron=False, width=10, height=2, relief=tk.RAISED, bd=2)
        self.light_int_btn.pack(side=tk.LEFT, padx=3)
        
        # 5. OPERATION MODE
        mode_container = tk.Frame(driver_inputs, bg='#80ffff', relief=tk.RAISED, bd=3)
        mode_container.pack(fill=tk.X, pady=15)
        
        tk.Label(mode_container, text="Operation Mode", font=('Arial', 15, 'bold'), 
                bg='#80ffff').pack(pady=5)
        
        mode_buttons = tk.Frame(mode_container, bg='#80ffff')
        mode_buttons.pack(pady=5)
        
        self.mode_var = tk.StringVar(value="Auto")
        tk.Radiobutton(mode_buttons, text="Auto", variable=self.mode_var, value="Auto", 
                      command=self.on_mode_change, bg='white', font=('Arial', 12, 'bold'), 
                      indicatoron=False, width=12, height=2, relief=tk.RAISED, bd=2).pack(side=tk.LEFT, padx=3)
        tk.Radiobutton(mode_buttons, text="Manual", variable=self.mode_var, value="Manual", 
                      command=self.on_mode_change, bg='white', font=('Arial', 12), 
                      indicatoron=False, width=12, height=2, relief=tk.RAISED, bd=2).pack(side=tk.LEFT, padx=3)
        
        #  RIGHT SIDE 
        right_frame = tk.Frame(main_container, bg='#f0f0f0', width=600)
        right_frame.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        
        # Driver Outputs Display
        outputs_section = tk.LabelFrame(right_frame, text="Driver Outputs Display", 
                                       font=('Arial', 15, 'bold'), bg='white', 
                                       padx=25, pady=25, relief=tk.RIDGE, bd=3)
        outputs_section.pack(fill=tk.BOTH, expand=True)
        
        grid_container = tk.Frame(outputs_section, bg='white')
        grid_container.pack(expand=True, pady=30)
        
        # Speed Display
        tk.Label(grid_container, text="Speed", font=('Arial', 14, 'bold'), 
                bg='white', fg='black', width=18, height=2, relief=tk.RAISED, bd=3).grid(row=0, column=0, padx=10, pady=12)
        
        self.speed_display = tk.Label(grid_container, text="0 mph", font=('Arial', 14, 'bold'), 
                                      bg='white', fg='black', width=18, height=2, relief=tk.SUNKEN, bd=3)
        self.speed_display.grid(row=0, column=1, padx=10, pady=12)
        
        # Authority Display
        tk.Label(grid_container, text="Authority", font=('Arial', 14, 'bold'), 
                bg='#ffff99', fg='black', width=18, height=2, relief=tk.RAISED, bd=3).grid(row=1, column=0, padx=10, pady=12)
        
        self.authority_display = tk.Label(grid_container, text="0 miles", font=('Arial', 14, 'bold'), 
                                         bg='white', fg='black', width=18, height=2, relief=tk.SUNKEN, bd=3)
        self.authority_display.grid(row=1, column=1, padx=10, pady=12)
        
        # Passengers Display
        tk.Label(grid_container, text="Passengers", font=('Arial', 14, 'bold'), 
                bg='#99ccff', fg='black', width=18, height=2, relief=tk.RAISED, bd=3).grid(row=2, column=0, padx=10, pady=12)
        
        self.passengers_display = tk.Label(grid_container, text="0", font=('Arial', 14, 'bold'), 
                                           bg='white', fg='black', width=18, height=2, relief=tk.SUNKEN, bd=3)
        self.passengers_display.grid(row=2, column=1, padx=10, pady=12)
        
        # Next Station Display
        tk.Label(grid_container, text="Next Station", font=('Arial', 14, 'bold'), 
                bg='#c0c0c0', fg='black', width=18, height=2, relief=tk.RAISED, bd=3).grid(row=3, column=0, padx=10, pady=12)
        
        self.station_display = tk.Label(grid_container, text="YARD", font=('Arial', 14, 'bold'), 
                                       bg='white', fg='black', width=18, height=2, relief=tk.SUNKEN, bd=3)
        self.station_display.grid(row=3, column=1, padx=10, pady=12)
        
        # TRAIN ENGINEER INPUTS 
        engineer_section = tk.LabelFrame(outputs_section, text="Train Engineer Inputs:", 
                                        font=('Arial', 14, 'bold'), bg='#ffffee', 
                                        padx=25, pady=20, relief=tk.RIDGE, bd=3)
        engineer_section.pack(fill=tk.BOTH, pady=(25, 0))
        
        engineer_grid = tk.Frame(engineer_section, bg='#ffffee')
        engineer_grid.pack()
        
        # Kp Input
        tk.Label(engineer_grid, text="Enter the amount of Kp:", font=('Arial', 13), 
                bg='#ffffee', fg='black').grid(row=0, column=0, pady=10, sticky='w', padx=10)
        
        self.kp_entry = tk.Entry(engineer_grid, font=('Arial', 14), width=20, 
                                justify='center', relief=tk.SUNKEN, bd=2, 
                                bg='white', fg='black', insertbackground='black')
        self.kp_entry.grid(row=1, column=0, pady=5, padx=10)
        self.kp_entry.insert(0, "10.0")
        
        tk.Button(engineer_grid, text="Set Kp", command=self.on_kp_set, 
                 bg='#90ee90', font=('Arial', 11, 'bold'), width=12).grid(row=2, column=0, pady=5)
        
        # Ki Input
        tk.Label(engineer_grid, text="Enter the amount of Ki:", font=('Arial', 13), 
                bg='#ffffee', fg='black').grid(row=0, column=1, pady=10, sticky='w', padx=10)
        
        self.ki_entry = tk.Entry(engineer_grid, font=('Arial', 14), width=20, 
                                justify='center', relief=tk.SUNKEN, bd=2,
                                bg='white', fg='black', insertbackground='black')
        self.ki_entry.grid(row=1, column=1, pady=5, padx=10)
        self.ki_entry.insert(0, "8000.0")
        
        tk.Button(engineer_grid, text="Set Ki", command=self.on_ki_set, 
                 bg='#90ee90', font=('Arial', 11, 'bold'), width=12).grid(row=2, column=1, pady=5)
        
        # TESTING SECTION 
        test_frame = tk.LabelFrame(self.root, text=" Testing Controls (Simulates CTC/Track Inputs)", 
                                  font=('Arial', 13, 'bold'), bg='#ffe9e9', 
                                  padx=20, pady=15, relief=tk.RIDGE, bd=3)
        test_frame.pack(fill=tk.X, padx=15, pady=(0, 10))
        
        test_grid = tk.Frame(test_frame, bg='#ffe9e9')
        test_grid.pack()
        
        # Commanded Speed
        tk.Label(test_grid, text="Commanded Speed (mph):", font=('Arial', 11), 
                bg='#ffe9e9').grid(row=0, column=0, padx=8, sticky='e')
        self.cmd_speed_entry = tk.Entry(test_grid, width=10, font=('Arial', 12), 
                                        bg='white', fg='black', insertbackground='black')
        self.cmd_speed_entry.grid(row=0, column=1, padx=5)
        self.cmd_speed_entry.insert(0, "30")
        tk.Button(test_grid, text="Apply", command=self.on_cmd_speed_set, 
                 bg='lightgreen', width=8, font=('Arial', 10, 'bold')).grid(row=0, column=2, padx=5)
        
        # Authority
        tk.Label(test_grid, text="Authority (meters):", font=('Arial', 11), 
                bg='#ffe9e9').grid(row=0, column=3, padx=8, sticky='e')
        self.auth_entry = tk.Entry(test_grid, width=10, font=('Arial', 12),
                                   bg='white', fg='black', insertbackground='black')
        self.auth_entry.grid(row=0, column=4, padx=5)
        self.auth_entry.insert(0, "500")
        tk.Button(test_grid, text="Apply", command=self.on_auth_set, 
                 bg='lightgreen', width=8, font=('Arial', 10, 'bold')).grid(row=0, column=5, padx=5)
        
        # Passengers
        tk.Label(test_grid, text="Passengers:", font=('Arial', 11), 
                bg='#ffe9e9').grid(row=1, column=0, padx=8, pady=8, sticky='e')
        self.passengers_entry = tk.Entry(test_grid, width=10, font=('Arial', 12),
                                         bg='white', fg='black', insertbackground='black')
        self.passengers_entry.grid(row=1, column=1, padx=5, pady=8)
        self.passengers_entry.insert(0, "0")
        tk.Button(test_grid, text="Apply", command=self.on_passengers_set, 
                 bg='lightgreen', width=8, font=('Arial', 10, 'bold')).grid(row=1, column=2, padx=5, pady=8)
        
        # Current Speed
        tk.Label(test_grid, text="Simulate Speed (mph):", font=('Arial', 11), 
                bg='#ffe9e9').grid(row=1, column=3, padx=8, pady=8, sticky='e')
        self.current_speed_entry = tk.Entry(test_grid, width=10, font=('Arial', 12),
                                            bg='white', fg='black', insertbackground='black')
        self.current_speed_entry.grid(row=1, column=4, padx=5, pady=8)
        self.current_speed_entry.insert(0, "0")
        tk.Button(test_grid, text="Apply", command=self.on_current_speed_set, 
                 bg='lightgreen', width=8, font=('Arial', 10, 'bold')).grid(row=1, column=5, padx=5, pady=8)
        
        # Failures
        tk.Label(test_grid, text="Simulate Failures:", font=('Arial', 11, 'bold'), 
                bg='#ffe9e9').grid(row=2, column=0, columnspan=2, pady=8)
        
        self.power_fail_btn = tk.Button(test_grid, text="Power Failure", 
                                        command=lambda: self.simulate_failure('power'), 
                                        bg='orange', width=12, font=('Arial', 10, 'bold'))
        self.power_fail_btn.grid(row=2, column=2, padx=3, pady=8)
        
        self.brake_fail_btn = tk.Button(test_grid, text="Brake Failure", 
                                        command=lambda: self.simulate_failure('brake'), 
                                        bg='orange', width=12, font=('Arial', 10, 'bold'))
        self.brake_fail_btn.grid(row=2, column=3, padx=3, pady=8)
        
        self.signal_fail_btn = tk.Button(test_grid, text="Signal Failure", 
                                         command=lambda: self.simulate_failure('signal'), 
                                         bg='orange', width=12, font=('Arial', 10, 'bold'))
        self.signal_fail_btn.grid(row=2, column=4, padx=3, pady=8)
        
        # Start Simulation
        self.sim_btn = tk.Button(test_grid, text=" START SIMULATION", 
                                command=self.start_simulation, 
                                bg='#90EE90', font=('Arial', 13, 'bold'), width=25, height=2)
        self.sim_btn.grid(row=3, column=0, columnspan=6, pady=15)
        
        #  STATUS BAR 
        self.status_bar = tk.Label(self.root, text="✓ System Ready - Automatic Mode", 
                                  font=('Arial', 12, 'bold'), bg='#2d2d2d', fg='#00ff00', 
                                  anchor='w', padx=15, height=2)
        self.status_bar.pack(fill=tk.X, side=tk.BOTTOM)
    
    
   
    # TEST UI CONTROL
  
    
    def open_test_ui(self):
        """Open or show the Test UI window"""
        if self.test_ui is None:
            # Create Test UI for the first time
            self.test_ui = TrainControllerTestUI(self.controller, self.root)
            print("✓ Test UI opened")
        else:
            # Show it if it was hidden
            self.test_ui.show()
            print("✓ Test UI shown")
    
    
    
    # EVENT HANDLERS
    
    
    def on_mode_change(self):
        """Handle mode change"""
        if self.mode_var.get() == "Auto":
            self.controller.set_automatic_mode()
            self.status_bar.config(text="✓ Automatic Mode - System Controls Train", 
                                 fg='#00ff00', bg='#2d2d2d')
        else:
            self.open_manual_speed_window()
    
    def open_manual_speed_window(self):
        """Open popup for manual speed input"""
        speed_window = tk.Toplevel(self.root)
        speed_window.title("Manual Speed Control")
        speed_window.geometry("450x280")
        speed_window.configure(bg='white')
        speed_window.transient(self.root)
        speed_window.grab_set()
        
        speed_window.update_idletasks()
        x = (speed_window.winfo_screenwidth() // 2) - (450 // 2)
        y = (speed_window.winfo_screenheight() // 2) - (280 // 2)
        speed_window.geometry(f"450x280+{x}+{y}")
        
        tk.Label(speed_window, text="Manual Speed Control", 
                font=('Arial', 18, 'bold'), bg='white', fg='black').pack(pady=20)
        
        tk.Label(speed_window, text="Enter the amount of the speed:", 
                font=('Arial', 14), bg='white', fg='black').pack(pady=15)
        
        speed_entry = tk.Entry(speed_window, font=('Arial', 18), width=15, 
                              justify='center', relief=tk.SUNKEN, bd=3,
                              bg='white', fg='black', insertbackground='black')
        speed_entry.pack(pady=15)
        speed_entry.focus()
        
        error_label = tk.Label(speed_window, text="", font=('Arial', 11), 
                              bg='white', fg='red')
        error_label.pack()
        
        buttons_frame = tk.Frame(speed_window, bg='white')
        buttons_frame.pack(pady=20)
        
        def set_speed():
            try:
                speed = float(speed_entry.get())
                if speed < 0 or speed > 80:
                    error_label.config(text="⚠️ Speed must be between 0-80 mph")
                    return
                
                self.controller.set_manual_mode(speed)
                self.status_bar.config(text=f"⚠ Manual Mode - Target: {speed} mph", 
                                     fg='yellow', bg='#2d2d2d')
                
                self.door_closed_btn.config(state='normal')
                self.door_left_btn.config(state='normal')
                self.door_right_btn.config(state='normal')
                
                self.light_off_btn.config(state='normal')
                self.light_ext_btn.config(state='normal')
                self.light_int_btn.config(state='normal')
                
                print(f" Manual Speed Set: {speed} mph")
                speed_window.destroy()
            except ValueError:
                error_label.config(text=" Invalid! Enter a number")
                speed_entry.delete(0, tk.END)
                speed_entry.focus()
        
        def cancel():
            self.mode_var.set("Auto")
            self.controller.set_automatic_mode()
            self.status_bar.config(text=" Cancelled - Automatic Mode", 
                                 fg='#00ff00', bg='#2d2d2d')
            
            self.door_closed_btn.config(state='disabled')
            self.door_left_btn.config(state='disabled')
            self.door_right_btn.config(state='disabled')
            
            self.light_off_btn.config(state='disabled')
            self.light_ext_btn.config(state='disabled')
            self.light_int_btn.config(state='disabled')
            
            speed_window.destroy()
        
        tk.Button(buttons_frame, text="Set Speed", command=set_speed, 
                 bg='#90ee90', font=('Arial', 13, 'bold'), width=12).pack(side=tk.LEFT, padx=5)
        
        tk.Button(buttons_frame, text="Cancel", command=cancel, 
                 bg='#ffcccc', font=('Arial', 13, 'bold'), width=12).pack(side=tk.LEFT, padx=5)
        
        speed_entry.bind('<Return>', lambda e: set_speed())
    
    def on_emergency_brake(self):
        """Emergency Brake clicked"""
        if not self.controller.emergency_brake_active:
            self.controller.activate_emergency_brake()
            self.ebrake_btn.config(bg='#8b0000', fg='white', 
                                  text="⚠️ E-BRAKE ACTIVE - CLICK TO RELEASE ⚠️")
            self.status_bar.config(text="⚠️ EMERGENCY BRAKE ACTIVATED ⚠️", 
                                 fg='white', bg='red')
        else:
            self.controller.release_emergency_brake()
            self.ebrake_btn.config(bg='#ffb3ba', fg='#8b0000', text="Emergency Brake")
            self.status_bar.config(text="✓ Emergency Brake Released", 
                                 fg='#00ff00', bg='#2d2d2d')
    
    def on_brake_toggle(self):
        """Service Brake toggled"""
        self.controller.service_brake_active = (self.brake_var.get() == 1)
        
        if self.controller.service_brake_active:
            self.brake_toggle.config(bg='#ff4444')
            self.status_bar.config(text="🛑 Service Brake Applied", fg='yellow', bg='#2d2d2d')
        else:
            self.brake_toggle.config(bg='#808080')
    
    def on_door_change(self):
        """Door selection changed"""
        if not self.controller.automatic_mode:
            door = self.door_var.get()
            door_code = {"Closed": 0, "Left": 2, "Right": 1}
            self.controller.set_doors(door_code.get(door, 0))
        else:
            self.door_var.set("Closed")
            self.status_bar.config(text="⚠️ Cannot control doors in Auto mode!", 
                                 fg='red', bg='#2d2d2d')
    
    def on_light_change(self):
        """Light selection changed"""
        if not self.controller.automatic_mode:
            light = self.light_var.get()
            self.controller.set_lights(light)
        else:
            self.light_var.set("Off")
            self.status_bar.config(text="⚠️ Cannot control lights in Auto mode!", 
                                 fg='red', bg='#2d2d2d')
    
    def on_kp_set(self):
        """Set Kp value"""
        try:
            kp = float(self.kp_entry.get())
            self.controller.kp = kp
            self.status_bar.config(text=f"✓ Kp updated: {kp}", fg='#00ff00', bg='#2d2d2d')
            print(f"✓ Kp = {kp}")
        except ValueError:
            self.status_bar.config(text="❌ Invalid Kp value", fg='red', bg='#2d2d2d')
    
    def on_ki_set(self):
        """Set Ki value"""
        try:
            ki = float(self.ki_entry.get())
            self.controller.ki = ki
            self.status_bar.config(text=f"✓ Ki updated: {ki}", fg='#00ff00', bg='#2d2d2d')
            print(f"✓ Ki = {ki}")
        except ValueError:
            self.status_bar.config(text="❌ Invalid Ki value", fg='red', bg='#2d2d2d')
    
    def on_cmd_speed_set(self):
        """Set commanded speed"""
        try:
            speed = float(self.cmd_speed_entry.get())
            self.controller.commanded_speed = speed
            self.status_bar.config(text=f"✓ CTC Command: {speed} mph", fg='#00ff00', bg='#2d2d2d')
            print(f"✓ Commanded Speed = {speed} mph")
        except ValueError:
            self.status_bar.config(text="❌ Invalid value", fg='red', bg='#2d2d2d')
    
    def on_auth_set(self):
        """Set authority"""
        try:
            auth = float(self.auth_entry.get())
            self.controller.authority = auth
            self.status_bar.config(text=f"✓ Authority: {auth}m", fg='#00ff00', bg='#2d2d2d')
            print(f"✓ Authority = {auth} meters")
        except ValueError:
            self.status_bar.config(text="❌ Invalid value", fg='red', bg='#2d2d2d')
    
    def on_passengers_set(self):
        """Set passenger count"""
        try:
            passengers = int(self.passengers_entry.get())
            self.controller.passengers = passengers
            print(f"✓ Passengers = {passengers}")
        except ValueError:
            self.status_bar.config(text="❌ Invalid value", fg='red', bg='#2d2d2d')
    
    def on_current_speed_set(self):
        """Set current speed"""
        try:
            speed = float(self.current_speed_entry.get())
            self.controller.current_speed = speed
            print(f"✓ Current Speed = {speed} mph")
        except ValueError:
            self.status_bar.config(text="❌ Invalid value", fg='red', bg='#2d2d2d')
    
    def simulate_failure(self, failure_type):
        """Simulate failures"""
        if failure_type == 'power':
            self.controller.handle_power_failure(not self.controller.power_failure)
            if self.controller.power_failure:
                self.power_fail_btn.config(bg='red', fg='white')
            else:
                self.power_fail_btn.config(bg='orange', fg='black')
        
        elif failure_type == 'brake':
            self.controller.handle_brake_failure(not self.controller.brake_failure)
            if self.controller.brake_failure:
                self.brake_fail_btn.config(bg='red', fg='white')
            else:
                self.brake_fail_btn.config(bg='orange', fg='black')
        
        elif failure_type == 'signal':
            self.controller.handle_signal_failure(not self.controller.signal_pickup_failure)
            if self.controller.signal_pickup_failure:
                self.signal_fail_btn.config(bg='red', fg='white')
            else:
                self.signal_fail_btn.config(bg='orange', fg='black')
    
    def start_simulation(self):
        """Start/stop simulation"""
        self.simulation_running = not self.simulation_running
        
        if self.simulation_running:
            self.sim_btn.config(text="⏸ STOP SIMULATION", bg='#ffcccc')
            self.status_bar.config(text="▶ Simulation Running...", fg='yellow', bg='#2d2d2d')
            print("▶ Simulation Started")
            self.simulate_train()
        else:
            self.sim_btn.config(text="▶ START SIMULATION", bg='#90EE90')
            self.status_bar.config(text="⏸ Simulation Paused", fg='#00ff00', bg='#2d2d2d')
            print("⏸ Simulation Stopped")
    
    def simulate_train(self):
        """Simulate train movement"""
        if not self.simulation_running:
            return
        
        if (self.controller.current_speed < self.controller.commanded_speed and 
            not self.controller.emergency_brake_active and
            not self.controller.service_brake_active and
            self.controller.authority > 0):
            self.controller.current_speed += 0.5
        
        if self.controller.emergency_brake_active and self.controller.current_speed > 0:
            self.controller.current_speed -= 2.0
            if self.controller.current_speed < 0:
                self.controller.current_speed = 0
        elif self.controller.service_brake_active and self.controller.current_speed > 0:
            self.controller.current_speed -= 1.0
            if self.controller.current_speed < 0:
                self.controller.current_speed = 0
        
        self.controller.update(0.1)
        self.root.after(100, self.simulate_train)
    
    
    
    # DISPLAY UPDATE LOOP
    
    
    def start_update_loop(self):
        """Start the display update loop"""
        self.update_display()
    
    def update_display(self):
        """Update all displays"""
        
        self.speed_display.config(text=f"{self.controller.current_speed:.1f} mph")
        
        auth_miles = self.controller.authority * 0.000621371
        self.authority_display.config(text=f"{auth_miles:.3f} miles")
        
        self.passengers_display.config(text=str(self.controller.passengers))
        
        self.station_display.config(text=self.controller.next_station)
        
        if self.controller.emergency_brake_active and self.ebrake_btn.cget('bg') == '#ffb3ba':
            self.ebrake_btn.config(bg='#8b0000', fg='white', 
                                  text="⚠️ E-BRAKE ACTIVE - CLICK TO RELEASE ⚠️")
        
        if self.controller.service_brake_active and self.brake_var.get() == 0:
            self.brake_var.set(1)
            self.brake_toggle.config(bg='#ff4444')
        
        self.root.after(100, self.update_display)
    
    
   
    # RUN
   
    
    def run(self):
        """Start the GUI"""
        print("\n" + "="*70)
        print("TRAIN CONTROLLER - Starting...")
        print("="*70)
        print("\n✓ Controller initialized")
        print("✓ UI ready")
        print("\n📖 Instructions:")
        print("  1. Click '📊 Open Test UI' to see all values in real-time")
        print("  2. Use Testing Controls to set Commanded Speed and Authority")
        print("  3. Click START SIMULATION to see train move")
        print("  4. Watch Test UI window - all values update automatically!")
        print("\n" + "="*70 + "\n")
        
        self.root.mainloop()
        
        print("\n✓ Train Controller closed.\n")



# MAIN PROGRAM


if __name__ == "__main__":
    app = TrainControllerUI()
    app.run()