"""
Display abstraction layer.
Auto-detects OLED (SSD1306 via luma.oled) or falls back to terminal (curses).
"""
from __future__ import annotations

import curses
import logging
from abc import ABC, abstractmethod
from typing import Optional

log = logging.getLogger(__name__)

DISPLAY_WIDTH = 128
DISPLAY_HEIGHT = 64
FONT_H = 10   # pixels per text row on OLED


class DisplayDriver(ABC):
    @abstractmethod
    def draw_menu(self, title: str, items: list[str], selected: int) -> None: ...

    @abstractmethod
    def draw_message(self, lines: list[str]) -> None: ...

    @abstractmethod
    def draw_progress(self, label: str, value: int, max_val: int) -> None: ...

    @abstractmethod
    def clear(self) -> None: ...

    @abstractmethod
    def cleanup(self) -> None: ...


# ---------------------------------------------------------------------------
# OLED backend (luma.oled + Pillow)
# ---------------------------------------------------------------------------

class OLEDDisplay(DisplayDriver):
    def __init__(self, config) -> None:
        from luma.core.interface.serial import i2c
        from luma.oled.device import ssd1306
        from PIL import ImageFont

        port = config.getint('hardware', 'oled_i2c_port', fallback=1)
        addr = int(config.get('hardware', 'oled_i2c_address', fallback='0x3C'), 16)
        serial = i2c(port=port, address=addr)
        self._device = ssd1306(serial, width=DISPLAY_WIDTH, height=DISPLAY_HEIGHT)

        try:
            self._font = ImageFont.truetype('/usr/share/fonts/truetype/dejavu/DejaVuSansMono.ttf', 9)
        except OSError:
            self._font = ImageFont.load_default()

        log.info('OLED display initialised at I2C %s port %d', hex(addr), port)

    def _canvas(self):
        from luma.core.render import canvas
        return canvas(self._device)

    def draw_menu(self, title: str, items: list[str], selected: int) -> None:
        from PIL import ImageDraw
        with self._canvas() as draw:
            draw.text((0, 0), title, font=self._font, fill='white')
            draw.line([(0, FONT_H), (DISPLAY_WIDTH, FONT_H)], fill='white')
            visible = (DISPLAY_HEIGHT - FONT_H - 2) // FONT_H
            start = max(0, selected - visible + 1)
            for i, item in enumerate(items[start: start + visible]):
                y = FONT_H + 2 + i * FONT_H
                idx = start + i
                if idx == selected:
                    draw.rectangle([(0, y), (DISPLAY_WIDTH, y + FONT_H)], fill='white')
                    draw.text((2, y), f'> {item}', font=self._font, fill='black')
                else:
                    draw.text((2, y), f'  {item}', font=self._font, fill='white')

    def draw_message(self, lines: list[str]) -> None:
        with self._canvas() as draw:
            for i, line in enumerate(lines[:6]):
                draw.text((0, i * FONT_H), line, font=self._font, fill='white')

    def draw_progress(self, label: str, value: int, max_val: int) -> None:
        with self._canvas() as draw:
            draw.text((0, 0), label, font=self._font, fill='white')
            bar_w = DISPLAY_WIDTH - 4
            filled = int(bar_w * value / max(max_val, 1))
            draw.rectangle([(2, 20), (DISPLAY_WIDTH - 2, 34)], outline='white')
            if filled:
                draw.rectangle([(2, 20), (2 + filled, 34)], fill='white')
            pct = f'{int(100 * value / max(max_val, 1))}%'
            draw.text((DISPLAY_WIDTH // 2 - 10, 38), pct, font=self._font, fill='white')

    def clear(self) -> None:
        self._device.clear()

    def cleanup(self) -> None:
        self.clear()
        self._device.cleanup()


# ---------------------------------------------------------------------------
# Terminal backend (curses)
# ---------------------------------------------------------------------------

class TerminalDisplay(DisplayDriver):
    def __init__(self, config=None) -> None:
        self._stdscr: Optional[curses.window] = None
        self._init_curses()

    def _init_curses(self) -> None:
        self._stdscr = curses.initscr()
        curses.noecho()
        curses.cbreak()
        curses.curs_set(0)
        self._stdscr.keypad(True)
        if curses.has_colors():
            curses.start_color()
            curses.init_pair(1, curses.COLOR_BLACK, curses.COLOR_WHITE)  # selected
            curses.init_pair(2, curses.COLOR_CYAN, curses.COLOR_BLACK)   # title
        log.info('Terminal (curses) display initialised')

    def draw_menu(self, title: str, items: list[str], selected: int) -> None:
        if not self._stdscr:
            return
        self._stdscr.clear()
        h, w = self._stdscr.getmaxyx()
        # Title bar
        title_str = f' PiFlip | {title} '
        try:
            self._stdscr.addstr(0, 0, title_str.ljust(w)[:w - 1],
                                curses.color_pair(2) | curses.A_BOLD)
        except curses.error:
            pass
        visible = h - 3
        start = max(0, selected - visible + 1)
        for i, item in enumerate(items[start: start + visible]):
            idx = start + i
            y = i + 2
            if y >= h - 1:
                break
            prefix = '> ' if idx == selected else '  '
            line = f'{prefix}{item}'
            try:
                if idx == selected:
                    self._stdscr.addstr(y, 0, line.ljust(w)[:w - 1], curses.color_pair(1))
                else:
                    self._stdscr.addstr(y, 0, line[:w - 1])
            except curses.error:
                pass
        self._stdscr.refresh()

    def draw_message(self, lines: list[str]) -> None:
        if not self._stdscr:
            return
        self._stdscr.clear()
        h, w = self._stdscr.getmaxyx()
        for i, line in enumerate(lines):
            if i >= h - 1:
                break
            try:
                self._stdscr.addstr(i, 0, line[:w - 1])
            except curses.error:
                pass
        self._stdscr.addstr(min(len(lines) + 1, h - 1), 0, '[BACK to continue]')
        self._stdscr.refresh()

    def draw_progress(self, label: str, value: int, max_val: int) -> None:
        if not self._stdscr:
            return
        self._stdscr.clear()
        h, w = self._stdscr.getmaxyx()
        pct = int(100 * value / max(max_val, 1))
        bar_w = w - 4
        filled = int(bar_w * pct / 100)
        bar = '[' + '#' * filled + '-' * (bar_w - filled) + ']'
        try:
            self._stdscr.addstr(0, 0, label[:w - 1])
            self._stdscr.addstr(2, 0, bar[:w - 1])
            self._stdscr.addstr(3, 0, f'{pct}%')
        except curses.error:
            pass
        self._stdscr.refresh()

    def getch(self) -> int:
        if self._stdscr:
            return self._stdscr.getch()
        return -1

    def clear(self) -> None:
        if self._stdscr:
            self._stdscr.clear()
            self._stdscr.refresh()

    def cleanup(self) -> None:
        if self._stdscr:
            self._stdscr.keypad(False)
            curses.nocbreak()
            curses.echo()
            curses.endwin()
            self._stdscr = None
