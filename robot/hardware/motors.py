"""Tank-style drive base on an L298N dual motor driver."""

from gpiozero import Motor


class DriveBase:
    def __init__(self, left_pins, right_pins, speed=0.8):
        self.left = Motor(forward=left_pins['forward'], backward=left_pins['backward'],
                           enable=left_pins['enable'])
        self.right = Motor(forward=right_pins['forward'], backward=right_pins['backward'],
                            enable=right_pins['enable'])
        self.speed = speed

    def set_drive(self, forward, backward, left, right):
        """Combine WASD key states into left/right track speeds."""
        l = r = 0
        if forward:
            l += 1
            r += 1
        if backward:
            l -= 1
            r -= 1
        if left:
            l -= 1
            r += 1
        if right:
            l += 1
            r -= 1

        l = max(-1, min(1, l)) * self.speed
        r = max(-1, min(1, r)) * self.speed
        self._apply(self.left, l)
        self._apply(self.right, r)

    def _apply(self, motor, value):
        if value > 0:
            motor.forward(value)
        elif value < 0:
            motor.backward(-value)
        else:
            motor.stop()

    def stop(self):
        self.left.stop()
        self.right.stop()
