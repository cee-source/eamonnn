#!/usr/bin/env python3
"""
PiFlip — Raspberry Pi Flipper Zero Clone
Entry point: initialises hardware, builds menu tree, starts event loop.

Usage:
  python3 main.py              # Auto-detect OLED or fall back to terminal
  python3 main.py --headless   # Force terminal UI
  python3 main.py --debug      # Enable debug logging
"""
import argparse
import logging
import sys

from core.config_manager import ConfigManager
from core.logger import setup_logging
from core.menu import MenuEngine, MenuEntry


VERSION = '0.1.0'
BANNER = f"""
 ____  _ _____ _ _
|  _ \\(_)  ___| (_)_ __
| |_) | | |_  | | | '_ \\
|  __/| |  _| | | | |_) |
|_|   |_|_|   |_|_| .__/
                   |_|     v{VERSION}

Raspberry Pi Flipper Zero Clone
"""


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description='PiFlip — Raspberry Pi hardware multi-tool',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog='Press ESC or Q to navigate back in menus.',
    )
    parser.add_argument('--headless', action='store_true',
                        help='Force terminal UI (no OLED display)')
    parser.add_argument('--config', default='/home/user/eamonnn/config.ini',
                        help='Path to config.ini (default: %(default)s)')
    parser.add_argument('--debug', action='store_true',
                        help='Enable debug logging')
    return parser.parse_args()


def init_display(args, config):
    from core.display import TerminalDisplay

    if not args.headless:
        try:
            from core.display import OLEDDisplay
            display = OLEDDisplay(config)
            display.clear()
            logging.info('OLED display active')
            return display
        except Exception as e:
            logging.warning('OLED unavailable (%s), using terminal', e)

    return TerminalDisplay(config)


def build_root_menu(config, display) -> list[MenuEntry]:
    from modules.rfid.rfid_menu import build_rfid_menu
    from modules.infrared.ir_menu import build_ir_menu
    from modules.subghz.subghz_menu import build_subghz_menu
    from modules.badusb.badusb_menu import build_badusb_menu
    from modules.gpio_tools.gpio_menu import build_gpio_menu
    from modules.firewall.firewall_menu import build_firewall_menu
    from modules.bluetooth.bluetooth_menu import build_bluetooth_menu

    return [
        MenuEntry(label='RFID / NFC',  children=build_rfid_menu(config, display)),
        MenuEntry(label='Infrared',    children=build_ir_menu(config, display)),
        MenuEntry(label='Sub-GHz',     children=build_subghz_menu(config, display)),
        MenuEntry(label='Bad USB',     children=build_badusb_menu(config, display)),
        MenuEntry(label='GPIO Tools',  children=build_gpio_menu(config, display)),
        MenuEntry(label='Firewall',    children=build_firewall_menu(config, display)),
        MenuEntry(label='Bluetooth',   children=build_bluetooth_menu(config, display)),
        MenuEntry(label='About',       action=lambda: _show_about(display)),
    ]


def _show_about(display) -> None:
    import time
    lines = [
        'PiFlip v' + VERSION,
        '',
        'Raspberry Pi',
        'Flipper Zero Clone',
        '',
        'Features:',
        ' RFID/NFC  IR  Sub-GHz',
        ' Bad USB  GPIO Tools',
    ]
    if display:
        display.draw_message(lines)
        time.sleep(4)
    else:
        print('\n'.join(lines))


def main() -> int:
    args = parse_args()
    setup_logging(debug=args.debug)
    log = logging.getLogger(__name__)

    print(BANNER)
    log.info('PiFlip starting (version %s)', VERSION)

    config = ConfigManager(args.config)
    display = init_display(args, config)

    root_entries = build_root_menu(config, display)
    engine = MenuEngine(display=display, config=config)
    engine.push(root_entries)

    try:
        engine.run()
    except KeyboardInterrupt:
        log.info('Interrupted by user')
    except Exception as e:
        log.exception('Fatal error: %s', e)
        return 1

    log.info('PiFlip exited cleanly')
    return 0


if __name__ == '__main__':
    sys.exit(main())
