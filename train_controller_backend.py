class TrainController:
    def __init__(self, train_id=1):
        self.train_id             = train_id
        self.current_speed        = 0.0
        self.commanded_speed      = 0.0
        self.speed_limit          = 70.0
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
        # Human-readable reason for the current emergency brake latch.
        # This is UI-facing only and does not affect control logic.
        self.ebrake_reason        = ""
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
        # distance travelled fed from the Train Model (km)
        self.distance_travelled_km = 0.0
        # Vital safety channel status (diverse, independent safety enforcement)
        self.vital_ok              = True
        self.vital_reason          = "OK"

    # -------------------------------------------------------------------------
    # Vital safety channel (diverse redundancy)
    # -------------------------------------------------------------------------

    def _vital_eval(self):
        """
        Diverse safety evaluation channel.

        Returns: (action, reason)
          action ∈ {"OK", "SVC", "EB"}
        """
        # Diverse computation path: use m/s internally, and apply explicit guards.
        try:
            v_mps = max(0.0, float(self.current_speed)) * 0.44704
        except Exception:
            v_mps = 0.0

        # Faults are always vital.
        if bool(self.fault_power) or bool(self.fault_brake) or bool(self.fault_signal):
            reasons = []
            if self.fault_power:
                reasons.append("POWER FAULT")
            if self.fault_brake:
                reasons.append("BRAKE FAULT")
            if self.fault_signal:
                reasons.append("SIGNAL FAULT")
            return "EB", " / ".join(reasons) if reasons else "FAULT"

        # Invalid authority is treated as unsafe.
        try:
            auth_m = float(self.authority)
        except Exception:
            auth_m = 0.0
        if auth_m < 0.0:
            return "EB", "INVALID AUTHORITY"

        # Authority exhausted → stop.
        if auth_m <= 0.0 and v_mps > 0.05:
            return "SVC", "NO AUTHORITY"

        # Overspeed protection (diverse cap calculation with tolerance).
        try:
            spd_lim = float(self.speed_limit)
        except Exception:
            spd_lim = 0.0
        try:
            cmd_spd = float(self.commanded_speed if self.automatic_mode else self.manual_speed_target)
        except Exception:
            cmd_spd = 0.0
        if spd_lim > 0.0:
            cap = min(cmd_spd, spd_lim)
        else:
            cap = cmd_spd

        # Tolerance reduces chatter at block boundaries when speed limit steps down.
        if float(self.current_speed) > float(cap) + 2.0:
            return "SVC", "OVERSPEED"

        # No "approach authority limit" SVC: wayside authority is per-block and jumps
        # at boundaries, which falsely tripped this and zeroed power every block.

        return "OK", "OK"

    def monitor(self):
        # Any fault coming from the train model or controller immediately triggers E-brake.
        if self.any_fault:
            reasons = []
            if self.fault_power:
                reasons.append("POWER FAULT")
            if self.fault_brake:
                reasons.append("BRAKE FAULT")
            if self.fault_signal:
                reasons.append("SIGNAL FAULT")
            self._activate_ebrake(" / ".join(reasons) if reasons else "FAULT")
            return

        # Zero authority means the train has no permission to move.
        if self.authority <= 0.0:
            self.auto_service_brake = (self.current_speed > 0.0)
            self.driver_power_req = 0
            return

        # Speed limit to enforce for overspeed protection. In AUTO mode we
        # track the commanded speed from the Train Model but never exceed the
        # simulated track speed limit. In MANUAL mode the driver's set speed
        # is capped by the same track speed limit.
        if self.automatic_mode:
            base_cap = self.commanded_speed
        else:
            base_cap = self.manual_speed_target
        if self.speed_limit > 0.0:
            speed_cap = min(base_cap, self.speed_limit)
        else:
            speed_cap = base_cap

        # Auto service brake: engage when target speed is 0 and train
        # is moving, or when above the speed cap.
        if speed_cap <= 0.0:
            self.auto_service_brake = (self.current_speed > 0.0)
            self.driver_power_req = 0
        elif self.current_speed > speed_cap:
            self.auto_service_brake = True
            self.driver_power_req = 0
        else:
            self.auto_service_brake = False

        if self.automatic_mode and not self.auto_service_brake:
            # PI loop target is the commanded speed. Scale traction ceiling with how far
            # we are below the cap so power varies smoothly instead of 0/25/50/100 steps.
            if speed_cap > 0.0 and self.current_speed < speed_cap:
                gap = (speed_cap - self.current_speed) / max(speed_cap, 1e-6)
                gap = max(0.0, min(1.0, gap))
                self.driver_power_req = max(0.0, min(100.0, 100.0 * gap))
            else:
                self.driver_power_req = 0
        # In manual mode we leave driver_power_req as set by set_manual().

        # ── Vital enforcement pass (diverse redundant channel) ──
        action, reason = self._vital_eval()
        self.vital_ok = (action == "OK")
        self.vital_reason = str(reason)
        if action == "EB":
            # Hard safe state: emergency brake + no traction.
            if not self.emergency_brake:
                self._activate_ebrake(f"VITAL: {reason}")
            else:
                # keep latest reason if already latched
                self.ebrake_reason = self.ebrake_reason or f"VITAL: {reason}"
            self.driver_power_req = 0
            self.auto_service_brake = False
            return
        if action == "SVC":
            # Soft safe state: service braking + cut traction.
            self.auto_service_brake = True
            self.driver_power_req = 0

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
        scale = float(self.driver_power_req) / 100.0
        if self.automatic_mode:
            # PI with ki=8000 winds up and pegs power at MAX until brakes — looks like 0/120kW only.
            # Automatic traction: map how far we are below the speed cap to a continuous power request.
            try:
                cmd = max(0.0, float(self.commanded_speed))
            except Exception:
                cmd = 0.0
            try:
                cur = max(0.0, float(self.current_speed))
            except Exception:
                cur = 0.0
            try:
                lim = float(self.speed_limit)
            except Exception:
                lim = 0.0
            if lim > 0.0:
                cap = min(cmd, lim)
            else:
                cap = cmd
            if cap <= 0.0:
                self.power_output = 0.0
                self.uk = 0.0
                self.prev_error = 0.0
                self.prev_uk = 0.0
                return 0.0
            gap = max(0.0, cap - cur) / max(cap, 1e-6)
            gap = max(0.0, min(1.0, gap))
            # Slight curve: gentler near the cap, stronger when far below
            pwr = float(self.MAX_POWER) * (gap ** 1.05) * scale
            self.power_output = max(0.0, min(float(self.MAX_POWER), pwr))
            self.uk = 0.0
            self.prev_error = 0.0
            self.prev_uk = 0.0
            return self.power_output
        cmd_v = self.manual_speed_target * 0.44704
        err = cmd_v - self.current_speed * 0.44704
        self.uk = self.prev_uk + (dt / 2) * (err + self.prev_error)
        # Anti-windup for manual PI so power does not sit at max after brief errors
        uk_max = float(self.MAX_POWER) / max(self.ki * scale, 1.0) * 0.85
        self.uk = max(-uk_max, min(uk_max, self.uk))
        pwr = (self.kp * err + self.ki * self.uk) * scale
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

    def _activate_ebrake(self, reason: str = "EMERGENCY"):
        self.emergency_brake = True
        self.ebrake_reason = str(reason or "EMERGENCY")
        self.power_output = 0
        self.driver_power_req = 0
        self.service_brake = False

    def release_ebrake(self):
        # Driver may release the emergency brake at any time.
        self.emergency_brake = False
        self.ebrake_reason = ""

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




