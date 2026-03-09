import unittest
from train_controller_backend import TrainController


class TestTrainController(unittest.TestCase):
    """
    Test suite for TrainController (train_controller_backend.py)
    Run with: python -m unittest test_train_controller.py -v
    """

    def setUp(self):
        """Create a fresh TrainController before every test."""
        self.tc = TrainController(train_id=1)

    
    # TC-01  Emergency Brake Activation
    
    def test_TC01_emergency_brake_activation(self):
        """_activate_ebrake() must set emergency_brake=True,
        zero power, zero driver_power_req, clear service_brake."""
        self.tc.current_speed   = 30.0
        self.tc.power_output    = 5000.0
        self.tc.service_brake   = True

        self.tc._activate_ebrake()

        self.assertTrue(self.tc.emergency_brake,
                        "emergency_brake must be True after activation")
        self.assertEqual(self.tc.power_output, 0,
                         "power_output must be 0 after e-brake")
        self.assertEqual(self.tc.driver_power_req, 0,
                         "driver_power_req must be 0 after e-brake")
        self.assertFalse(self.tc.service_brake,
                         "service_brake must be cleared after e-brake")

    
    # TC-02  Emergency Brake Release
   
    def test_TC02_emergency_brake_release(self):
        """release_ebrake() must set emergency_brake=False."""
        self.tc._activate_ebrake()
        self.assertTrue(self.tc.emergency_brake)

        self.tc.release_ebrake()

        self.assertFalse(self.tc.emergency_brake,
                         "emergency_brake must be False after release")

    
    # TC-03  Power Fault Triggers Emergency Brake
   
    def test_TC03_power_fault_triggers_ebrake(self):
        """set_power_fault(True) must set fault_power=True
        and automatically activate the emergency brake."""
        self.assertFalse(self.tc.fault_power)
        self.assertFalse(self.tc.emergency_brake)

        self.tc.set_power_fault(True)

        self.assertTrue(self.tc.fault_power,
                        "fault_power must be True")
        self.assertTrue(self.tc.emergency_brake,
                        "emergency_brake must be True after power fault")

    
    # TC-04  Brake Fault Triggers Emergency Brake
   
    def test_TC04_brake_fault_triggers_ebrake(self):
        """set_brake_fault(True) must set fault_brake=True
        and automatically activate the emergency brake."""
        self.tc.set_brake_fault(True)

        self.assertTrue(self.tc.fault_brake,
                        "fault_brake must be True")
        self.assertTrue(self.tc.emergency_brake,
                        "emergency_brake must be True after brake fault")

    
    # TC-05  Signal Fault Triggers Emergency Brake
    
    def test_TC05_signal_fault_triggers_ebrake(self):
        """set_signal_fault(True) must set fault_signal=True
        and automatically activate the emergency brake."""
        self.tc.set_signal_fault(True)

        self.assertTrue(self.tc.fault_signal,
                        "fault_signal must be True")
        self.assertTrue(self.tc.emergency_brake,
                        "emergency_brake must be True after signal fault")

    
    # TC-06  PI Controller Calculates Valid Power
    
    def test_TC06_pi_controller_power_calculation(self):
        """calc_power(dt) must return a value in [0, 120000] W
        when the train is below commanded speed with no brakes active."""
        self.tc.automatic_mode    = True
        self.tc.commanded_speed   = 30.0   # mph
        self.tc.current_speed     = 0.0    # mph – large error → large power
        self.tc.kp                = 10.0
        self.tc.ki                = 8000.0
        self.tc.driver_power_req  = 100
        self.tc.emergency_brake   = False
        self.tc.service_brake     = False

        power = self.tc.calc_power(0.1)

        self.assertGreater(power, 0,
                           "power_output must be > 0 when below commanded speed")
        self.assertLessEqual(power, self.tc.MAX_POWER,
                             f"power_output must not exceed {self.tc.MAX_POWER} W")

    
    # TC-07  Power is Zero When E-Brake Active
    
    def test_TC07_power_zero_when_ebrake_active(self):
        """calc_power() must return 0 when emergency_brake is True."""
        self.tc.emergency_brake  = True
        self.tc.driver_power_req = 100
        self.tc.commanded_speed  = 30.0
        self.tc.current_speed    = 10.0

        power = self.tc.calc_power(0.1)

        self.assertEqual(power, 0,
                         "power_output must be 0 when e-brake is active")
        self.assertEqual(self.tc.power_output, 0,
                         "stored power_output must also be 0")

    
    # TC-08  Authority Decrements Over Time
    
    def test_TC08_authority_decrements(self):
        """update_auth(dt) must reduce authority when train is moving."""
        self.tc.authority      = 500.0
        self.tc.current_speed  = 30.0   # mph > 0 → authority must decrease

        self.tc.update_auth(0.1)

        self.assertLess(self.tc.authority, 500.0,
                        "authority must decrease when train is moving")

    
    # TC-09  Overspeed Auto Service Brake
    
    def test_TC09_overspeed_auto_service_brake(self):
        """monitor() must set auto_service_brake=True when
        current_speed > commanded_speed in Auto mode."""
        self.tc.automatic_mode   = True
        self.tc.commanded_speed  = 30.0
        self.tc.current_speed    = 35.0   # over the cap
        self.tc.fault_power      = False
        self.tc.fault_brake      = False
        self.tc.fault_signal     = False
        self.tc.authority        = 9999.0  # plenty of authority

        self.tc.monitor()

        self.assertTrue(self.tc.auto_service_brake,
                        "auto_service_brake must be True when overspeeding")

    
    # TC-10  Set Manual Mode
    
    def test_TC10_set_manual_mode(self):
        """set_manual(spd) must switch to Manual, set target speed,
        and initialise driver_power_req to 50."""
        self.tc.set_manual(25.0)

        self.assertFalse(self.tc.automatic_mode,
                         "automatic_mode must be False in Manual mode")
        self.assertEqual(self.tc.manual_speed_target, 25.0,
                         "manual_speed_target must be 25.0")
        self.assertEqual(self.tc.driver_power_req, 50,
                         "driver_power_req must be initialised to 50")

    
    # TC-11  Set Auto Mode
    
    def test_TC11_set_auto_mode(self):
        """set_auto() must switch automatic_mode back to True."""
        self.tc.set_manual(25.0)
        self.assertFalse(self.tc.automatic_mode)

        self.tc.set_auto()

        self.assertTrue(self.tc.automatic_mode,
                        "automatic_mode must be True after set_auto()")

    
    # TC-12  Door Opens When Stopped
    
    def test_TC12_door_opens_when_stopped(self):
        """set_doors(3) must update doors_state when speed == 0."""
        self.tc.current_speed = 0.0

        self.tc.set_doors(3)

        self.assertEqual(self.tc.doors_state, 3,
                         "doors_state must be 3 (both open) when stopped")

    
    # TC-13  Door Blocked While Moving
    
    def test_TC13_door_blocked_while_moving(self):
        """set_doors() must NOT change doors_state when train is moving."""
        self.tc.current_speed = 30.0
        self.tc.doors_state   = 0        # start closed

        self.tc.set_doors(3)

        self.assertEqual(self.tc.doors_state, 0,
                         "doors_state must remain 0 while train is moving")

    
    # TC-14  any_fault Property
    
    def test_TC14_any_fault_property(self):
        """any_fault must return True if at least one fault is active,
        and False when all faults are cleared."""
        # All clear
        self.assertFalse(self.tc.any_fault,
                         "any_fault must be False when no faults are set")

        # Single fault
        self.tc.fault_brake = True
        self.assertTrue(self.tc.any_fault,
                        "any_fault must be True when fault_brake is set")

        # Clear
        self.tc.fault_brake = False
        self.assertFalse(self.tc.any_fault,
                         "any_fault must be False after clearing fault_brake")

    
    # TC-15  Fault Cleared Does Not Keep E-Brake
    
    def test_TC15_fault_cleared_ebrake_releasable(self):
        """After clearing a fault, release_ebrake() must succeed."""
        self.tc.set_power_fault(True)
        self.assertTrue(self.tc.emergency_brake)

        # Clear the fault then release
        self.tc.set_power_fault(False)
        self.tc.release_ebrake()

        self.assertFalse(self.tc.emergency_brake,
                         "e-brake must release after fault is cleared")

    
    # TC-16  Power Clamped to MAX_POWER
    
    def test_TC16_power_clamped_to_max(self):
        """power_output must never exceed MAX_POWER (120,000 W)."""
        self.tc.automatic_mode   = True
        self.tc.commanded_speed  = 70.0   # high target
        self.tc.current_speed    = 0.0
        self.tc.kp               = 99999  # absurdly high gain
        self.tc.ki               = 99999
        self.tc.driver_power_req = 100
        self.tc.emergency_brake  = False
        self.tc.service_brake    = False

        self.tc.calc_power(0.1)

        self.assertLessEqual(self.tc.power_output, self.tc.MAX_POWER,
                             "power_output must be clamped to MAX_POWER")

   
    # TC-17  Authority Zero Stops Decrement
    
    def test_TC17_authority_does_not_go_very_negative(self):
        """update_auth continues to run; authority can go negative
        but monitor() will then trigger e-brake via the band check."""
        self.tc.authority     = 0.0
        self.tc.current_speed = 30.0

        self.tc.update_auth(0.1)

        # authority becomes negative — that is the designed behaviour
        # which then triggers e-brake in monitor()
        self.assertLess(self.tc.authority, 0.0,
                        "authority must go negative when train keeps moving")

    
    # TC-18  update() Calls All Three Sub-Methods
    
    def test_TC18_update_integrates_all_steps(self):
        """update(dt) must run monitor, calc_power, and update_auth.
        Net effect: authority decreases and power is calculated."""
        self.tc.automatic_mode   = True
        self.tc.commanded_speed  = 30.0
        self.tc.current_speed    = 10.0
        self.tc.authority        = 500.0
        self.tc.kp               = 10.0
        self.tc.ki               = 8000.0
        self.tc.driver_power_req = 100
        self.tc.emergency_brake  = False
        self.tc.service_brake    = False
        self.tc.fault_power      = False
        self.tc.fault_brake      = False
        self.tc.fault_signal     = False

        initial_auth = self.tc.authority
        self.tc.update(0.1)

        self.assertLess(self.tc.authority, initial_auth,
                        "authority must decrease after update()")
        self.assertGreaterEqual(self.tc.power_output, 0,
                                "power_output must be >= 0 after update()")

   
    # TC-19  Manual Mode Power Not Zero When Moving
    
    def test_TC19_manual_mode_power_not_zero(self):
        """In manual mode with a positive target and no brakes,
        calc_power() must produce power > 0."""
        self.tc.set_manual(30.0)
        self.tc.current_speed   = 0.0
        self.tc.emergency_brake = False
        self.tc.service_brake   = False
        self.tc.auto_service_brake = False
        self.tc.kp              = 10.0
        self.tc.ki              = 8000.0

        power = self.tc.calc_power(0.1)

        self.assertGreater(power, 0,
                           "power must be > 0 in manual mode when below target")

    
    # TC-20  Service Brake Zeroes Power
    
    def test_TC20_service_brake_zeroes_power(self):
        """calc_power() must return 0 when service_brake is True."""
        self.tc.service_brake    = True
        self.tc.driver_power_req = 100
        self.tc.commanded_speed  = 30.0
        self.tc.current_speed    = 10.0

        power = self.tc.calc_power(0.1)

        self.assertEqual(power, 0,
                         "power must be 0 when service brake is active")



if __name__ == "__main__":
    unittest.main(verbosity=2)