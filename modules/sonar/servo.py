"""
SG90 micro servo driver for sonar sweep.

GPIO12 is a hardware PWM pin on the Pi — much smoother than software PWM.
Servo control: 50Hz PWM, pulse width 500µs (0°) → 2500µs (180°).

Wiring:
  Brown  → GND
  Red    → 5V  (external 5V supply recommended; Pi 5V pin works for SG90)
  Orange → GPIO12
"""

import time

# Pulse widths in microseconds for SG90
_PW_MIN_US  = 500    # 0°
_PW_MAX_US  = 2500   # 180°
_FREQ_HZ    = 50


class Servo:
    """SG90 servo on a hardware PWM GPIO pin via pigpio."""

    def __init__(self, pin: int = 12):
        self.pin = pin
        self._angle = 90
        self._pi = None
        self._init()

    def _init(self):
        try:
            import pigpio
            self._pi = pigpio.pi()
            if not self._pi.connected:
                self._pi = None
        except Exception:
            self._pi = None

    def _angle_to_pw(self, angle: float) -> int:
        """Convert angle (0–180) to pulse width in µs."""
        angle = max(0.0, min(180.0, angle))
        return int(_PW_MIN_US + (angle / 180.0) * (_PW_MAX_US - _PW_MIN_US))

    def set_angle(self, angle: float, delay: float = 0.0):
        """Move servo to angle (0–180 degrees)."""
        angle = max(0.0, min(180.0, angle))
        self._angle = angle
        if self._pi and self._pi.connected:
            self._pi.set_servo_pulsewidth(self.pin, self._angle_to_pw(angle))
        if delay:
            time.sleep(delay)

    @property
    def angle(self) -> float:
        return self._angle

    def sweep_to(self, target: float, step: float = 5.0, step_delay: float = 0.05):
        """Slowly sweep from current angle to target."""
        current = self._angle
        if current < target:
            angles = range(int(current), int(target) + 1, max(1, int(step)))
        else:
            angles = range(int(current), int(target) - 1, -max(1, int(step)))
        for a in angles:
            self.set_angle(float(a))
            time.sleep(step_delay)
        self.set_angle(target)

    def center(self):
        self.set_angle(90)

    def cleanup(self):
        if self._pi and self._pi.connected:
            self._pi.set_servo_pulsewidth(self.pin, 0)   # stop PWM signal
            self._pi.stop()
