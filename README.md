# eamonnn
eamonns first repository

PiFlip — a Raspberry Pi hardware multi-tool (RFID/NFC, IR, Sub-GHz, BadUSB,
GPIO, firewall, Bluetooth, radio, and a handful of games) with an OLED,
3.5" touchscreen, or terminal display.

## Gladiator Arena

A turn-based gladiator RPG: fight a rising roster of opponents, earn gold,
and gear up with armor from talking NPCs — Magnus the Armorer, Vita the
Healer, and Dominus the Arena Master. Two ways to play, sharing the same
rules and balance:

- **Terminal** (curses, works on the device's OLED/touchscreen too):
  ```bash
  python3 play_gladiator.py
  ```
  or from the full PiFlip menu: `python3 main.py` → Games → Gladiator Arena.
  Progress saves to `data/gladiator/save.json`.

- **Web** — [`docs/gladiator-arena.html`](docs/gladiator-arena.html) is a
  self-contained page; open it directly in a browser, or once this is on
  `main` it's also served by the repo's GitHub Pages workflow. Progress
  saves in that browser's local storage. (This is a separate save from the
  terminal version — they don't sync.)
