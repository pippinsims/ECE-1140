Installation Manual — Train Model 

ECE 1140  |  Locomotive Legends  |  Shokhrukh Kholmatjonov  |  v1.0  |  April 28, 2026 

 

1. Overview 

The Train Model is a single Python class (TrainModel) defined in train_backend.py. It simulates the physics of a train car — traction force, braking, grade dynamics, and passenger exchange — using a fixed 100 ms sample period. It has no GUI of its own. It receives inputs from the Track Model and the Train Controller, and exposes outputs back to both. 

 

An optional TrainSystem class (also in train_backend.py) wires the TrainModel together with a TrainController instance and handles the correct data-flow sequence each tick. 

 

2. Requirements 

Python:  3.10 or later 

Dependencies:  None beyond the Python standard library (math, random) 

OS:  Windows 10/11, macOS 12+, or Ubuntu 20.04+ 

Note: macOS is not recommended due to Tkinter limitations. The Train Model backend requires no pip packages. PyQt6 and Pillow are only needed if running the Train Model GUI (train_frontend_main.py). 

 

3. Files Needed 

Place all files in the same folder: 

train_backend.py              ← the physics model (required) 

train_frontend_test.py        ← unit test suite (optional but recommended) 

  

If running with the full Train System: 

train_controller_backend.py   ← controller logic 

train_frontend_main.py        ← PyQt6 GUI (requires PyQt6>=6.5.0) 

launch_system.py              ← entry point for the integrated system 

 

4. Installation Steps 

Step 1: Get Python 3.10+ 

# Verify your version 

python --version    # Windows 

python3 --version   # macOS / Linux 

 

Download from https://python.org if needed. On Windows, check "Add Python to PATH" during install. 

 

Step 2: Copy the Files 

Download or clone the repository and place train_backend.py (and optionally train_frontend_test.py) into your working folder. No build step, no compilation — it is plain Python. 

 

Step 3: Verify with the Test Suite 

cd <your_folder> 

python train_frontend_test.py 

 

Expected output: 

Ran N tests in 0.xxx s 

OK 

============================================================ 

 RESULTS: N/N passed — ALL PASSED 

============================================================ 

 

If all tests pass, the model is correctly installed. 

 

Step 4: (Optional) Install GUI Dependencies 

Only needed if you want the Train Model display window: 

pip install PyQt6>=6.5.0 Pillow>=9.0.0 

# or simply: 

pip install -r requirements.txt 

 

5. Basic Usage 

from train_backend import TrainModel 

  

model = TrainModel() 

  

# Feed values from the Track Model 

model.commandedSpeedKmh    = 60.0   # km/h 

model.speedLimitKmh        = 70.0   # km/h 

model.commandedAuthorityKm = 2.0    # km 

model.trackGradePercent    = 1.5    # % grade 

  

# Feed values from the Train Controller 

model.requestedTractionPowerW = 80000.0  # watts 

model.isServiceBrakeOn        = False 

model.isEmergencyBrakeOn      = False 

  

# Run one physics tick (call every 100 ms) 

model.tick() 

  

print(model.getCurrentSpeedKmh())         # current speed 

print(model.displayCurrentSpeedMph())     # same value in mph 

print(model.getDistanceTraveledKm())      # odometer 

print(model.getOnboardPassengers())       # passenger count 

 

6. Key Parameters & Defaults 

Parameter 

Default 

Description 

commandedSpeedKmh 

0.0 km/h 

Speed commanded by the Track Model 

speedLimitKmh 

70.0 km/h 

Track speed limit 

commandedAuthorityKm 

0.0 km 

Remaining travel permission 

trackGradePercent 

0.0 % 

Track incline (rise / run x 100) 

cabinTemperatureC 

20.0 C (68 F) 

Cabin temperature 

requestedTractionPowerW 

0.0 W 

Power command from controller 

onboardPassengers 

0 

Current passenger count 

samplePeriodSec 

0.1 s 

Physics tick interval 

emptyCarMassKg 

40,900 kg 

Empty car mass 

maxTractionPowerW 

120,000 W 

Traction power ceiling 

maxServiceBrakeDecelMps2 

1.2 m/s^2 

Service brake deceleration cap 

maxEmergencyBrakeDecelMps2 

2.73 m/s^2 

Emergency brake deceleration cap 

 

7. Brake & Fault Modes 

# Service brake 

model.isServiceBrakeOn = True 

  

# Emergency brake (overrides service brake) 

model.isEmergencyBrakeOn = True 

  

# Passenger pull-cord emergency brake 

model.isPassengerEmergencyBrakeOn = True 

  

# Fault injection (each also triggers emergency brake) 

model.hasEngineFault = True 

model.hasBrakeFault  = True 

model.hasPowerFault  = True 

  

# Read combined emergency brake status 

print(model.getEmergencyBrakeStatus())   # True if any brake/fault is active 

 

8. Display Helpers (American Units) 

The model exposes convenience methods that convert internal SI values to imperial units for frontend display: 

 

model.displayCurrentSpeedMph()          # km/h  → mph 

model.displayCommandedSpeedMph()        # km/h  → mph 

model.displaySpeedLimitMph()            # km/h  → mph 

model.displayDistanceTraveledMiles()    # km    → miles 

model.displayRemainingAuthorityMiles()  # km    → miles 

model.displayCabinTemperatureF()        # C     → F 

model.displayCurrentAccelFps2()         # m/s^2 → ft/s^2 

model.displayRequestedTractionPowerKw() # W     → kW 

 

9. Integrated System (TrainSystem) 

Use TrainSystem to run the model and controller together. It handles the correct data-flow sequence: Track Model → Train Model → Train Controller. 

 

from train_backend import TrainSystem 

  

system = TrainSystem()   # creates TrainModel + TrainController internally 

  

# Set track model inputs on system.model 

system.model.commandedSpeedKmh    = 50.0 

system.model.commandedAuthorityKm = 3.0 

  

# Run one integrated tick 

system.tick(dt=0.1) 

  

# Read outputs 

print(system.model.getCurrentSpeedKmh()) 

print(system.model.getOnboardPassengers()) 

 

10. Troubleshooting 

Symptom 

Fix 

ModuleNotFoundError: No module named 'train_backend' 

Run Python from the same folder as train_backend.py, or add that folder to PYTHONPATH. 

Tests fail immediately 

Confirm you are using Python 3.10+. Run: python --version 

qt.qpa.plugin error when launching GUI 

Run: pip install pyqt6 --force-reinstall 

currentSpeedKmh never increases 

Check that requestedTractionPowerW > 0, isEmergencyBrakeOn is False, commandedAuthorityKm > 0, and that tick() is called each step. 

Speed jumps unrealistically 

Set trackAccelerationLimitKmh2 and trackDecelerationLimitKmh2 to sensible values, or leave at 0.0 (uncapped). 

Passenger count does not change 

boardingPassengerCount must transition from 0 to a positive value to trigger a boarding event. The model resets it to 0 each tick — the Track Model must set it fresh each station stop. 

 

 

*AI was used to help create this document. 
