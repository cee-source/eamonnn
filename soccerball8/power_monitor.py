"""Low-power warning LED.

Two ways to flag "the power bank is running low":

1. An INA219 voltage sensor wired inline on the 5V rail (optional extra
   hardware, ~$5) - measures the actual rail voltage and warns as soon as
   it drops below a configurable threshold, before things get bad.
2. The Pi's own under-voltage detection (`vcgencmd get_throttled` bit 0) -
   free, needs no extra hardware, but only fires once the rail has already
   sagged to the Pi's own safety threshold - later than option 1.

If an INA219 is wired in and responds on the I2C bus, it's used
automatically for the earlier warning; otherwise this falls back to
vcgencmd with no extra configuration needed.
"""

import re
import subprocess
import threading
from typing import Callable, Optional

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
    a good proxy for "the power bank is running low", but it only trips
    once things have already sagged to the Pi's own safety threshold."""
    return bool(read_hex() & _UNDERVOLTAGE_NOW_BIT)


def is_voltage_below(threshold_v: float, read_voltage: Callable[[], float]) -> bool:
    """True once the measured rail voltage drops below `threshold_v` - an
    earlier warning than is_undervoltage_now when read_voltage comes from
    an INA219 wired inline on the power rail."""
    return read_voltage() < threshold_v


def _default_ina219_factory(address: int, bus_number: int):
    from .ina219 import INA219

    return INA219(address=address, bus_number=bus_number)


def _build_read_state(
    bus_number: int,
    address: int,
    threshold_v: float,
    ina219_factory: Callable[[int, int], object] = _default_ina219_factory,
    fallback_read_state: Callable[[], bool] = is_undervoltage_now,
) -> Callable[[], bool]:
    """Returns a read_state callable that prefers a live INA219 reading on
    each poll, and transparently falls back to the Pi's own under-voltage
    detection if no INA219 answers at startup, *or* if one stops responding
    partway through a run (e.g. its wire works loose) - rather than either
    locking onto one method for the process lifetime or going silently
    blind on a mid-run disconnect."""
    state = {"attempted": False, "sensor": None}

    def read_state() -> bool:
        if not state["attempted"]:
            state["attempted"] = True
            try:
                sensor = ina219_factory(address, bus_number)
                sensor.read_bus_voltage()  # probe - raises if nothing answers at this address
                state["sensor"] = sensor
            except Exception:
                state["sensor"] = None

        sensor = state["sensor"]
        if sensor is not None:
            try:
                return is_voltage_below(threshold_v, sensor.read_bus_voltage)
            except Exception:
                state["sensor"] = None  # dropped mid-run - fall back to vcgencmd from here on

        return fallback_read_state()

    return read_state


class LowPowerIndicator:
    """Drives an LED on a GPIO pin from a background thread based on live
    low-power state, so the main loop doesn't need to poll it itself."""

    def __init__(
        self,
        gpio_pin: int,
        poll_seconds: float = 5.0,
        read_state: Optional[Callable[[], bool]] = None,
        ina219_bus_number: int = 1,
        ina219_address: int = 0x40,
        ina219_threshold_v: float = 4.8,
    ):
        self._gpio_pin = gpio_pin
        self._poll_seconds = poll_seconds
        self._read_state = read_state or _build_read_state(
            ina219_bus_number, ina219_address, ina219_threshold_v
        )
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
