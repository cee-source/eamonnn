#!/usr/bin/env python3
"""
Downloads a free cat meow WAV file and saves it as meow.wav in this folder.
Run once:  python3 get_meow.py
"""

import os
import urllib.request

# Public-domain cat meow from the Wikimedia Commons audio library
URL = "https://upload.wikimedia.org/wikipedia/commons/2/2a/Cat_meow_2.ogg"
OGG_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "meow.ogg")
WAV_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "meow.wav")


def main():
    if os.path.exists(WAV_FILE):
        print(f"meow.wav already exists at {WAV_FILE} — nothing to do.")
        return

    print(f"Downloading meow sound from Wikimedia Commons...")
    urllib.request.urlretrieve(URL, OGG_FILE)
    print(f"Saved ogg to {OGG_FILE}")

    print("Converting ogg -> wav using ffmpeg...")
    ret = os.system(f"ffmpeg -y -i {OGG_FILE} {WAV_FILE}")
    if ret != 0:
        # ffmpeg not installed, try sox
        ret = os.system(f"sox {OGG_FILE} {WAV_FILE}")
    if ret != 0:
        print("\nCould not convert automatically. Install ffmpeg then run:")
        print(f"  ffmpeg -i {OGG_FILE} {WAV_FILE}")
        return

    os.remove(OGG_FILE)
    print(f"\nDone! meow.wav saved to {WAV_FILE}")
    print("You can test it with:  paplay meow.wav")


if __name__ == "__main__":
    main()
