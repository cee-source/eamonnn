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

SOUNDS = [
    os.path.join(FOLDER, "cat1.wav"),
    os.path.join(FOLDER, "cat2.wav"),
    os.path.join(FOLDER, "cat3.wav"),
    os.path.join(FOLDER, "cat4.wav"),
]

WEIGHTS = [50, 17, 17, 16]  # cat1 = 50%, others share the rest

current_sound = None
last_played = None


def play_meow():
    global current_sound, last_played
    if current_sound and current_sound.poll() is None:
        return  # already playing, don't overlap
    available = [(s, w) for s, w in zip(SOUNDS, WEIGHTS)
                 if os.path.exists(s) and s != last_played]
    if not available:
        return
    sounds, weights = zip(*available)
    sound = random.choices(sounds, weights=weights, k=1)[0]
    last_played = sound
    print(f"Playing {os.path.basename(sound)}")
    current_sound = subprocess.Popen(["paplay", sound])


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
