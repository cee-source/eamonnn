#!/usr/bin/env python3
"""
PIR Motion Sensor -> Bluetooth Speaker Cat Meow Alert
Plays a random cat mating call whenever the PIR sensor detects movement.
"""

import os
import subprocess
import time
import random

from gpiozero import MotionSensor

PIR_PIN = 17
FOLDER = os.path.dirname(os.path.abspath(__file__))

SOUND = os.path.join(FOLDER, "cat1.wav")

current_sound = None


def play_meow():
    global current_sound
    if current_sound and current_sound.poll() is None:
        return
    print("Playing cat1.wav")
    current_sound = subprocess.Popen(["paplay", SOUND])


pir = MotionSensor(PIR_PIN)
print("PIR meow alert is running. Press Ctrl+C to stop.")

try:
    while True:
        if pir.motion_detected:
            print(f"Motion detected! ({time.strftime('%H:%M:%S')})")
            play_meow()
        time.sleep(0.05)
except KeyboardInterrupt:
    print("\nStopped.")
    if current_sound:
        current_sound.terminate()
