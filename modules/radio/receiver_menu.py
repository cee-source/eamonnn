"""
Radio receiver menu — fully button-navigable.
Tune UP/DOWN with buttons, scan for stations, pick presets.
"""
import time
import logging

from core.menu import MenuEntry
from core.config_manager import ConfigManager

log = logging.getLogger(__name__)


def build_receiver_menu(config: ConfigManager, display=None) -> list[MenuEntry]:
    from modules.radio.radio_receiver import RadioReceiver, FM_PRESETS, RECEIVE_MODES
    rx = RadioReceiver(config)

    # Preset station entries
    preset_entries = [
        MenuEntry(
            label=name,
            action=lambda f=freq, n=name: _tune_to(rx, f, n, display)
        )
        for name, freq in FM_PRESETS.items()
        if freq is not None
    ]
    preset_entries.append(MenuEntry(
        label='Custom Frequency',
        action=lambda: _custom_tune(rx, display)
    ))

    # Mode entries
    mode_entries = [
        MenuEntry(
            label=f'{mode} - {desc}',
            action=lambda m=mode: _set_mode(rx, m, display)
        )
        for mode, desc in RECEIVE_MODES.items()
        if mode != 'RAW'
    ]

    return [
        MenuEntry(label='RX Status',         action=lambda: _status(rx, display)),
        MenuEntry(label='Preset Stations',    children=preset_entries),
        MenuEntry(label='Tune Manually',      action=lambda: _manual_tune(rx, display)),
        MenuEntry(label='Scan FM Band',       action=lambda: _scan(rx, display)),
        MenuEntry(label='Stop Radio',         action=lambda: _stop(rx, display)),
        MenuEntry(label='Change Mode',        children=mode_entries),
        MenuEntry(label='Hardware Guide',     action=lambda: _hw_guide(display)),
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


def _set_mode(rx, mode: str, display) -> None:
    rx._mode = mode
    _show(display, [f'Mode: {mode}', 'Will use on next tune'], pause=2.0)


# ---------------------------------------------------------------------------
# Tune to a frequency
# ---------------------------------------------------------------------------

def _tune_to(rx, freq_mhz: float, name: str, display) -> None:
    if rx.is_receiving:
        # Already on — just retune
        _show(display, [f'Tuning to...', f'{name}', f'{freq_mhz:.1f} MHz'], pause=0.8)
        ok = rx.tune(freq_mhz)
    else:
        _show(display, ['Starting radio...', f'{name}', f'{freq_mhz:.1f} MHz'], pause=0.8)
        ok = rx.start(freq_mhz, mode=rx.current_mode)

    if ok:
        # Show tuned-in display — UP/DOWN to retune, BACK to stop
        _tuner_display(rx, freq_mhz, display)
    else:
        _show(display, [
            'Failed to start!',
            'Check:',
            '1. RTL-SDR plugged in?',
            '2. USB audio adapter?',
            '3. sudo apt install rtl-sdr',
        ])


def _tuner_display(rx, start_freq: float, display) -> None:
    """Show live tuner on display. UP/DOWN tunes +/- 0.1 MHz."""
    if not display:
        input(f'Listening on {start_freq:.1f} MHz... ENTER to stop')
        rx.stop()
        return

    if not hasattr(display, 'getch'):
        return

    import curses
    freq = start_freq
    step = 0.1

    while rx.is_receiving:
        display.draw_message([
            f'>> RADIO ON <<',
            f'{freq:.1f} MHz {rx.current_mode}',
            '',
            f'UP   = +{step} MHz',
            f'DOWN = -{step} MHz',
            f'SEL  = step size',
            f'BACK = stop',
        ])

        ch = display.getch()
        if ch == curses.KEY_UP:
            freq = min(108.0, round(freq + step, 1))
            rx.tune(freq)
        elif ch == curses.KEY_DOWN:
            freq = max(76.0, round(freq - step, 1))
            rx.tune(freq)
        elif ch in (ord('\n'), ord('\r'), ord(' ')):
            # Cycle step size: 0.1 -> 0.5 -> 1.0 -> 0.1
            steps = [0.1, 0.5, 1.0]
            step = steps[(steps.index(step) + 1) % len(steps)]
        elif ch in (27, ord('q')):
            rx.stop()
            break

    _show(display, ['Radio stopped', f'{freq:.1f} MHz'], pause=2.0)


def _custom_tune(rx, display) -> None:
    try:
        freq = float(input('Frequency MHz (76–108): ').strip())
        freq = max(76.0, min(108.0, freq))
    except ValueError:
        _show(display, ['Invalid frequency'])
        return
    _tune_to(rx, freq, 'Custom', display)


def _manual_tune(rx, display) -> None:
    """Button-only frequency tuner — no typing needed."""
    if not display or not hasattr(display, 'getch'):
        _custom_tune(rx, display)
        return

    import curses
    freq = rx.current_freq if rx.is_receiving else 100.0
    step = 0.1
    steps = [0.1, 0.5, 1.0]

    while True:
        display.draw_message([
            'Manual Tune:',
            f'  {freq:.1f} MHz',
            f'  Step: {step} MHz',
            '',
            'UP/DN = tune',
            'SEL   = change step',
            'BACK  = start/stop',
        ])
        ch = display.getch()
        if ch == curses.KEY_UP:
            freq = min(108.0, round(freq + step, 1))
        elif ch == curses.KEY_DOWN:
            freq = max(76.0, round(freq - step, 1))
        elif ch in (ord('\n'), ord('\r'), ord(' ')):
            step = steps[(steps.index(step) + 1) % len(steps)]
        elif ch in (27, ord('q')):
            # BACK = start listening or go back if already playing
            if not rx.is_receiving:
                _tune_to(rx, freq, 'Manual', display)
            return


# ---------------------------------------------------------------------------
# FM band scan
# ---------------------------------------------------------------------------

def _scan(rx, display) -> None:
    if rx.is_receiving:
        _show(display, ['Stop radio first', 'before scanning'])
        return

    _show(display, [
        'FM Band Scan',
        '87.5 – 108.0 MHz',
        'Takes ~30 seconds...',
    ], pause=1.0)

    if display:
        display.draw_message(['Scanning...', 'Please wait'])

    stations = rx.scan_fm_band()

    if not stations:
        _show(display, ['No stations found', 'Check RTL-SDR is plugged in'])
        return

    # Show top stations, let user pick one
    top = stations[:6]
    labels = [f'{s["freq_mhz"]:.1f} MHz  {s["power_dbm"]:.0f}dBm' for s in top]

    if display and hasattr(display, 'getch'):
        import curses
        selected = 0
        while True:
            display.draw_menu(f'Found {len(stations)} stations:', labels, selected)
            ch = display.getch()
            if ch == curses.KEY_UP:
                selected = max(0, selected - 1)
            elif ch == curses.KEY_DOWN:
                selected = min(len(labels) - 1, selected + 1)
            elif ch in (ord('\n'), ord('\r'), ord(' ')):
                freq = top[selected]['freq_mhz']
                _tune_to(rx, freq, f'{freq:.1f} MHz', display)
                return
            elif ch in (27, ord('q')):
                return
    else:
        print(f'\nFound {len(stations)} stations:')
        for i, s in enumerate(top):
            print(f'  {i}: {s["freq_mhz"]:.1f} MHz  ({s["power_dbm"]:.0f} dBm)')
        try:
            idx = int(input('Select to tune (or ENTER to skip): ').strip())
            _tune_to(rx, top[idx]['freq_mhz'], '', display)
        except (ValueError, IndexError):
            pass


# ---------------------------------------------------------------------------
# Stop / status
# ---------------------------------------------------------------------------

def _stop(rx, display) -> None:
    if rx.is_receiving:
        rx.stop()
        _show(display, ['Radio stopped'], pause=2.0)
    else:
        _show(display, ['Radio not playing'], pause=2.0)


def _status(rx, display) -> None:
    s = rx.get_status()
    lines = [
        '>> ON AIR <<' if s['receiving'] else 'Radio off',
        f'{s["frequency_mhz"]:.1f} MHz {s["mode"]}' if s['receiving'] else '',
        f'RTL-SDR: {"OK" if s["rtlsdr_found"] else "NOT FOUND"}',
        f'Audio:   {"OK" if s["audio_found"] else "NOT FOUND"}',
    ]
    _show(display, [l for l in lines if l is not None], pause=4.0)


# ---------------------------------------------------------------------------
# Hardware guide
# ---------------------------------------------------------------------------

def _hw_guide(display) -> None:
    lines = [
        'Hardware needed:',
        '',
        '1. RTL-SDR dongle',
        '   ~£10 Amazon/Seeed',
        '   RTL2832U chip',
        '',
        '2. USB audio adapter',
        '   ~£3 Amazon',
        '   For headphones',
        '',
        '3. USB hub (Zero 2W',
        '   only has 1 port)',
    ]
    _show(display, lines[:8], pause=6.0)
