"""
IR signal replay using pigpio wave API for hardware-timed transmission.
38 kHz carrier is generated via hardware PWM on the IR TX pin (GPIO18/PWM0).
"""
from __future__ import annotations

import logging
import time

log = logging.getLogger(__name__)

IR_CARRIER_HZ = 38000
IR_CARRIER_DUTY = 0.5


class IRReplay:
    def __init__(self, config) -> None:
        self._tx_pin = config.getint('hardware', 'ir_tx_pin', fallback=18)
        self._pi = None

    def _connect_pigpio(self):
        import pigpio
        if self._pi is None or not self._pi.connected:
            self._pi = pigpio.pi()
            if not self._pi.connected:
                raise RuntimeError('pigpiod not running. Run: sudo pigpiod')
        return self._pi

    def replay(self, signal: dict) -> bool:
        """
        Replay a captured IR signal.
        signal: dict with 'pulses' key (list of (level, duration_us) tuples)
        """
        import pigpio

        pulses = signal.get('pulses', [])
        if not pulses:
            log.error('No pulse data in signal')
            return False

        pi = self._connect_pigpio()

        # Build pigpio waveform
        # Marks (level=1 from receiver = IR off in active-low receivers, but
        # for transmission: mark = carrier on, space = carrier off)
        # We emit the carrier on odd pulses (marks) and silence on spaces.
        wave_pulses = []
        carrier_period_us = int(1_000_000 / IR_CARRIER_HZ)
        half_period = carrier_period_us // 2

        for level, duration_us in pulses:
            if level == 1:  # mark — transmit carrier
                cycles = duration_us // carrier_period_us
                for _ in range(max(cycles, 1)):
                    wave_pulses.append(pigpio.pulse(1 << self._tx_pin, 0, half_period))
                    wave_pulses.append(pigpio.pulse(0, 1 << self._tx_pin, half_period))
            else:           # space — silence
                wave_pulses.append(pigpio.pulse(0, 1 << self._tx_pin, duration_us))

        if not wave_pulses:
            return False

        pi.set_mode(self._tx_pin, pigpio.OUTPUT)
        pi.wave_clear()
        pi.wave_add_generic(wave_pulses)
        wid = pi.wave_create()

        if wid < 0:
            log.error('Wave creation failed')
            return False

        pi.wave_send_once(wid)
        # Wait for transmission to finish
        while pi.wave_tx_busy():
            time.sleep(0.001)

        pi.wave_delete(wid)
        log.info('IR replay complete: %d pulses, protocol=%s',
                 len(pulses), signal.get('protocol', 'UNKNOWN'))
        return True

    def cleanup(self) -> None:
        if self._pi and self._pi.connected:
            self._pi.stop()
