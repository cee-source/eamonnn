# Robot build + wiring + control guide

A small tracked/wheeled base with a rotating arm and a claw, driven from a
webpage on your Mac: **WASD** drives, the **mouse** rotates the arm and
raises/lowers the boom, **arrow up/down** open and close the claw.

This is a separate physical build from the PiFlip project elsewhere in this
repo — it uses its own Pi and its own pins, so the two don't interfere.

---

## 1. Parts list

From your notebook list, organized by what each part is for:

**Brain / control**
- Raspberry Pi Zero 2 W (or Pi Zero W) — needs built-in wifi to be
  controlled wirelessly. A plain Pi Zero has no wifi; skip it unless you're
  adding a USB wifi dongle.
- MicroSD card (8GB+) for the Pi's OS

**Drive**
- 2x DC gear motors (chassis wheels/tracks)
- L298N dual motor driver board
- Wheels/tracks to match your motors

**Arm**
- 3x micro servos (SG90 or similar) — one each for turret rotation, boom
  up/down, and the claw

**Structure**
- Wood sheets, plastic sticks/panels — chassis and arm body
- Hot glue gun + glue sticks — assembly
- Strong wire — for the claw's cable/linkage if it's cable-driven like in
  your sketch

**Power**
- Battery pack for the motors/servos (e.g. a 2S Li-ion pack or a 6xAA
  holder, 6–9V) — do **not** power the Pi from this
- USB power bank (5V) to power the Pi itself, separately

---

## 2. Wiring, step by step

Do all wiring with **everything unplugged/unpowered**. Connect grounds
first, power last.

### Pin assignments (matches `server.py` — don't change one without the other)

| Function | Pi GPIO (BCM) | Physical pin |
|---|---|---|
| Left motor IN1 | GPIO5 | 29 |
| Left motor IN2 | GPIO6 | 31 |
| Left motor ENA (speed) | GPIO12 | 32 |
| Right motor IN3 | GPIO16 | 36 |
| Right motor IN4 | GPIO20 | 38 |
| Right motor ENB (speed) | GPIO21 | 40 |
| Turret servo signal | GPIO17 | 11 |
| Boom servo signal | GPIO27 | 13 |
| Claw servo signal | GPIO22 | 15 |

### Steps

1. **Mount the L298N.** Screw/glue it to the chassis near the drive motors.
2. **Wire the left motor** to the L298N's `OUT1`/`OUT2` terminals (polarity
   just determines which direction is "forward" — if it drives backwards
   later, swap these two wires).
3. **Wire the right motor** to `OUT3`/`OUT4`.
4. **Wire the Pi to the L298N control pins** using the table above:
   `IN1`→GPIO5, `IN2`→GPIO6, `ENA`→GPIO12, `IN3`→GPIO16, `IN4`→GPIO20,
   `ENB`→GPIO21.
5. **Power the L298N**: battery pack `+` → L298N `12V`/`VIN`, battery `−` →
   L298N `GND`.
6. **Common ground**: run a wire from the L298N `GND` to a Pi `GND` pin
   (e.g. physical pin 6, 9, 14, 20, 25, 30, 34, or 39). The Pi and the
   motor battery must share a ground or nothing will work reliably.
7. **Servos**: connect each servo's signal wire to its GPIO pin from the
   table (turret→GPIO17, boom→GPIO27, claw→GPIO22). Connect all three
   servo `+` wires to a 5V source — the L298N's onboard 5V regulator output
   works for light loads if its jumper is set, otherwise use a separate 5V
   BEC. Connect all three servo `−`/ground wires to the same common ground
   as everything else.
8. **Power the Pi** from its own USB power bank via the micro-USB power
   port — never from the L298N or a servo rail, it can't supply the current
   the Pi needs under load.
9. **Build the chassis/arm** around this — mount the motors to the
   wheels/tracks, the servos at the turret base and boom joint, and the
   claw (or hook, per your sketch) on strong wire/linkage at the end of the
   boom, driven by the claw servo.
10. Double check nothing metal is bridging pins, then power on: battery
    pack first, then the Pi.

---

## 3. Software setup, step by step

On your Mac, using the [Raspberry Pi Imager](https://www.raspberrypi.com/software/):

1. Flash Raspberry Pi OS Lite to the microSD card.
2. In the Imager's settings (gear icon) before writing: enable SSH, set a
   username/password, and enter your wifi network name + password.
3. Boot the Pi with that card. Find its IP address — check your router's
   device list, or run `ping raspberrypi.local` from your Mac.
4. SSH in: `ssh <username>@<pi-ip-address>`

On the Pi (over SSH):

```bash
sudo apt update
sudo apt install -y python3-pip python3-venv pigpio git
sudo systemctl enable pigpiod --now   # pigpio daemon must be running for servos
```

Get the code onto the Pi — either `git clone` this repo, or copy just the
`robot/` folder over with `scp -r robot <username>@<pi-ip>:~/robot`. Then:

```bash
cd robot
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
python3 server.py
```

You should see `Running on http://0.0.0.0:5000`. Leave this running.

**Optional — start automatically on boot**, so you don't need to SSH in
every time: create `/etc/systemd/system/robot.service` on the Pi with

```ini
[Unit]
Description=Robot control server
After=network-online.target pigpiod.service

[Service]
WorkingDirectory=/home/<username>/robot
ExecStart=/home/<username>/robot/venv/bin/python3 server.py
Restart=always
User=<username>

[Install]
WantedBy=multi-user.target
```

then `sudo systemctl enable robot --now`.

---

## 4. Controlling it from your Mac

1. Make sure your Mac is on the same wifi network as the Pi.
2. Open a browser and go to `http://<pi-ip-address>:5000`.
3. Click **"Click to control"** to lock your mouse to the page.
4. Drive with **W A S D**. Move the mouse to rotate the arm and raise/lower
   the boom. Use **Arrow Up** to close the claw, **Arrow Down** to open it.
   Press **Esc** to release the mouse.

If the browser tab loses connection or you close it, the drive motors stop
automatically within half a second (a watchdog in `server.py`) — the robot
won't run away if your wifi drops.

---

## Troubleshooting

- **Motors don't move**: check the common ground between the Pi and the
  L298N/battery — this is the most common miswire.
- **One side drives backwards**: swap that motor's two `OUT` wires on the
  L298N.
- **Servos jitter or reset**: they're likely browning out — give them their
  own 5V supply instead of sharing the L298N's regulator, and make sure
  `pigpiod` is running (`sudo systemctl status pigpiod`).
- **Page won't load**: confirm `server.py` is still running on the Pi and
  that your Mac and Pi are on the same network.
