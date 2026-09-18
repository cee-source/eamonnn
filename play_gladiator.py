#!/usr/bin/env python3
"""
Standalone launcher for Gladiator Arena — no PiFlip menu required.

Usage:
    python3 play_gladiator.py

Runs in the terminal via curses (or the OLED/touch display if PiFlip's
hardware libraries are installed and detected). Progress is saved to
data/gladiator/save.json and picked up again next time you play,
whether you launch it from here or from Games > Gladiator Arena in
the full PiFlip menu (main.py).
"""
import sys

from modules.games.gladiator import play_gladiator


if __name__ == '__main__':
    sys.exit(0 if play_gladiator() is not None else 1)
