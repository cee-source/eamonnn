"""
IR signal capture using pigpio for microsecond-accurate GPIO edge timing.
Records pulse trains and decodes against known IR protocols.
"""
from __future__ import annotations

import logging
import time
from typing import Optional

from modules.infrared.ir_decoder import decode, IRDecoded

log = logging.getLogger(__name__)

IR_CARRIER_HZ = 38000
MIN_PULSES = 10
GAP_US = 10000    # silence longer than this = end of signal


class IRCapture:
    def __init__(self, config) -> None:
        self._rx_pin = config.getint('hardware', 'ir_rx_pin', fallback=24)
        self._pi = None
        self._pulses: list[tuple[int, int]] = []
        self._last_tick: Optional[int] = None
        self._last_level: Optional[int] = None
        self._cb = None
        self._capturing = False

    def _connect_pigpio(self):
        import pigpio
        if self._pi is None or not self._pi.connected:
            self._pi = pigpio.pi()
            if not self._pi.connected:
                raise RuntimeError('pigpiod not running. Run: sudo pigpiod')
        return self._pi

    def _on_edge(self, gpio, level, tick) -> None:
        import pigpio
        if self._last_tick is not None:
            duration = pigpio.tickDiff(self._last_tick, tick)
            self._pulses.append((self._last_level, duration))
        self._last_tick = tick
        self._last_level = level

    def capture(self, timeout_s: float = 10.0, name: str = '') -> Optional[dict]:
        pi = self._connect_pigpio()
        import pigpio

        self._pulses = []
        self._last_tick = None
        self._last_level = None

        pi.set_mode(self._rx_pin, pigpio.INPUT)
        self._cb = pi.callback(self._rx_pin, pigpio.EITHER_EDGE, self._on_edge)

        log.info('IR capture started on GPIO%d (%.1fs timeout)', self._rx_pin, timeout_s)
        deadline = time.time() + timeout_s

        # Wait for first edge
        while not self._pulses and time.time() < deadline:
            time.sleep(0.01)

        if not self._pulses:
            self._cb.cancel()
            log.info('IR capture timed out — no signal')
            return None

        # Wait for end-of-signal gap
        while time.time() < deadline:
            time.sleep(0.001)
            if (self._pulses and
                    self._pulses[-1][1] > GAP_US and
                    len(self._pulses) >= MIN_PULSES):
                break

        self._cb.cancel()
        pulses = self._pulses[:]
        log.info('IR capture complete: %d pulses', len(pulses))

        decoded = decode(pulses)
        result = {
            'name': name,
            'pulses': pulses,
            'pulse_count': len(pulses),
            'protocol': decoded.protocol if decoded else 'UNKNOWN',
            'address': decoded.address if decoded else None,
            'command': decoded.command if decoded else None,
        }
        return result

    def cleanup(self) -> None:
        if self._pi and self._pi.connected:
            self._pi.stop()
