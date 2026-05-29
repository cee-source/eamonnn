import os
import time
import logging

from core.menu import MenuEntry
from core.config_manager import ConfigManager

log = logging.getLogger(__name__)

PAYLOADS_DIR = os.path.join(os.path.dirname(__file__), 'payloads')


def build_badusb_menu(config: ConfigManager, display=None) -> list[MenuEntry]:
    hid_path = config.get('badusb', 'hid_device', fallback='/dev/hidg0') if config else '/dev/hidg0'

    return [
        MenuEntry(label='USB (Wired)',     children=_build_usb_menu(hid_path, display)),
        MenuEntry(label='Bluetooth (BT)',  children=_build_bt_menu(display)),
        MenuEntry(label='Saved Payloads',  action=lambda: _list_payloads(display)),
    ]


# ---------------------------------------------------------------------------
# USB wired submenu
# ---------------------------------------------------------------------------

def _build_usb_menu(hid_path: str, display) -> list[MenuEntry]:
    return [
        MenuEntry(label='Run Payload', action=lambda: _run_payload_usb(hid_path, display)),
        MenuEntry(label='Type Text',   action=lambda: _type_text_usb(hid_path, display)),
        MenuEntry(label='HID Status',  action=lambda: _hid_status(hid_path, display)),
    ]


def _open_usb(hid_path: str):
    from modules.badusb.hid_device import HIDDevice
    hid = HIDDevice(hid_path)
    hid.open()
    return hid


def _run_payload_usb(hid_path: str, display) -> None:
    payload_path, name = _pick_payload(display)
    if payload_path is None:
        return
    try:
        hid = _open_usb(hid_path)
        from modules.badusb.script_runner import ScriptRunner
        ScriptRunner(hid).run_file(payload_path)
        hid.close()
        _msg(display, 'USB: Done!', name)
    except Exception as e:
        _msg(display, 'USB Error', str(e)[:40])
        log.error('USB payload error: %s', e)


def _type_text_usb(hid_path: str, display) -> None:
    text = input('Text to type: ')
    try:
        hid = _open_usb(hid_path)
        hid.type_string(text)
        hid.close()
        _msg(display, 'USB: Typed!', '')
    except Exception as e:
        _msg(display, 'USB Error', str(e)[:40])


def _hid_status(hid_path: str, display) -> None:
    exists = os.path.exists(hid_path)
    _msg(display,
         'HID: READY' if exists else 'HID: NOT FOUND',
         hid_path if exists else 'Run setup.sh first')


# ---------------------------------------------------------------------------
# Bluetooth wireless submenu
# ---------------------------------------------------------------------------

def _build_bt_menu(display) -> list[MenuEntry]:
    return [
        MenuEntry(label='Pair & Run Payload', action=lambda: _bt_run_payload(display)),
        MenuEntry(label='Pair & Type Text',   action=lambda: _bt_type_text(display)),
        MenuEntry(label='BT Status',          action=lambda: _bt_status(display)),
    ]


def _open_bt(display, timeout: int = 60):
    """Advertise PiFlip as BT keyboard and wait for host to connect."""
    from modules.badusb.bt_hid_device import BTHIDDevice
    _msg(display, 'BT: Advertising', '"PiFlip Keyboard"')
    dev = BTHIDDevice()
    dev.advertise()
    _msg(display, 'BT: Waiting...', f'Connect on target ({timeout}s)')
    if not dev.wait_for_connection(timeout):
        raise ConnectionError('No host connected in time')
    _msg(display, 'BT: Connected!', 'Running payload...')
    time.sleep(0.5)
    return dev


def _bt_run_payload(display) -> None:
    payload_path, name = _pick_payload(display)
    if payload_path is None:
        return
    try:
        dev = _open_bt(display)
        from modules.badusb.script_runner import ScriptRunner
        ScriptRunner(dev).run_file(payload_path)
        dev.close()
        _msg(display, 'BT: Done!', name)
    except Exception as e:
        _msg(display, 'BT Error', str(e)[:40])
        log.error('BT payload error: %s', e)


def _bt_type_text(display) -> None:
    text = input('Text to type via BT: ')
    try:
        dev = _open_bt(display)
        dev.type_string(text)
        dev.close()
        _msg(display, 'BT: Typed!', '')
    except Exception as e:
        _msg(display, 'BT Error', str(e)[:40])


def _bt_status(display) -> None:
    result = __import__('subprocess').run(
        ['hciconfig', 'hci0'], capture_output=True, text=True)
    up = 'UP' in result.stdout
    _msg(display, 'BT Adapter:', 'UP & ready' if up else 'DOWN / missing')


# ---------------------------------------------------------------------------
# Shared helpers
# ---------------------------------------------------------------------------

def _pick_payload(display) -> tuple:
    """Print payload list, prompt for selection. Returns (path, name) or (None, None)."""
    payloads = [f for f in os.listdir(PAYLOADS_DIR) if f.endswith('.duck')]
    if not payloads:
        _msg(display, 'No payloads', 'Add .duck files to', secs=3)
        return None, None

    print('Available payloads:')
    for i, p in enumerate(payloads):
        print(f'  {i}: {p}')
    try:
        idx  = int(input('Select index: '))
        name = payloads[idx]
        path = os.path.join(PAYLOADS_DIR, name)
    except (ValueError, IndexError) as e:
        print(f'Invalid: {e}')
        return None, None

    confirm = input(f'Run {name}? (yes/no): ').strip().lower()
    if confirm != 'yes':
        print('Cancelled')
        return None, None
    return path, name


def _list_payloads(display) -> None:
    payloads = [f for f in os.listdir(PAYLOADS_DIR) if f.endswith('.duck')]
    lines = [f'Payloads ({len(payloads)}):'] + payloads if payloads else ['No payloads']
    if display:
        display.draw_message(lines)
        time.sleep(3)
    else:
        print('\n'.join(lines))


def _msg(display, title: str, body: str = '', secs: int = 2) -> None:
    if display:
        display.draw_message([title, body])
        time.sleep(secs)
    else:
        print(f'{title} {body}')
