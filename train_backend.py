# ai was used to help with code development logic and structure

import math

#pulled from provided specsheet
samplePeriodSec             = 0.1      # 100 ms tick to update 
emptyCarMassKg              = 40900.0  # empty car mass 
maxTractionPowerW           = 120000.0 # max power avaliable 
gravityMps2                 = 9.81
maxServiceBrakeDecelMps2    = 1.2      # service brake 
maxEmergencyBrakeDecelMps2  = 2.73     # emergency brake 

# unit conversions for frontend display
def kmhToMph(kmh):  
    return kmh * 0.621371
def mphToKmh(mph):  
    return mph / 0.621371
def kmToMiles(km):  
    return km * 0.621371
def cToF(c):        
    return c * 9.0 / 5.0 + 32.0
def fToC(f):
    return (f - 32.0) * 5.0 / 9.0
def ms2ToFps2(a):   
    return a * 3.28084


class TrainModel:

    def __init__(self):

        # inputs from track model
        self.commandedSpeedKmh          = 70.0
        self.speedLimitKmh              = 70.0
        self.commandedAuthorityKm       = 0.0
        self.beaconData                 = ""
        self.trackGradePercent          = 0.0
        self.trackDecelerationLimitKmh2 = 0.0
        self.trackAccelerationLimitKmh2 = 0.0
        self.isRailBroken               = False
        self.isTrackCircuitFailed       = False
        self.isTrackPowerLost           = False
        self.boardingPassengerCount     = 0

        # inputs from train controller
        self.cabinTemperatureC       = 20.0
        self.isServiceBrakeOn        = False
        self.isEmergencyBrakeOn      = False
        self.areExternalLightsOn     = False
        self.areInternalLightsOn     = False
        self.isRightDoorOpen         = False
        self.isLeftDoorOpen          = False
        self.requestedTractionPowerW = 0.0

        # inputs from passenger/ui
        self.isPassengerEmergencyBrakeOn = False

        # inputs from murphy/ui
        self.hasEngineFault = False
        self.hasBrakeFault  = False
        self.hasPowerFault  = False

        # outputs / internal state
        self.currentSpeedKmh    = 0.0
        self.currentAccelMps2   = 0.0
        self.distanceTraveledKm = 0.0
        self.elapsedTimeSec     = 0.0
        self.onboardPassengers  = 0
        self.approachingStation = ""

        # previous step value needed for trapezoidal integration
        self._prevVelocityMps = 0.0
        self._prevAccelMps2   = 0.0

    def tick(self):
        # helps simulate time so the values change throughout
        # backend runs every .1 seconds
        dt          = samplePeriodSec 
        velocityMps = self.currentSpeedKmh / 3.6

        # determine which brake mode is active
        emergencyBrakeActive = (self.isEmergencyBrakeOn or self.isPassengerEmergencyBrakeOn)
        serviceBrakeActive = self.isServiceBrakeOn and not emergencyBrakeActive

        # traction force: F = P/v 
        if emergencyBrakeActive:
            tractionForceN = 0.0 #train will come to stop if there is a fualt
        else:
            safeVelocityMps = max(velocityMps, 0.1)  # avoid divide by zero at standstill, current fix dont know if i need to change later
            tractionForceN  = self.requestedTractionPowerW / safeVelocityMps

        # brake force opposes motion and brings the train to a stop
        brakeForceN = 0.0
        if emergencyBrakeActive:
            brakeForceN = emptyCarMassKg * maxEmergencyBrakeDecelMps2 
        elif serviceBrakeActive:
            brakeForceN = emptyCarMassKg * maxServiceBrakeDecelMps2 
        
        #ai was used to help generate tilt force dynamics
        gradeAngleRad = math.atan(self.trackGradePercent / 100.0) #rise/run * 100 is grade percent so div 100 and arc tan gives radians
        gradeForceN   = -emptyCarMassKg * gravityMps2 * math.sin(gradeAngleRad) #the radians then are converted to degree so they can be used in physics formula

        # net force and raw acceleration
        netForceN    = tractionForceN - brakeForceN + gradeForceN
        rawAccelMps2 = netForceN / emptyCarMassKg

        # apply track model acceleration and deceleration limits
        if self.trackAccelerationLimitKmh2 > 0.0:
            accelCapMps2 = self.trackAccelerationLimitKmh2 / 12960.0
        else:
            accelCapMps2 = 1.5

        if self.trackDecelerationLimitKmh2 > 0.0:
            decelCapMps2 = self.trackDecelerationLimitKmh2 / 12960.0
        else:
            decelCapMps2 = 1.5
        
        #will never exceed the cap of accel
        if rawAccelMps2 > accelCapMps2:
            newAccelMps2 = accelCapMps2
        elif rawAccelMps2 < -decelCapMps2:
            newAccelMps2 = -decelCapMps2
        else :
            newAccelMps2 = rawAccelMps2


        # a stopped train cannot decelerate further
        if self.currentSpeedKmh <= 0.0 and newAccelMps2 < 0.0:
            newAccelMps2 = 0.0

        self.currentAccelMps2 = newAccelMps2

        # trapezoidal velocity integration: v_n = v_{n-1} + (dt/2) * (a_n + a_{n-1})
        newVelocityMps = self._prevVelocityMps + (dt / 2.0) * (newAccelMps2 + self._prevAccelMps2)
        newVelocityMps = max(0.0, newVelocityMps)

        # trapezoidal position integration
        distanceDeltaM          = (dt / 2.0) * (newVelocityMps + self._prevVelocityMps)
        self.distanceTraveledKm += distanceDeltaM / 1000.0
        self.commandedAuthorityKm = max(0.0, self.commandedAuthorityKm - distanceDeltaM / 1000.0)

        # update state for this tick
        self.currentSpeedKmh        = newVelocityMps * 3.6
        self.onboardPassengers     += self.boardingPassengerCount
        self.boardingPassengerCount  = 0
        self.elapsedTimeSec        += dt
        self._prevVelocityMps       = newVelocityMps
        self._prevAccelMps2         = newAccelMps2

    # outputs to train controller
    def getCurrentSpeedKmh(self):         
        return self.currentSpeedKmh
    def getCurrentVelocityKmh(self):      
        return self.currentSpeedKmh    # to track model
    def getCommandedSpeedKmh(self):       
        return self.commandedSpeedKmh
    def getCommandedAuthorityKm(self):    
        return self.commandedAuthorityKm
    def getDistanceTraveledKm(self):      
        return self.distanceTraveledKm
    def getOnboardPassengers(self):       
        return self.onboardPassengers
    def getApproachingStation(self):      
        return self.approachingStation
    def getEngineFaultStatus(self):       
        return self.hasEngineFault
    def getBrakeFaultStatus(self):        
        return self.hasBrakeFault
    def getPowerFaultStatus(self):        
        return self.hasPowerFault
    def getTrackPowerFaultStatus(self):   
        return self.isTrackPowerLost
    def getTrackCircuitFaultStatus(self): 
        return self.isTrackCircuitFailed
    def getEmergencyBrakeStatus(self):
        return (self.isEmergencyBrakeOn or self.isPassengerEmergencyBrakeOn
                or self.hasEngineFault or self.hasPowerFault or self.isTrackPowerLost)

    # display helpers for frontend (american units)
    def displayCurrentSpeedMph(self):          
        return kmhToMph(self.currentSpeedKmh)
    def displayCommandedSpeedMph(self):        
        return kmhToMph(self.commandedSpeedKmh)
    def displaySpeedLimitMph(self):            
        return kmhToMph(self.speedLimitKmh)
    def displayDistanceTraveledMiles(self):    
        return kmToMiles(self.distanceTraveledKm)
    def displayRemainingAuthorityMiles(self):  
        return kmToMiles(self.commandedAuthorityKm)
    def displayCabinTemperatureF(self):        
        return cToF(self.cabinTemperatureC)
    def displayCurrentAccelMps2(self):        
        return self.currentAccelMps2
    def displayCurrentAccelFps2(self):        
        return ms2ToFps2(self.currentAccelMps2)
    def displayRequestedTractionPowerKw(self): 
        return self.requestedTractionPowerW / 1000.0


class TrainSystem:
    """
    Lightweight integration layer that keeps the Train Controller and Train Model
    in sync and advances the combined simulation on a single 100 ms tick.

    This intentionally avoids any UI dependencies so both the PyQt Train Model UI
    and the Tkinter Train Controller UI can share the same backend objects.
    """

    def __init__(self, model=None, controller=None):
        self.model = model or TrainModel()

        if controller is None:
            # Lazy import to avoid forcing the controller UI to import this module.
            from train_controller_backend import TrainController as _TrainController
            controller = _TrainController(train_id=1)

        self.controller = controller
        self._authority_pushed_to_controller_m = None
        self._prev_faults = {"pwr": False, "brk": False, "sig": False}

    def _sync_faults(self):
        m = self.model
        c = self.controller

        # In integrated mode, treat the Train Model's fault flags as the
        # source of truth and mirror them onto the controller.
        pwr = bool(m.hasPowerFault)
        brk = bool(m.hasBrakeFault)
        sig = bool(m.hasEngineFault)

        c.fault_power = pwr
        c.fault_brake = brk
        c.fault_signal = sig

        # If any fault transitions False -> True, activate controller e-brake once.
        # This still allows the driver to release it manually afterward.
        if (pwr and not self._prev_faults["pwr"]) or (brk and not self._prev_faults["brk"]) or (sig and not self._prev_faults["sig"]):
            try:
                c.emergency_brake = True
            except Exception:
                pass
        self._prev_faults = {"pwr": pwr, "brk": brk, "sig": sig}

    def _sync_authority_controller_to_model_if_user_changed(self):
        c = self.controller
        m = self.model

        if self._authority_pushed_to_controller_m is None:
            # First tick: treat controller's authority as the initial source.
            m.commandedAuthorityKm = max(0.0, float(getattr(c, "authority", 0.0)) / 1000.0)
            return

        current_m = float(getattr(c, "authority", 0.0))
        if abs(current_m - self._authority_pushed_to_controller_m) > 1e-6:
            m.commandedAuthorityKm = max(0.0, current_m / 1000.0)

    def _push_model_authority_to_controller(self):
        c = self.controller
        m = self.model
        authority_m = max(0.0, m.commandedAuthorityKm * 1000.0)
        c.authority = authority_m
        self._authority_pushed_to_controller_m = authority_m

    def tick(self, dt=samplePeriodSec):
        m = self.model
        c = self.controller

        # Allow controller UI to override authority when the user edits it.
        self._sync_authority_controller_to_model_if_user_changed()

        # Train Model → Train Controller (measured speed and commanded speed
        # for the control loop). Commanded speed is the speed the controller
        # must not exceed in AUTO mode.
        c.current_speed = kmhToMph(m.currentSpeedKmh)
        c.commanded_speed = kmhToMph(m.commandedSpeedKmh)

        # Two-way fault sync so either UI can toggle them.
        self._sync_faults()

        # Passenger emergency brake from the Train Model UI feeds into the
        # controller's emergency brake state, but the controller remains the
        # single source of truth for the active emergency brake command.
        passenger_ebrake = bool(m.isPassengerEmergencyBrakeOn)
        if passenger_ebrake:
            c.emergency_brake = True

        # Controller update (no internal authority integration here; TrainModel owns authority).
        c.monitor()
        c.calc_power(dt)

        # Consolidated emergency brake state used by BOTH controller and model.
        combined_ebrake = bool(getattr(c, "emergency_brake", False))
        c.emergency_brake = combined_ebrake
        m.isEmergencyBrakeOn = combined_ebrake

        # Service brake only applies when e-brake is not active. Combine the
        # manual service brake with any auto-applied brake in the controller.
        manual_svc = bool(getattr(c, "service_brake", False))
        auto_svc = bool(getattr(c, "auto_service_brake", False))
        m.isServiceBrakeOn = (manual_svc or auto_svc) and not m.isEmergencyBrakeOn

        # Lights
        m.areExternalLightsOn = bool(getattr(c, "headlights", False))
        m.areInternalLightsOn = bool(getattr(c, "interior_lights", 0))

        # Doors (0 closed, 1 right, 2 left, 3 both)
        doors_state = int(getattr(c, "doors_state", 0))
        m.isRightDoorOpen = doors_state in (1, 3)
        m.isLeftDoorOpen = doors_state in (2, 3)

        # Cabin temp (controller stores °F)
        m.cabinTemperatureC = fToC(float(getattr(c, "cabin_temp", cToF(m.cabinTemperatureC))))

        # Passengers / station (simple mapping for now)
        m.onboardPassengers = int(getattr(c, "passengers", m.onboardPassengers))
        m.boardingPassengerCount = 0

        # Beacon data flows: Train Model Test UI → Train Model.beaconData →
        # Train Controller.next_station → Train Model.approachingStation.
        # Always mirror the beacon string (including clearing it) so the
        # controller UI and model UI stay in sync.
        beacon_str = (m.beaconData or "").strip()
        c.next_station = beacon_str
        m.approachingStation = beacon_str

        # Traction power command
        m.requestedTractionPowerW = float(getattr(c, "power_output", 0.0))

        # Advance physics
        m.tick()

        # Push derived authority back to controller so its UI stays aligned.
        self._push_model_authority_to_controller()