"""Arm: turret + boom driven by the mouse, claw driven by the arrow keys."""

from gpiozero import AngularServo
from gpiozero.pins.pigpio import PiGPIOFactory

_factory = PiGPIOFactory()


def _clamp(value, low, high):
    return max(low, min(high, value))


class Arm:
    def __init__(self, turret_pin, boom_pin, claw_pin,
                 mouse_sensitivity=0.3, claw_step=3):
        self.turret = AngularServo(turret_pin, min_angle=0, max_angle=180, pin_factory=_factory)
        self.boom = AngularServo(boom_pin, min_angle=0, max_angle=180, pin_factory=_factory)
        self.claw = AngularServo(claw_pin, min_angle=0, max_angle=90, pin_factory=_factory)

        self.mouse_sensitivity = mouse_sensitivity
        self.claw_step = claw_step

        self.turret_angle = 90
        self.boom_angle = 90
        self.claw_angle = 0  # 0 = open, 90 = closed

        self._apply_all()

    def nudge(self, dx, dy):
        """dx/dy are raw mouse-movement deltas from the browser."""
        self.turret_angle = _clamp(self.turret_angle + dx * self.mouse_sensitivity, 0, 180)
        self.boom_angle = _clamp(self.boom_angle - dy * self.mouse_sensitivity, 0, 180)
        self.turret.angle = self.turret_angle
        self.boom.angle = self.boom_angle

    def claw_move(self, direction):
        """direction: +1 close (ArrowUp), -1 open (ArrowDown)."""
        self.claw_angle = _clamp(self.claw_angle + direction * self.claw_step, 0, 90)
        self.claw.angle = self.claw_angle

    def _apply_all(self):
        self.turret.angle = self.turret_angle
        self.boom.angle = self.boom_angle
        self.claw.angle = self.claw_angle
