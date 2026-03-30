"""
HC-SR04 ultrasonic distance sensor driver.

Uses pigpio for microsecond-accurate TRIG/ECHO timing.
Falls back to RPi.GPIO if pigpio is unavailable (less accurate).

Wiring:
  VCC  → 5V  (pin 2)
  GND  → GND (pin 6)
  TRIG → GPIO23 (configurable)
  ECHO → GPIO25 via voltage divider: 1kΩ series + 2kΩ to GND
         (ECHO is 5V logic; Pi GPIO is 3.3V max — MUST use divider)
"""

import time
import statistics
from typing import Optional

SPEED_OF_SOUND_CM_S = 34300   # cm/s at ~20°C


class HCSR04:
    """HC-SR04 driver using pigpio for accurate pulse timing."""

    def __init__(self, trig_pin: int = 23, echo_pin: int = 25,
                 max_range_cm: float = 300.0):
        self.trig_pin = trig_pin
        self.echo_pin = echo_pin
        self.max_range_cm = max_range_cm
        self._pi = None
        self._echo_start: Optional[float] = None
        self._echo_end: Optional[float] = None
        self._cb = None
        self._init_pigpio()

    # ------------------------------------------------------------------
    def _init_pigpio(self):
        try:
            import pigpio
            self._pi = pigpio.pi()
            if not self._pi.connected:
                self._pi = None
                return
            self._pi.set_mode(self.trig_pin, pigpio.OUTPUT)
            self._pi.set_mode(self.echo_pin, pigpio.INPUT)
            self._pi.write(self.trig_pin, 0)
            time.sleep(0.05)   # let sensor settle
        except Exception:
            self._pi = None

    # ------------------------------------------------------------------
    def _measure_pigpio(self) -> Optional[float]:
        """Single measurement using pigpio (accurate to ~1µs)."""
        import pigpio

        echo_start = [None]
        echo_end   = [None]

        def _cb(gpio, level, tick):
            if level == 1:
                echo_start[0] = tick
            elif level == 0 and echo_start[0] is not None:
                echo_end[0] = tick

        cb = self._pi.callback(self.echo_pin, pigpio.EITHER_EDGE, _cb)

        # 10µs TRIG pulse
        self._pi.gpio_trigger(self.trig_pin, 10, 1)

        # Wait up to 30ms for echo
        deadline = time.time() + 0.030
        while echo_end[0] is None and time.time() < deadline:
            time.sleep(0.0001)

        cb.cancel()

        if echo_start[0] is None or echo_end[0] is None:
            return None

        # pigpio ticks are µs; handle 32-bit rollover
        pulse_us = pigpio.tickDiff(echo_start[0], echo_end[0])
        distance_cm = (pulse_us * 1e-6 * SPEED_OF_SOUND_CM_S) / 2.0

        if distance_cm < 2.0 or distance_cm > self.max_range_cm:
            return None
        return round(distance_cm, 1)

    def _measure_rpi_gpio(self) -> Optional[float]:
        """Fallback using RPi.GPIO (less timing-accurate)."""
        try:
            import RPi.GPIO as GPIO
            GPIO.setmode(GPIO.BCM)
            GPIO.setup(self.trig_pin, GPIO.OUT)
            GPIO.setup(self.echo_pin, GPIO.IN)
            GPIO.output(self.trig_pin, False)
            time.sleep(0.002)

            GPIO.output(self.trig_pin, True)
            time.sleep(0.00001)
            GPIO.output(self.trig_pin, False)

            timeout = time.time() + 0.030
            while GPIO.input(self.echo_pin) == 0:
                if time.time() > timeout:
                    return None
            start = time.time()

            timeout = time.time() + 0.030
            while GPIO.input(self.echo_pin) == 1:
                if time.time() > timeout:
                    return None
            end = time.time()

            distance_cm = ((end - start) * SPEED_OF_SOUND_CM_S) / 2.0
            if distance_cm < 2.0 or distance_cm > self.max_range_cm:
                return None
            return round(distance_cm, 1)
        except Exception:
            return None

    # ------------------------------------------------------------------
    def measure(self) -> Optional[float]:
        """Return distance in cm, or None if out of range / no echo."""
        if self._pi and self._pi.connected:
            return self._measure_pigpio()
        return self._measure_rpi_gpio()

    def measure_median(self, samples: int = 3) -> Optional[float]:
        """Take multiple readings and return the median (filters noise)."""
        readings = []
        for _ in range(samples):
            d = self.measure()
            if d is not None:
                readings.append(d)
            time.sleep(0.06)   # HC-SR04 needs ~60ms between pings
        if not readings:
            return None
        return round(statistics.median(readings), 1)

    def cleanup(self):
        if self._pi and self._pi.connected:
            self._pi.write(self.trig_pin, 0)
            self._pi.stop()
