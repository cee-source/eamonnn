import time
import os

# ═══════════════════════════════════════════════════════════
#   BLUE FISH v3.0 — SERVO CONTROL
#   Controls all servos via PCA9685 board over I2C.
#   No external libraries — uses direct I2C register writes.
# ═══════════════════════════════════════════════════════════

# ── PCA9685 I2C address and registers ──────────────────────
PCA9685_ADDR   = 0x40   # default I2C address (solder pads change this)
MODE1          = 0x00
PRESCALE       = 0xFE
LED0_ON_L      = 0x06   # first channel base register
PWM_FREQ_HZ    = 50     # servos use 50 Hz

# ── Servo pulse widths in microseconds ─────────────────────
PULSE_MIN_US   = 500    # fully anticlockwise  (0°)
PULSE_MAX_US   = 2500   # fully clockwise      (180°)

# ── PCA9685 channel map ─────────────────────────────────────
# Change these numbers if you wire servos differently.
CHANNELS = {
    # HEAD
    "neck":            0,   # left / right

    # LEFT ARM
    "l_shoulder_ud":   1,   # up / down
    "l_shoulder_fb":   2,   # forward / back
    "l_elbow":         3,   # bend
    "l_wrist":         4,   # rotation
    "l_hand":          5,   # grip open / close

    # RIGHT ARM
    "r_shoulder_ud":   6,
    "r_shoulder_fb":   7,
    "r_elbow":         8,
    "r_wrist":         9,
    "r_hand":          10,
}

# ── Safe angle limits per joint ─────────────────────────────
# Prevents servos from being driven past their physical limits
# and snapping PETG parts. Tune after assembly.
LIMITS = {
    "neck":            (40,  140),
    "l_shoulder_ud":   (30,  150),
    "l_shoulder_fb":   (20,  160),
    "l_elbow":         (0,   120),
    "l_wrist":         (30,  150),
    "l_hand":          (0,   90),
    "r_shoulder_ud":   (30,  150),
    "r_shoulder_fb":   (20,  160),
    "r_elbow":         (0,   120),
    "r_wrist":         (30,  150),
    "r_hand":          (0,   90),
}

# ── Rest / home position ────────────────────────────────────
HOME = {
    "neck":            90,
    "l_shoulder_ud":   90,
    "l_shoulder_fb":   90,
    "l_elbow":         0,
    "l_wrist":         90,
    "l_hand":          0,
    "r_shoulder_ud":   90,
    "r_shoulder_fb":   90,
    "r_elbow":         0,
    "r_wrist":         90,
    "r_hand":          0,
}


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
#  I2C HELPERS  (pure Python, no smbus library)
#  Uses Linux /dev/i2c-1 directly via file descriptor
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

import struct
import fcntl

I2C_SLAVE = 0x0703   # ioctl request code to set I2C slave address

class I2C:
    def __init__(self, bus=1, addr=PCA9685_ADDR):
        self.addr = addr
        self.fd   = os.open(f"/dev/i2c-{bus}", os.O_RDWR)
        fcntl.ioctl(self.fd, I2C_SLAVE, addr)

    def write(self, reg, value):
        os.write(self.fd, bytes([reg, value]))

    def read(self, reg):
        os.write(self.fd, bytes([reg]))
        return ord(os.read(self.fd, 1))

    def close(self):
        os.close(self.fd)


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
#  PCA9685 DRIVER
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

class PCA9685:
    def __init__(self, bus=1, addr=PCA9685_ADDR):
        self._i2c = I2C(bus, addr)
        self._reset()
        self._set_freq(PWM_FREQ_HZ)

    def _reset(self):
        self._i2c.write(MODE1, 0x00)
        time.sleep(0.01)

    def _set_freq(self, freq_hz):
        # Calculate prescaler value
        prescale = round(25_000_000 / (4096 * freq_hz)) - 1
        old_mode = self._i2c.read(MODE1)
        # Put to sleep (required to change prescaler)
        self._i2c.write(MODE1, (old_mode & 0x7F) | 0x10)
        self._i2c.write(PRESCALE, prescale)
        self._i2c.write(MODE1, old_mode)
        time.sleep(0.005)
        # Enable auto-increment
        self._i2c.write(MODE1, old_mode | 0x80)

    def set_pwm(self, channel, on, off):
        """Set raw PWM on/off tick counts (0–4095) for one channel."""
        base = LED0_ON_L + 4 * channel
        self._i2c.write(base,     on  & 0xFF)
        self._i2c.write(base + 1, on  >> 8)
        self._i2c.write(base + 2, off & 0xFF)
        self._i2c.write(base + 3, off >> 8)

    def set_pulse_us(self, channel, pulse_us):
        """Set pulse width in microseconds."""
        period_us = 1_000_000 / PWM_FREQ_HZ          # 20000 µs
        off_tick  = round(pulse_us / period_us * 4096)
        off_tick  = max(0, min(4095, off_tick))
        self.set_pwm(channel, 0, off_tick)

    def close(self):
        self._i2c.close()


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
#  SERVO CONTROLLER
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

class ServoController:
    def __init__(self):
        self._pca   = PCA9685()
        self._pos   = dict(HOME)   # track current angle per joint
        print("[Servos] PCA9685 ready.")

    # ── Core move ──────────────────────────────────────────

    def move(self, joint, angle):
        """Move a named joint to an angle (degrees). Respects limits."""
        if joint not in CHANNELS:
            print(f"[Servos] Unknown joint: {joint}")
            return

        lo, hi = LIMITS.get(joint, (0, 180))
        angle  = max(lo, min(hi, angle))

        pulse  = PULSE_MIN_US + (angle / 180) * (PULSE_MAX_US - PULSE_MIN_US)
        self._pca.set_pulse_us(CHANNELS[joint], pulse)
        self._pos[joint] = angle

    def move_smooth(self, joint, target, steps=20, delay=0.02):
        """Slowly move a joint from its current position to target."""
        start = self._pos.get(joint, 90)
        for i in range(1, steps + 1):
            angle = start + (target - start) * (i / steps)
            self.move(joint, angle)
            time.sleep(delay)

    # ── Poses ──────────────────────────────────────────────

    def home(self):
        """Move all joints to home position."""
        print("[Servos] Going home...")
        for joint, angle in HOME.items():
            self.move(joint, angle)
            time.sleep(0.05)

    def home_smooth(self):
        """Smoothly return all joints to home."""
        for joint, angle in HOME.items():
            self.move_smooth(joint, angle, steps=15, delay=0.015)

    # ── Gestures ───────────────────────────────────────────

    def wave(self, side="r"):
        """Wave one hand."""
        prefix = side + "_"
        print(f"[Servos] Waving {side} arm...")
        self.move_smooth(prefix + "shoulder_ud", 130, steps=20, delay=0.02)
        self.move_smooth(prefix + "elbow",        60, steps=15, delay=0.02)
        for _ in range(3):
            self.move_smooth(prefix + "wrist", 60,  steps=8, delay=0.015)
            self.move_smooth(prefix + "wrist", 120, steps=8, delay=0.015)
        self.move_smooth(prefix + "elbow",         0, steps=15, delay=0.02)
        self.move_smooth(prefix + "shoulder_ud",  90, steps=20, delay=0.02)

    def nod(self):
        """Nod head yes."""
        print("[Servos] Nodding...")
        for _ in range(2):
            self.move_smooth("neck", 110, steps=10, delay=0.02)
            self.move_smooth("neck",  70, steps=10, delay=0.02)
        self.move_smooth("neck", 90, steps=10, delay=0.02)

    def shake_head(self):
        """Shake head no."""
        print("[Servos] Shaking head...")
        for _ in range(2):
            self.move_smooth("neck", 60,  steps=10, delay=0.02)
            self.move_smooth("neck", 120, steps=10, delay=0.02)
        self.move_smooth("neck", 90, steps=10, delay=0.02)

    def thinking(self):
        """Tilt head like thinking."""
        self.move_smooth("neck", 115, steps=15, delay=0.025)
        time.sleep(1.0)
        self.move_smooth("neck",  90, steps=15, delay=0.025)

    def point(self, side="r"):
        """Point forward with one arm."""
        prefix = side + "_"
        print(f"[Servos] Pointing {side}...")
        self.move_smooth(prefix + "shoulder_fb", 140, steps=20, delay=0.02)
        self.move_smooth(prefix + "elbow",         0, steps=15, delay=0.02)
        time.sleep(1.5)
        self.move_smooth(prefix + "shoulder_fb",  90, steps=20, delay=0.02)

    def shrug(self):
        """Shrug both shoulders."""
        print("[Servos] Shrugging...")
        self.move_smooth("l_shoulder_ud", 130, steps=15, delay=0.02)
        self.move_smooth("r_shoulder_ud", 130, steps=15, delay=0.02)
        time.sleep(0.8)
        self.move_smooth("l_shoulder_ud",  90, steps=15, delay=0.02)
        self.move_smooth("r_shoulder_ud",  90, steps=15, delay=0.02)

    def grab(self, side="r"):
        """Close hand to grab."""
        self.move_smooth(side + "_hand", 90, steps=12, delay=0.02)

    def release(self, side="r"):
        """Open hand."""
        self.move_smooth(side + "_hand", 0, steps=12, delay=0.02)

    # ── Status ─────────────────────────────────────────────

    def status(self):
        print("\n  Joint positions:")
        for joint, angle in self._pos.items():
            lo, hi = LIMITS.get(joint, (0, 180))
            bar_len = 20
            filled  = round((angle - lo) / max(hi - lo, 1) * bar_len)
            bar     = "█" * filled + "░" * (bar_len - filled)
            print(f"  {joint:<20} {bar}  {angle:>5.1f}°")
        print()

    def close(self):
        self._pca.close()


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
#  RUN — interactive servo test
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

if __name__ == "__main__":
    sc = ServoController()
    sc.home()
    print()
    print("  Blue Fish servo tester")
    print("  Commands:")
    print("  wave [l/r]         — wave left or right arm")
    print("  nod                — nod head")
    print("  shake              — shake head no")
    print("  shrug              — shrug shoulders")
    print("  point [l/r]        — point forward")
    print("  think              — thinking pose")
    print("  grab [l/r]         — close hand")
    print("  release [l/r]      — open hand")
    print("  home               — all joints to rest")
    print("  move <joint> <deg> — move one joint to angle")
    print("  status             — show all joint angles")
    print("  quit               — exit\n")

    while True:
        try:
            cmd = input("Servo> ").strip().lower().split()
        except (EOFError, KeyboardInterrupt):
            break

        if not cmd:
            continue

        try:
            if cmd[0] == "wave":
                sc.wave(cmd[1] if len(cmd) > 1 else "r")
            elif cmd[0] == "nod":
                sc.nod()
            elif cmd[0] == "shake":
                sc.shake_head()
            elif cmd[0] == "shrug":
                sc.shrug()
            elif cmd[0] == "point":
                sc.point(cmd[1] if len(cmd) > 1 else "r")
            elif cmd[0] == "think":
                sc.thinking()
            elif cmd[0] == "grab":
                sc.grab(cmd[1] if len(cmd) > 1 else "r")
            elif cmd[0] == "release":
                sc.release(cmd[1] if len(cmd) > 1 else "r")
            elif cmd[0] == "home":
                sc.home_smooth()
            elif cmd[0] == "status":
                sc.status()
            elif cmd[0] == "move" and len(cmd) == 3:
                sc.move_smooth(cmd[1], float(cmd[2]))
            elif cmd[0] in ("quit", "exit"):
                break
            else:
                print("  Unknown command.")
        except Exception as e:
            print(f"  Error: {e}")

    sc.home()
    sc.close()
    print("[Servos] Shutdown.")
