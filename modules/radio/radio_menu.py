"""
Voice radio menu.
Fully button-navigable — pick mode, pick frequency, transmit.
"""
import time
import logging
import threading

from core.menu import MenuEntry
from core.config_manager import ConfigManager

log = logging.getLogger(__name__)


def build_radio_menu(config: ConfigManager, display=None) -> list[MenuEntry]:
    from modules.radio.voice_transmitter import VoiceTransmitter, PRESET_FREQUENCIES, MODES
    from modules.radio.receiver_menu import build_receiver_menu
    tx = VoiceTransmitter(config)

    # Preset frequency entries — one button starts transmitting
    freq_entries = []
    for label, freq in PRESET_FREQUENCIES.items():
        if freq is not None:
            freq_entries.append(MenuEntry(
                label=label,
                action=lambda f=freq, l=label: _live_tx_menu(tx, f, display)
            ))
    freq_entries.append(MenuEntry(
        label='Custom Frequency',
        action=lambda: _custom_freq(tx, display)
    ))

    # Mode select sub-menu
    mode_entries = [
        MenuEntry(label=f'{mode} - {desc}',
                  action=lambda m=mode: _set_mode(tx, m, display))
        for mode, desc in MODES.items()
    ]

    return [
        MenuEntry(label='-- Receive --',       action=None),
        MenuEntry(label='Play Radio',          children=build_receiver_menu(config, display)),
        MenuEntry(label='-- Transmit --',      action=None),
        MenuEntry(label='TX Status',           action=lambda: _status(tx, display)),
        MenuEntry(label='Live Transmit',       children=freq_entries),
        MenuEntry(label='Record & Transmit',   action=lambda: _record_tx(tx, display)),
        MenuEntry(label='Stop Transmitting',   action=lambda: _stop(tx, display)),
        MenuEntry(label='Change Mode',         children=mode_entries),
        MenuEntry(label='Setup Guide',         action=lambda: _setup_guide(display)),
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


def _pick_mode(tx, display) -> str:
    """Button-driven mode picker."""
    from modules.radio.voice_transmitter import MODES
    modes = list(MODES.keys())
    if display and hasattr(display, 'getch'):
        import curses
        selected = modes.index(tx.current_mode) if tx.current_mode in modes else 0
        while True:
            display.draw_menu('TX Mode?', modes, selected)
            ch = display.getch()
            if ch == curses.KEY_UP:
                selected = max(0, selected - 1)
            elif ch == curses.KEY_DOWN:
                selected = min(len(modes) - 1, selected + 1)
            elif ch in (ord('\n'), ord('\r'), ord(' ')):
                return modes[selected]
            elif ch in (27, ord('q')):
                return tx.current_mode
    else:
        print('Mode options:', ', '.join(modes))
        m = input(f'Mode [{tx.current_mode}]: ').strip().upper()
        return m if m in modes else tx.current_mode


def _set_mode(tx, mode: str, display) -> None:
    tx._mode = mode
    _show(display, [f'Mode set to {mode}', f'Next TX will use {mode}'], pause=2.0)


# ---------------------------------------------------------------------------
# Live transmit
# ---------------------------------------------------------------------------

def _live_tx_menu(tx, freq_mhz: float, display) -> None:
    if tx.is_transmitting:
        _show(display, [
            'Already Transmitting!',
            f'{tx.current_freq:.3f} MHz {tx.current_mode}',
            'Stop first',
        ])
        return

    mode = _pick_mode(tx, display)

    _show(display, [
        'Starting TX...',
        f'Freq:  {freq_mhz:.3f} MHz',
        f'Mode:  {mode}',
        'Speak into mic',
        'BACK = Stop',
    ], pause=1.5)

    ok = tx.transmit_live(freq_mhz, mode=mode)

    if ok:
        # Show live TX indicator until user presses BACK
        if display and hasattr(display, 'getch'):
            import curses
            while tx.is_transmitting:
                display.draw_message([
                    f'** ON AIR **',
                    f'{freq_mhz:.3f} MHz {mode}',
                    '',
                    'Press BACK to stop',
                ])
                ch = display.getch()
                if ch in (27, ord('q')):
                    break
            tx.stop()
            _show(display, ['TX Stopped', f'{freq_mhz:.3f} MHz'], pause=2.0)
        else:
            input('Transmitting... press ENTER to stop')
            tx.stop()
            print(f'TX stopped: {freq_mhz:.3f} MHz {mode}')
    else:
        _show(display, [
            'TX Failed!',
            'Check:',
            '1. rpitx installed?',
            '2. Mic connected?',
            '3. Run as root?',
        ])


def _custom_freq(tx, display) -> None:
    if display and hasattr(display, 'getch'):
        # Frequency tuner with UP/DOWN buttons
        import curses
        freq = 100.0
        step = 0.1
        steps = [0.1, 0.5, 1.0]
        step_idx = 0

        while True:
            display.draw_message([
                'Set Frequency:',
                f'  {freq:.1f} MHz',
                '',
                f'Step: {step} MHz',
                'UP/DN=tune  SEL=TX',
                'BACK=cancel',
            ])
            ch = display.getch()
            if ch == curses.KEY_UP:
                freq = min(108.0, round(freq + step, 1))
            elif ch == curses.KEY_DOWN:
                freq = max(76.0, round(freq - step, 1))
            elif ch == ord(' '):
                step_idx = (step_idx + 1) % len(steps)
                step = steps[step_idx]
            elif ch in (ord('\n'), ord('\r')):
                _live_tx_menu(tx, freq, display)
                return
            elif ch in (27, ord('q')):
                return
    else:
        try:
            freq = float(input('Frequency MHz (76.0–108.0): ').strip())
            freq = max(76.0, min(108.0, freq))
            _live_tx_menu(tx, freq, display)
        except ValueError:
            print('Invalid frequency')


# ---------------------------------------------------------------------------
# Record & transmit
# ---------------------------------------------------------------------------

def _record_tx(tx, display) -> None:
    if tx.is_transmitting:
        _show(display, ['Already transmitting!', 'Stop first'])
        return

    # Pick duration
    if display and hasattr(display, 'getch'):
        import curses
        options = ['3 seconds', '5 seconds', '10 seconds', '30 seconds']
        durations = [3, 5, 10, 30]
        selected = 1
        while True:
            display.draw_menu('Record duration?', options, selected)
            ch = display.getch()
            if ch == curses.KEY_UP:
                selected = max(0, selected - 1)
            elif ch == curses.KEY_DOWN:
                selected = min(len(options) - 1, selected + 1)
            elif ch in (ord('\n'), ord('\r'), ord(' ')):
                duration = durations[selected]
                break
            elif ch in (27, ord('q')):
                return
    else:
        try:
            duration = int(input('Record for how many seconds? [5]: ').strip() or '5')
        except ValueError:
            duration = 5

    # Pick frequency
    freq_str = input('Frequency MHz [100.0]: ').strip() or '100.0'
    try:
        freq = float(freq_str)
    except ValueError:
        freq = 100.0

    mode = _pick_mode(tx, display)

    _show(display, [
        f'Recording {duration}s...',
        'Speak NOW',
        '',
        f'Will TX on {freq:.1f} MHz',
    ], pause=0.5)

    ok = tx.record_then_transmit(
        freq_mhz=freq,
        record_s=float(duration),
        mode=mode,
    )

    _show(display, [
        'Done!' if ok else 'Failed',
        f'{freq:.1f} MHz {mode}',
        f'{duration}s recording',
    ])


# ---------------------------------------------------------------------------
# Stop / status
# ---------------------------------------------------------------------------

def _stop(tx, display) -> None:
    if tx.is_transmitting:
        tx.stop()
        _show(display, ['TX Stopped'], pause=2.0)
    else:
        _show(display, ['Not transmitting'], pause=2.0)


def _status(tx, display) -> None:
    s = tx.get_status()
    lines = [
        '** ON AIR **' if s['transmitting'] else 'Not transmitting',
        f'Freq: {s["frequency_mhz"]:.3f} MHz' if s['transmitting'] else '',
        f'Mode: {s["mode"]}',
        f'rpitx: {"OK" if s["rpitx_found"] else "NOT FOUND"}',
        f'Mic:   {"OK" if s["mic_found"] else "NOT FOUND"}',
    ]
    _show(display, [l for l in lines if l], pause=4.0)


# ---------------------------------------------------------------------------
# Setup guide
# ---------------------------------------------------------------------------

def _setup_guide(display) -> None:
    lines = [
        'Radio TX Setup:',
        '',
        '1. Wire: GPIO4 -> 20cm',
        '   wire as antenna',
        '',
        '2. Install rpitx:',
        '   git clone rpitx repo',
        '   sudo ./install.sh',
        '',
        '3. USB mic or I2S',
        '   mic module',
        '',
        '4. Tune FM radio to',
        '   your chosen freq',
    ]
    _show(display, lines[:8], pause=6.0)
