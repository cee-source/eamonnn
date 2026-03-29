"""
Cat Videos module for PiFlip.

On OLED  : plays pixel-art ASCII-style cat animations (frame-by-frame Pillow rendering).
On HDMI  : launches mpv to stream a cat video from the internet (requires mpv + network).
Terminal : plays ANSI ASCII-art cat animations full-screen via curses.
"""

import time
import threading
import subprocess
import os
from typing import List, Tuple, Optional

# ---------------------------------------------------------------------------
# ASCII art cat frames (21-char wide, 9-line tall — fits SSD1306 at 6×7 font)
# ---------------------------------------------------------------------------

NYAN_FRAMES: List[List[str]] = [
    [
        r"  /\_____/\  ",
        r" ( o     o ) ",
        r" (  =   =  ) ",
        r"  \ ~w~w~ /  ",
        r"  /|     |\  ",
        r" /_|_____|_\ ",
        r"   |     |   ",
        r"  /|     |\  ",
        r" * * * * * * ",
    ],
    [
        r"  /\_____/\  ",
        r" ( ^     ^ ) ",
        r" (  =   =  ) ",
        r"  \ ~w~w~ /  ",
        r"  /|     |\  ",
        r" /_|_____|_\ ",
        r"   |     |   ",
        r"  _|_____|_  ",
        r" * * * * * * ",
    ],
    [
        r"  /\_____/\  ",
        r" ( -     - ) ",
        r" (  =   =  ) ",
        r"  \ ~w~w~ /  ",
        r"  /|     |\  ",
        r" /_|_____|_\ ",
        r"   |     |   ",
        r"  /|     |\  ",
        r" * * * * * * ",
    ],
    [
        r"  /\_____/\  ",
        r" ( o     o ) ",
        r" (  =   =  ) ",
        r"  \  vvv  /  ",
        r"  /|     |\  ",
        r" /_|_____|_\ ",
        r"   |     |   ",
        r"  _|_____|_  ",
        r" * * * * * * ",
    ],
]

WALKING_CAT_FRAMES: List[List[str]] = [
    [
        r"    /\   /\   ",
        r"   (  o o  )  ",
        r"   =( Y )=    ",
        r"    )   (     ",
        r"   (_)-(_)    ",
        r"              ",
        r" >meow meow<  ",
        r"              ",
        r"              ",
    ],
    [
        r"    /\   /\   ",
        r"   (  - -  )  ",
        r"   =( Y )=    ",
        r"    )   (     ",
        r"   (_)_(_)    ",
        r"              ",
        r" >meow meow<  ",
        r"              ",
        r"              ",
    ],
    [
        r"    /\   /\   ",
        r"   (  ^ ^  )  ",
        r"   =( Y )=    ",
        r"    )   (     ",
        r"   (_)-(_)    ",
        r"              ",
        r" >meow meow<  ",
        r"              ",
        r"              ",
    ],
    [
        r"    /\   /\   ",
        r"   (  o o  )  ",
        r"   =( Y )=    ",
        r"    )   (     ",
        r"   (_)_(_)    ",
        r"              ",
        r" >meow meow<  ",
        r"              ",
        r"              ",
    ],
]

LOAF_CAT_FRAMES: List[List[str]] = [
    [
        r"   ________   ",
        r"  /  /\__/\   ",
        r" | (  o  o )  ",
        r" | (  =w=  )  ",
        r"  \  ____/    ",
        r"   |_|  |_|   ",
        r"              ",
        r"  loaf mode   ",
        r"              ",
    ],
    [
        r"   ________   ",
        r"  /  /\__/\   ",
        r" | (  -  - )  ",
        r" | (  =w=  )  ",
        r"  \  ____/    ",
        r"   |_|  |_|   ",
        r"              ",
        r"  loaf mode   ",
        r"              ",
    ],
]

ANIMATIONS = [
    ("Nyan Cat",    NYAN_FRAMES,        0.15),
    ("Walking Cat", WALKING_CAT_FRAMES, 0.20),
    ("Loaf Cat",    LOAF_CAT_FRAMES,    0.50),
]

# ---------------------------------------------------------------------------
# OLED renderer
# ---------------------------------------------------------------------------

def _play_oled(display, frames: List[List[str]], fps: float, stop_event: threading.Event):
    """Render ASCII frames onto the OLED via Pillow."""
    try:
        from PIL import Image, ImageDraw, ImageFont
        font = ImageFont.load_default()
    except ImportError:
        display.draw_message("PIL missing", "pip install pillow")
        time.sleep(2)
        return

    frame_delay = fps
    while not stop_event.is_set():
        for frame in frames:
            if stop_event.is_set():
                return
            img = Image.new("1", (128, 64), 0)
            draw = ImageDraw.Draw(img)
            for row_idx, line in enumerate(frame[:9]):
                draw.text((0, row_idx * 7), line[:21], font=font, fill=1)
            display.device.display(img)
            time.sleep(frame_delay)


# ---------------------------------------------------------------------------
# Terminal renderer
# ---------------------------------------------------------------------------

def _play_terminal(frames: List[List[str]], fps: float, stop_event: threading.Event,
                   label: str):
    import curses

    def _inner(stdscr):
        curses.curs_set(0)
        stdscr.nodelay(True)
        frame_delay = fps
        while not stop_event.is_set():
            for frame in frames:
                if stop_event.is_set():
                    return
                stdscr.clear()
                h, w = stdscr.getmaxyx()
                title = f"  {label}  (press any key to stop)"
                stdscr.addstr(0, max(0, (w - len(title)) // 2), title)
                for row_idx, line in enumerate(frame):
                    y = row_idx + 2
                    if y >= h - 1:
                        break
                    x = max(0, (w - len(line)) // 2)
                    try:
                        stdscr.addstr(y, x, line)
                    except curses.error:
                        pass
                stdscr.refresh()
                key = stdscr.getch()
                if key != -1:
                    stop_event.set()
                    return
                time.sleep(frame_delay)

    curses.wrapper(_inner)


# ---------------------------------------------------------------------------
# HDMI mpv playback
# ---------------------------------------------------------------------------

# Royalty-free / CC0 Big Buck Bunny cat clip via yt-dlp / direct mp4
# Using a well-known short open-licensed cat clip.
CAT_VIDEO_URLS = [
    # These are placeholder search queries — mpv can open YouTube URLs directly
    # if yt-dlp is installed.  Falls back to a direct mp4.
    "https://www.youtube.com/watch?v=2XID_W4neJo",   # Famous cat compilation (CC)
    "https://www.youtube.com/watch?v=W86cTIoMv2U",   # Nyan Cat original
]


def play_hdmi(url: str = CAT_VIDEO_URLS[0]) -> Tuple[bool, str]:
    """Launch mpv to play a cat video on HDMI output.  Returns (success, message)."""
    if subprocess.run(["which", "mpv"], capture_output=True).returncode != 0:
        return False, "mpv not found. Run: sudo apt install mpv"
    if subprocess.run(["which", "yt-dlp"], capture_output=True).returncode != 0:
        # Try without yt-dlp — mpv may still handle it
        pass
    try:
        env = os.environ.copy()
        env["DISPLAY"] = ":0"          # HDMI framebuffer
        proc = subprocess.Popen(
            ["mpv", "--fs", "--really-quiet", "--no-terminal", url],
            env=env,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
        return True, f"Playing on HDMI (PID {proc.pid}). Ctrl+C or Q to stop."
    except Exception as exc:
        return False, str(exc)


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

class CatPlayer:
    """Manages cat animation playback with start/stop control."""

    def __init__(self, display):
        self._display = display
        self._stop = threading.Event()
        self._thread: Optional[threading.Thread] = None

    def play_animation(self, index: int = 0):
        """Play animation by index (0=Nyan, 1=Walking, 2=Loaf). Blocks until stopped."""
        label, frames, fps = ANIMATIONS[index % len(ANIMATIONS)]
        self._stop.clear()

        has_oled = hasattr(self._display, "device")

        if has_oled:
            _play_oled(self._display, frames, fps, self._stop)
        else:
            _play_terminal(frames, fps, self._stop, label)

    def stop(self):
        self._stop.set()

    def play_on_hdmi(self, url_index: int = 0) -> Tuple[bool, str]:
        return play_hdmi(CAT_VIDEO_URLS[url_index % len(CAT_VIDEO_URLS)])
