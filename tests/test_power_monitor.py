import time

from soccerball8.power_monitor import (
    LowPowerIndicator,
    _build_read_state,
    _parse_throttled_hex,
    is_undervoltage_now,
    is_voltage_below,
)


class _FakeSensor:
    """Reads a fixed voltage a certain number of times, then starts raising -
    simulating a wire that works loose partway through a run."""

    def __init__(self, voltage: float, good_reads: int = 999):
        self._voltage = voltage
        self._good_reads = good_reads

    def read_bus_voltage(self) -> float:
        if self._good_reads <= 0:
            raise OSError("simulated disconnected wire")
        self._good_reads -= 1
        return self._voltage


def test_parse_throttled_hex():
    assert _parse_throttled_hex("throttled=0x50005\n") == 0x50005


def test_is_undervoltage_now_true_when_bit0_set():
    assert is_undervoltage_now(read_hex=lambda: 0x50005) is True


def test_is_undervoltage_now_false_when_bit0_clear():
    assert is_undervoltage_now(read_hex=lambda: 0x50000) is False


def test_is_voltage_below_threshold():
    assert is_voltage_below(4.8, read_voltage=lambda: 4.5) is True
    assert is_voltage_below(4.8, read_voltage=lambda: 5.0) is False


def test_build_read_state_falls_back_when_no_ina219_present():
    def failing_factory(address, bus_number):
        raise OSError("no device at this address")

    read_state = _build_read_state(
        bus_number=1, address=0x40, threshold_v=4.8,
        ina219_factory=failing_factory, fallback_read_state=lambda: True,
    )
    # No INA219 answers -> every call goes straight to the fallback.
    assert read_state() is True
    assert read_state() is True


def test_build_read_state_uses_ina219_when_present():
    sensor = _FakeSensor(voltage=4.5)
    read_state = _build_read_state(
        bus_number=1, address=0x40, threshold_v=4.8,
        ina219_factory=lambda address, bus_number: sensor,
        fallback_read_state=lambda: False,
    )
    # INA219 reports 4.5V, below the 4.8V threshold -> low power, and the
    # fallback should never be consulted while the sensor is healthy.
    assert read_state() is True


def test_build_read_state_falls_back_when_ina219_disconnects_mid_run():
    calls = {"factory": 0}

    def factory(address, bus_number):
        calls["factory"] += 1
        # The first call does a probe read plus a real read, so 3 good
        # reads covers: probe, first real read, second real read.
        return _FakeSensor(voltage=5.0, good_reads=3)

    read_state = _build_read_state(
        bus_number=1, address=0x40, threshold_v=4.8,
        ina219_factory=factory, fallback_read_state=lambda: True,
    )
    assert read_state() is False  # probe + first real read succeed (5.0V, not low)
    assert read_state() is False  # second real read succeeds
    assert read_state() is True   # sensor now "disconnected" -> falls back
    assert read_state() is True   # stays on the fallback, doesn't re-probe
    assert calls["factory"] == 1  # only ever constructed once


def test_low_power_indicator_starts_and_stops_without_hardware():
    # Off the Pi (no RPi.GPIO), the indicator should still run its polling
    # loop cleanly with no physical LED attached.
    calls = []

    def fake_read_state():
        calls.append(1)
        return False

    indicator = LowPowerIndicator(gpio_pin=27, poll_seconds=0.01, read_state=fake_read_state)
    indicator.start()
    time.sleep(0.05)
    indicator.stop()

    assert len(calls) >= 1
