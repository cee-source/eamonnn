import time
import logging

from core.menu import MenuEntry
from core.config_manager import ConfigManager

log = logging.getLogger(__name__)


def build_gpio_menu(config: ConfigManager, display=None) -> list[MenuEntry]:
    from modules.gpio_tools.pin_control import PinControl
    from modules.gpio_tools.logic_analyzer import LogicAnalyzer

    ctrl = PinControl()
    analyzer = LogicAnalyzer(config)

    return [
        MenuEntry(label='Pin State',      action=lambda: _read_pin(ctrl, display)),
        MenuEntry(label='Set Pin High',   action=lambda: _set_pin(ctrl, True, display)),
        MenuEntry(label='Set Pin Low',    action=lambda: _set_pin(ctrl, False, display)),
        MenuEntry(label='Logic Analyzer', action=lambda: _logic_capture(analyzer, config, display)),
        MenuEntry(label='Pin Blink Test', action=lambda: _blink(ctrl, display)),
    ]


def _read_pin(ctrl, display) -> None:
    try:
        pin = int(input('GPIO pin (BCM): '))
        val = ctrl.read_input(pin)
        msg = [f'GPIO{pin} = {"HIGH" if val else "LOW"}' if val >= 0 else 'GPIO not available']
    except ValueError:
        msg = ['Invalid pin number']

    if display:
        display.draw_message(msg)
        time.sleep(2)
    else:
        print(msg[0])


def _set_pin(ctrl, high: bool, display) -> None:
    try:
        pin = int(input('GPIO pin (BCM): '))
        ctrl.set_output(pin, high)
        msg = [f'GPIO{pin} set to {"HIGH" if high else "LOW"}']
    except ValueError:
        msg = ['Invalid pin number']

    if display:
        display.draw_message(msg)
        time.sleep(2)
    else:
        print(msg[0])


def _logic_capture(analyzer, config, display) -> None:
    try:
        pins_str = input('Pins to monitor (comma-separated BCM): ')
        pins = [int(p.strip()) for p in pins_str.split(',') if p.strip().isdigit()]
        duration = float(input('Duration (seconds) [1.0]: ').strip() or '1.0')
    except ValueError as e:
        print(f'Invalid input: {e}')
        return

    if not pins:
        print('No valid pins specified')
        return

    if display:
        display.draw_message([f'Logic Analyzer', f'Pins: {pins}', f'Duration: {duration}s', 'Capturing...'])

    events = analyzer.capture(pins=pins, duration_s=duration)
    if events:
        path = analyzer.save_csv(events, pins)
        msg = [f'Captured {len(events)} events', f'Saved: {path.split("/")[-1]}']
    else:
        msg = ['No events captured', 'No edges detected']

    if display:
        display.draw_message(msg)
        time.sleep(3)
    else:
        print('\n'.join(msg))


def _blink(ctrl, display) -> None:
    try:
        pin = int(input('GPIO pin (BCM) [default 24]: ').strip() or '24')
        count = int(input('Blink count [5]: ').strip() or '5')
    except ValueError:
        print('Invalid input')
        return

    if display:
        display.draw_message([f'Blinking GPIO{pin}', f'{count} times...'])

    import time as _time
    for _ in range(count):
        ctrl.set_output(pin, True)
        _time.sleep(0.2)
        ctrl.set_output(pin, False)
        _time.sleep(0.2)

    msg = [f'Blink test done', f'GPIO{pin} x{count}']
    if display:
        display.draw_message(msg)
        _time.sleep(2)
    else:
        print('\n'.join(msg))
