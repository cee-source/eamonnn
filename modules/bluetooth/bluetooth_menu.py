"""
Bluetooth menu — BLE advertisement spam + device scanner.
All preset payloads are one button press. Custom message requires typing.
"""
import time
import logging
import threading

from core.menu import MenuEntry
from core.config_manager import ConfigManager

log = logging.getLogger(__name__)


def build_bluetooth_menu(config: ConfigManager, display=None) -> list[MenuEntry]:
    from modules.bluetooth.ble_advertiser import BLEAdvertiser, APPLE_PAYLOADS, SAMSUNG_PAYLOADS
    adv = BLEAdvertiser()

    # Build Apple sub-menu entries dynamically from payload list
    apple_entries = [
        MenuEntry(
            label=name,
            action=lambda n=name: _spam_apple(adv, n, display)
        )
        for name in APPLE_PAYLOADS
    ]

    # Build Android sub-menu entries
    android_entries = [
        MenuEntry(
            label=name,
            action=lambda n=name: _spam_android(adv, n, display)
        )
        for name in SAMSUNG_PAYLOADS
    ]

    return [
        MenuEntry(label='Scan Nearby',        action=lambda: _scan(adv, display)),
        MenuEntry(label='Custom Message',      action=lambda: _custom_spam(adv, display)),
        MenuEntry(label='iOS / Apple Popups',  children=apple_entries),
        MenuEntry(label='Android Popups',      children=android_entries),
        MenuEntry(label='BT Status',           action=lambda: _status(adv, display)),
    ]


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _show(display, lines: list[str], pause: float = 3.0) -> None:
    if display:
        display.draw_message(lines)
        time.sleep(pause)
    else:
        print('\n'.join(lines))


def _get_duration(display) -> float:
    """Ask user for spam duration."""
    if display and hasattr(display, 'getch'):
        # Button-driven: cycle through preset durations
        options = ['10s', '30s', '60s', '5 min', 'Until stopped']
        seconds = [10, 30, 60, 300, 9999]
        import curses
        selected = 1  # default 30s
        while True:
            display.draw_menu('Duration?', options, selected)
            ch = display.getch()
            if ch == curses.KEY_UP:
                selected = max(0, selected - 1)
            elif ch == curses.KEY_DOWN:
                selected = min(len(options) - 1, selected + 1)
            elif ch in (ord('\n'), ord('\r'), ord(' ')):
                return float(seconds[selected])
            elif ch in (27, ord('q')):
                return 30.0
    else:
        try:
            return float(input('Duration in seconds [30]: ').strip() or '30')
        except ValueError:
            return 30.0


def _spam_in_thread(fn, display, label: str) -> None:
    """Run spam in background thread, show live countdown on display."""
    _show(display, [f'Spamming:', label, 'Press BACK to stop...'], pause=0.5)
    t = threading.Thread(target=fn, daemon=True)
    t.start()
    # Wait for thread or user interrupt
    while t.is_alive():
        time.sleep(0.5)
    _show(display, ['Done!', label], pause=2.0)


# ---------------------------------------------------------------------------
# Actions
# ---------------------------------------------------------------------------

def _spam_apple(adv, payload_name: str, display) -> None:
    duration = _get_duration(display)
    _show(display, [
        'Apple Popup Spam',
        payload_name,
        f'Duration: {duration:.0f}s',
        'Sending...',
    ], pause=1.0)
    try:
        adv.spam_apple(payload_name, duration_s=duration)
        _show(display, ['Done!', f'{payload_name}', f'Ran for {duration:.0f}s'])
    except Exception as e:
        _show(display, ['Error:', str(e)[:40]])


def _spam_android(adv, payload_name: str, display) -> None:
    duration = _get_duration(display)
    _show(display, [
        'Android Popup Spam',
        payload_name,
        f'Duration: {duration:.0f}s',
        'Sending...',
    ], pause=1.0)
    try:
        adv.spam_android(payload_name, duration_s=duration)
        _show(display, ['Done!', payload_name, f'Ran for {duration:.0f}s'])
    except Exception as e:
        _show(display, ['Error:', str(e)[:40]])


def _custom_spam(adv, display) -> None:
    message = input('Custom message (max 28 chars): ').strip()[:28]
    if not message:
        return

    # Choose target
    if display and hasattr(display, 'getch'):
        import curses
        options = ['Apple (iPhone)', 'Android', 'Both']
        selected = 0
        while True:
            display.draw_menu('Target device?', options, selected)
            ch = display.getch()
            if ch == curses.KEY_UP:
                selected = max(0, selected - 1)
            elif ch == curses.KEY_DOWN:
                selected = min(len(options) - 1, selected + 1)
            elif ch in (ord('\n'), ord('\r'), ord(' ')):
                break
        targets = ['apple', 'android', 'both'][selected]
    else:
        t = input('Target (apple/android/both) [apple]: ').strip().lower() or 'apple'
        targets = t

    duration = _get_duration(display)

    _show(display, [
        'Custom BLE Spam',
        f'Msg: {message}',
        f'Target: {targets}',
        'Sending...',
    ], pause=1.0)

    try:
        if targets == 'both':
            adv.spam_custom(message, target='apple',   duration_s=duration / 2)
            adv.spam_custom(message, target='android', duration_s=duration / 2)
        else:
            adv.spam_custom(message, target=targets, duration_s=duration)
        _show(display, ['Done!', f'"{message}"'])
    except Exception as e:
        _show(display, ['Error:', str(e)[:40]])


def _scan(adv, display) -> None:
    _show(display, ['BLE Scan', 'Scanning 10s...', 'Please wait...'], pause=1.0)
    devices = adv.scan_nearby(duration_s=10.0)
    if not devices:
        _show(display, ['No devices found'])
        return
    lines = [f'Found {len(devices)} devices:'] + [
        f'{d["mac"]}  {d["name"][:16]}'
        for d in devices[:7]
    ]
    _show(display, lines, pause=5.0)


def _status(adv, display) -> None:
    available = adv.is_available()
    lines = [
        'Bluetooth: READY' if available else 'Bluetooth: NOT FOUND',
    ]
    if not available:
        lines += ['Install BlueZ:', 'sudo apt install bluez']
    _show(display, lines)
