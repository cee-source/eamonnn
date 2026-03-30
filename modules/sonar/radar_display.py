"""
Radar sweep display for PiFlip OLED (128x64) and terminal.

OLED layout (128x64):
  - Semicircle radar centred at bottom-centre (64, 63)
  - Radius = 55 px  → fills the display nicely
  - 3 range rings at 25%, 50%, 75% of max range
  - Rotating sweep line (green-ish = bright pixel)
  - Detected objects as bright dots that fade over time
  - Distance + angle readout at top-left

Terminal layout:
  - 40-char wide × 20-line ASCII radar using curses
  - . = empty space  O = detected object  / = sweep line
"""

import math
import time
import threading
from collections import deque
from typing import List, Tuple, Optional, Deque

# (angle_deg, distance_cm, timestamp)
Hit = Tuple[float, float, float]


# ---------------------------------------------------------------------------
# OLED renderer
# ---------------------------------------------------------------------------

class OLEDRadar:
    """Draws the radar sweep on a 128×64 SSD1306 via Pillow."""

    CX     = 64     # centre X (horizontal middle)
    CY     = 63     # centre Y (bottom of screen)
    RADIUS = 55     # px

    FADE_SECS = 5.0  # how long hits stay visible

    def __init__(self, device, max_range_cm: float = 300.0):
        self._device      = device
        self._max_range   = max_range_cm
        self._hits: Deque[Hit] = deque(maxlen=60)
        self._sweep_angle = 0.0   # degrees (0=left, 90=up, 180=right)
        self._lock        = threading.Lock()

    def update(self, angle_deg: float, distance_cm: Optional[float]):
        with self._lock:
            self._sweep_angle = angle_deg
            if distance_cm is not None:
                self._hits.append((angle_deg, distance_cm, time.time()))

    def _polar_to_xy(self, angle_deg: float, distance_cm: float) -> Tuple[int, int]:
        """Convert sonar polar coords to OLED pixel coords."""
        # angle 0° = left edge, 90° = straight up, 180° = right edge
        rad    = math.radians(angle_deg)
        ratio  = min(distance_cm / self._max_range, 1.0)
        px_r   = ratio * self.RADIUS
        x = int(self.CX + px_r * math.cos(math.pi - rad))
        y = int(self.CY - px_r * math.sin(rad))
        return x, y

    def render(self):
        """Render one frame onto the OLED device."""
        try:
            from PIL import Image, ImageDraw, ImageFont
        except ImportError:
            return

        img  = Image.new("1", (128, 64), 0)
        draw = ImageDraw.Draw(img)
        font = ImageFont.load_default()

        # --- range rings ---
        for frac in (0.25, 0.50, 0.75, 1.0):
            r = int(self.RADIUS * frac)
            # arc: bounding box for full circle, but we only draw the top half
            bbox = [self.CX - r, self.CY - r, self.CX + r, self.CY + r]
            draw.arc(bbox, start=180, end=0, fill=1)

        # --- centre cross ---
        draw.line([(self.CX - 2, self.CY), (self.CX + 2, self.CY)], fill=1)
        draw.line([(self.CX, self.CY - 2), (self.CX, self.CY)],     fill=1)

        # --- sweep line ---
        with self._lock:
            sweep = self._sweep_angle
            hits  = list(self._hits)

        rad   = math.radians(sweep)
        sx    = int(self.CX + self.RADIUS * math.cos(math.pi - rad))
        sy    = int(self.CY - self.RADIUS * math.sin(rad))
        draw.line([(self.CX, self.CY), (sx, sy)], fill=1)

        # --- hits (fade by age) ---
        now = time.time()
        for angle, dist, ts in hits:
            age = now - ts
            if age > self.FADE_SECS:
                continue
            hx, hy = self._polar_to_xy(angle, dist)
            # bright dot: 3x3 square
            draw.rectangle([hx - 1, hy - 1, hx + 1, hy + 1], fill=1)

        # --- text readout ---
        nearest = None
        with self._lock:
            recent = [(d, a) for a, d, ts in self._hits
                      if time.time() - ts < 2.0]
        if recent:
            nearest = min(recent, key=lambda x: x[0])
            draw.text((0, 0), f"{nearest[0]:.0f}cm @{nearest[1]:.0f}°",
                      font=font, fill=1)
        else:
            draw.text((0, 0), f"Sweep {sweep:.0f}°", font=font, fill=1)

        self._device.display(img)


# ---------------------------------------------------------------------------
# Terminal renderer
# ---------------------------------------------------------------------------

class TerminalRadar:
    """ASCII radar for curses terminal (40 cols × 20 rows)."""

    W = 40
    H = 20
    CX = 20
    CY = 19   # bottom row
    R  = 18

    FADE_SECS = 6.0

    def __init__(self, max_range_cm: float = 300.0):
        self._max_range   = max_range_cm
        self._hits: Deque[Hit] = deque(maxlen=60)
        self._sweep_angle = 0.0
        self._lock        = threading.Lock()

    def update(self, angle_deg: float, distance_cm: Optional[float]):
        with self._lock:
            self._sweep_angle = angle_deg
            if distance_cm is not None:
                self._hits.append((angle_deg, distance_cm, time.time()))

    def _polar_to_rc(self, angle_deg: float, distance_cm: float) -> Tuple[int, int]:
        rad   = math.radians(angle_deg)
        ratio = min(distance_cm / self._max_range, 1.0)
        r     = ratio * self.R
        col = int(self.CX + r * math.cos(math.pi - rad))
        row = int(self.CY - r * math.sin(rad))
        return row, col

    def draw(self, stdscr):
        import curses
        h, w = stdscr.getmaxyx()
        offset_col = max(0, (w - self.W) // 2)
        offset_row = 1

        with self._lock:
            sweep = self._sweep_angle
            hits  = list(self._hits)

        # Build char grid
        grid = [['.' for _ in range(self.W)] for _ in range(self.H)]

        # Range arcs (every 25%)
        for frac in (0.25, 0.5, 0.75, 1.0):
            r = self.R * frac
            for deg in range(0, 181, 2):
                rad = math.radians(deg)
                col = int(self.CX + r * math.cos(math.pi - rad))
                row = int(self.CY - r * math.sin(rad))
                if 0 <= row < self.H and 0 <= col < self.W:
                    grid[row][col] = '-'

        # Sweep line
        rad = math.radians(sweep)
        for t_frac in [i / 20 for i in range(1, 21)]:
            r   = t_frac * self.R
            col = int(self.CX + r * math.cos(math.pi - rad))
            row = int(self.CY - r * math.sin(rad))
            if 0 <= row < self.H and 0 <= col < self.W:
                grid[row][col] = '/'

        # Hits
        now = time.time()
        for angle, dist, ts in hits:
            if now - ts > self.FADE_SECS:
                continue
            row, col = self._polar_to_rc(angle, dist)
            if 0 <= row < self.H and 0 <= col < self.W:
                grid[row][col] = 'O'

        # Centre
        grid[self.CY][self.CX] = '+'

        # Render
        stdscr.clear()
        title = " PiFlip SONAR  (Q=quit) "
        try:
            stdscr.addstr(0, offset_col, title)
        except curses.error:
            pass

        for row_idx, row in enumerate(grid):
            line = ''.join(row)
            try:
                stdscr.addstr(offset_row + row_idx, offset_col, line)
            except curses.error:
                pass

        # Status line
        recent = [(d, a) for a, d, ts in hits if now - ts < 2.0]
        if recent:
            nearest = min(recent, key=lambda x: x[0])
            status = f" Nearest: {nearest[0]:.0f}cm @ {nearest[1]:.0f}deg "
        else:
            status = f" Sweep: {sweep:.0f} deg    no target "
        try:
            stdscr.addstr(offset_row + self.H, offset_col, status)
        except curses.error:
            pass

        stdscr.refresh()
