import os
import time
import logging

from core.menu import MenuEntry
from core.config_manager import ConfigManager

log = logging.getLogger(__name__)

PAYLOADS_DIR = os.path.join(os.path.dirname(__file__), 'payloads')


def build_badusb_menu(config: ConfigManager, display=None) -> list[MenuEntry]:
    from modules.badusb.hid_device import HIDDevice
    from modules.badusb.script_runner import ScriptRunner

    hid_path = config.get('badusb', 'hid_device', fallback='/dev/hidg0')

    return [
        MenuEntry(label='Run Payload',    action=lambda: _run_payload(hid_path, display)),
        MenuEntry(label='Type Text',      action=lambda: _type_text(hid_path, display)),
        MenuEntry(label='Saved Payloads', action=lambda: _list_payloads(display)),
        MenuEntry(label='HID Status',     action=lambda: _hid_status(hid_path, display)),
    ]


def _open_hid(hid_path: str):
    from modules.badusb.hid_device import HIDDevice
    hid = HIDDevice(hid_path)
    hid.open()
    return hid


def _run_payload(hid_path: str, display) -> None:
    payloads = [f for f in os.listdir(PAYLOADS_DIR) if f.endswith('.duck')]
    if not payloads:
        msg = ['No payloads found', f'Add .duck files to', 'modules/badusb/payloads/']
        if display:
            display.draw_message(msg)
            time.sleep(3)
        else:
            print('\n'.join(msg))
        return

    print('Available payloads:')
    for i, p in enumerate(payloads):
        print(f'  {i}: {p}')
    try:
        idx = int(input('Select index: '))
        payload_path = os.path.join(PAYLOADS_DIR, payloads[idx])
    except (ValueError, IndexError) as e:
        print(f'Invalid selection: {e}')
        return

    confirm = input(f'Run {payloads[idx]}? (yes/no): ').strip().lower()
    if confirm != 'yes':
        print('Cancelled')
        return

    try:
        hid = _open_hid(hid_path)
        from modules.badusb.script_runner import ScriptRunner
        runner = ScriptRunner(hid)
        runner.run_file(payload_path)
        hid.close()
        msg = ['Payload complete!', payloads[idx]]
    except Exception as e:
        msg = ['Error:', str(e)[:40]]
        log.error('Payload error: %s', e)

    if display:
        display.draw_message(msg)
        time.sleep(2)
    else:
        print('\n'.join(msg))


def _type_text(hid_path: str, display) -> None:
    text = input('Text to type: ')
    try:
        hid = _open_hid(hid_path)
        hid.type_string(text)
        hid.close()
        msg = ['Typed successfully!']
    except Exception as e:
        msg = ['Error:', str(e)[:40]]

    if display:
        display.draw_message(msg)
        time.sleep(2)
    else:
        print('\n'.join(msg))


def _list_payloads(display) -> None:
    payloads = [f for f in os.listdir(PAYLOADS_DIR) if f.endswith('.duck')]
    lines = [f'Payloads ({len(payloads)}):'] + payloads if payloads else ['No payloads']
    if display:
        display.draw_message(lines)
        time.sleep(3)
    else:
        print('\n'.join(lines))


def _hid_status(hid_path: str, display) -> None:
    exists = os.path.exists(hid_path)
    lines = [
        'HID Status:',
        f'{hid_path}',
        'READY' if exists else 'NOT FOUND',
        '' if exists else 'Run setup.sh first',
    ]
    if display:
        display.draw_message(lines)
        time.sleep(3)
    else:
        print('\n'.join(lines))
