"""
Multi-channel software logic analyzer using pigpio.
Captures GPIO edge events with microsecond timestamps on up to 8 pins.
Output is saved as CSV: timestamp_us, pin0, pin1, ..., pin7
"""
from __future__ import annotations

import csv
import logging
import os
import time
from datetime import datetime
from typing import Optional

log = logging.getLogger(__name__)

MAX_CHANNELS = 8


class LogicAnalyzer:
    def __init__(self, config) -> None:
        self._config = config
        self._pi = None
        self._events: list[tuple] = []
        self._callbacks = []
        self._pin_states: dict[int, int] = {}

    def _connect_pigpio(self):
        import pigpio
        if self._pi is None or not self._pi.connected:
            self._pi = pigpio.pi()
            if not self._pi.connected:
                raise RuntimeError('pigpiod not running. Run: sudo pigpiod')
        return self._pi

    def capture(self,
                pins: list[int],
                duration_s: float = 1.0,
                trigger_pin: Optional[int] = None) -> list[dict]:
        import pigpio
        if len(pins) > MAX_CHANNELS:
            pins = pins[:MAX_CHANNELS]
            log.warning('Truncated to %d channels', MAX_CHANNELS)

        pi = self._connect_pigpio()
        self._events = []
        self._pin_states = {p: 0 for p in pins}

        start_tick = None

        def on_edge(gpio, level, tick):
            nonlocal start_tick
            if start_tick is None:
                start_tick = tick
            ts = pigpio.tickDiff(start_tick, tick)
            self._pin_states[gpio] = level
            state = {p: self._pin_states[p] for p in pins}
            self._events.append({'ts_us': ts, 'gpio': gpio, 'level': level, 'state': state})

        for pin in pins:
            pi.set_mode(pin, pigpio.INPUT)
            cb = pi.callback(pin, pigpio.EITHER_EDGE, on_edge)
            self._callbacks.append(cb)

        if trigger_pin is not None and trigger_pin in pins:
            log.info('Logic analyzer waiting for trigger on GPIO%d', trigger_pin)
            deadline = time.time() + 30
            while not self._events and time.time() < deadline:
                time.sleep(0.01)
        else:
            log.info('Logic analyzer capturing for %.2f s on pins %s', duration_s, pins)
            time.sleep(duration_s)

        time.sleep(duration_s)  # capture for full duration after trigger

        for cb in self._callbacks:
            cb.cancel()
        self._callbacks = []

        log.info('Logic analyzer: %d events captured', len(self._events))
        return self._events

    def save_csv(self, events: list[dict], pins: list[int]) -> str:
        data_dir = os.path.join(self._config.data_dir, 'logic')
        os.makedirs(data_dir, exist_ok=True)
        ts = datetime.now().strftime('%Y%m%d_%H%M%S')
        path = os.path.join(data_dir, f'logic_{ts}.csv')

        with open(path, 'w', newline='') as f:
            fieldnames = ['ts_us', 'gpio', 'level'] + [f'pin{p}' for p in pins]
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()
            for ev in events:
                row = {'ts_us': ev['ts_us'], 'gpio': ev['gpio'], 'level': ev['level']}
                for p in pins:
                    row[f'pin{p}'] = ev['state'].get(p, 0)
                writer.writerow(row)

        log.info('Logic analyzer CSV saved: %s', path)
        return path

    def cleanup(self) -> None:
        for cb in self._callbacks:
            cb.cancel()
        self._callbacks = []
        if self._pi and self._pi.connected:
            self._pi.stop()
