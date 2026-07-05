"""Shake-to-ask trigger using an MPU6050 accelerometer over I2C.

A real Magic 8-Ball is shaken to ask it something, so this replaces a
push-button trigger with a shake gesture: sample the accelerometer, and
treat several rapid swings above a G-force threshold within a short window
as "shaken", then wait out a cooldown so one shake doesn't fire twice.
"""

import math
import time
from typing import Callable, Optional, Tuple

_MPU6050_ADDR = 0x68
_PWR_MGMT_1 = 0x6B
_ACCEL_XOUT_H = 0x3B
_ACCEL_SCALE = 16384.0  # LSB/g at the default +-2g range


class MPU6050:
    """Minimal register-level MPU6050 driver - no dependency beyond smbus2,
    which is light enough for a Pi Zero."""

    def __init__(self, address: int = _MPU6050_ADDR, bus_number: int = 1):
        import smbus2

        self._bus = smbus2.SMBus(bus_number)
        self._address = address
        self._bus.write_byte_data(self._address, _PWR_MGMT_1, 0)  # wake from sleep

    def _read_word(self, register: int) -> int:
        high = self._bus.read_byte_data(self._address, register)
        low = self._bus.read_byte_data(self._address, register + 1)
        value = (high << 8) | low
        return value - 65536 if value >= 0x8000 else value

    def read_acceleration_g(self) -> Tuple[float, float, float]:
        ax = self._read_word(_ACCEL_XOUT_H) / _ACCEL_SCALE
        ay = self._read_word(_ACCEL_XOUT_H + 2) / _ACCEL_SCALE
        az = self._read_word(_ACCEL_XOUT_H + 4) / _ACCEL_SCALE
        return ax, ay, az


def _magnitude(ax: float, ay: float, az: float) -> float:
    return math.sqrt(ax * ax + ay * ay + az * az)


def wait_for_shake(
    sensor=None,
    threshold_g: float = 0.8,
    required_spikes: int = 3,
    window_seconds: float = 1.0,
    poll_hz: float = 40.0,
    cooldown_seconds: float = 1.5,
    bus_number: int = 1,
    i2c_address: int = _MPU6050_ADDR,
    clock: Callable[[], float] = time.monotonic,
    sleep: Callable[[float], None] = time.sleep,
) -> None:
    """Blocks until the device is shaken: `required_spikes` samples that
    deviate from resting gravity (1g) by more than `threshold_g`, all within
    a rolling `window_seconds` window. `sensor`/`clock`/`sleep` are
    injectable for testing without real hardware or real time."""
    if sensor is None:
        sensor = MPU6050(address=i2c_address, bus_number=bus_number)

    poll_interval = 1.0 / poll_hz
    spike_times = []

    while True:
        ax, ay, az = sensor.read_acceleration_g()
        deviation = abs(_magnitude(ax, ay, az) - 1.0)
        now = clock()

        if deviation > threshold_g:
            spike_times.append(now)
            spike_times = [t for t in spike_times if now - t <= window_seconds]
            if len(spike_times) >= required_spikes:
                sleep(cooldown_seconds)  # let the shaking settle before returning
                return

        sleep(poll_interval)
