import time
import logging

from core.menu import MenuEntry
from core.config_manager import ConfigManager

log = logging.getLogger(__name__)


def build_subghz_menu(config: ConfigManager, display=None) -> list[MenuEntry]:
    from modules.subghz.subghz_capture import SubGHzCapture
    from modules.subghz.subghz_replay import SubGHzReplay

    capture = SubGHzCapture(config)
    replay = SubGHzReplay(config)

    return [
        MenuEntry(label='Scan 433 MHz',    action=lambda: _scan(capture, config, 433.92, display)),
        MenuEntry(label='Scan 315 MHz',    action=lambda: _scan(capture, config, 315.0,  display)),
        MenuEntry(label='Scan 868 MHz',    action=lambda: _scan(capture, config, 868.35, display)),
        MenuEntry(label='Custom Scan',     action=lambda: _custom_scan(capture, config, display)),
        MenuEntry(label='Replay Saved',    action=lambda: _replay_saved(replay, config, display)),
        MenuEntry(label='Saved Signals',   action=lambda: _list_saved(config, display)),
    ]


def _scan(capture, config, freq_mhz: float, display, duration_s: float = 3.0) -> None:
    if display:
        display.draw_message([
            f'SubGHz Scan',
            f'Freq: {freq_mhz} MHz',
            'Listening...',
        ])
    name = input(f'Signal name [{freq_mhz}MHz]: ').strip() or f'sig_{freq_mhz}'
    result = capture.capture(freq_mhz=freq_mhz, duration_s=duration_s, name=name)
    if result:
        saved = config.save_capture('subghz', result, prefix=name)
        lines = [
            'Captured!',
            f'{freq_mhz} MHz {result["modulation"]}',
            f'Packets: {result["packet_count"]}',
            f'Saved: {saved.split("/")[-1]}',
        ]
    else:
        lines = ['No signal detected', f'at {freq_mhz} MHz']

    if display:
        display.draw_message(lines)
        time.sleep(3)
    else:
        print('\n'.join(lines))


def _custom_scan(capture, config, display) -> None:
    try:
        freq = float(input('Frequency (MHz): '))
        mod = input('Modulation [ASK_OOK/2FSK/GFSK]: ').strip() or 'ASK_OOK'
        baud = int(input('Baud rate [4800]: ').strip() or '4800')
    except ValueError as e:
        print(f'Invalid input: {e}')
        return
    _scan(capture, config, freq, display)


def _replay_saved(replay, config, display) -> None:
    captures = config.load_captures('subghz')
    if not captures:
        msg = ['No saved SubGHz signals']
        if display:
            display.draw_message(msg)
            time.sleep(2)
        else:
            print(msg[0])
        return

    print('Saved signals:')
    for i, c in enumerate(captures):
        d = c['data']
        print(f'  {i}: {c["filename"]} ({d.get("frequency_mhz","?")} MHz)')
    try:
        idx = int(input('Select index: '))
        signal = captures[idx]['data']
        repeat = int(input('Repeat count [3]: ').strip() or '3')
        ok = replay.replay(signal, repeat=repeat)
        msg = [f'Replayed x{repeat}!' if ok else 'Replay failed']
    except (ValueError, IndexError) as e:
        msg = [f'Error: {e}']

    if display:
        display.draw_message(msg)
        time.sleep(2)
    else:
        print(msg[0])


def _list_saved(config, display) -> None:
    captures = config.load_captures('subghz')
    if not captures:
        lines = ['No saved SubGHz signals']
    else:
        lines = [f'SubGHz ({len(captures)}):'] + [
            f'{c["filename"][:20]} {c["data"].get("frequency_mhz","?")}MHz'
            for c in captures
        ]
    if display:
        display.draw_message(lines)
        time.sleep(3)
    else:
        print('\n'.join(lines))
