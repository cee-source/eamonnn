#!/usr/bin/env python3
"""Blue Fish v2.2 - Servo control module
Requires: pip install adafruit-circuitpython-pca9685 adafruit-circuitpython-motor
Wiring: PCA9685 SDA→GPIO2, SCL→GPIO3, VCC→3.3V, GND→GND
        Servo power: V+→separate 5V supply, GND→shared GND with Pi
"""

import time
import threading

try:
    import board
    import busio
    from adafruit_pca9685 import PCA9685
    _HW = True
except Exception as e:
    print(f"[Servo] Hardware not available: {e} — running in simulation mode")
    _HW = False

# ── Channel map — PCA9685 #1 (address 0x40) ──────────────────────────────────
HEAD_PAN          = 0    # left (+) / right (-)
HEAD_TILT         = 1    # up (+) / down (-)

R_SHOULDER_PITCH  = 2    # arm forward (+) / back (-)
R_SHOULDER_ROLL   = 3    # arm up (+) / down (-)
R_ELBOW_PITCH     = 4    # forearm up (+) / straight (-)
R_ELBOW_ROLL      = 5    # forearm twist
R_WRIST_PITCH     = 6    # hand up/down
R_WRIST_ROLL      = 7    # hand twist

L_SHOULDER_PITCH  = 8
L_SHOULDER_ROLL   = 9
L_ELBOW_PITCH     = 10
L_ELBOW_ROLL      = 11
L_WRIST_PITCH     = 12
L_WRIST_ROLL      = 13

# ── Channel map — PCA9685 #2 (address 0x41) ──────────────────────────────────
R_HIP_PITCH       = 0    # leg forward (+) / back (-)
R_HIP_ROLL        = 1    # leg out (+) / in (-)
R_KNEE            = 2    # knee bend (+) / straight (0)
R_ANKLE           = 3    # foot down (+) / flat (0)

L_HIP_PITCH       = 4
L_HIP_ROLL        = 5
L_KNEE            = 6
L_ANKLE           = 7

# ── Neutral / rest angles (degrees) ──────────────────────────────────────────
# Adjust these after wiring to make the robot stand straight
NEUTRAL = {
    # Head
    HEAD_PAN: 90, HEAD_TILT: 90,
    # Right arm
    R_SHOULDER_PITCH: 90, R_SHOULDER_ROLL: 0,
    R_ELBOW_PITCH: 0,     R_ELBOW_ROLL: 90,
    R_WRIST_PITCH: 90,    R_WRIST_ROLL: 90,
    # Left arm
    L_SHOULDER_PITCH: 90, L_SHOULDER_ROLL: 180,
    L_ELBOW_PITCH: 0,     L_ELBOW_ROLL: 90,
    L_WRIST_PITCH: 90,    L_WRIST_ROLL: 90,
}

NEUTRAL_LEGS = {
    R_HIP_PITCH: 90, R_HIP_ROLL: 90, R_KNEE: 0, R_ANKLE: 0,
    L_HIP_PITCH: 90, L_HIP_ROLL: 90, L_KNEE: 0, L_ANKLE: 0,
}

# ── Hardware init ─────────────────────────────────────────────────────────────
_pca_upper = None   # PCA9685 #1 — head + arms
_pca_lower = None   # PCA9685 #2 — legs
_servo_lock = threading.Lock()
_walking = False
_walk_thread = None

def init_servos():
    global _pca_upper, _pca_lower
    if not _HW:
        print("[Servo] Simulation mode — no hardware")
        return False
    try:
        i2c = busio.I2C(board.SCL, board.SDA)
        _pca_upper = PCA9685(i2c, address=0x40)
        _pca_upper.frequency = 50
        print("[Servo] Upper body (0x40) connected")
    except Exception as e:
        print(f"[Servo] Upper body board not found: {e}")

    try:
        i2c2 = busio.I2C(board.SCL, board.SDA)
        _pca_lower = PCA9685(i2c2, address=0x41)
        _pca_lower.frequency = 50
        print("[Servo] Lower body (0x41) connected")
    except Exception as e:
        print(f"[Servo] Lower body board not found (legs not available): {e}")

    go_neutral()
    return True


def _angle_to_duty(angle):
    """Convert 0-180 degrees to 16-bit duty cycle for 50Hz PWM."""
    # Standard servo: 1ms (0°) to 2ms (180°) pulse, 20ms period
    pulse_ms  = 1.0 + (angle / 180.0)   # 1.0ms → 2.0ms
    duty      = int((pulse_ms / 20.0) * 65535)
    return max(1638, min(8192, duty))    # clamp to safe range


def set_servo(board_num, channel, angle):
    """Set a servo to an angle (0-180). board_num: 1=upper, 2=lower."""
    angle = max(0, min(180, angle))
    if _HW:
        pca = _pca_upper if board_num == 1 else _pca_lower
        if pca is None:
            return
        with _servo_lock:
            pca.channels[channel].duty_cycle = _angle_to_duty(angle)
    else:
        board_name = "upper" if board_num == 1 else "lower"
        print(f"[Servo SIM] board={board_name} ch={channel} angle={angle}°")


def set_upper(channel, angle):
    set_servo(1, channel, angle)

def set_lower(channel, angle):
    set_servo(2, channel, angle)


def go_neutral():
    """Move all servos to resting position."""
    print("[Servo] Going to neutral")
    for ch, angle in NEUTRAL.items():
        set_upper(ch, angle)
        time.sleep(0.02)
    for ch, angle in NEUTRAL_LEGS.items():
        set_lower(ch, angle)
        time.sleep(0.02)


def move_head(pan=90, tilt=90, speed=0.02):
    """Pan: 0=full left, 90=center, 180=full right. Tilt: 0=down, 90=level, 180=up."""
    set_upper(HEAD_PAN, pan)
    time.sleep(speed)
    set_upper(HEAD_TILT, tilt)


def wave_right():
    """Wave the right hand."""
    print("[Servo] Waving right hand")
    set_upper(R_SHOULDER_ROLL, 45)
    time.sleep(0.4)
    set_upper(R_ELBOW_PITCH, 90)
    time.sleep(0.3)
    for _ in range(3):
        set_upper(R_WRIST_ROLL, 45)
        time.sleep(0.2)
        set_upper(R_WRIST_ROLL, 135)
        time.sleep(0.2)
    set_upper(R_WRIST_ROLL, 90)
    time.sleep(0.3)
    set_upper(R_ELBOW_PITCH, 0)
    time.sleep(0.3)
    set_upper(R_SHOULDER_ROLL, 0)


def wave_left():
    """Wave the left hand."""
    print("[Servo] Waving left hand")
    set_upper(L_SHOULDER_ROLL, 135)
    time.sleep(0.4)
    set_upper(L_ELBOW_PITCH, 90)
    time.sleep(0.3)
    for _ in range(3):
        set_upper(L_WRIST_ROLL, 45)
        time.sleep(0.2)
        set_upper(L_WRIST_ROLL, 135)
        time.sleep(0.2)
    set_upper(L_WRIST_ROLL, 90)
    time.sleep(0.3)
    set_upper(L_ELBOW_PITCH, 0)
    time.sleep(0.3)
    set_upper(L_SHOULDER_ROLL, 180)


# ── Walking ───────────────────────────────────────────────────────────────────
# Gait parameters (tune these after wiring)
STEP_HIP_FORWARD  = 60    # degrees — hip swings forward
STEP_HIP_BACK     = 120   # degrees — hip pushes back
STEP_HIP_LEAN     = 70    # degrees — lean to weight-bearing side
STEP_HIP_CENTER   = 90    # neutral
STEP_KNEE_LIFT    = 45    # degrees — knee bends when lifting foot
STEP_KNEE_STRAIGHT = 0    # degrees — leg straight
STEP_ANKLE_LIFT   = 20    # degrees — ankle flexes on lift
STEP_SPEED        = 0.15  # seconds between servo moves (lower = faster)

STAIR_KNEE_LIFT   = 80    # much higher knee lift for stairs
STAIR_HIP_FORWARD = 50
STAIR_SPEED       = 0.25  # slower and more deliberate


def _one_step(leading_side, knee_lift=STEP_KNEE_LIFT, hip_fwd=STEP_HIP_FORWARD,
              hip_back=STEP_HIP_BACK, spd=STEP_SPEED):
    """Take one step with the given leading side ('R' or 'L')."""
    if leading_side == 'R':
        lift_hip_p, lift_hip_r, lift_knee, lift_ankle = R_HIP_PITCH, R_HIP_ROLL, R_KNEE, R_ANKLE
        push_hip_p, push_hip_r, push_knee, push_ankle = L_HIP_PITCH, L_HIP_ROLL, L_KNEE, L_ANKLE
        lean_dir = 70    # lean left (weight on left) while right foot lifts
        push_dir = 110   # lean right while left foot lifts
    else:
        lift_hip_p, lift_hip_r, lift_knee, lift_ankle = L_HIP_PITCH, L_HIP_ROLL, L_KNEE, L_ANKLE
        push_hip_p, push_hip_r, push_knee, push_ankle = R_HIP_PITCH, R_HIP_ROLL, R_KNEE, R_ANKLE
        lean_dir = 110
        push_dir = 70

    # 1. Shift weight to standing leg (lean)
    set_lower(push_hip_r, lean_dir)
    time.sleep(spd)

    # 2. Lift the stepping foot (bend knee + flex ankle)
    set_lower(lift_knee, knee_lift)
    set_lower(lift_ankle, STEP_ANKLE_LIFT)
    time.sleep(spd)

    # 3. Swing hip forward
    set_lower(lift_hip_p, hip_fwd)
    time.sleep(spd)

    # 4. Plant foot (straighten knee + ankle)
    set_lower(lift_knee, STEP_KNEE_STRAIGHT)
    set_lower(lift_ankle, 0)
    time.sleep(spd)

    # 5. Push off with back leg — drive body forward
    set_lower(push_hip_p, hip_back)
    time.sleep(spd)

    # 6. Recenter hips
    set_lower(push_hip_r, STEP_HIP_CENTER)
    set_lower(lift_hip_p, STEP_HIP_CENTER)
    time.sleep(spd)


def _walk_loop(steps, knee_lift, hip_fwd, hip_back, spd):
    global _walking
    print(f"[Servo] Walking {steps} steps")
    go_neutral()
    time.sleep(0.5)
    side = 'R'
    for i in range(steps):
        if not _walking:
            break
        _one_step(side, knee_lift=knee_lift, hip_fwd=hip_fwd,
                  hip_back=hip_back, spd=spd)
        side = 'L' if side == 'R' else 'R'
    go_neutral()
    _walking = False
    print("[Servo] Walk complete")


def walk(steps=4):
    """Walk forward the given number of steps."""
    global _walking, _walk_thread
    if _walking:
        print("[Servo] Already walking")
        return
    _walking = True
    _walk_thread = threading.Thread(
        target=_walk_loop,
        args=(steps, STEP_KNEE_LIFT, STEP_HIP_FORWARD, STEP_HIP_BACK, STEP_SPEED),
        daemon=True
    )
    _walk_thread.start()


def walk_stairs(steps=3):
    """Walk up stairs — higher knee lift, slower, more deliberate."""
    global _walking, _walk_thread
    if _walking:
        print("[Servo] Already walking")
        return
    print(f"[Servo] Walking up {steps} stairs")
    _walking = True
    _walk_thread = threading.Thread(
        target=_walk_loop,
        args=(steps, STAIR_KNEE_LIFT, STAIR_HIP_FORWARD, STEP_HIP_BACK, STAIR_SPEED),
        daemon=True
    )
    _walk_thread.start()


def stop_walking():
    """Stop walking mid-gait and return to neutral."""
    global _walking
    _walking = False
    time.sleep(0.5)
    go_neutral()


# ── Voice command hooks (call these from bluefish.py handle_command) ──────────
def handle_servo_command(text):
    """Returns True if a servo command was handled."""
    t = text.lower()

    if "walk" in t and "stair" in t:
        walk_stairs()
        return True

    if "walk" in t or "go forward" in t:
        # Try to parse number of steps
        import re
        nums = re.findall(r'\d+', t)
        steps = int(nums[0]) if nums else 4
        walk(steps)
        return True

    if "stop" in t or "stand still" in t or "freeze" in t:
        stop_walking()
        return True

    if "wave" in t and "left" in t:
        threading.Thread(target=wave_left, daemon=True).start()
        return True

    if "wave" in t or "hello" in t or "hi" in t:
        threading.Thread(target=wave_right, daemon=True).start()
        return True

    if "look left" in t:
        move_head(pan=45)
        return True

    if "look right" in t:
        move_head(pan=135)
        return True

    if "look up" in t:
        move_head(tilt=130)
        return True

    if "look down" in t:
        move_head(tilt=50)
        return True

    if "look straight" in t or "look forward" in t or "center" in t:
        move_head(pan=90, tilt=90)
        return True

    if "neutral" in t or "rest" in t or "stand" in t:
        threading.Thread(target=go_neutral, daemon=True).start()
        return True

    return False
