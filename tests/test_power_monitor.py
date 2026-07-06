import time

from soccerball8.power_monitor import (
    LowPowerIndicator,
    _build_ina219_read_state,
    _parse_throttled_hex,
    is_undervoltage_now,
    is_voltage_below,
)


def test_parse_throttled_hex():
    assert _parse_throttled_hex("throttled=0x50005\n") == 0x50005


def test_is_undervoltage_now_true_when_bit0_set():
    assert is_undervoltage_now(read_hex=lambda: 0x50005) is True


def test_is_undervoltage_now_false_when_bit0_clear():
    assert is_undervoltage_now(read_hex=lambda: 0x50000) is False


def test_is_voltage_below_threshold():
    assert is_voltage_below(4.8, read_voltage=lambda: 4.5) is True
    assert is_voltage_below(4.8, read_voltage=lambda: 5.0) is False


def test_build_ina219_read_state_returns_none_when_no_sensor_present():
    # No INA219 (or even smbus2) attached in a dev/test environment - the
    # probe should fail closed and return None so the caller falls back to
    # vcgencmd, rather than raising.
    assert _build_ina219_read_state(bus_number=1, address=0x40, threshold_v=4.8) is None


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
