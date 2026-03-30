"""
Sonar scanner: sweeps the SG90 servo 0°→180°→0° while pinging the HC-SR04
at each step, then feeds readings into the radar display.

Sweep config:
  - STEP_DEG  : degrees between measurements (5° = 37 readings per sweep)
  - STEP_DELAY: seconds between steps (includes sensor settle time)
  - Continuous back-and-forth sweeping until stop() is called
"""

import time
import threading
from typing import Optional

from modules.sonar.hcsr04        import HCSR04
from modules.sonar.servo         import Servo
from modules.sonar.radar_display import OLEDRadar, TerminalRadar

STEP_DEG   = 5.0
STEP_DELAY = 0.08   # seconds — HC-SR04 needs ≥60ms between pings


class SonarScanner:
    """Orchestrates servo sweep + distance measurement + display update."""

    def __init__(self, trig_pin: int = 23, echo_pin: int = 25,
                 servo_pin: int = 12, max_range_cm: float = 300.0):
        self._sensor    = HCSR04(trig_pin, echo_pin, max_range_cm)
        self._servo     = Servo(servo_pin)
        self._max_range = max_range_cm
        self._stop_evt  = threading.Event()
        self._thread: Optional[threading.Thread] = None
        self._radar_oled: Optional[OLEDRadar]     = None
        self._radar_term: Optional[TerminalRadar] = None

    # ------------------------------------------------------------------
    def _sweep_loop(self):
        """Background thread: sweeps servo and pings sensor."""
        direction = 1   # +1 = increasing angle, -1 = decreasing
        angle     = 0.0

        self._servo.set_angle(angle, delay=0.5)

        while not self._stop_evt.is_set():
            dist = self._sensor.measure()
            self._update_display(angle, dist)

            angle += direction * STEP_DEG
            if angle >= 180.0:
                angle     = 180.0
                direction = -1
            elif angle <= 0.0:
                angle     = 0.0
                direction = 1

            self._servo.set_angle(angle)
            time.sleep(STEP_DELAY)

    def _update_display(self, angle: float, dist: Optional[float]):
        if self._radar_oled:
            self._radar_oled.update(angle, dist)
            self._radar_oled.render()
        if self._radar_term:
            self._radar_term.update(angle, dist)

    # ------------------------------------------------------------------
    def start(self):
        self._stop_evt.clear()
        self._thread = threading.Thread(target=self._sweep_loop, daemon=True)
        self._thread.start()

    def stop(self):
        self._stop_evt.set()
        if self._thread:
            self._thread.join(timeout=3)
        self._servo.center()
        self._servo.cleanup()
        self._sensor.cleanup()

    # ------------------------------------------------------------------
    def run_oled(self, device):
        """Run sweep with OLED rendering. Blocks until stop() or KeyboardInterrupt."""
        self._radar_oled = OLEDRadar(device, self._max_range)
        self.start()
        try:
            while not self._stop_evt.is_set():
                time.sleep(0.1)
        except KeyboardInterrupt:
            pass
        finally:
            self.stop()

    def run_terminal(self):
        """Run sweep with curses terminal rendering. Blocks until Q pressed."""
        import curses

        self._radar_term = TerminalRadar(self._max_range)
        self.start()

        def _inner(stdscr):
            curses.curs_set(0)
            stdscr.nodelay(True)
            while not self._stop_evt.is_set():
                self._radar_term.draw(stdscr)
                key = stdscr.getch()
                if key in (ord('q'), ord('Q'), 27):
                    self.stop()
                    break
                time.sleep(0.05)

        try:
            curses.wrapper(_inner)
        finally:
            self.stop()
