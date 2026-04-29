# ECE-1140
Installation Manual — Train Controller 

ECE 1140 | Locomotive Legends (Omar Morsy) | v1.0 | April 28, 2026 
1. Overview 

The Train Controller is a single Python class (TrainController) in train_controller_backend.py. It handles traction power, speed enforcement, brake logic, fault detection, doors, lights, and cabin temperature. It has no GUI of its own. It is driven by the Train Model and outputs commands back to it. 

 

2. Requirements 

Python: 3.10 or later Dependencies: none beyond the Python standard library (math, sys) OS: Windows 10/11, macOS 12+ (I do not Advice using MAC because of Tkinter limitations), or Ubuntu 20.04+ 

The Train Controller backend itself requires no pip packages. PyQt6 and Pillow are only needed if you are also running the Train Model GUI (train_frontend_main.py). 

 

3. Files Needed 

Place these two files in the same folder: 

train_controller_backend.py    ← the controller (required) 
test_train_controller.py       ← unit test suite (optional but recommended) 

If running with the full Train Model: 

train_backend.py               ← wires the controller to the physics model 
train_frontend_main.py         ← PyQt6 GUI (requires PyQt6>=6.5.0) 

If running the full system add all the files to the same folder and run launch_system.py 

4. Installation Steps 

Step 1: Get Python 3.10+ 

bash 

# Verify your version 
python --version        # Windows 
python3 --version       # macOS / Linux 

Download from https://python.org if needed. On Windows, check "Add Python to PATH" during install. 

 

Step 2: Copy the files 

Download or clone the repository and place train_controller_backend.py and TrainController.py (and optionally test_train_controller.py) into your working folder. No build step, no compilation. It is plain Python. 

 

Step 3;  Verify with the test suite 

bash 

cd <your_folder> 
python test_train_controller.py 

Expected output: 

Ran 44 tests in 0.xxx s 
 
OK 
 
============================================================ 
  RESULTS:  44/44 passed  —  ALL PASSED 
============================================================ 

If all 44 pass, the controller is correctly installed. 

 

Step 4: (Optional) Install GUI dependencies 

Only needed if you want the Train Model display window: 

bash 

pip install PyQt6>=6.5.0 Pillow>=9.0.0 
# or simply: 
pip install -r requirements.txt 

 

5. Basic Usage 

python 

from train_controller_backend import TrainController 
 
ctrl = TrainController(train_id=1) 
 
# Feed values from the Track/Train Model 
ctrl.commanded_speed = 40.0   # mph 
ctrl.speed_limit     = 70.0   # mph 
ctrl.authority       = 500.0  # metres 
ctrl.current_speed   = 0.0    # mph 
 
# Run one control tick (call every 100 ms) 
ctrl.monitor() 
ctrl.calc_power(dt=0.1) 
 
print(ctrl.power_output)       # watts 
print(ctrl.emergency_brake)    # True/False 
print(ctrl.auto_service_brake) # True/False 

 

6. Key Parameters & Defaults 

Parameter 

Default 

Description 

kp 

10.0 

Proportional gain (manual PI mode) 

ki 

8000.0 

Integral gain (manual PI mode) 

MAX_POWER 

120,000 W 

Traction power ceiling 

speed_limit 

70.0 mph 

Track speed limit 

authority 

500.0 m 

Remaining travel permission 

cabin_temp 

70 °F 

Cabin temperature 

automatic_mode 

True 

Auto vs. manual control 

 

7. Switching Modes 

python 

ctrl.set_auto()          # automatic mode (uses commanded_speed) 
ctrl.set_manual(35.0)    # manual mode, target = 35 mph 

 

8. Fault Injection 

python 

ctrl.set_power_fault(True)    # triggers emergency brake 
ctrl.set_brake_fault(True)    # triggers emergency brake 
ctrl.set_signal_fault(True)   # triggers emergency brake 
ctrl.release_ebrake()         # clears the latch manually 

 9. Troubleshooting 

ModuleNotFoundError: No module named 'train_controller_backend' → Run Python from the same folder as the file, or add that folder to your PYTHONPATH. 

Tests fail immediately → Confirm you are using Python 3.10+. Run python --version. 

qt.qpa.plugin error when launching the GUI → Run pip install pyqt6 --force-reinstall 

power_output is always 0 → Check that authority > 0, commanded_speed > 0, and no fault flags are set. 
