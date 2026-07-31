"""
Display abstraction layer.
Priority: TouchDisplay (3.5" TFT) → OLEDDisplay (SSD1306) → TerminalDisplay (curses).
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


# ---------------------------------------------------------------------------
# TouchDisplay backend (pygame → /dev/fb1 framebuffer, 320×480)
# ---------------------------------------------------------------------------

class TouchDisplay(DisplayDriver):
    """
    3.5" TFT touchscreen (320×480) via pygame + Linux framebuffer.

    One-time Pi setup:
        sudo apt install python3-pygame
        # Add to /boot/config.txt (Waveshare/MPI3501 HAT):
        #   dtoverlay=piscreen,speed=16000000,rotate=90
        # Reboot, then the screen appears as /dev/fb1 and touch as
        # /dev/input/touchscreen.
    """

    W       = 320
    H       = 480
    TITLE_H = 48
    ITEM_H  = 58
    BACK_H  = 52

    # Palette
    C_BG     = ( 10,  12,  20)
    C_TITLE  = ( 18,  22,  38)
    C_PANEL  = ( 22,  26,  42)
    C_SEL    = (  0, 110, 255)
    C_ACCENT = (  0, 155,  80)
    C_TEXT   = (210, 215, 230)
    C_BRIGHT = (255, 255, 255)
    C_DIV    = ( 40,  45,  65)

    def __init__(self, config=None) -> None:
        import os
        import pygame
        os.environ.setdefault('SDL_FBDEV',       '/dev/fb1')
        os.environ.setdefault('SDL_VIDEODRIVER',  'fbcon')
        os.environ.setdefault('SDL_MOUSEDEV',    '/dev/input/touchscreen')
        os.environ.setdefault('SDL_MOUSEDRV',    'EV')
        pygame.init()
        pygame.mouse.set_visible(False)
        self._pg     = pygame
        self._screen = pygame.display.set_mode((self.W, self.H), pygame.FULLSCREEN)
        self._ft     = pygame.font.SysFont('freemono', 22, bold=True)
        self._fi     = pygame.font.SysFont('freemono', 20)
        self._fs     = pygame.font.SysFont('freemono', 16)
        self._zones: list[tuple[int, int, object]] = []  # (y0, y1, 'back'|int)
        log.info('TouchDisplay ready %dx%d', self.W, self.H)

    def draw_menu(self, title: str, items: list[str], selected: int) -> None:
        pg = self._pg
        self._zones = []
        self._screen.fill(self.C_BG)

        # Title bar
        pg.draw.rect(self._screen, self.C_TITLE, (0, 0, self.W, self.TITLE_H))
        hdr = self._ft.render(f'PiFlip  {title}', True, self.C_BRIGHT)
        self._screen.blit(hdr, (10, (self.TITLE_H - hdr.get_height()) // 2))
        pg.draw.line(self._screen, self.C_DIV,
                     (0, self.TITLE_H), (self.W, self.TITLE_H), 2)

        # Items (scrollable)
        avail   = self.H - self.TITLE_H - self.BACK_H
        max_vis = avail // self.ITEM_H
        start   = max(0, selected - max_vis + 1)

        for i, label in enumerate(items[start: start + max_vis]):
            idx = start + i
            y   = self.TITLE_H + i * self.ITEM_H
            sel = (idx == selected)
            pg.draw.rect(self._screen,
                         self.C_SEL if sel else self.C_PANEL,
                         (0, y, self.W, self.ITEM_H - 2), border_radius=4)
            surf = self._fi.render(f'  {label}',
                                   True, self.C_BRIGHT if sel else self.C_TEXT)
            self._screen.blit(surf, (8, y + (self.ITEM_H - surf.get_height()) // 2))
            pg.draw.line(self._screen, self.C_DIV,
                         (0, y + self.ITEM_H - 1), (self.W, y + self.ITEM_H - 1), 1)
            self._zones.append((y, y + self.ITEM_H, idx))

        # Back button
        by = self.H - self.BACK_H
        pg.draw.rect(self._screen, self.C_ACCENT, (0, by, self.W, self.BACK_H))
        bs = self._fi.render('< BACK', True, self.C_BRIGHT)
        self._screen.blit(bs, (10, by + (self.BACK_H - bs.get_height()) // 2))
        self._zones.append((by, self.H, 'back'))

        pg.display.flip()

    def draw_message(self, lines: list[str]) -> None:
        pg = self._pg
        self._zones = [(0, self.H, 'back')]
        self._screen.fill(self.C_BG)
        pg.draw.rect(self._screen, self.C_TITLE, (0, 0, self.W, self.TITLE_H))
        hdr = self._ft.render('PiFlip', True, self.C_BRIGHT)
        self._screen.blit(hdr, (10, (self.TITLE_H - hdr.get_height()) // 2))
        y = self.TITLE_H + 16
        for line in lines:
            surf = self._fi.render(str(line)[:32], True, self.C_TEXT)
            self._screen.blit(surf, (10, y))
            y += surf.get_height() + 8
        hint = self._fs.render('Tap anywhere to go back', True, self.C_DIV)
        self._screen.blit(hint, (10, self.H - 28))
        pg.display.flip()

    def draw_progress(self, label: str, value: int, max_val: int) -> None:
        pg = self._pg
        self._screen.fill(self.C_BG)
        pct    = int(100 * value / max(max_val, 1))
        filled = int((self.W - 20) * pct / 100)
        lbl = self._ft.render(label, True, self.C_TEXT)
        self._screen.blit(lbl, (10, 60))
        pg.draw.rect(self._screen, self.C_PANEL,
                     (10, 130, self.W - 20, 40), border_radius=6)
        if filled:
            pg.draw.rect(self._screen, self.C_SEL,
                         (10, 130, filled, 40), border_radius=6)
        pct_s = self._ft.render(f'{pct}%', True, self.C_BRIGHT)
        self._screen.blit(pct_s,
                          (self.W // 2 - pct_s.get_width() // 2, 185))
        pg.display.flip()

    def get_tap(self) -> Optional[tuple[int, int]]:
        """Non-blocking; returns (x, y) of a touch event or None."""
        for event in self._pg.event.get():
            if event.type == self._pg.MOUSEBUTTONDOWN:
                return event.pos
        return None

    def tap_to_zone(self, x: int, y: int) -> Optional[str]:
        """Convert touch coords to 'BACK' or 'JUMP:N'."""
        for y0, y1, target in self._zones:
            if y0 <= y < y1:
                return 'BACK' if target == 'back' else f'JUMP:{target}'
        return None

    def clear(self) -> None:
        self._screen.fill(self.C_BG)
        self._pg.display.flip()

    def cleanup(self) -> None:
        self._pg.quit()
