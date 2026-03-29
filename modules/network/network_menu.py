"""
Network tools menu: WiFi scanner, port scanner, deauth tester.
"""
import time
import logging

from core.menu import MenuEntry
from core.config_manager import ConfigManager

log = logging.getLogger(__name__)


def build_network_menu(config: ConfigManager, display=None) -> list[MenuEntry]:
    from modules.network.wifi_scanner  import WiFiScanner
    from modules.network.port_scanner  import PortScanner, get_local_network, get_local_ip
    from modules.network.deauth_tester import DeauthTester

    wifi    = WiFiScanner()
    scanner = PortScanner()
    deauth  = DeauthTester()

    return [
        # WiFi
        MenuEntry(label='-- WiFi --',         action=None),
        MenuEntry(label='Scan Networks',       action=lambda: _wifi_scan(wifi, display)),

        # Port scanner
        MenuEntry(label='-- Port Scanner --',  action=None),
        MenuEntry(label='Scan This Device',    action=lambda: _scan_self(scanner, display)),
        MenuEntry(label='Scan Custom Host',    action=lambda: _scan_host(scanner, display)),
        MenuEntry(label='Scan Network',        action=lambda: _scan_network(scanner, display)),

        # Deauth tester
        MenuEntry(label='-- Deauth Tester --', action=None),
        MenuEntry(label='Scan APs',            action=lambda: _scan_aps(deauth, display)),
        MenuEntry(label='Test My Network',     action=lambda: _deauth_test(deauth, display)),

        # Info
        MenuEntry(label='My IP Address',       action=lambda: _my_ip(display)),
    ]


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _show(display, lines: list[str], pause: float = 4.0) -> None:
    if display:
        display.draw_message(lines)
        time.sleep(pause)
    else:
        print('\n'.join(lines))


def _progress(display, label: str, done: int, total: int) -> None:
    if display:
        display.draw_progress(label, done, total)
    else:
        pct = int(100 * done / max(total, 1))
        print(f'\r{label}: {pct}%', end='', flush=True)


# ---------------------------------------------------------------------------
# WiFi scanner
# ---------------------------------------------------------------------------

def _wifi_scan(wifi, display) -> None:
    _show(display, ['WiFi Scan', 'Scanning...', 'Please wait'], pause=0.5)

    networks = wifi.scan()

    if not networks:
        _show(display, ['No networks found', 'Check wlan0 is up'])
        return

    if display and hasattr(display, 'getch'):
        import curses
        selected = 0
        while True:
            labels = [n.summary() for n in networks[:10]]
            display.draw_menu(f'Networks: {len(networks)}', labels, selected)
            ch = display.getch()
            if ch == curses.KEY_UP:
                selected = max(0, selected - 1)
            elif ch == curses.KEY_DOWN:
                selected = min(len(labels) - 1, selected + 1)
            elif ch in (ord('\n'), ord('\r'), ord(' ')):
                n = networks[selected]
                _show(display, [
                    n.ssid or '<hidden>',
                    f'BSSID: {n.bssid}',
                    f'Signal: {n.signal_dbm}dBm {n.signal_bar}',
                    f'Channel: {n.channel}',
                    f'Security: {n.security}',
                ], pause=4.0)
            elif ch in (27, ord('q')):
                break
    else:
        print(f'\n{"SSID":<18} {"Signal":>8} {"Ch":>4} {"Security":<10}')
        print('-' * 44)
        for n in networks:
            print(n.summary())


# ---------------------------------------------------------------------------
# Port scanner
# ---------------------------------------------------------------------------

def _scan_self(scanner, display) -> None:
    from modules.network.port_scanner import get_local_ip
    ip = get_local_ip()
    _show(display, ['Scanning local device', f'IP: {ip}', 'Please wait...'], pause=0.5)
    result = scanner.scan_host(
        ip,
        progress_cb=lambda d, t: _progress(display, 'Scanning', d, t)
    )
    _show_scan_result(result, display)


def _scan_host(scanner, display) -> None:
    host = input('Enter IP or hostname: ').strip()
    if not host:
        return
    _show(display, [f'Scanning {host}', 'Please wait...'], pause=0.5)
    result = scanner.scan_host(
        host,
        progress_cb=lambda d, t: _progress(display, 'Scanning', d, t)
    )
    _show_scan_result(result, display)


def _scan_network(scanner, display) -> None:
    from modules.network.port_scanner import get_local_network
    net = get_local_network()
    if not net:
        _show(display, ['Could not detect network'])
        return
    confirm = input(f'Scan {net}? (yes/no): ').strip().lower()
    if confirm != 'yes':
        return

    _show(display, [f'Scanning {net}', 'Finding live hosts...'], pause=0.5)
    results = scanner.scan_network(
        net,
        progress_cb=lambda d, t: _progress(display, 'Scanning', d, t)
    )

    if not results:
        _show(display, ['No hosts with open ports', f'on {net}'])
        return

    if display and hasattr(display, 'getch'):
        import curses
        selected = 0
        while True:
            labels = [f'{r["host"]} ({len(r["open_ports"])} ports)' for r in results]
            display.draw_menu(f'Hosts: {len(results)}', labels, selected)
            ch = display.getch()
            if ch == curses.KEY_UP:
                selected = max(0, selected - 1)
            elif ch == curses.KEY_DOWN:
                selected = min(len(labels)-1, selected + 1)
            elif ch in (ord('\n'), ord('\r'), ord(' ')):
                _show_scan_result(results[selected], display)
            elif ch in (27, ord('q')):
                break
    else:
        for r in results:
            print(f'\n{r["host"]} ({r["hostname"]})')
            for p in r['open_ports']:
                print(f'  {p["port"]:5d}/tcp  {p["service"]:<12} {p["banner"]}')


def _show_scan_result(result: dict, display) -> None:
    ports = result['open_ports']
    if not ports:
        _show(display, [f'{result["host"]}', 'No open ports found'], pause=3.0)
        return

    if display and hasattr(display, 'getch'):
        import curses
        selected = 0
        labels = [f'{p["port"]:5d} {p["service"]:<8} {p["banner"][:10]}' for p in ports]
        while True:
            display.draw_menu(
                f'{result["host"]} ({len(ports)} open)',
                labels, selected
            )
            ch = display.getch()
            if ch == curses.KEY_UP:
                selected = max(0, selected - 1)
            elif ch == curses.KEY_DOWN:
                selected = min(len(labels)-1, selected + 1)
            elif ch in (ord('\n'), ord('\r'), ord(' ')):
                p = ports[selected]
                _show(display, [
                    f'Port {p["port"]}',
                    f'Service: {p["service"]}',
                    f'Banner: {p["banner"][:30]}' if p['banner'] else 'No banner',
                ], pause=3.0)
            elif ch in (27, ord('q')):
                break
    else:
        print(f'\n{result["host"]} ({result["hostname"]}):')
        for p in ports:
            print(f'  {p["port"]:5d}/tcp  {p["service"]:<12} {p["banner"]}')


# ---------------------------------------------------------------------------
# Deauth tester
# ---------------------------------------------------------------------------

def _scan_aps(deauth, display) -> None:
    _show(display, [
        'Scanning APs',
        'Enabling monitor mode',
        'Takes ~10 seconds...',
    ], pause=1.0)

    aps = deauth.scan_aps(duration_s=10.0)
    deauth.cleanup()

    if not aps:
        _show(display, ['No APs found', 'Check WiFi adapter', 'supports monitor mode'])
        return

    if display and hasattr(display, 'getch'):
        import curses
        selected = 0
        labels = [f'{ap["essid"][:12]:<12} {ap["bssid"]} ch{ap["channel"]}' for ap in aps]
        while True:
            display.draw_menu(f'APs: {len(aps)}', labels, selected)
            ch = display.getch()
            if ch == curses.KEY_UP:
                selected = max(0, selected - 1)
            elif ch == curses.KEY_DOWN:
                selected = min(len(labels)-1, selected + 1)
            elif ch in (27, ord('q')):
                break
    else:
        print(f'\n{"ESSID":<16} {"BSSID":<20} {"Ch":>4} {"Enc":<10}')
        for ap in aps:
            print(f'{ap["essid"]:<16} {ap["bssid"]:<20} {ap["channel"]:>4} {ap["encryption"]:<10}')


def _deauth_test(deauth, display) -> None:
    _show(display, [
        'Deauth Test',
        '!! YOUR NETWORK ONLY !!',
        'Tests WPA3/MFP protection',
    ], pause=1.5)

    bssid = input('Your AP BSSID (e.g. AA:BB:CC:DD:EE:FF): ').strip()
    if not bssid or ':' not in bssid:
        _show(display, ['Invalid BSSID'])
        return

    try:
        channel = int(input('Channel [6]: ').strip() or '6')
        packets = int(input('Packets [10]: ').strip() or '10')
    except ValueError:
        channel, packets = 6, 10

    confirm = input(f'Test {bssid} on ch{channel}? (yes/no): ').strip().lower()
    if confirm != 'yes':
        _show(display, ['Cancelled'])
        return

    _show(display, ['Running test...', f'{bssid}', f'ch{channel} x{packets}'], pause=1.0)

    result = deauth.test_deauth(bssid, packets=packets, channel=channel)
    deauth.cleanup()

    lines = [
        'Test Complete!',
        result['verdict'],
        f'AP: {bssid[:17]}',
        f'Packets: {result["packets_sent"]}',
        f'Time: {result["elapsed_s"]}s',
    ]
    _show(display, lines, pause=5.0)


# ---------------------------------------------------------------------------
# My IP
# ---------------------------------------------------------------------------

def _my_ip(display) -> None:
    from modules.network.port_scanner import get_local_ip, get_local_network
    ip  = get_local_ip()
    net = get_local_network() or 'unknown'
    _show(display, ['My IP Address:', ip, '', f'Network: {net}'], pause=4.0)
