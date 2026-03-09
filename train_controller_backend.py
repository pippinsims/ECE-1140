class TrainController:
    def __init__(self, train_id=1):
        self.train_id             = train_id
        self.current_speed        = 0.0
        self.commanded_speed      = 0.0
        self.speed_limit          = 30.0
        self.authority            = 500.0
        self.kp                   = 10.0
        self.ki                   = 8000.0
        self.power_output         = 0.0
        self.uk                   = 0.0
        self.prev_error           = 0.0
        self.prev_uk              = 0.0
        self.emergency_brake      = False
        self.service_brake        = False
        self.MAX_POWER            = 120_000
        self.SERVICE_DECEL        = 1.2
        self.EMERGENCY_DECEL      = 2.73
        self.fault_power          = False
        self.fault_brake          = False
        self.fault_signal         = False
        self.automatic_mode       = True
        self.doors_state          = 0
        self.headlights           = False
        self.interior_lights      = 0
        self.cabin_temp           = 70
        self.passengers           = 0
        self.next_station         = "YARD"
        self.driver_power_req     = 0
        self.manual_speed_target  = 0.0
        # controller-internal auto-applied service brake (eg. overspeed)
        self.auto_service_brake   = False

    def _stop_dist(self, decel):
        v = self.current_speed * 0.44704
        return (v**2 / (2 * decel) + v * 0.1) if decel > 0 else 0.0

    def monitor(self):
        svc = self._stop_dist(self.SERVICE_DECEL)
        emg = self._stop_dist(self.EMERGENCY_DECEL)
        # Any fault coming from the train model or controller immediately triggers E-brake.
        if self.any_fault:
            self._activate_ebrake()
            return

        # Hard authority-based emergency braking band.
        if 5 <= self.authority <= emg:
            self._activate_ebrake()
            return

        # Speed limit to enforce for overspeed protection
        if self.automatic_mode:
            speed_cap = self.commanded_speed
        else:
            speed_cap = self.manual_speed_target

        # Auto service brake engages only when we are above the cap, and
        # clears once we drop back to or below it.
        if self.current_speed > speed_cap and speed_cap > 0.0:
            self.auto_service_brake = True
        else:
            self.auto_service_brake = False

        if self.automatic_mode:
            # PI loop target is the commanded speed. We only apply traction
            # when we are below commanded speed; overspeed is handled by the
            # auto_service_brake flag above.
            if self.current_speed < self.commanded_speed:
                self.driver_power_req = (25 if self.authority <= 50 else 50 if self.authority <= 60 else 100)
            else:
                self.driver_power_req = 0
        # In manual mode we leave driver_power_req as set by set_manual().

    def calc_power(self, dt):
        effective_service_brake = self.service_brake or self.auto_service_brake
        if self.emergency_brake or effective_service_brake:
            self.power_output = 0
            self.uk = 0
            return 0.0
        # In manual mode, ensure we always have a non-zero traction request
        # whenever a positive manual target exists and no brakes are applied.
        if (not self.automatic_mode
                and self.manual_speed_target > 0.0
                and self.driver_power_req == 0):
            self.driver_power_req = 50
        if self.driver_power_req == 0:
            self.power_output = 0
            return 0.0
        cmd_v = (self.commanded_speed if self.automatic_mode else self.manual_speed_target) * 0.44704
        err = cmd_v - self.current_speed * 0.44704
        self.uk = self.prev_uk + (dt / 2) * (err + self.prev_error)
        pwr = (self.kp * err + self.ki * self.uk) * (self.driver_power_req / 100.0)
        self.prev_error = err
        self.prev_uk = self.uk
        self.power_output = max(0.0, min(float(self.MAX_POWER), pwr))
        return self.power_output

    def update_auth(self, dt):
        if self.current_speed > 0:
            self.authority -= self.current_speed * 0.00044704 * dt * 1000

    def update(self, dt):
        self.monitor()
        self.calc_power(dt)
        self.update_auth(dt)

    def _activate_ebrake(self):
        self.emergency_brake = True
        self.power_output = 0
        self.driver_power_req = 0
        self.service_brake = False

    def release_ebrake(self):
        # Driver may release the emergency brake at any time.
        self.emergency_brake = False

    def set_power_fault(self, v):
        self.fault_power = v
        if v:
            self._activate_ebrake()

    def set_brake_fault(self, v):
        self.fault_brake = v
        if v:
            self._activate_ebrake()

    def set_signal_fault(self, v):
        self.fault_signal = v
        if v:
            self._activate_ebrake()

    def set_doors(self, s):
        if self.current_speed == 0:
            self.doors_state = s

    def set_auto(self):
        self.automatic_mode = True

    def set_manual(self, spd):
        self.automatic_mode = False
        self.manual_speed_target = spd
        self.driver_power_req = 50

    @property
    def any_fault(self):
        return self.fault_power or self.fault_brake or self.fault_signal

