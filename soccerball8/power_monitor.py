"""Low-power warning LED.

The Pi's own power management chip already detects when the 5V input rail
sags below its safe threshold - this happens more and more often as a
power bank's battery runs down and its internal resistance rises under
load. `vcgencmd get_throttled` bit 0 reports that live, so the low-power
indicator needs no extra sensor hardware beyond the LED itself.
"""

import re
import subprocess
import threading
from typing import Callable

_UNDERVOLTAGE_NOW_BIT = 0x1


def _parse_throttled_hex(output: str) -> int:
    match = re.search(r"0x([0-9a-fA-F]+)", output)
    if not match:
        raise RuntimeError(f"Unexpected vcgencmd output: {output!r}")
    return int(match.group(1), 16)


def _read_throttled_hex() -> int:
    output = subprocess.run(
        ["vcgencmd", "get_throttled"], capture_output=True, text=True, timeout=2, check=True
    ).stdout
    return _parse_throttled_hex(output)


def is_undervoltage_now(read_hex: Callable[[], int] = _read_throttled_hex) -> bool:
    """True if the Pi is *currently* seeing under-voltage on its 5V input -
    a good proxy for "the power bank is running low"."""
    return bool(read_hex() & _UNDERVOLTAGE_NOW_BIT)


class LowPowerIndicator:
    """Drives an LED on a GPIO pin from a background thread based on live
    under-voltage state, so the main loop doesn't need to poll it itself."""

    def __init__(
        self,
        gpio_pin: int,
        poll_seconds: float = 5.0,
        read_state: Callable[[], bool] = is_undervoltage_now,
    ):
        self._gpio_pin = gpio_pin
        self._poll_seconds = poll_seconds
        self._read_state = read_state
        self._stop = threading.Event()
        self._gpio = None
        try:
            import RPi.GPIO as GPIO

            GPIO.setmode(GPIO.BCM)
            GPIO.setwarnings(False)
            GPIO.setup(gpio_pin, GPIO.OUT, initial=GPIO.LOW)
            self._gpio = GPIO
        except Exception:
            self._gpio = None  # dev/off-Pi: runs without a physical LED

        self._thread = threading.Thread(target=self._run, daemon=True)

    def start(self) -> None:
        self._thread.start()

    def stop(self) -> None:
        self._stop.set()
        self._thread.join(timeout=self._poll_seconds + 1)
        if self._gpio:
            self._gpio.output(self._gpio_pin, self._gpio.LOW)

    def _run(self) -> None:
        while not self._stop.is_set():
            try:
                low_power = self._read_state()
            except Exception:
                low_power = False
            if self._gpio:
                self._gpio.output(self._gpio_pin, self._gpio.HIGH if low_power else self._gpio.LOW)
            self._stop.wait(self._poll_seconds)
