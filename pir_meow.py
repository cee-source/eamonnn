#!/usr/bin/env python3
"""
PIR Motion Sensor -> Bluetooth Speaker Cat Meow Alert
Plays meow.wav whenever the PIR sensor detects movement.
"""

import os
import subprocess
import time

import RPi.GPIO as GPIO

PIR_PIN = 17        # GPIO 17 = physical pin 11
SOUND_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "meow.wav")
COOLDOWN_SECONDS = 5  # minimum gap between meows so it doesn't spam


def play_meow():
    """Play the meow sound through the default PulseAudio sink (Bluetooth speaker)."""
    if not os.path.exists(SOUND_FILE):
        print(f"ERROR: sound file not found: {SOUND_FILE}")
        print("Run  python3 get_meow.py  to download one, or copy your own meow.wav here.")
        return
    subprocess.Popen(["paplay", SOUND_FILE])


def main():
    GPIO.setmode(GPIO.BCM)
    GPIO.setup(PIR_PIN, GPIO.IN)

    print("PIR meow alert is running.")
    print(f"  GPIO pin : {PIR_PIN}")
    print(f"  Sound    : {SOUND_FILE}")
    print(f"  Cooldown : {COOLDOWN_SECONDS}s")
    print("Press Ctrl+C to stop.\n")

    # The HC-SR501 needs ~30 s to stabilise on first power-on.
    # If the script starts at boot give it a moment.
    time.sleep(2)

    last_trigger = 0.0

    try:
        while True:
            if GPIO.input(PIR_PIN):
                now = time.time()
                if now - last_trigger >= COOLDOWN_SECONDS:
                    print(f"Motion detected! ({time.strftime('%H:%M:%S')})")
                    play_meow()
                    last_trigger = now
            time.sleep(0.05)  # 50 ms poll — low CPU, fast enough response
    except KeyboardInterrupt:
        print("\nStopped by user.")
    finally:
        GPIO.cleanup()


if __name__ == "__main__":
    main()
