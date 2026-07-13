#!/usr/bin/env python3
"""AR pass-through renderer for the Spectrum Goggles VR build.

Reads "<band-key>,<value>\\n" lines from the Arduino sensor hub over serial,
draws the matching overlay (rings, laser, rays, glow, or a blocked stamp) on
top of a live camera frame, and shows the result as two eyes side by side —
one window spanning both HDMI outputs when the Pi desktop is configured as
one extended desktop. See README.md for wiring and setup.
"""

import argparse
import math
import random
import time

import cv2
import numpy as np

BANDS = {
    "radio": {
        "name": "Radio Waves", "overlay": "ripple", "color": (60, 90, 255),
        "marker": "ROUTER", "ring_interval_ms": 700, "ring_speed": 0.09,
    },
    "micro": {
        "name": "Microwaves", "overlay": "ripple", "color": (60, 210, 255),
        "marker": "RADAR", "ring_interval_ms": 320, "ring_speed": 0.14,
    },
    "ir": {
        "name": "Infrared", "overlay": "laser", "color": (45, 45, 255),
        "marker": "HEAT SRC",
    },
    "visible": {
        "name": "Visible Light", "overlay": "none", "color": (122, 214, 143),
        "marker": "LAMP",
    },
    "uv": {
        "name": "Ultraviolet", "overlay": "rays", "color": (255, 92, 155),
        "marker": "UV LAMP",
    },
    "xray": {
        "name": "X-Rays", "overlay": "blocked", "color": (90, 106, 201),
        "marker": None,
    },
    "gamma": {
        "name": "Gamma Rays", "overlay": "glow", "color": (106, 255, 57),
        "marker": "ISOTOPE",
    },
}

# Rough normalization so overlay intensity scales sensibly with each sensor's
# real-world range. Matches the ranges used in the web simulator.
VALUE_RANGES = {
    "radio": (0, 100),
    "micro": (0, 1),
    "ir": (18, 38),
    "visible": (0, 950),
    "uv": (0, 11),
    "xray": (0, 1),
    "gamma": (12, 42),
}


def normalize(band_key, value):
    lo, hi = VALUE_RANGES.get(band_key, (0, 1))
    if hi == lo:
        return 0.5
    return max(0.0, min(1.0, (value - lo) / (hi - lo)))


class SerialReader:
    """Non-blocking reader for the Arduino's "key,value" lines."""

    def __init__(self, port, baud=9600):
        import serial  # imported lazily so --demo works without pyserial
        self.ser = serial.Serial(port, baud, timeout=0)
        self.buf = b""

    def poll(self):
        """Returns (band_key, value) if a new full line arrived, else None."""
        self.buf += self.ser.read(4096)
        if b"\n" not in self.buf:
            return None
        line, _, self.buf = self.buf.partition(b"\n")
        try:
            key, value = line.decode("ascii", "ignore").strip().split(",")
            return key, float(value)
        except ValueError:
            return None


class DemoReader:
    """Cycles through bands with simulated values, no hardware required."""

    def __init__(self):
        self.keys = list(BANDS.keys())
        self.i = 0
        self.last_switch = time.time()

    def poll(self):
        if time.time() - self.last_switch > 3.0:
            self.i = (self.i + 1) % len(self.keys)
            self.last_switch = time.time()
        key = self.keys[self.i]
        lo, hi = VALUE_RANGES.get(key, (0, 1))
        return key, random.uniform(lo, hi)


class RingSet:
    def __init__(self):
        self.rings = []
        self.last_spawn = 0

    def reset(self):
        self.rings = []
        self.last_spawn = 0

    def update_and_draw(self, frame, sx, sy, t_ms, band, value01):
        max_r = max(frame.shape[:2]) * 0.62
        if t_ms - self.last_spawn > band["ring_interval_ms"]:
            self.rings.append(t_ms)
            self.last_spawn = t_ms
        self.rings = [r for r in self.rings if (t_ms - r) * band["ring_speed"] < max_r]
        overlay = frame.copy()
        for born in self.rings:
            age = t_ms - born
            radius = age * band["ring_speed"]
            alpha = max(0.0, 1 - radius / max_r) * (0.35 + value01 * 0.5)
            cv2.circle(overlay, (int(sx), int(sy)), int(radius), band["color"], 2, cv2.LINE_AA)
            cv2.addWeighted(overlay, alpha, frame, 1 - alpha, 0, frame)
            overlay = frame.copy()


def draw_marker(frame, sx, sy, band):
    cv2.circle(frame, (int(sx), int(sy)), 5, (242, 238, 232), -1, cv2.LINE_AA)
    cv2.circle(frame, (int(sx), int(sy)), 9, band["color"], 2, cv2.LINE_AA)
    if band["marker"]:
        cv2.putText(frame, band["marker"], (int(sx) - 30, int(sy) + 28),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.4, (232, 238, 242), 1, cv2.LINE_AA)


def draw_laser(frame, sx, sy, t_ms, band, value01):
    h, w = frame.shape[:2]
    ex, ey = int(w * 0.22), int(h * 0.88)
    alpha = 0.55 + 0.25 * value01
    dash_on = int(t_ms / 60) % 2 == 0
    overlay = frame.copy()
    if dash_on:
        cv2.line(overlay, (int(sx), int(sy)), (ex, ey), band["color"], 3, cv2.LINE_AA)
    cv2.addWeighted(overlay, alpha, frame, 1 - alpha, 0, frame)
    cv2.circle(frame, (ex, ey), 6, band["color"], -1, cv2.LINE_AA)


def draw_rays(frame, sx, sy, t_ms, band, value01):
    h, w = frame.shape[:2]
    length = max(w, h) * 0.42
    overlay = frame.copy()
    for i in range(9):
        base_angle = (i / 9) * 2 * math.pi + t_ms * 0.00025
        shimmer = 0.75 + 0.25 * math.sin(t_ms * 0.002 + i)
        l = length * shimmer
        ex = int(sx + math.cos(base_angle) * l)
        ey = int(sy + math.sin(base_angle) * l)
        alpha = (0.25 + value01 * 0.55) * shimmer
        cv2.line(overlay, (int(sx), int(sy)), (ex, ey), band["color"], 2, cv2.LINE_AA)
        cv2.addWeighted(overlay, alpha, frame, 1 - alpha, 0, frame)
        overlay = frame.copy()


def draw_glow(frame, t_ms, value01):
    h, w = frame.shape[:2]
    pulse = 0.08 * math.sin(t_ms * 0.003)
    alpha = max(0.05, 0.12 + value01 * 0.55 + pulse)
    glow = np.zeros_like(frame)
    cv2.circle(glow, (w // 2, h // 2), int(max(w, h) * 0.62), (57, 255, 106), -1, cv2.LINE_AA)
    glow = cv2.GaussianBlur(glow, (0, 0), sigmaX=max(w, h) * 0.2)
    cv2.addWeighted(glow, alpha, frame, 1.0, 0, frame)


def draw_blocked(frame):
    h, w = frame.shape[:2]
    dim = (frame * 0.55).astype(np.uint8)
    frame[:] = dim
    for x in range(-h, w, 22):
        cv2.line(frame, (x, 0), (x + h, h), (90, 106, 201), 1, cv2.LINE_AA)
    cv2.putText(frame, "NO SIGNAL - NOT FEASIBLE", (w // 2 - 130, h // 2),
                cv2.FONT_HERSHEY_SIMPLEX, 0.5, (242, 238, 232), 1, cv2.LINE_AA)


def render_eye(base_frame, band_key, value, rings, t_ms):
    band = BANDS[band_key]
    frame = base_frame.copy()
    h, w = frame.shape[:2]
    sx, sy = w * 0.52, h * 0.36
    value01 = normalize(band_key, value)

    if band["overlay"] == "ripple":
        rings.update_and_draw(frame, sx, sy, t_ms, band, value01)
    elif band["overlay"] == "laser":
        draw_laser(frame, sx, sy, t_ms, band, value01)
    elif band["overlay"] == "rays":
        draw_rays(frame, sx, sy, t_ms, band, value01)
    elif band["overlay"] == "glow":
        draw_glow(frame, t_ms, value01)
    elif band["overlay"] == "blocked":
        draw_blocked(frame)
        return frame

    draw_marker(frame, sx, sy, band)
    cv2.putText(frame, band["name"].upper(), (12, 22),
                cv2.FONT_HERSHEY_SIMPLEX, 0.42, (232, 238, 242), 1, cv2.LINE_AA)
    return frame


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--port", default="/dev/ttyUSB0", help="Arduino serial port")
    ap.add_argument("--baud", type=int, default=9600)
    ap.add_argument("--cam", type=int, default=0, help="camera index")
    ap.add_argument("--eye-size", type=int, default=480, help="pixels per eye, square")
    ap.add_argument("--demo", action="store_true", help="simulate sensor data, no Arduino needed")
    args = ap.parse_args()

    reader = DemoReader() if args.demo else SerialReader(args.port, args.baud)

    cap = cv2.VideoCapture(args.cam)
    if not cap.isOpened():
        raise SystemExit(f"Could not open camera index {args.cam}")

    rings = RingSet()
    current_band = "radio"
    current_value = 0.0

    cv2.namedWindow("Spectrum Goggles", cv2.WINDOW_NORMAL)

    while True:
        ok, frame = cap.read()
        if not ok:
            break

        h, w = frame.shape[:2]
        side = min(h, w)
        y0, x0 = (h - side) // 2, (w - side) // 2
        square = frame[y0:y0 + side, x0:x0 + side]
        eye_frame = cv2.resize(square, (args.eye_size, args.eye_size))

        polled = reader.poll()
        if polled is not None:
            key, value = polled
            if key != current_band:
                rings.reset()
            current_band, current_value = key, value

        t_ms = time.time() * 1000
        left = render_eye(eye_frame, current_band, current_value, rings, t_ms)
        right = left.copy()  # single camera duplicated to both eyes

        combined = np.hstack([left, right])
        cv2.imshow("Spectrum Goggles", combined)

        if cv2.waitKey(1) & 0xFF == ord("q"):
            break

    cap.release()
    cv2.destroyAllWindows()


if __name__ == "__main__":
    main()
