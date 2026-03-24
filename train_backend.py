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

        # traction force: f = p/v 
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

        if self.trackDecelerationLimitKmh2 > 0.0:
            decelCapMps2 = self.trackDecelerationLimitKmh2 / 12960.0
        
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

        # v_n = v_{n-1} + (dt/2) * (a_n + a_{n-1})
        newVelocityMps = self._prevVelocityMps + (dt / 2.0) * (newAccelMps2 + self._prevAccelMps2)
        newVelocityMps = max(0.0, newVelocityMps)

        # position integration
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
    def displayCurrentAccelFps2(self):        
        return ms2ToFps2(self.currentAccelMps2)
    def displayRequestedTractionPowerKw(self): 
        return self.requestedTractionPowerW / 1000.0


#current integration for train model and controller to check functionality.
# class TrainSystem:
#     def __init__(self, model=None, controller=None):
#         self.model = model or TrainModel()
#
#         if controller is None:
#             from train_controller_backend import TrainController as _TrainController
#             controller = _TrainController(train_id=1)
#
#         self.controller = controller
#         self._authority_pushed_to_controller_m = None
#         self._prev_faults = {"pwr": False, "brk": False, "sig": False}
#
#     def _sync_faults(self):
#         m = self.model
#         c = self.controller
#
#         pwr = bool(m.hasPowerFault)
#         brk = bool(m.hasBrakeFault)
#         sig = bool(m.hasEngineFault)
#
#         c.fault_power = pwr
#         c.fault_brake = brk
#         c.fault_signal = sig
#
#         if (pwr and not self._prev_faults["pwr"]) or (brk and not self._prev_faults["brk"]) or (sig and not self._prev_faults["sig"]):
#             try:
#                 c.emergency_brake = True
#             except Exception:
#                 pass
#         self._prev_faults = {"pwr": pwr, "brk": brk, "sig": sig}
#
#     def _sync_authority_controller_to_model_if_user_changed(self):
#         self._push_model_authority_to_controller()
#
#     def _push_model_authority_to_controller(self):
#         c = self.controller
#         m = self.model
#         authority_m = max(0.0, m.commandedAuthorityKm * 1000.0)
#         c.authority = authority_m
#         self._authority_pushed_to_controller_m = authority_m
#
#     def tick(self, dt=samplePeriodSec):
#         m = self.model
#         c = self.controller
#
#         self._sync_authority_controller_to_model_if_user_changed()
#
#         c.current_speed = kmhToMph(m.currentSpeedKmh)
#         c.commanded_speed = kmhToMph(m.commandedSpeedKmh)
#         c.speed_limit = kmhToMph(m.speedLimitKmh)
#         c.distance_travelled_km = m.distanceTraveledKm
#
#         self._sync_faults()
#
#         passenger_ebrake = bool(m.isPassengerEmergencyBrakeOn)
#         if passenger_ebrake:
#             c.emergency_brake = True
#
#         c.monitor()
#         c.calc_power(dt)
#
#         combined_ebrake = bool(getattr(c, "emergency_brake", False))
#         c.emergency_brake = combined_ebrake
#         m.isEmergencyBrakeOn = combined_ebrake
#
#         manual_svc = bool(getattr(c, "service_brake", False))
#         auto_svc = bool(getattr(c, "auto_service_brake", False))
#         m.isServiceBrakeOn = (manual_svc or auto_svc) and not m.isEmergencyBrakeOn
#
#         m.areExternalLightsOn = bool(getattr(c, "headlights", False))
#         m.areInternalLightsOn = bool(getattr(c, "interior_lights", 0))
#
#         doors_state = int(getattr(c, "doors_state", 0))
#         m.isRightDoorOpen = doors_state in (1, 3)
#         m.isLeftDoorOpen = doors_state in (2, 3)
#
#         m.cabinTemperatureC = fToC(float(getattr(c, "cabin_temp", cToF(m.cabinTemperatureC))))
#
#         m.onboardPassengers = int(getattr(c, "passengers", m.onboardPassengers))
#         m.boardingPassengerCount = 0
#
#         beacon_str = (m.beaconData or "").strip()
#         c.next_station = beacon_str
#         m.approachingStation = beacon_str
#
#         m.requestedTractionPowerW = float(getattr(c, "power_output", 0.0))
#
#         m.tick()
#
#         self._push_model_authority_to_controller()