#!/usr/bin/env python3
"""Blue Fish - AI robot brain for Raspberry Pi 5 / CrunchLabs Omnibot"""

import os, sys, time, json, queue, threading, subprocess, pickle, datetime
import numpy as np
import sounddevice as sd
import whisper
from http.server import HTTPServer, BaseHTTPRequestHandler
from socketserver import ThreadingMixIn
from urllib.parse import parse_qs, urlparse

# ── Audio config ─────────────────────────────────────────────────────────────
SAMPLERATE    = 48000
DEVICE        = 0
CHUNK         = 4096
SILENCE_THRESHOLD = 300
MAX_SILENCE   = 1.5

# ── Paths ─────────────────────────────────────────────────────────────────────
HOME             = "/home/fussykitten12"
PIPER            = f"{HOME}/.local/bin/piper"
VOICE_MODEL      = f"{HOME}/piper_voices/en_US-ryan-high.onnx"
BT_SPEAKER       = "E6_8A_D3_4B_55_67"
VOICE_PROFILE    = f"{HOME}/voice_profile.pkl"
FACE_PROFILES_DB = f"{HOME}/face_profiles.pkl"   # {name: encoding}
FACE_PROFILE_OLD = f"{HOME}/face_profile.pkl"    # legacy single-person file
KNOWLEDGE_DB     = f"{HOME}/knowledge.json"
SHAPE_MODEL      = f"{HOME}/shape_predictor_68_face_landmarks.dat"
CONVO_LOG        = f"{HOME}/conversation_log.json"

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
enroll_lock       = threading.Lock()
ENROLL_NEEDED     = 10

learn_mode        = False
knowledge         = {"facts": []}
speaking          = False
serial_conn       = None
conversation_log  = []          # list of {when, who, said, replied}

# ── Face profiles ─────────────────────────────────────────────────────────────
def load_face_profiles():
    global face_profiles
    if os.path.exists(FACE_PROFILES_DB):
        try:
            with open(FACE_PROFILES_DB, "rb") as f:
                face_profiles = pickle.load(f)
            print(f"[Faces] Loaded {len(face_profiles)} profile(s): {list(face_profiles.keys())}")
            return
        except Exception:
            pass
    # Migrate legacy single-person file
    if os.path.exists(FACE_PROFILE_OLD):
        try:
            with open(FACE_PROFILE_OLD, "rb") as f:
                enc = pickle.load(f)
            face_profiles = {"Eamonn": enc}
            save_face_profiles()
            print("[Faces] Migrated legacy face_profile.pkl → Eamonn")
        except Exception:
            pass

def save_face_profiles():
    with face_profiles_lock:
        with open(FACE_PROFILES_DB, "wb") as f:
            pickle.dump(face_profiles, f)

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
            print(f"[Enroll] {current_name}: {count}/{ENROLL_NEEDED} samples")
            if count >= ENROLL_NEEDED:
                with enroll_lock:
                    avg = np.mean(enroll_samples, axis=0)
                with face_profiles_lock:
                    face_profiles[current_name] = avg
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
            if profiles_snapshot:
                names = list(profiles_snapshot.keys())
                known_encs = list(profiles_snapshot.values())
                matches = face_recognition.compare_faces(known_encs, enc, tolerance=0.5)
                if True in matches:
                    name = names[matches.index(True)]

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
                                  "color": color, "head": head_label, "gaze": gaze_label})
            print(f"[Face] {name}")

        with face_overlay_lock:
            face_overlays = new_overlays

    except Exception as e:
        print(f"[Face error] {e}")

# ── Camera loop ───────────────────────────────────────────────────────────────
def camera_loop():
    global latest_camera_frame, stream_frame

    import cv2

    cmd = ["rpicam-vid", "-t", "0", "--width", "640", "--height", "480",
           "--framerate", "10", "--codec", "mjpeg", "--inline", "-o", "-"]
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
                        (tw, th), _ = cv2.getTextSize(name, cv2.FONT_HERSHEY_SIMPLEX, 0.8, 2)
                        cx = (l+r)//2
                        cv2.rectangle(display, (cx-tw//2-4, ly-th-6), (cx+tw//2+4, ly+2), col, -1)
                        cv2.putText(display, name, (cx-tw//2, ly), cv2.FONT_HERSHEY_SIMPLEX, 0.8, (255,255,255), 2)
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

                    _, raw_buf = cv2.imencode(".jpg", display, [cv2.IMWRITE_JPEG_QUALITY, 70])
                    with stream_lock:
                        stream_frame = raw_buf.tobytes()

                    face_counter += 1
                    if face_counter % 30 == 0:
                        print(f"[Camera] {face_counter} frames")
                    if face_counter % 15 == 0:
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

    def do_GET(self):
        parsed = urlparse(self.path)
        path   = parsed.path

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
                names = list(face_profiles.keys())
            body = json.dumps({"names": names}).encode()
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)

        else:
            self._serve_page()

    def do_POST(self):
        parsed = urlparse(self.path)
        path   = parsed.path
        length = int(self.headers.get("Content-Length", 0))
        body   = self.rfile.read(length).decode()
        params = parse_qs(body)

        if path == "/enroll":
            name = params.get("name", [""])[0].strip()
            if not name:
                self._json_response({"error": "no name"}, 400)
                return
            with enroll_lock:
                global enrolling, enroll_name, enroll_samples, enroll_done
                enrolling      = True
                enroll_name    = name
                enroll_samples = []
                enroll_done    = False
            print(f"[Enroll] Starting enrollment for: {name}")
            self._json_response({"started": True, "name": name})

        elif path == "/forget":
            name = params.get("name", [""])[0].strip()
            with face_profiles_lock:
                if name in face_profiles:
                    del face_profiles[name]
                    save_face_profiles()
                    self._json_response({"deleted": True, "name": name})
                else:
                    self._json_response({"error": "not found"}, 404)
        else:
            self.send_response(404)
            self.end_headers()

    def _json_response(self, data, code=200):
        body = json.dumps(data).encode()
        self.send_response(code)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def _serve_page(self):
        html = b"""<!DOCTYPE html>
<html><head><title>Blue Fish</title>
<style>
body{background:#111;color:#0f0;font-family:monospace;text-align:center;margin:0;padding:20px;}
img{max-width:100%;border:2px solid #0f0;display:block;margin:auto;}
input,button,select{background:#222;color:#0f0;border:1px solid #0f0;padding:6px 12px;
  font-family:monospace;font-size:14px;margin:4px;border-radius:4px;}
button{cursor:pointer;}button:hover{background:#0f0;color:#111;}
#status{color:#ff0;margin:8px 0;min-height:24px;}
#profiles{color:#0af;margin:8px 0;}
.section{border:1px solid #0f0;padding:12px;margin:12px auto;max-width:500px;border-radius:8px;}
</style></head>
<body>
<h2>Blue Fish Camera</h2>
<div id="fps" style="color:#555;font-size:12px;">frames: 0</div>
<img id="f" src="/frame"
  onload="frameCount++;document.getElementById('fps').textContent='frames: '+frameCount;setTimeout(function(){document.getElementById('f').src='/frame?t='+Date.now();},100);"
  onerror="setTimeout(function(){document.getElementById('f').src='/frame?t='+Date.now();},400);">
<script>var frameCount=0;</script>

<div class="section">
  <b>Enroll a New Person</b><br>
  <input id="ename" placeholder="Enter name" maxlength="30">
  <button onclick="startEnroll()">Enroll</button>
  <div id="status"></div>
  <div id="bar" style="height:8px;background:#222;border:1px solid #0f0;border-radius:4px;margin:6px 0;display:none;">
    <div id="fill" style="height:100%;background:#0f0;width:0%;border-radius:4px;transition:width 0.3s;"></div>
  </div>
</div>

<div class="section">
  <b>Known People</b>
  <div id="profiles">Loading...</div>
</div>

<script>

var polling=null;

function xhr(method,url,body,cb){
  var r=new XMLHttpRequest();
  r.open(method,url,true);
  if(body)r.setRequestHeader('Content-Type','application/x-www-form-urlencoded');
  r.onload=function(){if(r.status<400)cb(JSON.parse(r.responseText));};
  r.send(body||null);
}

function startEnroll(){
  var name=document.getElementById('ename').value.trim();
  if(!name){alert('Enter a name first!');return;}
  xhr('POST','/enroll','name='+encodeURIComponent(name),function(d){
    document.getElementById('status').textContent='Look at the camera, '+name+'!';
    document.getElementById('bar').style.display='block';
    if(polling)clearInterval(polling);
    polling=setInterval(pollEnroll,500);
  });
}

function pollEnroll(){
  xhr('GET','/enroll_status',null,function(d){
    var pct=Math.round(d.samples/d.needed*100);
    document.getElementById('fill').style.width=pct+'%';
    document.getElementById('status').textContent=
      d.done?'Done! '+d.name+' enrolled!':
      (d.enrolling?'Capturing... '+d.samples+'/'+d.needed:'');
    if(d.done){clearInterval(polling);document.getElementById('ename').value='';loadProfiles();}
  });
}

function loadProfiles(){
  xhr('GET','/profiles',null,function(d){
    if(!d.names.length){document.getElementById('profiles').textContent='No one enrolled yet.';return;}
    var html='';
    d.names.forEach(function(n){
      html+='<span style="margin:0 8px;">'+n+' <button onclick="forget(\''+n+'\')">forget</button></span>';
    });
    document.getElementById('profiles').innerHTML=html;
  });
}

function forget(name){
  if(!confirm('Forget '+name+'?'))return;
  xhr('POST','/forget','name='+encodeURIComponent(name),function(){loadProfiles();});
}

loadProfiles();
</script>
</body></html>"""
        self.send_response(200)
        self.send_header("Content-Type", "text/html")
        self.send_header("Content-Length", str(len(html)))
        self.end_headers()
        self.wfile.write(html)

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
def handle_command(text, speaker):
    global learn_mode, knowledge

    print(f"[CMD] {speaker}: {text}")
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

# ── Microphone listener ───────────────────────────────────────────────────────
audio_queue = queue.Queue()

def audio_callback(indata, frames, time_info, status):
    if status:
        print(f"[Audio] {status}")
    audio_queue.put(indata.copy())

def listen_loop():
    print("[Listen] Starting microphone listener...")
    with sd.InputStream(samplerate=SAMPLERATE, device=DEVICE,
                        channels=1, dtype="int16",
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
                    if len(audio_np) > SAMPLERATE * 0.5:
                        text = transcribe(audio_np)
                        if text and len(text) > 2:
                            speaker = identify_speaker(audio_np)
                            threading.Thread(target=handle_command, args=(text, speaker), daemon=True).start()
                    buf.clear(); silence_chunks = 0; in_speech = False

# ── Main ──────────────────────────────────────────────────────────────────────
def main():
    load_knowledge()
    load_face_profiles()
    load_conversation_log()
    init_serial()

    threading.Thread(target=start_stream, daemon=True).start()
    threading.Thread(target=camera_loop, daemon=True).start()

    time.sleep(2)
    speak("Blue Fish online. I'm ready to help, Eamonn!")

    listen_loop()

if __name__ == "__main__":
    main()
