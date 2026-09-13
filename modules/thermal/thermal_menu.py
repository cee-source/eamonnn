import logging
import time

from core.config_manager import ConfigManager
from core.menu import MenuEntry

log = logging.getLogger(__name__)


def build_thermal_menu(config: ConfigManager, display=None) -> list[MenuEntry]:
    from modules.thermal.thermal_cam import ThermalCam

    cam = ThermalCam(config)

    return [
        MenuEntry(label='Live View', action=lambda: _live_view(cam, display)),
        MenuEntry(label='Snapshot',  action=lambda: _snapshot(cam, config, display)),
    ]


def _live_view(cam, display, duration_s: float = 20.0) -> None:
    cols, rows = (26, 5) if display else (64, 20)
    end = time.time() + duration_s
    while time.time() < end:
        frame = cam.read_frame()
        if frame is None:
            continue
        lines, lo, hi = cam.render_ascii(frame, cols, rows)
        lines.append(f'{lo:.1f}C .. {hi:.1f}C')
        if display:
            display.draw_message(lines)
        else:
            print('\x1b[2J\x1b[H' + '\n'.join(lines))
        time.sleep(0.2)


def _snapshot(cam, config, display) -> None:
    frame = cam.read_frame()
    if frame is None:
        lines = ['Sensor read failed', 'Check I2C wiring']
    else:
        saved = config.save_capture('thermal', {'frame': frame, 'w': 32, 'h': 24}, prefix='thermal')
        lines, lo, hi = cam.render_ascii(frame, 26, 5)
        lines.append(f'{lo:.1f}C .. {hi:.1f}C')
        lines.append(f'Saved: {saved.split("/")[-1]}')

    if display:
        display.draw_message(lines)
        time.sleep(3)
    else:
        print('\n'.join(lines))
