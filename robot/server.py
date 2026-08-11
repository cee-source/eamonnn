#!/usr/bin/env python3
"""
Robot control server — runs on the Pi.

Serves the control webpage and drives the chassis motors + arm servos from
WASD, mouse, and arrow-key input sent over a websocket by the browser.

Usage:
  python3 server.py
"""
import json
import logging
import threading
import time

from flask import Flask, send_from_directory
from flask_sock import Sock

from hardware.motors import DriveBase
from hardware.servos import Arm

logging.basicConfig(level=logging.INFO)
log = logging.getLogger('robot')

# --- Pin assignments (BCM numbering) — see robot/README.md for wiring ---
LEFT_MOTOR = {'forward': 5, 'backward': 6, 'enable': 12}
RIGHT_MOTOR = {'forward': 16, 'backward': 20, 'enable': 21}
TURRET_PIN = 17
BOOM_PIN = 27
CLAW_PIN = 22

WATCHDOG_TIMEOUT = 0.5  # stop the drive motors if the browser goes silent

app = Flask(__name__, static_folder='static', static_url_path='')
sock = Sock(app)

drive = DriveBase(LEFT_MOTOR, RIGHT_MOTOR)
arm = Arm(TURRET_PIN, BOOM_PIN, CLAW_PIN)

_last_command_time = time.time()
_lock = threading.Lock()


def _watchdog():
    while True:
        time.sleep(0.1)
        with _lock:
            idle = time.time() - _last_command_time
        if idle > WATCHDOG_TIMEOUT:
            drive.stop()


threading.Thread(target=_watchdog, daemon=True).start()


@app.route('/')
def index():
    return send_from_directory('static', 'index.html')


@sock.route('/ws')
def ws(connection):
    global _last_command_time
    log.info('client connected')
    try:
        while True:
            raw = connection.receive()
            if raw is None:
                break
            with _lock:
                _last_command_time = time.time()
            try:
                msg = json.loads(raw)
            except ValueError:
                continue

            msg_type = msg.get('type')
            if msg_type == 'state':
                drive.set_drive(msg.get('w', False), msg.get('s', False),
                                 msg.get('a', False), msg.get('d', False))
                if msg.get('arrowUp'):
                    arm.claw_move(1)
                elif msg.get('arrowDown'):
                    arm.claw_move(-1)
            elif msg_type == 'arm':
                arm.nudge(msg.get('dx', 0), msg.get('dy', 0))
    finally:
        log.info('client disconnected')
        drive.stop()


if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)
