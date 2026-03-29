"""
ADS-B aircraft tracker menu.
Live list of nearby planes — callsign, altitude, speed, distance.
Auto-refreshes every second on OLED or terminal.
"""
import time
import logging
import threading

from core.menu import MenuEntry
from core.config_manager import ConfigManager

log = logging.getLogger(__name__)


def build_aircraft_menu(config: ConfigManager, display=None) -> list[MenuEntry]:
    from modules.aircraft.adsb_tracker import ADSBTracker
    tracker = ADSBTracker(config)

    return [
        MenuEntry(label='Start Tracking',    action=lambda: _start_tracking(tracker, display)),
        MenuEntry(label='Live Aircraft List', action=lambda: _live_list(tracker, display)),
        MenuEntry(label='Nearest Aircraft',  action=lambda: _nearest(tracker, display)),
        MenuEntry(label='Set Home Location', action=lambda: _set_home(tracker, display)),
        MenuEntry(label='Stop Tracker',      action=lambda: _stop(tracker, display)),
        MenuEntry(label='ADS-B Status',      action=lambda: _status(tracker, display)),
    ]


def _show(display, lines: list[str], pause: float = 3.0) -> None:
    if display:
        display.draw_message(lines)
        time.sleep(pause)
    else:
        print('\n'.join(lines))


# ---------------------------------------------------------------------------
# Start / stop
# ---------------------------------------------------------------------------

def _start_tracking(tracker, display) -> None:
    if tracker.is_running:
        _show(display, ['Already running!', f'{tracker.get_count()} aircraft tracked'])
        return

    _show(display, ['Starting ADS-B...', 'Launching dump1090', 'Please wait...'], pause=1.0)
    ok = tracker.start()
    if ok:
        _show(display, [
            'ADS-B Active!',
            'Tracking 1090 MHz',
            'Select Live List',
            'to see aircraft',
        ])
    else:
        _show(display, [
            'Failed to start!',
            'Install dump1090:',
            'sudo apt install',
            'dump1090-mutability',
        ])


def _stop(tracker, display) -> None:
    tracker.stop()
    _show(display, ['Tracker stopped'], pause=2.0)


# ---------------------------------------------------------------------------
# Live aircraft list — auto-refreshes
# ---------------------------------------------------------------------------

def _live_list(tracker, display) -> None:
    if not tracker.is_running:
        _show(display, ['Tracker not running', 'Start tracking first'])
        return

    if display and hasattr(display, 'getch'):
        import curses
        selected = 0
        while True:
            aircraft = tracker.get_aircraft()
            if not aircraft:
                lines = [
                    f'ADS-B Live',
                    '0 aircraft',
                    '',
                    'Waiting for',
                    'signals...',
                    'BACK = exit',
                ]
                display.draw_message(lines)
            else:
                labels = [ac.summary(tracker._home_lat, tracker._home_lon)
                          for ac in aircraft[:8]]
                header = f'Aircraft: {len(aircraft)}'
                display.draw_menu(header, labels, selected)

            display._stdscr.timeout(1000)   # refresh every second
            ch = display.getch()
            if ch == curses.KEY_UP:
                selected = max(0, selected - 1)
            elif ch == curses.KEY_DOWN:
                aircraft = tracker.get_aircraft()
                selected = min(max(len(aircraft) - 1, 0), selected + 1)
            elif ch in (ord('\n'), ord('\r'), ord(' ')):
                aircraft = tracker.get_aircraft()
                if aircraft and selected < len(aircraft):
                    _show_detail(aircraft[selected], tracker, display)
            elif ch in (27, ord('q')):
                break
    else:
        print('\nLive aircraft (press Ctrl+C to stop):')
        try:
            while True:
                aircraft = tracker.get_aircraft()
                print(f'\033[H\033[J', end='')  # clear screen
                print(f'ADS-B Live — {len(aircraft)} aircraft\n')
                print(f'{"Callsign":<9} {"Alt":>7} {"Spd":>5} {"Dist":>7} {"Hdg":>4}')
                print('-' * 40)
                for ac in aircraft[:15]:
                    print(ac.summary(tracker._home_lat, tracker._home_lon))
                time.sleep(1)
        except KeyboardInterrupt:
            pass


def _show_detail(ac, tracker, display) -> None:
    dist = ac.distance_nm(tracker._home_lat, tracker._home_lon)
    vr = ac.vrate or 0
    vr_str = f'{"CLB" if vr > 0 else "DSC" if vr < 0 else "LVL"} {abs(vr)}fpm'
    lines = [
        f'{(ac.callsign or ac.icao).strip()}',
        f'ICAO:  {ac.icao}',
        f'Alt:   {ac.altitude_ft or "?"}ft',
        f'Speed: {int(ac.speed_kts or 0)}kts',
        f'Hdg:   {int(ac.heading or 0)}°',
        f'Dist:  {dist:.1f}nm' if dist else 'Dist:  ???',
        f'{vr_str}',
        f'Msgs:  {ac.msgs}',
    ]
    _show(display, lines, pause=5.0)


def _nearest(tracker, display) -> None:
    if not tracker.is_running:
        _show(display, ['Tracker not running', 'Start tracking first'])
        return
    aircraft = tracker.get_aircraft()
    if not aircraft:
        _show(display, ['No aircraft detected', 'Waiting for signals...'])
        return
    _show_detail(aircraft[0], tracker, display)


# ---------------------------------------------------------------------------
# Set home location
# ---------------------------------------------------------------------------

def _set_home(tracker, display) -> None:
    _show(display, ['Set Home Location', 'Enter your coords', 'for distance calc'], pause=0.5)
    try:
        lat = float(input('Latitude  (e.g. 40.7128): ').strip())
        lon = float(input('Longitude (e.g. -74.006): ').strip())
        tracker.set_home(lat, lon)
        _show(display, ['Home set!', f'Lat: {lat:.4f}', f'Lon: {lon:.4f}'])
    except ValueError:
        _show(display, ['Invalid coordinates'])


# ---------------------------------------------------------------------------
# Status
# ---------------------------------------------------------------------------

def _status(tracker, display) -> None:
    lines = [
        'ADS-B Status:',
        f'Running: {"YES" if tracker.is_running else "NO"}',
        f'Aircraft: {tracker.get_count()}',
        f'dump1090: {"OK" if tracker.dump1090_available() else "NOT FOUND"}',
        '',
        'Install:',
        'sudo apt install',
        'dump1090-mutability',
    ]
    _show(display, lines, pause=4.0)
