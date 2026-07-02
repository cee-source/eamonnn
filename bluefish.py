#!/usr/bin/env python3
"""Blue Fish - AI robot brain for Raspberry Pi 5 / CrunchLabs Omnibot"""

import os, sys, time, json, queue, threading, subprocess, pickle, datetime, math, secrets
sys.stdout.reconfigure(line_buffering=True)
import numpy as np
import sounddevice as sd
import whisper
from http.server import HTTPServer, BaseHTTPRequestHandler
from socketserver import ThreadingMixIn
from urllib.parse import parse_qs, urlparse

# ── Audio config ─────────────────────────────────────────────────────────────
CHUNK         = 1024
# Auto-find the USB mic by name, fall back to default input
try:
    import sounddevice as _sd
    _devs = _sd.query_devices()
    DEVICE = next(
        (i for i, d in enumerate(_devs)
         if "usb" in d["name"].lower() and d["max_input_channels"] > 0),
        None
    )
    if DEVICE is None:
        DEVICE = _sd.default.device[0]
    _dev         = _sd.query_devices(DEVICE, "input")
    SAMPLERATE   = int(_dev["default_samplerate"])
    MIC_CHANNELS = max(1, int(_dev["max_input_channels"]))
    print(f"[Audio] Using mic: {_dev['name']} (device {DEVICE}, {SAMPLERATE}Hz, {MIC_CHANNELS}ch)")
except Exception as e:
    DEVICE       = None
    SAMPLERATE   = 44100
    MIC_CHANNELS = 1
    print(f"[Audio] Mic detection failed: {e}")
SILENCE_THRESHOLD = 300
MAX_SILENCE   = 1.5

# ── Paths ─────────────────────────────────────────────────────────────────────
HOME             = "/home/fussykitten12"
PIPER            = f"{HOME}/.local/bin/piper"
VOICE_MODEL      = f"{HOME}/piper_voices/en_US-ryan-high.onnx"
BT_SPEAKER       = "E6:8A:D3:4B:55:67"
VOICE_PROFILE    = f"{HOME}/voice_profile.pkl"
FACE_PROFILES_DB = f"{HOME}/face_profiles.pkl"   # {name: encoding}
FACE_PROFILE_OLD = f"{HOME}/face_profile.pkl"    # legacy single-person file
KNOWLEDGE_DB     = f"{HOME}/knowledge.json"
SHAPE_MODEL      = f"{HOME}/shape_predictor_68_face_landmarks.dat"
CONVO_LOG        = f"{HOME}/conversation_log.json"

# ── Auth config ──────────────────────────────────────────────────────────────
OWNER_EMAIL    = "ehmcdermott77@gmail.com"
OWNER_PASSWORD = "bluefish2025"      # change this to whatever you want
DRIVE_OVERRIDE = "BLUEFISH"          # type this to unlock drive mode

valid_sessions  = set()
sessions_lock   = threading.Lock()

# ── Sonar config ─────────────────────────────────────────────────────────────
SONAR_TRIG     = 23          # GPIO BCM pin for HC-SR04 trigger
SONAR_ECHO     = 24          # GPIO BCM pin for HC-SR04 echo
SONAR_MAX_CM   = 300         # anything beyond this is "open"
SCAN_STEPS     = 8           # readings per 360° sweep (every 45°)
SCAN_ROT_TIME  = 0.45        # seconds of "R" motor per 45° — tune on your bot

# ── Global state ──────────────────────────────────────────────────────────────
stream_frame      = b""
stream_lock       = threading.Lock()
latest_camera_frame = None
camera_lock       = threading.Lock()

face_in_view      = False
face_is_known     = False
face_direction    = "center"
gaze_direction    = "center"
face_overlays     = []
face_overlay_lock = threading.Lock()

# Multi-person face profiles
face_profiles     = {}          # {name: numpy encoding}
face_profiles_lock = threading.Lock()

# Enrollment state
enrolling         = False
enroll_name       = ""
enroll_samples    = []
enroll_done       = False
enroll_level      = 3           # level chosen in browser for current enrollment
enroll_lock       = threading.Lock()
ENROLL_NEEDED     = 100

STRANGER_LEVEL    = 99          # strangers: read-only (questions only)
commander_level   = STRANGER_LEVEL   # level of whoever gave the last command
commander_lock    = threading.Lock()

learn_mode        = False
knowledge         = {"facts": []}
speaking          = False
serial_conn       = None
conversation_log  = []          # list of {when, who, said, replied}

# Sonar state
sonar_distance    = None        # float cm, or None if no reading
sonar_map         = []          # list of [angle_deg, dist_cm] from last scan
sonar_scanning    = False
sonar_lock        = threading.Lock()
_sonar_sensor     = None        # gpiozero DistanceSensor instance

# ── Face profiles ─────────────────────────────────────────────────────────────
def _normalise(v):
    """Ensure profile value is always {enc, level} dict."""
    if isinstance(v, dict) and "enc" in v:
        return v
    return {"enc": v, "level": 1}   # old plain-array format → assume owner

def load_face_profiles():
    global face_profiles
    if os.path.exists(FACE_PROFILES_DB):
        try:
            with open(FACE_PROFILES_DB, "rb") as f:
                raw = pickle.load(f)
            face_profiles = {n: _normalise(v) for n, v in raw.items()}
            print(f"[Faces] Loaded {len(face_profiles)} profile(s): "
                  + ", ".join(f"{n}(L{v['level']})" for n,v in face_profiles.items()))
            return
        except Exception:
            pass
    # Migrate legacy single-person file
    if os.path.exists(FACE_PROFILE_OLD):
        try:
            with open(FACE_PROFILE_OLD, "rb") as f:
                enc = pickle.load(f)
            face_profiles = {"Eamonn": {"enc": enc, "level": 1}}
            save_face_profiles()
            print("[Faces] Migrated legacy face_profile.pkl → Eamonn (level 1)")
        except Exception:
            pass

def save_face_profiles():
    with open(FACE_PROFILES_DB, "wb") as f:
        pickle.dump(face_profiles, f)

# ── Sonar ─────────────────────────────────────────────────────────────────────
def init_sonar():
    global _sonar_sensor
    try:
        from gpiozero import DistanceSensor
        _sonar_sensor = DistanceSensor(echo=SONAR_ECHO, trigger=SONAR_TRIG,
                                       max_distance=SONAR_MAX_CM / 100)
        print(f"[Sonar] HC-SR04 ready on TRIG={SONAR_TRIG} ECHO={SONAR_ECHO}")
    except Exception as e:
        _sonar_sensor = None
        print(f"[Sonar] Not available: {e}")

def sonar_read_cm():
    """Return distance in cm, or None on error."""
    if _sonar_sensor is None:
        return None
    try:
        d = _sonar_sensor.distance * 100
        return round(d, 1) if d < SONAR_MAX_CM else None
    except Exception:
        return None

def sonar_loop():
    """Background thread: refresh sonar_distance every 0.2 s."""
    global sonar_distance
    while True:
        d = sonar_read_cm()
        with sonar_lock:
            sonar_distance = d
        time.sleep(0.2)

def do_scan():
    """Rotate 360° in SCAN_STEPS steps and build a polar map."""
    global sonar_map, sonar_scanning
    with sonar_lock:
        sonar_scanning = True
    pts = []
    deg_per_step = 360 // SCAN_STEPS
    for i in range(SCAN_STEPS):
        angle = i * deg_per_step
        d = sonar_read_cm() or SONAR_MAX_CM
        pts.append([angle, d])
        print(f"[Sonar] scan {angle}°: {d} cm")
        send_motor("R", SCAN_ROT_TIME)
        time.sleep(SCAN_ROT_TIME + 0.25)   # wait for rotation + settle
    with sonar_lock:
        sonar_map = pts
        sonar_scanning = False
    speak("Scan complete.")

def make_sonar_image():
    """Render the current sonar map as a 400×400 PNG bytes — blue radar style."""
    import cv2
    SIZE = 400
    img = np.zeros((SIZE, SIZE, 3), dtype=np.uint8)
    cx, cy, r = SIZE // 2, SIZE // 2, SIZE // 2 - 16

    # Deep blue background tint
    img[:] = (18, 6, 0)   # very dark navy

    # Concentric range rings — bright inner → dim outer
    ring_colors = [(180, 60, 0), (140, 45, 0), (100, 30, 0), (60, 18, 0)]
    ring_labels = ["75", "150", "225", str(SONAR_MAX_CM)]
    for i, frac in enumerate([0.25, 0.5, 0.75, 1.0]):
        rr = int(r * frac)
        cv2.circle(img, (cx, cy), rr, ring_colors[i], 1, cv2.LINE_AA)
        cv2.putText(img, ring_labels[i] + "cm", (cx + rr + 2, cy - 2),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.28, ring_colors[i], 1, cv2.LINE_AA)

    # Diagonal spokes at 45° intervals — dim
    for deg in range(0, 360, 45):
        rad = math.radians(deg - 90)
        ex = int(cx + math.cos(rad) * r)
        ey = int(cy + math.sin(rad) * r)
        cv2.line(img, (cx, cy), (ex, ey), (50, 16, 0), 1, cv2.LINE_AA)

    # Cardinal labels
    cv2.putText(img, "FWD", (cx - 14, 10),   cv2.FONT_HERSHEY_SIMPLEX, 0.35, (200, 90, 0), 1, cv2.LINE_AA)
    cv2.putText(img, "BCK", (cx - 14, SIZE - 3), cv2.FONT_HERSHEY_SIMPLEX, 0.35, (120, 50, 0), 1, cv2.LINE_AA)
    cv2.putText(img, "L",   (3, cy + 4),      cv2.FONT_HERSHEY_SIMPLEX, 0.35, (120, 50, 0), 1, cv2.LINE_AA)
    cv2.putText(img, "R",   (SIZE - 14, cy + 4), cv2.FONT_HERSHEY_SIMPLEX, 0.35, (120, 50, 0), 1, cv2.LINE_AA)

    with sonar_lock:
        pts = list(sonar_map)
        d_now = sonar_distance
        scanning = sonar_scanning

    # Plot scan rays — bright blue line + glowing dot at obstacle
    for angle_deg, dist in pts:
        ratio = min(dist / SONAR_MAX_CM, 1.0)
        rad = math.radians(angle_deg - 90)
        px = int(cx + math.cos(rad) * r * ratio)
        py = int(cy + math.sin(rad) * r * ratio)
        # Faint ray from centre to obstacle
        cv2.line(img, (cx, cy), (px, py), (130, 40, 0), 1, cv2.LINE_AA)
        # Bright dot with soft glow
        cv2.circle(img, (px, py), 8,  (200, 80,  0), -1, cv2.LINE_AA)
        cv2.circle(img, (px, py), 5,  (255, 160, 0), -1, cv2.LINE_AA)
        cv2.circle(img, (px, py), 2,  (255, 255, 200), -1, cv2.LINE_AA)

    # Live forward-distance sweep line — bright cyan-blue
    if d_now is not None:
        ratio = min(d_now / SONAR_MAX_CM, 1.0)
        py2 = int(cy - r * ratio)
        cv2.line(img, (cx, cy), (cx, py2), (255, 200, 0), 2, cv2.LINE_AA)
        cv2.circle(img, (cx, py2), 4, (255, 255, 0), -1, cv2.LINE_AA)

    # Centre dot
    cv2.circle(img, (cx, cy), 4, (180, 100, 0), -1, cv2.LINE_AA)

    # Status text bottom-left
    if scanning:
        label = "SCANNING..."
        col = (100, 220, 255)
    elif d_now is not None:
        label = f"{d_now:.0f} cm ahead"
        col = (160, 220, 255)
    else:
        label = "no sensor"
        col = (80, 80, 120)
    cv2.putText(img, label, (6, SIZE - 6), cv2.FONT_HERSHEY_SIMPLEX, 0.45, col, 1, cv2.LINE_AA)

    _, buf = cv2.imencode(".png", img)
    return buf.tobytes()

# ── Walkie-talkie ─────────────────────────────────────────────────────────────
_talk_proc  = None
_talk_lock  = threading.Lock()
_talk_timer = None

def play_talk_chunk(data):
    global _talk_proc, _talk_timer
    with _talk_lock:
        if _talk_proc is None or _talk_proc.poll() is not None:
            try:
                _talk_proc = subprocess.Popen(
                    ["aplay", "-D", f"bluealsa:DEV={BT_SPEAKER},PROFILE=a2dp",
                     "-r", "22050", "-f", "S16_LE", "-c", "1"],
                    stdin=subprocess.PIPE,
                    stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL
                )
            except Exception as e:
                print(f"[Talk] {e}")
                return
        try:
            _talk_proc.stdin.write(data)
            _talk_proc.stdin.flush()
        except Exception:
            pass
    if _talk_timer:
        _talk_timer.cancel()
    _talk_timer = threading.Timer(1.5, _close_talk)
    _talk_timer.daemon = True
    _talk_timer.start()

def _close_talk():
    global _talk_proc
    with _talk_lock:
        if _talk_proc:
            try:
                _talk_proc.stdin.close()
                _talk_proc.wait(timeout=2)
            except Exception:
                try: _talk_proc.kill()
                except Exception: pass
            _talk_proc = None

# ── Knowledge base ────────────────────────────────────────────────────────────
def load_knowledge():
    global knowledge
    if os.path.exists(KNOWLEDGE_DB):
        try:
            with open(KNOWLEDGE_DB) as f:
                knowledge = json.load(f)
        except Exception:
            knowledge = {"facts": []}

def save_knowledge():
    with open(KNOWLEDGE_DB, "w") as f:
        json.dump(knowledge, f, indent=2)

# ── Conversation log ──────────────────────────────────────────────────────────
def load_conversation_log():
    global conversation_log
    if os.path.exists(CONVO_LOG):
        try:
            with open(CONVO_LOG) as f:
                conversation_log = json.load(f)
            # Keep last 200 entries in memory
            conversation_log = conversation_log[-200:]
        except Exception:
            conversation_log = []

def save_conversation(who, said, replied):
    entry = {
        "when": datetime.datetime.now().strftime("%Y-%m-%d %H:%M"),
        "who": who,
        "said": said,
        "replied": replied,
    }
    conversation_log.append(entry)
    try:
        # Keep file to last 500 entries
        log = conversation_log[-500:]
        with open(CONVO_LOG, "w") as f:
            json.dump(log, f, indent=2)
    except Exception as e:
        print(f"[Log] {e}")

def recent_conversation_context(n=5):
    """Return last n exchanges as a string for the AI prompt."""
    recent = conversation_log[-n:]
    if not recent:
        return ""
    lines = ["Recent conversation:"]
    for e in recent:
        lines.append(f"  {e['who']}: {e['said']}")
        lines.append(f"  Blue Fish: {e['replied']}")
    return "\n".join(lines)

# ── TTS ───────────────────────────────────────────────────────────────────────
def speak(text):
    global speaking
    speaking = True
    print(f"[TTS] {text}")
    try:
        proc = subprocess.Popen(
            [PIPER, "--model", VOICE_MODEL, "--output_raw"],
            stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.DEVNULL
        )
        raw, _ = proc.communicate(text.encode())
        try:
            bt = subprocess.run(
                ["aplay", "-D", f"bluealsa:DEV={BT_SPEAKER},PROFILE=a2dp",
                 "-r", "22050", "-f", "S16_LE", "-c", "1"],
                input=raw, capture_output=True, timeout=30
            )
            if bt.returncode != 0:
                raise Exception("BT failed")
        except Exception:
            subprocess.run(
                ["aplay", "-r", "22050", "-f", "S16_LE", "-c", "1"],
                input=raw, capture_output=True, timeout=30
            )
    except Exception as e:
        print(f"[TTS error] {e}")
    finally:
        speaking = False

# ── Arduino serial ────────────────────────────────────────────────────────────
def init_serial():
    global serial_conn
    try:
        import serial
        serial_conn = serial.Serial("/dev/ttyUSB0", 115200, timeout=1)
        time.sleep(2)
        print("[Serial] Arduino connected")
    except Exception as e:
        print(f"[Serial] Not connected: {e}")

def send_motor(cmd, duration=0.5):
    if serial_conn:
        try:
            serial_conn.write(f"{cmd}\n".encode())
            time.sleep(duration)
            serial_conn.write(b"S\n")
        except Exception as e:
            print(f"[Serial] {e}")

# ── Face analysis ─────────────────────────────────────────────────────────────
def analyze_face(frame):
    global face_in_view, face_is_known, face_direction, gaze_direction
    global face_overlays, enroll_done, enrolling, enroll_name, enroll_samples

    try:
        import cv2, face_recognition, dlib

        rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        locations = face_recognition.face_locations(rgb, number_of_times_to_upsample=2, model="hog")
        face_in_view = len(locations) > 0

        if not face_in_view:
            with face_overlay_lock:
                face_overlays = []
            return

        encodings = face_recognition.face_encodings(rgb, locations)

        # Handle enrollment
        with enroll_lock:
            currently_enrolling = enrolling
            current_name = enroll_name

        if currently_enrolling and encodings:
            with enroll_lock:
                enroll_samples.append(encodings[0])
                count = len(enroll_samples)
                lvl   = enroll_level
            print(f"[Enroll] {current_name}: {count}/{ENROLL_NEEDED} samples")
            if count >= ENROLL_NEEDED:
                with enroll_lock:
                    avg = np.mean(enroll_samples, axis=0)
                with face_profiles_lock:
                    face_profiles[current_name] = {"enc": avg, "level": lvl}
                    save_face_profiles()
                with enroll_lock:
                    enrolling = False
                    enroll_done = True
                print(f"[Enroll] Done! {current_name} saved.")
                speak(f"Got it! I've saved {current_name}'s face to my memory.")

        # Load dlib predictor if available
        predictor = None
        if os.path.exists(SHAPE_MODEL):
            try:
                predictor = dlib.shape_predictor(SHAPE_MODEL)
            except Exception:
                pass

        new_overlays = []
        with face_profiles_lock:
            profiles_snapshot = dict(face_profiles)

        for (top, right, bottom, left), enc in zip(locations, encodings):
            name = "Stranger"
            face_level = STRANGER_LEVEL
            if profiles_snapshot:
                pnames = list(profiles_snapshot.keys())
                pencs  = [v["enc"] for v in profiles_snapshot.values()]
                plvls  = [v["level"] for v in profiles_snapshot.values()]
                distances = face_recognition.face_distance(pencs, enc)
                best_idx = int(np.argmin(distances))
                if distances[best_idx] < 0.45:
                    name = pnames[best_idx]
                    face_level = plvls[best_idx]

            face_is_known = (name != "Stranger")
            color = (0, 200, 0) if name != "Stranger" else (0, 140, 255)

            head_label = ""
            gaze_label = ""
            if predictor is not None:
                try:
                    h, w = frame.shape[:2]
                    gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
                    rect = dlib.rectangle(left, top, right, bottom)
                    shape = predictor(gray, rect)
                    pts = np.array([[shape.part(i).x, shape.part(i).y] for i in range(68)], dtype=np.float32)

                    model_pts = np.array([
                        (0.0,    0.0,    0.0),
                        (0.0,  -330.0,  -65.0),
                        (-225.0, 170.0, -135.0),
                        ( 225.0, 170.0, -135.0),
                        (-150.0,-150.0, -125.0),
                        ( 150.0,-150.0, -125.0),
                    ], dtype=np.float64)
                    image_pts = np.array([pts[30], pts[8], pts[36], pts[45], pts[48], pts[54]], dtype=np.float64)
                    focal = w
                    cam_mat = np.array([[focal,0,w/2],[0,focal,h/2],[0,0,1]], dtype=np.float64)
                    ok, rvec, _ = cv2.solvePnP(model_pts, image_pts, cam_mat, np.zeros((4,1)), flags=cv2.SOLVEPNP_ITERATIVE)
                    if ok:
                        rot_mat, _ = cv2.Rodrigues(rvec)
                        angles, *_ = cv2.RQDecomp3x3(rot_mat)
                        yaw = angles[1]
                        face_direction = "left" if yaw < -15 else "right" if yaw > 15 else "center"
                        head_label = f"Head: {face_direction}"

                    def eye_ratio(idxs):
                        eye = pts[idxs].astype(int)
                        ex, ey, ew, eh = cv2.boundingRect(eye)
                        if ew < 2 or eh < 2: return 0.5
                        roi = gray[ey:ey+eh, ex:ex+ew]
                        if roi.size == 0: return 0.5
                        _, thr = cv2.threshold(roi, 70, 255, cv2.THRESH_BINARY_INV)
                        lh = thr[:, :ew//2].sum(); rh = thr[:, ew//2:].sum()
                        return lh / (lh + rh) if (lh + rh) > 0 else 0.5

                    ratio = (eye_ratio(list(range(36,42))) + eye_ratio(list(range(42,48)))) / 2
                    gaze_direction = "left" if ratio > 0.6 else "right" if ratio < 0.4 else "center"
                    gaze_label = f"Gaze: {gaze_direction}"
                except Exception:
                    pass

            new_overlays.append({"box": (left,top,right,bottom), "name": name,
                                  "level": face_level, "color": color,
                                  "head": head_label, "gaze": gaze_label})
            print(f"[Face] {name} (level {face_level})")

        with face_overlay_lock:
            face_overlays = new_overlays

    except Exception as e:
        print(f"[Face error] {e}")

# ── Camera loop ───────────────────────────────────────────────────────────────
def camera_loop():
    global latest_camera_frame, stream_frame

    import cv2

    cmd = ["rpicam-vid", "-t", "0", "--width", "640", "--height", "480",
           "--framerate", "30", "--codec", "mjpeg", "--inline", "-o", "-"]
    proc = None
    face_counter = 0
    print("[Camera] thread started")

    while True:
        print("[Camera] launching rpicam-vid")
        try:
            proc = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, bufsize=0)
            buf = b""
            while True:
                chunk = proc.stdout.read(4096)
                if not chunk:
                    break
                buf += chunk
                while True:
                    start = buf.find(b"\xff\xd8")
                    end   = buf.find(b"\xff\xd9", start + 2)
                    if start == -1 or end == -1:
                        break
                    jpeg = buf[start:end+2]
                    buf  = buf[end+2:]

                    arr   = np.frombuffer(jpeg, dtype=np.uint8)
                    frame = cv2.imdecode(arr, cv2.IMREAD_COLOR)
                    if frame is None:
                        continue

                    with camera_lock:
                        latest_camera_frame = frame.copy()

                    # Draw face overlays on every frame
                    display = frame.copy()
                    with face_overlay_lock:
                        overlays = list(face_overlays)
                    for o in overlays:
                        l, t, r, b2 = o["box"]
                        col  = o["color"]
                        name = o["name"]
                        cv2.rectangle(display, (l,t), (r,b2), col, 2)
                        ly = max(t-10, 20)
                        label = name + " L" + str(o.get("level", "?"))
                        (tw,th),_ = cv2.getTextSize(label, cv2.FONT_HERSHEY_SIMPLEX, 0.8, 2)
                        cx = (l+r)//2
                        cv2.rectangle(display,(cx-tw//2-4,ly-th-6),(cx+tw//2+4,ly+2),col,-1)
                        cv2.putText(display,label,(cx-tw//2,ly),cv2.FONT_HERSHEY_SIMPLEX,0.8,(255,255,255),2)
                        if o["head"]:
                            cv2.putText(display, o["head"], (l, b2+20), cv2.FONT_HERSHEY_SIMPLEX, 0.55, col, 1)
                        if o["gaze"]:
                            cv2.putText(display, o["gaze"], (l, b2+40), cv2.FONT_HERSHEY_SIMPLEX, 0.55, col, 1)

                    # Show enrollment progress on screen
                    with enroll_lock:
                        if enrolling:
                            n = len(enroll_samples)
                            elabel = f"Enrolling {enroll_name}: {n}/{ENROLL_NEEDED}"
                            cv2.putText(display, elabel, (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0,255,255), 2)

                    _, raw_buf = cv2.imencode(".jpg", display, [cv2.IMWRITE_JPEG_QUALITY, 85])
                    with stream_lock:
                        stream_frame = raw_buf.tobytes()

                    face_counter += 1
                    if face_counter % 30 == 0:
                        print(f"[Camera] {face_counter} frames")
                    if face_counter % 30 == 0:
                        t2 = threading.Thread(target=analyze_face, args=(frame.copy(),), daemon=True)
                        t2.start()

        except Exception as e:
            err = b""
            if proc:
                try: err = proc.stderr.read(300)
                except Exception: pass
            print(f"[Camera] error: {e} stderr: {err}")
        finally:
            if proc:
                try: proc.kill()
                except Exception: pass
        time.sleep(2)

# ── HTTP server ───────────────────────────────────────────────────────────────
class StreamHandler(BaseHTTPRequestHandler):
    def log_message(self, fmt, *args):
        pass

    def _check_session(self):
        cookie = self.headers.get("Cookie", "")
        for part in cookie.split(";"):
            k, _, v = part.strip().partition("=")
            if k.strip() == "bf_session":
                with sessions_lock:
                    return v.strip() in valid_sessions
        return False

    def _serve_locked_page(self, error=False):
        err_msg = '<p style="color:#c00;font-size:13px;">Wrong email or password.</p>' if error else ""
        html = f"""<!DOCTYPE html>
<html><head><title> </title>
<style>
*{{margin:0;padding:0;box-sizing:border-box;}}
body{{background:#fff;}}
#corner{{position:fixed;top:0;right:0;width:60px;height:60px;
  background:transparent;border:none;cursor:default;z-index:10;}}
#box{{display:none;position:fixed;top:50%;left:50%;
  transform:translate(-50%,-50%);
  background:#0a0a0a;border:1px solid #1a5fa8;border-radius:10px;
  padding:32px 36px;min-width:280px;text-align:center;
  box-shadow:0 0 40px rgba(30,100,255,0.25);}}
h3{{color:#4a9eff;font-family:monospace;letter-spacing:2px;margin-bottom:18px;}}
input{{display:block;width:100%;background:#111;color:#cde;
  border:1px solid #1a5fa8;border-radius:5px;padding:9px 12px;
  font-size:14px;margin-bottom:12px;font-family:monospace;outline:none;}}
input:focus{{border-color:#4a9eff;}}
button[type=submit]{{width:100%;background:#1a5fa8;color:#fff;
  border:none;border-radius:5px;padding:10px;font-size:14px;
  font-family:monospace;cursor:pointer;letter-spacing:1px;}}
button[type=submit]:hover{{background:#2274d4;}}
</style>
</head>
<body>
<button id="corner" onclick="document.getElementById('box').style.display='block';"></button>
<div id="box">
  <h3>BLUE FISH</h3>
  {err_msg}
  <form method="POST" action="/login">
    <input name="email" type="email" placeholder="Email" autocomplete="email" required>
    <input name="password" type="password" placeholder="Password" autocomplete="current-password" required>
    <button type="submit">ENTER</button>
  </form>
</div>
</body></html>"""
        body = html.encode()
        self.send_response(200)
        self.send_header("Content-Type", "text/html")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self):
        parsed = urlparse(self.path)
        path   = parsed.path
        params = parse_qs(parsed.query)

        if path == "/login":
            self._serve_locked_page(error="err" in params)
            return
        if not self._check_session():
            self._serve_locked_page()
            return

        if path == "/stream":
            # Write raw HTTP — bypasses BaseHTTPRequestHandler's Connection:close
            header = (
                b"HTTP/1.1 200 OK\r\n"
                b"Content-Type: multipart/x-mixed-replace; boundary=bf\r\n"
                b"Cache-Control: no-cache\r\n"
                b"Connection: keep-alive\r\n\r\n"
            )
            self.connection.sendall(header)
            try:
                last = None
                while True:
                    with stream_lock:
                        data = stream_frame
                    if data and data is not last:
                        chunk = (
                            b"--bf\r\nContent-Type: image/jpeg\r\nContent-Length: " +
                            str(len(data)).encode() + b"\r\n\r\n" + data + b"\r\n"
                        )
                        self.connection.sendall(chunk)
                        last = data
                    time.sleep(0.05)
            except Exception:
                pass
            return

        elif path.startswith("/frame"):
            with stream_lock:
                data = stream_frame
            if data:
                self.send_response(200)
                self.send_header("Content-Type", "image/jpeg")
                self.send_header("Content-Length", str(len(data)))
                self.send_header("Cache-Control", "no-store")
                self.end_headers()
                self.wfile.write(data)
            else:
                self.send_response(503)
                self.end_headers()

        elif path == "/enroll_status":
            with enroll_lock:
                n     = len(enroll_samples)
                done  = enroll_done
                busy  = enrolling
                ename = enroll_name
            body = json.dumps({
                "enrolling": busy,
                "name": ename,
                "samples": n,
                "needed": ENROLL_NEEDED,
                "done": done,
            }).encode()
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)

        elif path == "/profiles":
            with face_profiles_lock:
                people = [{"name": n, "level": v.get("level", 1)}
                          for n, v in face_profiles.items()]
            body = json.dumps({"people": people}).encode()
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)

        elif path == "/drive":
            self._serve_drive_page()
            return

        elif path == "/sonar_map":
            if _sonar_sensor is None:
                # Return a placeholder image when sensor isn't wired up
                data = make_sonar_image()
            else:
                data = make_sonar_image()
            self.send_response(200)
            self.send_header("Content-Type", "image/png")
            self.send_header("Content-Length", str(len(data)))
            self.send_header("Cache-Control", "no-store")
            self.end_headers()
            self.wfile.write(data)

        else:
            self._serve_page()

    def do_POST(self):
        parsed = urlparse(self.path)
        path   = parsed.path
        length = int(self.headers.get("Content-Length", 0))
        raw    = self.rfile.read(length).decode()
        params = parse_qs(raw)

        if path == "/login":
            email = params.get("email", [""])[0].strip().lower()
            pw    = params.get("password", [""])[0]
            if email == OWNER_EMAIL.lower() and pw == OWNER_PASSWORD:
                token = secrets.token_hex(32)
                with sessions_lock:
                    valid_sessions.add(token)
                self.send_response(302)
                self.send_header("Location", "/")
                self.send_header("Set-Cookie",
                    f"bf_session={token}; Path=/; HttpOnly; SameSite=Strict")
                self.send_header("Content-Length", "0")
                self.end_headers()
            else:
                self.send_response(302)
                self.send_header("Location", "/login?err=1")
                self.send_header("Content-Length", "0")
                self.end_headers()
            return

        if not self._check_session():
            self.send_response(403)
            self.send_header("Content-Length", "0")
            self.end_headers()
            return

        if path == "/enroll":
            name = params.get("name", [""])[0].strip()
            lvl  = int(params.get("level", ["3"])[0])
            if name:
                with enroll_lock:
                    global enrolling, enroll_name, enroll_samples, enroll_done, enroll_level
                    enrolling      = True
                    enroll_name    = name
                    enroll_level   = lvl
                    enroll_samples = []
                    enroll_done    = False
                print(f"[Enroll] Starting: {name} level {lvl}")
            self.send_response(302)
            self.send_header("Location", "/")
            self.send_header("Content-Length", "0")
            self.end_headers()

        elif path == "/forget":
            name = params.get("name", [""])[0].strip()
            with face_profiles_lock:
                if name in face_profiles:
                    del face_profiles[name]
                    save_face_profiles()
            self.send_response(302)
            self.send_header("Location", "/")
            self.send_header("Content-Length", "0")
            self.end_headers()

        elif path == "/forget_all":
            with face_profiles_lock:
                face_profiles.clear()
                save_face_profiles()
            self.send_response(302)
            self.send_header("Location", "/")
            self.send_header("Content-Length", "0")
            self.end_headers()

        elif path == "/scan":
            if not sonar_scanning:
                threading.Thread(target=do_scan, daemon=True).start()
            self.send_response(302)
            self.send_header("Location", "/")
            self.send_header("Content-Length", "0")
            self.end_headers()

        elif path == "/talk":
            length = int(self.headers.get("Content-Length", 0))
            data = self.rfile.read(length)
            print(f"[Talk] received {length} bytes")
            play_talk_chunk(data)
            self.send_response(200)
            self.send_header("Content-Length", "0")
            self.end_headers()

        elif path == "/motor":
            cmd = params.get("cmd", ["S"])[0].strip().upper()
            if cmd in ("F", "B", "L", "R", "S", "U", "D", "SL", "SR"):
                if serial_conn:
                    try:
                        serial_conn.write(f"{cmd}\n".encode())
                    except Exception as e:
                        print(f"[Motor] {e}")
            self.send_response(200)
            self.send_header("Content-Length", "0")
            self.end_headers()

        else:
            self.send_response(404)
            self.send_header("Content-Length", "0")
            self.end_headers()

    def _serve_drive_page(self):
        html = f"""<!DOCTYPE html>
<html><head><title>Blue Fish — Drive Mode</title>
<style>
*{{margin:0;padding:0;box-sizing:border-box;}}
body{{background:#000;overflow:hidden;font-family:monospace;}}
#gate{{position:fixed;top:0;left:0;width:100%;height:100%;
  background:#000;display:flex;flex-direction:column;
  align-items:center;justify-content:center;z-index:100;}}
#gate h2{{color:#f00;letter-spacing:6px;font-size:24px;margin-bottom:8px;}}
#gate p{{color:#555;margin-bottom:20px;}}
#code{{background:#111;color:#f00;border:2px solid #f00;
  padding:12px 20px;font-size:20px;font-family:monospace;
  text-align:center;border-radius:6px;outline:none;width:280px;
  letter-spacing:4px;}}
#code.wrong{{border-color:#f00;animation:shake 0.3s;}}
@keyframes shake{{0%,100%{{transform:translateX(0)}}25%{{transform:translateX(-8px)}}75%{{transform:translateX(8px)}}}}
#cam{{width:100vw;height:100vh;object-fit:cover;display:block;}}
#sonar{{position:fixed;bottom:12px;right:12px;width:220px;height:220px;
  border:2px solid #0f0;border-radius:4px;opacity:0.9;}}
#hud{{position:fixed;top:12px;left:12px;color:#f00;
  background:rgba(0,0,0,0.7);padding:8px 14px;border-radius:4px;
  border:1px solid #f00;letter-spacing:2px;font-size:13px;}}
#back{{position:fixed;top:12px;right:12px;color:#555;
  background:rgba(0,0,0,0.7);padding:6px 12px;border-radius:4px;
  border:1px solid #333;font-size:12px;text-decoration:none;}}
#back:hover{{color:#0f0;border-color:#0f0;}}
#keys{{position:fixed;bottom:12px;left:12px;
  background:rgba(0,0,0,0.7);padding:10px;border-radius:6px;
  border:1px solid #333;color:#0f0;font-size:13px;line-height:2;}}
.k{{display:inline-block;background:#222;border:1px solid #0f0;
  border-radius:3px;padding:1px 7px;margin:1px;min-width:24px;text-align:center;}}
.k.on{{background:#0f0;color:#000;}}
</style></head>
<body>

<div id="gate">
  <h2>⚠ MANUAL OVERRIDE ⚠</h2>
  <p>Type the override code to enter drive mode</p>
  <input id="code" type="password" placeholder="override code" autofocus
    autocomplete="off" spellcheck="false">
  <p id="hint" style="color:#333;margin-top:10px;font-size:12px;">press ENTER to confirm</p>
</div>

<img id="cam" src="" style="display:none;">
<img id="sonar" src="" style="display:none;"
  onload="setTimeout(function(){{document.getElementById('sonar').src='/sonar_map?t='+Date.now();}},400);"
  onerror="setTimeout(function(){{document.getElementById('sonar').src='/sonar_map?t='+Date.now();}},800);">
<div id="hud" style="display:none;">&#9632; DRIVE MODE ACTIVE</div>
<a id="back" href="/" style="display:none;">&#8592; back</a>
<div id="keys" style="display:none;">
  <div style="text-align:center;"><span class="k" id="kw">W</span></div>
  <div><span class="k" id="ka">A</span> <span class="k" id="ks">S</span> <span class="k" id="kd">D</span></div>
  <div style="color:#555;font-size:11px;margin-top:4px;">SPACE = stop &nbsp; &#8593;&#8595;&#8592;&#8594; also work</div>
</div>
<button id="talkbtn" style="display:none;position:fixed;bottom:12px;left:50%;
  transform:translateX(-50%);background:#300;color:#f55;border:2px solid #f00;
  border-radius:50px;padding:14px 32px;font-family:monospace;font-size:16px;
  letter-spacing:2px;cursor:pointer;user-select:none;-webkit-user-select:none;">
  🎙 HOLD TO TALK
</button>

<script>
var go = false;
var held = null;

document.getElementById('code').addEventListener('keydown', function(e) {{
  if (e.key !== 'Enter') return;
  if (this.value.toUpperCase() === '{DRIVE_OVERRIDE}') {{
    unlock();
  }} else {{
    this.value = '';
    this.placeholder = 'wrong code!';
    this.classList.add('wrong');
    var t = this;
    setTimeout(function(){{t.classList.remove('wrong');t.placeholder='override code';}}, 600);
  }}
}});

function unlock() {{
  document.getElementById('gate').style.display = 'none';
  document.getElementById('cam').style.display = 'block';
  document.getElementById('sonar').style.display = 'block';
  document.getElementById('hud').style.display = 'block';
  document.getElementById('back').style.display = 'block';
  document.getElementById('keys').style.display = 'block';
  go = true;
  document.getElementById('cam').src = '/stream';
  document.getElementById('sonar').src = '/sonar_map?t=' + Date.now();
  showBtn();
}}

var keyMap = {{'w':'F','arrowup':'F','a':'L','arrowleft':'L',
               's':'B','arrowdown':'B','d':'R','arrowright':'R',' ':'S'}};
var keyEls = {{'w':'kw','a':'ka','s':'ks','d':'kd'}};

function motor(cmd) {{
  fetch('/motor', {{method:'POST',
    headers:{{'Content-Type':'application/x-www-form-urlencoded'}},
    body:'cmd='+cmd}});
}}

document.addEventListener('keydown', function(e) {{
  if (!go) return;
  var k = e.key.toLowerCase();
  if (k === ' ') e.preventDefault();
  if (keyMap[k] && held !== k) {{
    held = k;
    motor(keyMap[k]);
    if (keyEls[k]) document.getElementById(keyEls[k]).classList.add('on');
  }}
}});

document.addEventListener('keyup', function(e) {{
  if (!go) return;
  var k = e.key.toLowerCase();
  if (keyMap[k]) {{
    held = null;
    motor('S');
    if (keyEls[k]) document.getElementById(keyEls[k]).classList.remove('on');
  }}
}});

// ── Walkie-talkie ──────────────────────────────────────────
var talkCtx = null, talkProc = null, talkStream = null, talkChunks = [];

function showBtn() {{
  document.getElementById('talkbtn').style.display = 'block';
}}

async function startTalk() {{
  try {{
    talkStream = await navigator.mediaDevices.getUserMedia({{audio:true}});
    talkCtx = new AudioContext({{sampleRate:22050}});
    var src = talkCtx.createMediaStreamSource(talkStream);
    talkProc = talkCtx.createScriptProcessor(8192, 1, 1);
    talkProc.onaudioprocess = function(e) {{
      var f32 = e.inputBuffer.getChannelData(0);
      var i16 = new Int16Array(f32.length);
      for (var i = 0; i < f32.length; i++)
        i16[i] = Math.max(-32768, Math.min(32767, f32[i] * 32768));
      fetch('/talk', {{method:'POST',
        headers:{{'Content-Type':'application/octet-stream'}},
        body: new Uint8Array(i16.buffer)}});
    }};
    src.connect(talkProc);
    talkProc.connect(talkCtx.destination);
    var btn = document.getElementById('talkbtn');
    btn.style.background = '#f00';
    btn.style.color = '#fff';
    btn.textContent = '🔴 TALKING...';
  }} catch(e) {{ alert('Mic error: ' + e.message); }}
}}

function stopTalk() {{
  if (talkProc) {{ talkProc.disconnect(); talkProc = null; }}
  if (talkStream) {{ talkStream.getTracks().forEach(function(t){{t.stop();}}); talkStream = null; }}
  if (talkCtx) {{ talkCtx.close(); talkCtx = null; }}
  var btn = document.getElementById('talkbtn');
  btn.style.background = '#300';
  btn.style.color = '#f55';
  btn.textContent = '🎙 HOLD TO TALK';
}}

document.getElementById('talkbtn').addEventListener('mousedown', startTalk);
document.getElementById('talkbtn').addEventListener('mouseup', stopTalk);
document.getElementById('talkbtn').addEventListener('touchstart', function(e){{e.preventDefault();startTalk();}});
document.getElementById('talkbtn').addEventListener('touchend', function(e){{e.preventDefault();stopTalk();}});
</script>
</body></html>"""
        body = html.encode()
        self.send_response(200)
        self.send_header("Content-Type", "text/html")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def _serve_page(self):
        # Build profiles section server-side — no AJAX needed
        with face_profiles_lock:
            people = [(n, v.get("level", 1)) for n, v in face_profiles.items()]

        people_html = ""
        for name, level in people:
            col = "#0f0" if level == 1 else "#af0" if level <= 2 else "#fa0" if level <= 3 else "#f80"
            safe = name.replace("'", "&#39;").replace('"', "&quot;")
            people_html += (
                f'<span style="margin:4px;display:inline-block;">'
                f'<b style="color:{col};">[L{level}]</b> {safe} '
                f'<form method="POST" action="/forget" style="display:inline;"'
                f' onsubmit="return confirm(\'Forget {safe}?\');">'
                f'<input type="hidden" name="name" value="{safe}">'
                f'<button type="submit">forget</button></form></span>'
            )
        if not people_html:
            people_html = "No one enrolled yet."
        elif people:
            people_html += (
                '<br><form method="POST" action="/forget_all" style="display:inline;margin-top:6px;"'
                ' onsubmit="return confirm(\'Delete ALL profiles?\');">'
                '<button type="submit" style="background:#600;color:#fff;margin-top:6px;">forget everyone</button>'
                '</form>'
            )

        # Check enrollment status for banner
        with enroll_lock:
            busy  = enrolling
            ename = enroll_name
            esamp = len(enroll_samples)
            edone = enroll_done

        banner = ""
        if edone:
            banner = f'<div style="color:#0f0;font-weight:bold;">✓ {ename} enrolled!</div>'
        elif busy:
            banner = f'<div style="color:#ff0;">Enrolling {ename}... look at the camera! ({esamp}/{ENROLL_NEEDED})</div>'

        with sonar_lock:
            _sd = sonar_distance
            _scanning = sonar_scanning
        sonar_label  = f"{_sd:.0f} cm" if _sd is not None else ("scanning..." if _scanning else "no sensor")
        scan_status  = "scanning now..." if _scanning else "last scan: " + (f"{len(sonar_map)} pts" if sonar_map else "none")
        scan_busy    = "true" if _scanning else "false"

        html = f"""<!DOCTYPE html>
<html><head><title>Blue Fish</title>
<style>
body{{background:#111;color:#0f0;font-family:monospace;text-align:center;margin:0;padding:20px;}}
img{{max-width:100%;border:2px solid #0f0;display:block;margin:auto;}}
input,button,select{{background:#222;color:#0f0;border:1px solid #0f0;padding:6px 12px;
  font-family:monospace;font-size:14px;margin:4px;border-radius:4px;}}
button{{cursor:pointer;}}button:hover{{background:#0f0;color:#111;}}
.section{{border:1px solid #0f0;padding:12px;margin:12px auto;max-width:500px;border-radius:8px;}}
</style></head>
<body>
<h2>Blue Fish Camera</h2>
<a href="/drive" style="display:inline-block;margin-bottom:10px;padding:8px 24px;
  background:#300;color:#f55;border:1px solid #f00;border-radius:5px;
  font-family:monospace;font-size:13px;text-decoration:none;letter-spacing:2px;">
  &#9632; DRIVE MODE</a>
<div id="fps" style="color:#555;font-size:12px;">frames: 0</div>
<img id="f" src="/frame"
  onload="frameCount++;document.getElementById('fps').textContent='frames: '+frameCount;setTimeout(function(){{document.getElementById('f').src='/frame?t='+Date.now();}},100);"
  onerror="setTimeout(function(){{document.getElementById('f').src='/frame?t='+Date.now();}},400);">
<script>var frameCount=0;</script>

{banner}

<div class="section">
  <b>Enroll a New Person</b><br>
  <form method="POST" action="/enroll">
    <input name="name" placeholder="Enter name" maxlength="30" required>
    <select name="level">
      <option value="1">Level 1 - Owner (me!)</option>
      <option value="2">Level 2 - Family</option>
      <option value="3" selected>Level 3 - Friend</option>
      <option value="4">Level 4 - Guest</option>
      <option value="5">Level 5 - Basic</option>
    </select>
    <button type="submit">Enroll</button>
  </form>
  <div style="color:#888;font-size:12px;">After clicking Enroll, look at the camera. Progress shows on the video feed.</div>
</div>

<div class="section">
  <b>Known People</b><br>
  {people_html}
</div>

<div class="section">
  <b>Sonar Map</b>
  <div style="color:#888;font-size:11px;">live distance: {sonar_label} &nbsp;|&nbsp; {scan_status}</div>
  <img id="sm" src="/sonar_map"
    onload="setTimeout(function(){{document.getElementById('sm').src='/sonar_map?t='+Date.now();}},400);"
    onerror="setTimeout(function(){{document.getElementById('sm').src='/sonar_map?t='+Date.now();}},800);"
    style="width:400px;height:400px;image-rendering:pixelated;">
  <br>
  <form method="POST" action="/scan" style="display:inline;"
    onsubmit="return !{scan_busy};">
    <button type="submit" {'disabled' if sonar_scanning else ''}>360° Scan</button>
  </form>
  <div style="color:#555;font-size:11px;">Green dots = obstacles. Yellow line = current distance forward.<br>
    Tune SCAN_ROT_TIME in bluefish.py if the map looks rotated wrong.</div>
</div>
</body></html>"""
        body = html.encode()
        self.send_response(200)
        self.send_header("Content-Type", "text/html")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

class ThreadedHTTPServer(ThreadingMixIn, HTTPServer):
    daemon_threads = True

def start_stream():
    server = ThreadedHTTPServer(("0.0.0.0", 8080), StreamHandler)
    print("[Stream] HTTP server started on port 8080")
    server.serve_forever()

# ── Ollama helpers ────────────────────────────────────────────────────────────
def ask_ollama(prompt, model="bluefish"):
    import urllib.request
    payload = json.dumps({"model": model, "prompt": prompt, "stream": False}).encode()
    try:
        req = urllib.request.Request(
            "http://localhost:11434/api/generate",
            data=payload,
            headers={"Content-Type": "application/json"}
        )
        with urllib.request.urlopen(req, timeout=30) as r:
            return json.loads(r.read())["response"].strip()
    except Exception as e:
        print(f"[Ollama] {e}")
        return "I'm thinking..."

def describe_scene(frame):
    import cv2, base64, urllib.request
    _, buf = cv2.imencode(".jpg", frame, [cv2.IMWRITE_JPEG_QUALITY, 60])
    b64 = base64.b64encode(buf.tobytes()).decode()
    payload = json.dumps({
        "model": "moondream",
        "prompt": "Describe what you see briefly in 1-2 sentences.",
        "images": [b64],
        "stream": False
    }).encode()
    try:
        req = urllib.request.Request(
            "http://localhost:11434/api/generate",
            data=payload,
            headers={"Content-Type": "application/json"}
        )
        with urllib.request.urlopen(req, timeout=20) as r:
            return json.loads(r.read())["response"].strip()
    except Exception as e:
        print(f"[Vision] {e}")
        return "I can't describe the scene right now."

# ── Voice recognition ─────────────────────────────────────────────────────────
def identify_speaker(audio_np):
    if not os.path.exists(VOICE_PROFILE):
        return "Guest"
    try:
        from resemblyzer import VoiceEncoder, preprocess_wav
        with open(VOICE_PROFILE, "rb") as f:
            profile = pickle.load(f)
        encoder = VoiceEncoder()
        wav = preprocess_wav(audio_np, source_sr=SAMPLERATE)
        enc = encoder.embed_utterance(wav)
        sim = np.dot(enc, profile) / (np.linalg.norm(enc) * np.linalg.norm(profile))
        return "Eamonn" if sim > 0.75 else "Guest"
    except Exception as e:
        print(f"[Voice ID] {e}")
        return "Guest"

# ── Speech recognition ────────────────────────────────────────────────────────
print("[Whisper] Loading model...")
whisper_model = whisper.load_model("tiny")
print("[Whisper] Ready")

def transcribe(audio_np):
    audio_f32 = audio_np.astype(np.float32) / 32768.0
    if SAMPLERATE != 16000:
        import scipy.signal
        audio_f32 = scipy.signal.resample_poly(
            audio_f32, 16000, SAMPLERATE).astype(np.float32)
    result = whisper_model.transcribe(audio_f32, fp16=False, language="en")
    return result["text"].strip().lower()

# ── Autonomous navigation ─────────────────────────────────────────────────────
def navigate_to(destination):
    speak(f"Navigating to {destination}.")
    for _ in range(6):
        with camera_lock:
            frame = latest_camera_frame.copy() if latest_camera_frame is not None else None
        scene = describe_scene(frame) if frame is not None else "no camera"
        decision = ask_ollama(
            f"You are Blue Fish robot. You see: {scene}. Goal: {destination}. "
            f"Reply with ONE word: forward, backward, left, right, or stop."
        ).lower()
        if   "forward"  in decision: send_motor("F", 0.7)
        elif "backward" in decision: send_motor("B", 0.7)
        elif "left"     in decision: send_motor("L", 0.5)
        elif "right"    in decision: send_motor("R", 0.5)
        elif "stop"     in decision: break
        time.sleep(0.3)
    speak(f"I've tried to reach {destination}.")

# ── Command handler ───────────────────────────────────────────────────────────
def get_speaker_level():
    """Return the trust level of the highest-priority visible person."""
    with face_overlay_lock:
        levels = [o.get("level", STRANGER_LEVEL) for o in face_overlays]
    return min(levels) if levels else STRANGER_LEVEL

MOVEMENT_COMMANDS = [
    "move forward","go forward","move backward","go backward",
    "turn left","turn right","lift up","raise fork","lift down","lower fork",
    "go to","navigate to","stop",
]

def handle_command(text, speaker):
    global learn_mode, knowledge, commander_level

    print(f"[CMD] {speaker}: {text}")

    # ── Trust level check ─────────────────────────────────────────────────────
    my_level = get_speaker_level()
    is_movement = any(cmd in text for cmd in MOVEMENT_COMMANDS)

    with commander_lock:
        if my_level > commander_level:
            # A higher-priority person is already in control
            speak(f"Sorry, someone with a higher level is in control right now.")
            return
        # Take control
        commander_level = my_level
    reply = None

    if "learn mode on" in text:
        learn_mode = True
        reply = "Learn mode on. Tell me anything and I'll remember it."
        speak(reply)
        save_conversation(speaker, text, reply)
        return

    if "learn mode off" in text:
        learn_mode = False
        reply = "Learn mode off."
        speak(reply)
        save_conversation(speaker, text, reply)
        return

    if "what have you learned" in text or "what did you learn" in text:
        facts = knowledge.get("facts", [])
        reply = (f"I know {len(facts)} facts: " + ". ".join(facts[-3:])) if facts else "Nothing yet!"
        speak(reply)
        save_conversation(speaker, text, reply)
        return

    if "who do you see" in text or "who is there" in text:
        if face_in_view:
            with face_overlay_lock:
                names = [o["name"] for o in face_overlays]
            people = ", ".join(names) if names else "someone"
            reply = f"I can see {people}. They are facing {face_direction}, looking {gaze_direction}."
        else:
            reply = "I don't see anyone right now."
        speak(reply)
        save_conversation(speaker, text, reply)
        return

    if "what do you see" in text or "describe" in text:
        with camera_lock:
            frame = latest_camera_frame.copy() if latest_camera_frame is not None else None
        if frame is not None:
            def _describe():
                r = describe_scene(frame)
                speak(r)
                save_conversation(speaker, text, r)
            threading.Thread(target=_describe, daemon=True).start()
        else:
            speak("Camera isn't ready yet.")
        return

    if "go to" in text or "navigate to" in text:
        dest = text.replace("go to","").replace("navigate to","").strip()
        if dest:
            threading.Thread(target=navigate_to, args=(dest,), daemon=True).start()
        return

    if "move forward" in text or "go forward" in text:
        send_motor("F"); reply = "Moving forward."; speak(reply)
        save_conversation(speaker, text, reply); return
    if "move backward" in text or "go backward" in text:
        send_motor("B"); reply = "Moving backward."; speak(reply)
        save_conversation(speaker, text, reply); return
    if "turn left" in text:
        send_motor("L"); reply = "Turning left."; speak(reply)
        save_conversation(speaker, text, reply); return
    if "turn right" in text:
        send_motor("R"); reply = "Turning right."; speak(reply)
        save_conversation(speaker, text, reply); return
    if "lift up" in text or "raise fork" in text:
        send_motor("U"); reply = "Lifting up."; speak(reply)
        save_conversation(speaker, text, reply); return
    if "lift down" in text or "lower fork" in text:
        send_motor("D"); reply = "Lowering down."; speak(reply)
        save_conversation(speaker, text, reply); return
    if text.strip() == "stop":
        send_motor("S", 0); reply = "Stopping."; speak(reply)
        save_conversation(speaker, text, reply); return

    if any(w in text for w in ("scan the room", "scan room", "do a scan", "map the room")):
        if sonar_scanning:
            reply = "I'm already scanning, hang on!"
        elif _sonar_sensor is None:
            reply = "My sonar sensor isn't connected yet."
        else:
            reply = "Scanning the room now — stay still!"
            speak(reply)
            threading.Thread(target=do_scan, daemon=True).start()
            save_conversation(speaker, text, reply)
        speak(reply); return

    if any(w in text for w in ("how far", "what's in front", "whats in front",
                                "distance to", "how close")):
        with sonar_lock:
            d = sonar_distance
        if d is None:
            reply = "My sonar sensor isn't connected, so I can't tell."
        else:
            reply = f"There's something about {d:.0f} centimetres in front of me."
        speak(reply); save_conversation(speaker, text, reply); return

    if learn_mode:
        knowledge.setdefault("facts", []).append(text)
        save_knowledge()
        reply = "Got it, I'll remember that."
        speak(reply)
        save_conversation(speaker, text, reply)
        return

    # Build context from knowledge + recent conversation
    facts = knowledge.get("facts", [])
    context_parts = []
    if facts:
        context_parts.append("Facts I know: " + "; ".join(facts[-20:]))
    recent = recent_conversation_context(5)
    if recent:
        context_parts.append(recent)
    context = "\n".join(context_parts)

    prompt = (
        f"{context}\n\n"
        f"You are Blue Fish, a helpful friendly AI robot built by Eamonn, age 10. "
        f"Use the conversation history above to give a consistent, connected reply. "
        f"Keep your answer short and clear.\n"
        f"{speaker} says: {text}"
    )
    reply = ask_ollama(prompt)
    speak(reply)
    save_conversation(speaker, text, reply)

    with commander_lock:
        commander_level = STRANGER_LEVEL   # release control after command done

# ── Microphone listener ───────────────────────────────────────────────────────
audio_queue = queue.Queue()

def audio_callback(indata, frames, time_info, status):
    if status:
        print(f"[Audio] {status}")
    # Mix down to mono if stereo
    if indata.shape[1] > 1:
        mono = indata.mean(axis=1).astype(np.int16)
    else:
        mono = indata[:, 0]
    audio_queue.put(mono.copy())

def listen_loop():
    print("[Listen] Starting microphone listener...")
    print(f"[Listen] device={DEVICE} rate={SAMPLERATE} ch={MIC_CHANNELS}")
    with sd.InputStream(samplerate=SAMPLERATE, device=DEVICE,
                        channels=MIC_CHANNELS, dtype="int16",
                        blocksize=CHUNK, callback=audio_callback):
        buf = []
        silence_chunks = 0
        in_speech = False
        silence_limit = int(MAX_SILENCE * SAMPLERATE / CHUNK)

        while True:
            try:
                chunk = audio_queue.get(timeout=1)
            except queue.Empty:
                continue

            if speaking:
                buf.clear(); silence_chunks = 0; in_speech = False
                continue

            amplitude = np.abs(chunk).mean()
            if amplitude > SILENCE_THRESHOLD:
                buf.append(chunk); silence_chunks = 0; in_speech = True
            elif in_speech:
                buf.append(chunk); silence_chunks += 1
                if silence_chunks >= silence_limit:
                    audio_np = np.concatenate(buf).flatten()
                    buf.clear(); silence_chunks = 0; in_speech = False
                    if len(audio_np) > SAMPLERATE * 0.5:
                        def _process(a=audio_np):
                            text = transcribe(a)
                            if text and len(text) > 2:
                                speaker = identify_speaker(a)
                                handle_command(text, speaker)
                        threading.Thread(target=_process, daemon=True).start()

# ── Main ──────────────────────────────────────────────────────────────────────
def main():
    load_knowledge()
    load_face_profiles()
    load_conversation_log()
    init_serial()

    init_sonar()
    threading.Thread(target=start_stream, daemon=True).start()
    threading.Thread(target=camera_loop, daemon=True).start()
    threading.Thread(target=sonar_loop, daemon=True).start()

    time.sleep(2)
    speak("Blue Fish online. I'm ready to help, Eamonn!")

    listen_loop()

if __name__ == "__main__":
    main()
