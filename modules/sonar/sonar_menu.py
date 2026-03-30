"""Sonar menu for PiFlip."""

import time
from core.menu import MenuEntry


def build_sonar_menu(config, display) -> list:

    def _get_pins():
        hw = config.parser['hardware'] if config else {}
        return (
            int(hw.get('sonar_trig_pin',  23)),
            int(hw.get('sonar_echo_pin',  25)),
            int(hw.get('sonar_servo_pin', 12)),
            float(hw.get('sonar_max_range_cm', 300)),
        )

    def _run_sweep():
        from modules.sonar.sonar_scanner import SonarScanner
        trig, echo, servo, max_r = _get_pins()
        scanner = SonarScanner(trig, echo, servo, max_r)

        if hasattr(display, 'device'):
            # OLED mode
            display.draw_message("Sonar Active", "Btn BACK = stop")
            time.sleep(0.8)
            scanner.run_oled(display.device)
        else:
            # Terminal mode
            scanner.run_terminal()

    def _single_ping():
        from modules.sonar.hcsr04 import HCSR04
        trig, echo, _, max_r = _get_pins()
        sensor = HCSR04(trig, echo, max_r)
        display.draw_message("Pinging...", "")
        time.sleep(0.3)
        dist = sensor.measure_median(samples=5)
        if dist is None:
            display.draw_message("No echo", "Out of range")
        else:
            display.draw_message(f"{dist:.1f} cm", f"{dist/100:.2f} m")
        sensor.cleanup()
        time.sleep(3)

    def _servo_test():
        from modules.sonar.servo import Servo
        _, _, servo_pin, _ = _get_pins()
        s = Servo(servo_pin)
        display.draw_message("Servo test", "0 → 180 → 90")
        time.sleep(0.5)
        s.sweep_to(0,   step=10, step_delay=0.04)
        s.sweep_to(180, step=10, step_delay=0.04)
        s.sweep_to(90,  step=10, step_delay=0.04)
        s.cleanup()
        display.draw_message("Done", "Servo centered")
        time.sleep(1.5)

    return [
        MenuEntry(label="Radar Sweep",   action=_run_sweep),
        MenuEntry(label="Single Ping",   action=_single_ping),
        MenuEntry(label="Servo Test",    action=_servo_test),
    ]
