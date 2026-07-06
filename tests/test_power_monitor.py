import time

from soccerball8.power_monitor import LowPowerIndicator, _parse_throttled_hex, is_undervoltage_now


def test_parse_throttled_hex():
    assert _parse_throttled_hex("throttled=0x50005\n") == 0x50005


def test_is_undervoltage_now_true_when_bit0_set():
    assert is_undervoltage_now(read_hex=lambda: 0x50005) is True


def test_is_undervoltage_now_false_when_bit0_clear():
    assert is_undervoltage_now(read_hex=lambda: 0x50000) is False


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
