"""
Stack-based menu engine.
Input: GPIO buttons (UP/DOWN/SELECT/BACK) or keyboard arrow keys.
Renders through DisplayDriver abstraction.
"""
from __future__ import annotations

import curses
import logging
import threading
from dataclasses import dataclass, field
from typing import Callable, Optional

from core.display import DisplayDriver, TerminalDisplay, TouchDisplay

log = logging.getLogger(__name__)

KEY_UP = 'UP'
KEY_DOWN = 'DOWN'
KEY_SELECT = 'SELECT'
KEY_BACK = 'BACK'


@dataclass
class MenuEntry:
    label: str
    action: Optional[Callable] = None
    children: list['MenuEntry'] = field(default_factory=list)


class InputHandler:
    """Reads from GPIO buttons or keyboard depending on available hardware."""

    def __init__(self, config, display: DisplayDriver) -> None:
        self._display = display
        self._queue: list[str] = []
        self._lock = threading.Lock()
        self._gpio_ok = False
        self._config = config
        self._setup_gpio()

    def _setup_gpio(self) -> None:
        try:
            import RPi.GPIO as GPIO
            GPIO.setmode(GPIO.BCM)
            pins = {
                KEY_UP:     self._config.getint('hardware', 'btn_up', fallback=17),
                KEY_DOWN:   self._config.getint('hardware', 'btn_down', fallback=27),
                KEY_SELECT: self._config.getint('hardware', 'btn_select', fallback=22),
                KEY_BACK:   self._config.getint('hardware', 'btn_back', fallback=5),
            }
            for key, pin in pins.items():
                GPIO.setup(pin, GPIO.IN, pull_up_down=GPIO.PUD_UP)
                GPIO.add_event_detect(pin, GPIO.FALLING,
                                      callback=lambda ch, k=key: self._enqueue(k),
                                      bouncetime=200)
            self._gpio_ok = True
            log.info('GPIO buttons initialised')
        except Exception as e:
            log.info('GPIO not available (%s), using keyboard input', e)

    def _enqueue(self, key: str) -> None:
        with self._lock:
            self._queue.append(key)

    def get_key(self) -> Optional[str]:
        """Non-blocking if GPIO/touch; blocking keyboard read if terminal."""
        # GPIO buttons (highest priority — always checked)
        if self._gpio_ok:
            with self._lock:
                if self._queue:
                    return self._queue.pop(0)

        # Touch input
        if isinstance(self._display, TouchDisplay):
            tap = self._display.get_tap()
            if tap:
                return self._display.tap_to_zone(*tap)
            return None

        # Keyboard fallback via curses
        if isinstance(self._display, TerminalDisplay):
            self._display._stdscr.timeout(100)
            ch = self._display.getch()
            mapping = {
                curses.KEY_UP: KEY_UP,
                curses.KEY_DOWN: KEY_DOWN,
                ord('\n'): KEY_SELECT,
                ord('\r'): KEY_SELECT,
                27: KEY_BACK,
                ord('q'): KEY_BACK,
                ord('w'): KEY_UP,
                ord('s'): KEY_DOWN,
                ord(' '): KEY_SELECT,
            }
            return mapping.get(ch)
        return None

    def cleanup(self) -> None:
        if self._gpio_ok:
            try:
                import RPi.GPIO as GPIO
                GPIO.cleanup()
            except Exception:
                pass


class MenuEngine:
    def __init__(self, display: DisplayDriver, config) -> None:
        self._display = display
        self._input = InputHandler(config, display)
        self._stack: list[tuple[list[MenuEntry], int]] = []  # (entries, selected_idx)
        self._running = False

    def push(self, entries: list[MenuEntry]) -> None:
        self._stack.append((entries, 0))

    def pop(self) -> None:
        if len(self._stack) > 1:
            self._stack.pop()

    def _current(self) -> tuple[list[MenuEntry], int]:
        return self._stack[-1]

    def _set_selected(self, idx: int) -> None:
        entries, _ = self._stack[-1]
        self._stack[-1] = (entries, idx)

    def run(self) -> None:
        self._running = True
        log.info('Menu engine started')

        while self._running and self._stack:
            entries, selected = self._current()
            labels = [e.label for e in entries]
            self._display.draw_menu('Main Menu' if len(self._stack) == 1 else '', labels, selected)

            key = self._input.get_key()
            if key is None:
                continue

            if key == KEY_UP:
                self._set_selected(max(0, selected - 1))

            elif key == KEY_DOWN:
                self._set_selected(min(len(entries) - 1, selected + 1))

            elif key == KEY_SELECT or (key and key.startswith('JUMP:')):
                if key and key.startswith('JUMP:'):
                    selected = int(key.split(':', 1)[1])
                    self._set_selected(selected)
                entry = entries[selected]
                if entry.children:
                    self.push(entry.children)
                elif entry.action:
                    try:
                        self._display.clear()
                        entry.action()
                    except Exception as e:
                        log.error('Action error: %s', e)
                        self._display.draw_message([
                            'Error:',
                            str(e)[:40],
                            '',
                            '[BACK to continue]'
                        ])
                        self._wait_back()

            elif key == KEY_BACK or key == 'BACK':
                self.pop()

        self._input.cleanup()
        self._display.cleanup()
        log.info('Menu engine stopped')

    def _wait_back(self) -> None:
        while True:
            key = self._input.get_key()
            if key == KEY_BACK:
                break

    def stop(self) -> None:
        self._running = False
