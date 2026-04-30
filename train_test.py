# ai was used to aid the creation of this code

import unittest
import sys
import os

from train_backend import (
    TrainModel,
    samplePeriodSec,
    maxEmergencyBrakeDecelMps2,
    maxServiceBrakeDecelMps2,
    kmhToMph,
)

# PyQt6 is required for the Train Model GUI (train_frontend_main.py).
# If it is not installed, UI tests are skipped so the physics test suite
# can still run in headless / CI environments.
try:
    from PyQt6.QtWidgets import QApplication
    from train_frontend_main import TrainControlUI
    _qt_app = QApplication.instance() or QApplication(sys.argv)
    _QT_AVAILABLE = True
except ImportError:
    _QT_AVAILABLE = False


class TestTrainModel(unittest.TestCase):

    def setUp(self):
        self.model = TrainModel()

    def test_initial_state(self):
        m = self.model
        # commandedSpeedKmh starts at 0.0; the Track Model supplies the real value at runtime
        self.assertAlmostEqual(m.commandedSpeedKmh, 0.0)
        self.assertAlmostEqual(m.currentSpeedKmh, 0.0)
        self.assertAlmostEqual(m.currentAccelMps2, 0.0)
        self.assertFalse(m.isEmergencyBrakeOn)
        self.assertFalse(m.hasEngineFault)
        self.assertEqual(m.onboardPassengers, 0)
        self.assertAlmostEqual(m.distanceTraveledKm, 0.0)
        self.assertAlmostEqual(m.elapsedTimeSec, 0.0)

    def test_tick_accelerates_with_traction(self):
        m = self.model
        m.currentSpeedKmh = 36.0
        m._prevVelocityMps = 10.0
        m.requestedTractionPowerW = 60000.0
        m.tick()
        self.assertGreater(m.currentSpeedKmh, 36.0)
        self.assertGreater(m.currentAccelMps2, 0.0)

    def test_emergency_brake_zeroes_traction(self):
        m = self.model
        m.currentSpeedKmh = 72.0
        m._prevVelocityMps = 20.0
        m.requestedTractionPowerW = 120000.0
        m.isEmergencyBrakeOn = True
        m.tick()
        self.assertLess(m.currentSpeedKmh, 72.0)
        self.assertLessEqual(m.currentAccelMps2, 0.0)

    def test_passenger_ebrake_same_as_controller(self):
        m = self.model
        m.currentSpeedKmh = 50.0
        m._prevVelocityMps = 50.0 / 3.6
        m.isPassengerEmergencyBrakeOn = True
        m.isEmergencyBrakeOn = False
        m.tick()
        self.assertLess(m.currentSpeedKmh, 50.0)
        self.assertLessEqual(m.currentAccelMps2, 0.0)

    def test_service_brake_decel_rate(self):
        m = self.model
        m.currentSpeedKmh = 50.0
        m._prevVelocityMps = 50.0 / 3.6
        m.isServiceBrakeOn = True
        m.requestedTractionPowerW = 0.0
        m.tick()
        self.assertLess(m.currentSpeedKmh, 50.0)
        self.assertAlmostEqual(m.currentAccelMps2, -maxServiceBrakeDecelMps2, delta=0.15)

    def test_speed_cannot_go_negative(self):
        m = self.model
        m.currentSpeedKmh = 0.0
        m._prevVelocityMps = 0.0
        m.isServiceBrakeOn = True
        m.tick()
        self.assertAlmostEqual(m.currentSpeedKmh, 0.0, places=5)
        self.assertGreaterEqual(m.currentAccelMps2, 0.0)

    def test_trapezoidal_distance_update(self):
        m = self.model
        speed_mps = 10.0
        m.currentSpeedKmh = speed_mps * 3.6
        m._prevVelocityMps = speed_mps
        m.requestedTractionPowerW = 0.0
        m.isServiceBrakeOn = False
        dist_before = m.distanceTraveledKm
        m.tick()
        dist_delta = m.distanceTraveledKm - dist_before
        self.assertAlmostEqual(dist_delta, speed_mps * samplePeriodSec / 1000.0, delta=0.0005)

    def test_authority_decreases_and_clamps(self):
        m = self.model
        m.commandedAuthorityKm = 1.0
        m.currentSpeedKmh = 36.0
        m._prevVelocityMps = 10.0
        m.tick()
        self.assertLess(m.commandedAuthorityKm, 1.0)
        self.assertGreaterEqual(m.commandedAuthorityKm, 0.0)

    def test_uphill_grade_increases_decel(self):
        m_flat = TrainModel()
        m_flat.currentSpeedKmh = 36.0
        m_flat._prevVelocityMps = 10.0
        m_flat.requestedTractionPowerW = 0.0
        m_flat.tick()

        m_hill = TrainModel()
        m_hill.currentSpeedKmh = 36.0
        m_hill._prevVelocityMps = 10.0
        m_hill.requestedTractionPowerW = 0.0
        m_hill.trackGradePercent = 5.0
        m_hill.tick()

        self.assertLess(m_hill.currentAccelMps2, m_flat.currentAccelMps2)

    def test_elapsed_time_increments(self):
        m = self.model
        for _ in range(10):
            m.tick()
        self.assertAlmostEqual(m.elapsedTimeSec, 10 * samplePeriodSec, places=5)

    def test_boarding_passengers_accumulate_then_reset(self):
        m = self.model
        m.boardingPassengerCount = 5
        m.tick()
        self.assertEqual(m.onboardPassengers, 5)
        self.assertEqual(m.boardingPassengerCount, 0)

    def test_ebrake_status_true_on_engine_fault(self):
        m = self.model
        m.hasEngineFault = True
        self.assertTrue(m.getEmergencyBrakeStatus())

    def test_ebrake_status_true_on_power_fault(self):
        m = self.model
        m.hasPowerFault = True
        self.assertTrue(m.getEmergencyBrakeStatus())

    def test_ebrake_status_false_when_no_faults(self):
        m = self.model
        self.assertFalse(m.getEmergencyBrakeStatus())

    def test_display_speed_mph_conversion(self):
        m = self.model
        m.currentSpeedKmh = 100.0
        self.assertAlmostEqual(m.displayCurrentSpeedMph(), 62.1371, places=3)

    def test_display_cabin_temp_fahrenheit(self):
        m = self.model
        m.cabinTemperatureC = 20.0
        self.assertAlmostEqual(m.displayCabinTemperatureF(), 68.0, places=3)

    def test_display_traction_power_kw(self):
        m = self.model
        m.requestedTractionPowerW = 120000.0
        self.assertAlmostEqual(m.displayRequestedTractionPowerKw(), 120.0, places=3)

    def test_accel_capped_by_track_limit(self):
        m = self.model
        m.currentSpeedKmh = 36.0
        m._prevVelocityMps = 10.0
        m.requestedTractionPowerW = 120000.0
        m.trackAccelerationLimitKmh2 = 100.0
        cap_mps2 = 100.0 / 12960.0
        m.tick()
        self.assertLessEqual(m.currentAccelMps2, cap_mps2 + 1e-6)

    def test_service_brake_overridden_by_ebrake(self):
        m = self.model
        m.currentSpeedKmh = 50.0
        m._prevVelocityMps = 50.0 / 3.6
        m.isServiceBrakeOn = True
        m.isEmergencyBrakeOn = True
        m.tick()
        self.assertLessEqual(m.currentAccelMps2, -maxServiceBrakeDecelMps2 + 0.1)

    def test_display_accel_fps2_conversion(self):
        m = self.model
        m.currentAccelMps2 = 1.0
        self.assertAlmostEqual(m.displayCurrentAccelFps2(), 3.28084, places=3)


@unittest.skipUnless(_QT_AVAILABLE, "PyQt6 not installed — skipping UI tests")
class TestTrainControlUI(unittest.TestCase):

    def setUp(self):
        self.model = TrainModel()
        self.ui = TrainControlUI(trainModel=self.model)

    def test_init_model_reference(self):
        self.assertIsNotNone(self.ui.trainModel)
        self.assertIs(self.ui.trainModel, self.model)

    def test_toggle_ebrake_on(self):
        self.ui.emergencyBrakeOn = False
        self.ui.toggleEmergencyBrake()
        self.assertTrue(self.ui.emergencyBrakeOn)
        self.assertTrue(self.model.isPassengerEmergencyBrakeOn)

    def test_toggle_ebrake_off(self):
        self.ui.emergencyBrakeOn = True
        self.model.isPassengerEmergencyBrakeOn = True
        self.ui.toggleEmergencyBrake()
        self.assertFalse(self.ui.emergencyBrakeOn)
        self.assertFalse(self.model.isPassengerEmergencyBrakeOn)

    def test_toggle_engine_fault(self):
        self.model.hasEngineFault = False
        self.ui.toggleEngineFault()
        self.assertTrue(self.model.hasEngineFault)

    def test_toggle_brake_fault(self):
        self.model.hasBrakeFault = False
        self.ui.toggleBrakeFault()
        self.assertTrue(self.model.hasBrakeFault)

    def test_toggle_power_fault(self):
        self.model.hasPowerFault = False
        self.ui.togglePowerFault()
        self.assertTrue(self.model.hasPowerFault)

    def test_refresh_speed_label(self):
        self.model.currentSpeedKmh = 80.0
        self.ui.refreshFromModel()
        text = self.ui.speedLabel.text()
        expected_mph = round(kmhToMph(80.0), 1)
        self.assertIn(str(expected_mph), text)

    def test_refresh_temperature_label(self):
        self.model.cabinTemperatureC = 25.0
        self.ui.refreshFromModel()
        text = self.ui.tempLabel.text()
        self.assertIn("77", text)

    def test_refresh_door_status(self):
        self.model.isRightDoorOpen = True
        self.model.isLeftDoorOpen = False
        self.ui.refreshFromModel()
        self.assertIn("Right Open", self.ui.doorLabel.text())
        self.assertNotIn("Left Open", self.ui.doorLabel.text())

    def test_refresh_lights_status(self):
        self.model.areExternalLightsOn = True
        self.model.areInternalLightsOn = False
        self.ui.refreshFromModel()
        self.assertIn("On", self.ui.exteriorLightsLabel.text())
        self.assertIn("Off", self.ui.interiorLightsLabel.text())

    def test_set_train_model_replaces_reference(self):
        # TrainControlUI does not expose a setTrainModel() method;
        # the reference is replaced by assigning the attribute directly.
        new_model = TrainModel()
        new_model.currentSpeedKmh = 99.0
        self.ui.trainModel = new_model
        self.assertIs(self.ui.trainModel, new_model)

    def test_refresh_passenger_count(self):
        self.model.onboardPassengers = 42
        self.ui.refreshFromModel()
        self.assertIn("42", self.ui.passengersLabel.text())

    def test_emergency_style_active(self):
        style = self.ui._emergencyStyle(True)
        self.assertIsInstance(style, str)
        self.assertGreater(len(style), 0)

    def test_emergency_style_inactive(self):
        active = self.ui._emergencyStyle(True)
        inactive = self.ui._emergencyStyle(False)
        self.assertNotEqual(active, inactive)

    def test_refresh_beacon_label(self):
        self.model.beaconData = "Station A"
        self.ui.refreshFromModel()
        self.assertIn("Station A", self.ui.beaconDataLabel.text())


if __name__ == "__main__":
    unittest.main(verbosity=2)
