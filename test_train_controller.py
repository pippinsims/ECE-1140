
import sys
import math
import unittest


# Import the controller

try:
    from train_controller_backend import TrainController
except ImportError:
    print("ERROR: train_controller_backend.py not found in the current directory.")
    sys.exit(1)


# Helpers


def make_ctrl(**kwargs) -> TrainController:
    """Create a TrainController and apply any keyword overrides."""
    c = TrainController(train_id=1)
    for k, v in kwargs.items():
        setattr(c, k, v)
    return c


def run_ticks(ctrl: TrainController, n: int, dt: float = 0.1):
    """Run monitor + calc_power for n ticks."""
    for _ in range(n):
        ctrl.monitor()
        ctrl.calc_power(dt)



# TC-01 to TC-10: Power and acceleration


class TestPowerAndAcceleration(unittest.TestCase):

    def test_TC01_auto_mode_produces_positive_power(self):
        """TC-01: Normal auto mode — positive power when below commanded speed."""
        c = make_ctrl(automatic_mode=True, commanded_speed=40.0,
                      current_speed=0.0, speed_limit=70.0, authority=500.0)
        c.monitor()
        c.calc_power(0.1)
        self.assertGreater(c.power_output, 0)
        self.assertLessEqual(c.power_output, 120_000)
        self.assertFalse(c.auto_service_brake)
        self.assertFalse(c.emergency_brake)

    def test_TC02_power_never_exceeds_max(self):
        """TC-02: Power never exceeds MAX_POWER across 50 ticks."""
        c = make_ctrl(automatic_mode=True, commanded_speed=70.0,
                      current_speed=0.0, speed_limit=70.0, authority=1000.0)
        for _ in range(50):
            c.monitor()
            c.calc_power(0.1)
            self.assertLessEqual(c.power_output, 120_000,
                                  f"power_output exceeded MAX_POWER: {c.power_output}")

    def test_TC03_auto_speed_at_cap_produces_small_power(self):
        """TC-03: When current speed is just below cap, power is very small."""
        c = make_ctrl(automatic_mode=True, commanded_speed=40.0,
                      current_speed=39.9, speed_limit=40.0, authority=500.0)
        c.monitor()
        c.calc_power(0.1)
        self.assertGreaterEqual(c.power_output, 0)
        # gap = 0.1/40 = 0.0025 → power << MAX
        self.assertLess(c.power_output, 1_000)
        self.assertFalse(c.auto_service_brake)

    def test_TC04_zero_commanded_speed_no_power(self):
        """TC-04: Commanded speed = 0 produces zero power output."""
        c = make_ctrl(automatic_mode=True, commanded_speed=0.0,
                      current_speed=0.0, speed_limit=70.0, authority=500.0)
        c.monitor()
        c.calc_power(0.1)
        self.assertEqual(c.power_output, 0)

    def test_TC05_full_cycle_auto_power_converges(self):
        """TC-05: Controller alone: without a train model updating current_speed,
        auto mode holds MAX power as long as the speed gap persists.
        Verify steady-state MAX power output and no emergency brake."""
        c = make_ctrl(automatic_mode=True, commanded_speed=40.0,
                      current_speed=0.0, speed_limit=40.0, authority=2000.0)
        for _ in range(200):
            c.monitor()
            c.calc_power(0.1)
            # Power must never exceed ceiling
            self.assertLessEqual(c.power_output, 120_000)
        # With current_speed=0 and cmd=40, gap=1.0 → full power sustained
        self.assertAlmostEqual(c.power_output, 120_000, delta=1)
        self.assertFalse(c.emergency_brake)

    def test_TC06_speed_limit_zero_no_crash(self):
        """TC-06: speed_limit=0 must not raise ZeroDivisionError."""
        c = make_ctrl(automatic_mode=True, commanded_speed=30.0,
                      current_speed=10.0, speed_limit=0.0, authority=500.0)
        try:
            c.monitor()
            result = c.calc_power(0.1)
        except ZeroDivisionError:
            self.fail("ZeroDivisionError when speed_limit=0")
        self.assertTrue(math.isfinite(c.power_output))

    def test_TC07_manual_mode_positive_target_produces_power(self):
        """TC-07: Manual mode with positive target and zero current speed → power > 0."""
        c = make_ctrl(authority=500.0, current_speed=0.0)
        c.set_manual(25.0)
        c.monitor()
        c.calc_power(0.1)
        self.assertFalse(c.automatic_mode)
        self.assertGreater(c.power_output, 0)
        self.assertLessEqual(c.power_output, 120_000)

    def test_TC08_manual_zero_target_applies_service_brake(self):
        """TC-08: Manual mode with target=0 and moving train applies service brake."""
        c = make_ctrl(current_speed=10.0, authority=500.0)
        c.set_manual(0.0)
        c.monitor()
        self.assertTrue(c.auto_service_brake)
        self.assertEqual(c.driver_power_req, 0)

    def test_TC09_pi_integral_resets_when_brake_applied(self):
        """TC-09: uk and prev_error reset to 0 when brake is applied (auto mode)."""
        c = make_ctrl(automatic_mode=True, commanded_speed=40.0,
                      current_speed=0.0, speed_limit=70.0, authority=500.0)
        run_ticks(c, 10)  # build up uk
        c.service_brake = True
        c.calc_power(0.1)
        self.assertEqual(c.uk, 0)
        self.assertEqual(c.prev_error, 0)
        self.assertEqual(c.power_output, 0)

    def test_TC10_service_brake_cuts_power(self):
        """TC-10: Service brake active → power_output forced to 0."""
        c = make_ctrl(service_brake=True, emergency_brake=False,
                      driver_power_req=100)
        c.calc_power(0.1)
        self.assertEqual(c.power_output, 0)
        self.assertEqual(c.uk, 0)



# TC-11 to TC-18: Brake logic


class TestBrakeLogic(unittest.TestCase):

    def test_TC11_overspeed_triggers_auto_service_brake(self):
        """TC-11: Current speed > cap + 2 mph tolerance → auto_service_brake."""
        c = make_ctrl(automatic_mode=True, commanded_speed=30.0,
                      current_speed=35.0, speed_limit=40.0, authority=500.0)
        c.monitor()
        self.assertTrue(c.auto_service_brake)
        self.assertFalse(c.emergency_brake)

    def test_TC12_release_ebrake_clears_latch(self):
        """TC-12: release_ebrake() clears emergency_brake and ebrake_reason."""
        c = make_ctrl(emergency_brake=True, ebrake_reason="TEST")
        c.release_ebrake()
        self.assertFalse(c.emergency_brake)
        self.assertEqual(c.ebrake_reason, "")

    def test_TC13_emergency_brake_prevents_service_brake_in_calc(self):
        """TC-13: Emergency brake active — calc_power returns 0 regardless of service_brake."""
        c = make_ctrl(emergency_brake=True, service_brake=False,
                      driver_power_req=100)
        c.calc_power(0.1)
        self.assertEqual(c.power_output, 0)

    def test_TC14_ebrake_disables_service_brake_flag(self):
        """TC-14: _activate_ebrake() sets emergency_brake and clears service_brake."""
        c = make_ctrl(service_brake=True)
        c._activate_ebrake("TEST")
        self.assertTrue(c.emergency_brake)
        self.assertFalse(c.service_brake)
        self.assertEqual(c.power_output, 0)

    def test_TC15_auto_service_brake_with_authority_zero_moving(self):
        """TC-15: authority=0 and train moving → auto_service_brake applied."""
        c = make_ctrl(authority=0.0, current_speed=10.0, automatic_mode=True)
        c.monitor()
        self.assertTrue(c.auto_service_brake)
        self.assertEqual(c.driver_power_req, 0)

    def test_TC16_authority_zero_train_stopped_no_brake(self):
        """TC-16: authority=0 and current_speed=0 → auto_service_brake stays False."""
        c = make_ctrl(authority=0.0, current_speed=0.0, automatic_mode=True)
        c.monitor()
        self.assertFalse(c.auto_service_brake)
        self.assertEqual(c.driver_power_req, 0)

    def test_TC17_negative_authority_triggers_ebrake(self):
        """TC-17: Negative authority is treated as zero by monitor() (authority <= 0 branch),
        which applies auto_service_brake and cuts power. _vital_eval independently returns EB
        with INVALID AUTHORITY when called directly."""
        c = make_ctrl(authority=-1.0, current_speed=5.0,
                      commanded_speed=40.0, speed_limit=40.0)
        # Vital channel correctly identifies negative auth as EB
        action, reason = c._vital_eval()
        self.assertEqual(action, "EB")
        self.assertIn("INVALID AUTHORITY", reason)
        # monitor() hits authority<=0 guard first → service brake, not e-brake
        c.monitor()
        self.assertTrue(c.auto_service_brake)
        self.assertEqual(c.driver_power_req, 0)

    def test_TC18_ebrake_reason_updated_when_fault_overrides(self):
        """TC-18: When monitor() detects a new fault while e-brake is already
        latched, the reason is updated to reflect the active fault."""
        c = make_ctrl()
        c._activate_ebrake("FIRST REASON")
        self.assertEqual(c.ebrake_reason, "FIRST REASON")
        # Now add a power fault and call monitor — reason will update to fault label
        c.fault_power = True
        c.monitor()
        self.assertTrue(c.emergency_brake)
        self.assertIn("POWER FAULT", c.ebrake_reason)



# TC-19 to TC-24: Fault injection


class TestFaultInjection(unittest.TestCase):

    def test_TC19_power_fault_triggers_ebrake(self):
        """TC-19: set_power_fault(True) → emergency_brake, ebrake_reason."""
        c = make_ctrl()
        c.set_power_fault(True)
        self.assertTrue(c.emergency_brake)
        self.assertEqual(c.power_output, 0)

    def test_TC20_brake_fault_triggers_ebrake(self):
        """TC-20: set_brake_fault(True) → emergency_brake."""
        c = make_ctrl()
        c.set_brake_fault(True)
        self.assertTrue(c.emergency_brake)

    def test_TC21_signal_fault_triggers_ebrake(self):
        """TC-21: set_signal_fault(True) → emergency_brake."""
        c = make_ctrl()
        c.set_signal_fault(True)
        self.assertTrue(c.emergency_brake)

    def test_TC22_monitor_with_power_fault_includes_reason(self):
        """TC-22: monitor() with fault_power sets ebrake_reason to 'POWER FAULT'."""
        c = make_ctrl(fault_power=True)
        c.monitor()
        self.assertIn("POWER FAULT", c.ebrake_reason)

    def test_TC23_multi_fault_reason_contains_both(self):
        """TC-23: Both power and brake faults → ebrake_reason contains both labels."""
        c = make_ctrl(fault_power=True, fault_brake=True)
        c.monitor()
        self.assertIn("POWER FAULT", c.ebrake_reason)
        self.assertIn("BRAKE FAULT", c.ebrake_reason)
        self.assertTrue(c.emergency_brake)

    def test_TC24_any_fault_property(self):
        """TC-24: any_fault is False with no faults, True after one is set."""
        c = make_ctrl()
        self.assertFalse(c.any_fault)
        c.fault_power = True
        self.assertTrue(c.any_fault)
        c.fault_power = False
        c.fault_signal = True
        self.assertTrue(c.any_fault)



# TC-25 to TC-28: Safety / vital channel


class TestVitalChannel(unittest.TestCase):

    def test_TC25_vital_ok_when_under_cap(self):
        """TC-25: Vital channel returns OK when speed is under cap."""
        c = make_ctrl(current_speed=30.0, commanded_speed=40.0,
                      speed_limit=50.0, authority=200.0, automatic_mode=True)
        action, reason = c._vital_eval()
        self.assertEqual(action, "OK")

    def test_TC26_vital_svc_on_overspeed(self):
        """TC-26: Vital channel returns SVC when current > cap + 2."""
        c = make_ctrl(current_speed=55.0, commanded_speed=40.0,
                      speed_limit=50.0, authority=200.0, automatic_mode=True)
        action, reason = c._vital_eval()
        self.assertEqual(action, "SVC")
        self.assertIn("OVERSPEED", reason)

    def test_TC27_vital_eb_on_any_fault(self):
        """TC-27: Vital channel returns EB when a fault flag is set."""
        c = make_ctrl(fault_signal=True, authority=100.0,
                      current_speed=0.0, speed_limit=40.0)
        action, _ = c._vital_eval()
        self.assertEqual(action, "EB")

    def test_TC28_vital_svc_when_no_authority_and_moving(self):
        """TC-28: Vital channel returns SVC when authority=0 and speed > 0.05 m/s."""
        # current_speed is in mph; 0.1 mph > 0.05 m/s threshold
        c = make_ctrl(authority=0.0, current_speed=5.0,
                      speed_limit=40.0, commanded_speed=40.0)
        action, reason = c._vital_eval()
        self.assertEqual(action, "SVC")
        self.assertIn("NO AUTHORITY", reason)



# TC-29 to TC-32: Mode switching and state attributes


class TestModeAndState(unittest.TestCase):

    def test_TC29_set_auto_switches_mode(self):
        """TC-29: set_auto() sets automatic_mode=True."""
        c = make_ctrl()
        c.set_manual(30.0)
        self.assertFalse(c.automatic_mode)
        c.set_auto()
        self.assertTrue(c.automatic_mode)

    def test_TC30_passengers_attribute_writable(self):
        """TC-30: passengers attribute accepts integer write."""
        c = make_ctrl()
        c.passengers = 150
        self.assertEqual(c.passengers, 150)

    def test_TC31_next_station_attribute_stores_string(self):
        """TC-31: next_station stores arbitrary station name."""
        c = make_ctrl()
        c.next_station = "CENTRAL"
        self.assertEqual(c.next_station, "CENTRAL")

    def test_TC32_distance_travelled_km_attribute(self):
        """TC-32: distance_travelled_km attribute can be read and set."""
        c = make_ctrl()
        c.distance_travelled_km = 3.5
        self.assertAlmostEqual(c.distance_travelled_km, 3.5)



# TC-33 to TC-36: Doors and lights


class TestDoorsAndLights(unittest.TestCase):

    def test_TC33_doors_open_when_stopped(self):
        """TC-33: set_doors(1) succeeds when current_speed=0."""
        c = make_ctrl(current_speed=0.0)
        c.set_doors(1)
        self.assertEqual(c.doors_state, 1)

    def test_TC34_doors_blocked_while_moving(self):
        """TC-34: set_doors() is ignored when current_speed > 0."""
        c = make_ctrl(current_speed=15.0, doors_state=0)
        c.set_doors(3)
        self.assertEqual(c.doors_state, 0)

    def test_TC35_headlights_toggle(self):
        """TC-35: headlights attribute can be toggled."""
        c = make_ctrl(headlights=False)
        c.headlights = True
        self.assertTrue(c.headlights)
        c.headlights = False
        self.assertFalse(c.headlights)

    def test_TC36_interior_lights_value_accepted(self):
        """TC-36: interior_lights accepts integer value."""
        c = make_ctrl(interior_lights=0)
        c.interior_lights = 1
        self.assertEqual(c.interior_lights, 1)



# TC-37: Temperature (cabin_temp)


class TestTemperature(unittest.TestCase):

    def test_TC37_cabin_temp_default(self):
        """TC-37a: Default cabin_temp is 70 (°F)."""
        c = TrainController()
        self.assertEqual(c.cabin_temp, 70)

    def test_TC37_cabin_temp_accepts_float(self):
        """TC-37b: cabin_temp accepts a float value."""
        c = make_ctrl()
        c.cabin_temp = 68.5
        self.assertAlmostEqual(c.cabin_temp, 68.5)

    def test_TC37_cabin_temp_cold(self):
        """TC-37c: cabin_temp can be set to a low value (e.g. 32°F)."""
        c = make_ctrl()
        c.cabin_temp = 32.0
        self.assertEqual(c.cabin_temp, 32.0)

    def test_TC37_cabin_temp_hot(self):
        """TC-37d: cabin_temp can be set to a high value (e.g. 90°F)."""
        c = make_ctrl()
        c.cabin_temp = 90.0
        self.assertEqual(c.cabin_temp, 90.0)

    def test_TC37_cabin_temp_survives_tick(self):
        """TC-37e: cabin_temp is not modified by monitor() or calc_power()."""
        c = make_ctrl(automatic_mode=True, commanded_speed=30.0,
                      current_speed=0.0, speed_limit=70.0, authority=500.0)
        c.cabin_temp = 72.3
        c.monitor()
        c.calc_power(0.1)
        self.assertAlmostEqual(c.cabin_temp, 72.3,
                                msg="cabin_temp should not be altered by controller ticks")



# TC-38 to TC-40: Authority drainage and edge cases


class TestAuthorityAndEdgeCases(unittest.TestCase):

    def test_TC38_authority_drains_with_update_auth(self):
        """TC-38: update_auth() reduces authority proportional to speed × dt."""
        c = make_ctrl(authority=500.0, current_speed=30.0)
        for _ in range(10):
            c.update_auth(0.1)
        self.assertLess(c.authority, 500.0)

    def test_TC39_update_called_integrates_all_three_steps(self):
        """TC-39: update() calls monitor, calc_power, and update_auth without error."""
        c = make_ctrl(automatic_mode=True, commanded_speed=40.0,
                      current_speed=0.0, speed_limit=40.0, authority=500.0)
        try:
            c.update(0.1)
        except Exception as e:
            self.fail(f"update() raised an exception: {e}")

    def test_TC40_no_fault_no_ebrake_on_clean_run(self):
        """TC-40: 100-tick clean run with valid inputs never triggers emergency brake."""
        c = make_ctrl(automatic_mode=True, commanded_speed=40.0,
                      current_speed=0.0, speed_limit=40.0, authority=5000.0)
        for _ in range(100):
            c.monitor()
            c.calc_power(0.1)
            c.update_auth(0.1)
            self.assertFalse(c.emergency_brake,
                              f"emergency_brake unexpectedly triggered on tick")



# Entry point


if __name__ == "__main__":
    loader  = unittest.TestLoader()
    suite   = unittest.TestSuite()

    suite.addTests(loader.loadTestsFromTestCase(TestPowerAndAcceleration))
    suite.addTests(loader.loadTestsFromTestCase(TestBrakeLogic))
    suite.addTests(loader.loadTestsFromTestCase(TestFaultInjection))
    suite.addTests(loader.loadTestsFromTestCase(TestVitalChannel))
    suite.addTests(loader.loadTestsFromTestCase(TestModeAndState))
    suite.addTests(loader.loadTestsFromTestCase(TestDoorsAndLights))
    suite.addTests(loader.loadTestsFromTestCase(TestTemperature))
    suite.addTests(loader.loadTestsFromTestCase(TestAuthorityAndEdgeCases))

    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)

    total  = result.testsRun
    passed = total - len(result.failures) - len(result.errors)
    print("\n" + "=" * 60)
    print(f"  RESULTS:  {passed}/{total} passed", end="")
    if result.failures or result.errors:
        print(f"  |  {len(result.failures)} failed  |  {len(result.errors)} errors")
    else:
        print("  —  ALL PASSED")
    print("=" * 60)

    sys.exit(0 if result.wasSuccessful() else 1)
