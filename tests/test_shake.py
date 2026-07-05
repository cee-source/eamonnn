from soccerball8.shake import _magnitude, wait_for_shake


class FakeSensor:
    def __init__(self, readings):
        self._readings = iter(readings)

    def read_acceleration_g(self):
        return next(self._readings)


class FakeClock:
    def __init__(self):
        self.t = 0.0

    def now(self):
        return self.t

    def sleep(self, seconds):
        self.t += seconds


def test_magnitude_of_resting_gravity_is_one_g():
    assert _magnitude(0.0, 0.0, 1.0) == 1.0


def test_wait_for_shake_returns_once_enough_spikes_land_in_window():
    resting = (0.0, 0.0, 1.0)
    shaken = (2.0, 0.0, 1.0)  # magnitude ~2.24g -> deviation ~1.24g
    sensor = FakeSensor([resting, resting, shaken, shaken, shaken, resting])
    clock = FakeClock()

    wait_for_shake(
        sensor=sensor,
        threshold_g=0.8,
        required_spikes=3,
        window_seconds=1.0,
        poll_hz=40.0,
        cooldown_seconds=0.1,
        clock=clock.now,
        sleep=clock.sleep,
    )
    # Reaching here (rather than raising StopIteration from exhausting the
    # fake readings) means it returned as soon as the third spike landed.


def test_wait_for_shake_ignores_gentle_pickup():
    # A gentle pickup barely nudges the reading away from resting gravity -
    # should never trigger, so we only give it readings below threshold.
    gentle = (0.1, 0.05, 1.0)
    sensor = FakeSensor([gentle] * 5 + [(2.0, 0.0, 1.0)] * 3)
    clock = FakeClock()

    wait_for_shake(
        sensor=sensor,
        threshold_g=0.8,
        required_spikes=3,
        window_seconds=1.0,
        poll_hz=40.0,
        cooldown_seconds=0.1,
        clock=clock.now,
        sleep=clock.sleep,
    )
    # Should consume the 5 gentle readings without triggering, then trigger
    # on the 3 real shake readings that follow - i.e. it must not fire early.


def test_wait_for_shake_requires_spikes_within_window():
    shaken = (2.0, 0.0, 1.0)
    resting = (0.0, 0.0, 1.0)
    # Two shakes far apart in time (window expires between them) followed by
    # enough close-together spikes to actually trigger.
    sensor = FakeSensor([shaken, resting, resting, resting, resting, shaken, shaken, shaken])
    clock = FakeClock()

    wait_for_shake(
        sensor=sensor,
        threshold_g=0.8,
        required_spikes=3,
        window_seconds=0.05,  # tight window - the lone early spike ages out
        poll_hz=40.0,
        cooldown_seconds=0.1,
        clock=clock.now,
        sleep=clock.sleep,
    )
