"""
Manual GPIO pin control: digital high/low, PWM output, pin state readback.
"""
from __future__ import annotations

import logging
from typing import Optional

log = logging.getLogger(__name__)


class PinControl:
    def __init__(self) -> None:
        self._gpio_ok = False
        self._setup()

    def _setup(self) -> None:
        try:
            import RPi.GPIO as GPIO
            GPIO.setmode(GPIO.BCM)
            self._GPIO = GPIO
            self._gpio_ok = True
        except Exception as e:
            log.warning('RPi.GPIO not available: %s', e)

    def set_output(self, pin: int, high: bool) -> None:
        if not self._gpio_ok:
            return
        self._GPIO.setup(pin, self._GPIO.OUT)
        self._GPIO.output(pin, self._GPIO.HIGH if high else self._GPIO.LOW)
        log.info('GPIO%d -> %s', pin, 'HIGH' if high else 'LOW')

    def read_input(self, pin: int) -> int:
        if not self._gpio_ok:
            return -1
        self._GPIO.setup(pin, self._GPIO.IN)
        val = self._GPIO.input(pin)
        log.info('GPIO%d read: %d', pin, val)
        return val

    def set_pwm(self, pin: int, freq_hz: int, duty_pct: float) -> None:
        if not self._gpio_ok:
            return
        self._GPIO.setup(pin, self._GPIO.OUT)
        pwm = self._GPIO.PWM(pin, freq_hz)
        pwm.start(duty_pct)
        log.info('GPIO%d PWM: %d Hz %.1f%%', pin, freq_hz, duty_pct)
        return pwm

    def cleanup(self, pin: Optional[int] = None) -> None:
        if not self._gpio_ok:
            return
        if pin is not None:
            self._GPIO.cleanup(pin)
        else:
            self._GPIO.cleanup()
