import time
import logging

from core.menu import MenuEntry
from core.config_manager import ConfigManager

log = logging.getLogger(__name__)


def build_ir_menu(config: ConfigManager, display=None) -> list[MenuEntry]:
    from modules.infrared.ir_capture import IRCapture
    from modules.infrared.ir_replay import IRReplay

    capture = IRCapture(config)
    replay = IRReplay(config)

    return [
        MenuEntry(label='Capture Signal',  action=lambda: _capture(capture, config, display)),
        MenuEntry(label='Replay Saved',    action=lambda: _replay_menu(replay, config, display)),
        MenuEntry(label='Saved Signals',   action=lambda: _list_saved(config, display)),
    ]


def _capture(capture, config, display) -> None:
    if display:
        display.draw_message(['IR Capture', 'Point remote at receiver', 'Press button now...'])
    name = input('Signal name (e.g. TV_POWER): ').strip() or 'signal'
    result = capture.capture(timeout_s=10.0, name=name)
    if result:
        saved = config.save_capture('ir', result, prefix=name)
        lines = [
            'Captured!',
            f'Protocol: {result["protocol"]}',
            f'Pulses: {result["pulse_count"]}',
        ]
        if result['address'] is not None:
            lines.append(f'Addr: 0x{result["address"]:02X}  Cmd: 0x{result["command"]:02X}')
        lines.append(f'Saved: {saved.split("/")[-1]}')
    else:
        lines = ['No signal detected', 'Timed out']

    if display:
        display.draw_message(lines)
        time.sleep(3)
    else:
        print('\n'.join(lines))


def _replay_menu(replay, config, display) -> None:
    captures = config.load_captures('ir')
    if not captures:
        msg = ['No saved IR signals']
        if display:
            display.draw_message(msg)
            time.sleep(2)
        else:
            print(msg[0])
        return

    print('Saved signals:')
    for i, c in enumerate(captures):
        print(f'  {i}: {c["filename"]}')
    try:
        idx = int(input('Select index: '))
        signal = captures[idx]['data']
        ok = replay.replay(signal)
        msg = ['Replayed!' if ok else 'Replay failed']
    except (ValueError, IndexError) as e:
        msg = [f'Error: {e}']

    if display:
        display.draw_message(msg)
        time.sleep(2)
    else:
        print(msg[0])


def _list_saved(config, display) -> None:
    captures = config.load_captures('ir')
    if not captures:
        lines = ['No saved IR signals']
    else:
        lines = [f'IR Signals ({len(captures)}):'] + [
            f'{c["filename"][:28]} [{c["data"].get("protocol","?")}]'
            for c in captures
        ]
    if display:
        display.draw_message(lines)
        time.sleep(3)
    else:
        print('\n'.join(lines))
