import logging
import time

from core.menu import MenuEntry
from core.config_manager import ConfigManager

log = logging.getLogger(__name__)


def build_camera_menu(config: ConfigManager, display=None) -> list[MenuEntry]:
    from modules.camera.camera_capture import CameraCapture
    from modules.camera.camera_qr import QRScanner

    capture = CameraCapture(config, display)
    qr = QRScanner()

    return [
        MenuEntry(label='Take Photo',   action=lambda: _take_photo(capture, display)),
        MenuEntry(label='Scan QR Code', action=lambda: _scan_qr(qr, display)),
        MenuEntry(label='Saved Photos', action=lambda: _list_saved(capture, display)),
    ]


def _take_photo(capture, display) -> None:
    if display:
        display.draw_message(['Camera', 'Capturing...'])
    name = input('Photo name: ').strip() or 'photo'
    try:
        result = capture.capture(name)
        lines = [
            'Captured!',
            f'File: {result["filename"]}',
            f'Via:  {result["backend"]}',
        ]
    except Exception as e:
        lines = ['Capture failed', str(e)[:40]]
        log.error('Capture error: %s', e)

    if display:
        display.draw_message(lines)
        time.sleep(3)
    else:
        print('\n'.join(lines))


def _scan_qr(qr, display) -> None:
    if not qr.available():
        lines = ['QR scan unavailable', 'pip install pyzbar', 'opencv-python']
        if display:
            display.draw_message(lines)
            time.sleep(3)
        else:
            print('\n'.join(lines))
        return

    if display:
        display.draw_message(['QR Scanner', 'Aim at code...'])
    print('Scanning (10s)...')

    results = qr.scan(timeout_s=10.0)
    if results:
        lines = [f'{r["type"]}: {r["data"][:40]}' for r in results]
    else:
        lines = ['Nothing detected', 'Timed out after 10s']

    if display:
        display.draw_message(lines)
        time.sleep(3)
    else:
        print('\n'.join(lines))


def _list_saved(capture, display) -> None:
    files = capture.list_saved()
    if not files:
        lines = ['No photos saved']
    else:
        lines = [f'Photos ({len(files)}):'] + [f[:30] for f in files[:8]]

    if display:
        display.draw_message(lines)
        time.sleep(3)
    else:
        print('\n'.join(lines))
