#!/usr/bin/env python3
"""Blue Fish - AI robot brain for Raspberry Pi 5 / CrunchLabs Omnibot"""

import os, sys, time, json, queue, threading, subprocess, struct, pickle, io
import numpy as np
import sounddevice as sd
import whisper
from http.server import HTTPServer, BaseHTTPRequestHandler
from socketserver import ThreadingMixIn

# ── Audio config ─────────────────────────────────────────────────────────────
SAMPLERATE    = 48000
DEVICE        = 0          # USB PnP microphone
CHUNK         = 4096
SILENCE_THRESHOLD = 300
MAX_SILENCE   = 1.5        # seconds of silence before processing

# ── Paths ─────────────────────────────────────────────────────────────────────
HOME          = "/home/fussykitten12"
PIPER         = f"{HOME}/.local/bin/piper"
VOICE_MODEL   = f"{HOME}/piper_voices/en_US-ryan-high.onnx"
BT_SPEAKER    = "E6_8A_D3_4B_55_67"
VOICE_PROFILE = f"{HOME}/voice_profile.pkl"
FACE_PROFILE  = f"{HOME}/face_profile.pkl"
KNOWLEDGE_DB  = f"{HOME}/knowledge.json"
SHAPE_MODEL   = f"{HOME}/shape_predictor_68_face_landmarks.dat"

# ── Global state ──────────────────────────────────────────────────────────────
stream_frame  = b""
stream_lock   = threading.Lock()
latest_camera_frame = None
camera_lock   = threading.Lock()

face_in_view    = False
face_is_eamonn  = False
face_direction  = "center"
gaze_direction  = "center"

learn_mode    = False
knowledge     = {"facts": []}
speaking      = False
serial_conn   = None

# ── Load knowledge base ───────────────────────────────────────────────────────
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
        # Try Bluetooth speaker first, fall back to aplay default
        try:
            bt = subprocess.run(
                ["aplay", "-D", f"bluealsa:DEV={BT_SPEAKER},PROFILE=a2dp", "-r", "22050", "-f", "S16_LE", "-c", "1"],
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
    global face_in_view, face_is_eamonn, face_direction, gaze_direction, stream_frame

    try:
        import cv2
        import face_recognition
        import dlib

        rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        locations = face_recognition.face_locations(rgb, number_of_times_to_upsample=2, model="hog")

        annotated = frame.copy()
        face_in_view = len(locations) > 0

        if not face_in_view:
            _, buf = cv2.imencode(".jpg", annotated, [cv2.IMWRITE_JPEG_QUALITY, 70])
            with stream_lock:
                stream_frame = buf.tobytes()
            return

        # Load known face
        known_enc = None
        if os.path.exists(FACE_PROFILE):
            try:
                with open(FACE_PROFILE, "rb") as f:
                    known_enc = pickle.load(f)
            except Exception:
                pass

        # Load dlib predictor if available
        predictor = None
        if os.path.exists(SHAPE_MODEL):
            try:
                detector  = dlib.get_frontal_face_detector()
                predictor = dlib.shape_predictor(SHAPE_MODEL)
            except Exception:
                pass

        encodings = face_recognition.face_encodings(rgb, locations)

        for (top, right, bottom, left), enc in zip(locations, encodings):
            # Identity check
            name = "Stranger"
            if known_enc is not None:
                match = face_recognition.compare_faces([known_enc], enc, tolerance=0.5)
                if match[0]:
                    name = "Eamonn"
            face_is_eamonn = (name == "Eamonn")

            # Box colour
            color = (0, 200, 0) if name == "Eamonn" else (0, 140, 255)
            cv2.rectangle(annotated, (left, top), (right, bottom), color, 2)

            # Head pose + eye gaze via dlib landmarks
            head_label = ""
            gaze_label = ""
            if predictor is not None:
                h, w = frame.shape[:2]
                gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
                rect = dlib.rectangle(left, top, right, bottom)
                shape = predictor(gray, rect)
                pts  = np.array([[shape.part(i).x, shape.part(i).y] for i in range(68)], dtype=np.float32)

                # 3D model points for solvePnP
                model_pts = np.array([
                    (0.0,   0.0,    0.0),
                    (0.0,  -330.0, -65.0),
                    (-225.0, 170.0, -135.0),
                    (225.0,  170.0, -135.0),
                    (-150.0,-150.0, -125.0),
                    (150.0, -150.0, -125.0),
                ], dtype=np.float64)

                image_pts = np.array([
                    pts[30], pts[8], pts[36], pts[45], pts[48], pts[54]
                ], dtype=np.float64)

                focal = w
                cam_mat = np.array([[focal, 0, w/2],
                                    [0, focal, h/2],
                                    [0, 0, 1]], dtype=np.float64)
                dist_coeffs = np.zeros((4, 1))

                ok, rvec, tvec = cv2.solvePnP(model_pts, image_pts, cam_mat, dist_coeffs, flags=cv2.SOLVEPNP_ITERATIVE)
                if ok:
                    rot_mat, _ = cv2.Rodrigues(rvec)
                    angles, _, _, _, _, _ = cv2.RQDecomp3x3(rot_mat)
                    yaw   = angles[1]
                    pitch = angles[0]
                    if   yaw < -15: face_direction = "left"
                    elif yaw >  15: face_direction = "right"
                    else:           face_direction = "center"
                    head_label = f"Head: {face_direction}"

                # Eye gaze
                def eye_ratio(idxs):
                    eye = pts[idxs].astype(int)
                    ex, ey, ew, eh = cv2.boundingRect(eye)
                    if ew < 2 or eh < 2:
                        return 0.5
                    roi = gray[ey:ey+eh, ex:ex+ew]
                    if roi.size == 0:
                        return 0.5
                    _, thr = cv2.threshold(roi, 70, 255, cv2.THRESH_BINARY_INV)
                    left_half  = thr[:, :ew//2].sum()
                    right_half = thr[:, ew//2:].sum()
                    total = left_half + right_half
                    return left_half / total if total > 0 else 0.5

                l_ratio = eye_ratio(list(range(36, 42)))
                r_ratio = eye_ratio(list(range(42, 48)))
                ratio   = (l_ratio + r_ratio) / 2
                if   ratio > 0.6: gaze_direction = "left"
                elif ratio < 0.4: gaze_direction = "right"
                else:             gaze_direction = "center"
                gaze_label = f"Gaze: {gaze_direction}"

            # Floating name label above box
            label_y = max(top - 10, 20)
            (tw, th), _ = cv2.getTextSize(name, cv2.FONT_HERSHEY_SIMPLEX, 0.8, 2)
            cx = (left + right) // 2
            cv2.rectangle(annotated, (cx - tw//2 - 4, label_y - th - 6),
                          (cx + tw//2 + 4, label_y + 2), color, -1)
            cv2.putText(annotated, name, (cx - tw//2, label_y),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.8, (255, 255, 255), 2)

            # Head/gaze info below box
            if head_label:
                cv2.putText(annotated, head_label, (left, bottom + 20),
                            cv2.FONT_HERSHEY_SIMPLEX, 0.55, color, 1)
            if gaze_label:
                cv2.putText(annotated, gaze_label, (left, bottom + 40),
                            cv2.FONT_HERSHEY_SIMPLEX, 0.55, color, 1)

        _, buf = cv2.imencode(".jpg", annotated, [cv2.IMWRITE_JPEG_QUALITY, 70])
        with stream_lock:
            stream_frame = buf.tobytes()

    except Exception as e:
        print(f"[Face] {e}")

# ── Camera loop ───────────────────────────────────────────────────────────────
def camera_loop():
    global latest_camera_frame, stream_frame

    import cv2

    cmd = [
        "rpicam-vid", "-t", "0",
        "--width", "640", "--height", "480",
        "--framerate", "10",
        "--codec", "mjpeg",
        "--inline",
        "-o", "-"
    ]
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
                    jpeg = buf[start:end + 2]
                    buf  = buf[end + 2:]

                    arr   = np.frombuffer(jpeg, dtype=np.uint8)
                    frame = cv2.imdecode(arr, cv2.IMREAD_COLOR)
                    if frame is None:
                        continue

                    with camera_lock:
                        latest_camera_frame = frame.copy()

                    # Always update stream_frame with latest raw frame
                    _, raw_buf = cv2.imencode(".jpg", frame, [cv2.IMWRITE_JPEG_QUALITY, 70])
                    with stream_lock:
                        stream_frame = raw_buf.tobytes()

                    face_counter += 1
                    if face_counter % 30 == 0:
                        print(f"[Camera] {face_counter} frames captured")
                    if face_counter % 15 == 0:
                        t = threading.Thread(target=analyze_face, args=(frame.copy(),), daemon=True)
                        t.start()

        except Exception as e:
            err = b""
            if proc:
                try:
                    err = proc.stderr.read(300)
                except Exception:
                    pass
            print(f"[Camera] error: {e} stderr: {err}")
        finally:
            if proc:
                try:
                    proc.kill()
                except Exception:
                    pass
        time.sleep(2)

# ── HTTP stream server ────────────────────────────────────────────────────────
class StreamHandler(BaseHTTPRequestHandler):
    def log_message(self, fmt, *args):
        pass

    def do_GET(self):
        if self.path.startswith("/frame"):
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
        else:
            html = b"""<!DOCTYPE html>
<html><head><title>Blue Fish Camera</title>
<style>body{background:#111;color:#0f0;font-family:monospace;text-align:center;}
img{max-width:100%;border:2px solid #0f0;display:block;margin:auto;}</style>
</head><body>
<h2>Blue Fish Camera Feed</h2>
<img id="f" src="/frame">
<script>
setInterval(function(){
  var img = document.getElementById('f');
  var src = '/frame?' + Date.now();
  var tmp = new Image();
  tmp.onload = function(){ img.src = tmp.src; };
  tmp.src = src;
}, 150);
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
def load_voice_profile():
    if os.path.exists(VOICE_PROFILE):
        try:
            with open(VOICE_PROFILE, "rb") as f:
                return pickle.load(f)
        except Exception:
            pass
    return None

def identify_speaker(audio_np):
    profile = load_voice_profile()
    if profile is None:
        return "Guest"
    try:
        from resemblyzer import VoiceEncoder, preprocess_wav
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
    speak(f"Navigating to {destination}. Let me look around first.")
    for _ in range(6):
        with camera_lock:
            frame = latest_camera_frame.copy() if latest_camera_frame is not None else None
        if frame is not None:
            scene = describe_scene(frame)
        else:
            scene = "no camera feed"
        prompt = (f"You are Blue Fish, an AI robot. You can see: {scene}. "
                  f"You want to go to: {destination}. "
                  f"Give one short movement command from: forward, backward, left, right, stop.")
        decision = ask_ollama(prompt)
        decision_lower = decision.lower()
        if   "forward"  in decision_lower: send_motor("F", 0.7)
        elif "backward" in decision_lower: send_motor("B", 0.7)
        elif "left"     in decision_lower: send_motor("L", 0.5)
        elif "right"    in decision_lower: send_motor("R", 0.5)
        elif "stop"     in decision_lower: break
        time.sleep(0.3)
    speak(f"I've tried to reach {destination}.")

# ── Command handler ───────────────────────────────────────────────────────────
def handle_command(text, speaker):
    global learn_mode, knowledge

    print(f"[CMD] {speaker}: {text}")

    # Learn mode toggle
    if "learn mode on" in text:
        learn_mode = True
        speak("Learn mode activated. Tell me anything and I'll remember it.")
        return

    if "learn mode off" in text:
        learn_mode = False
        speak("Learn mode off. I'll stop recording new facts.")
        return

    # What have you learned
    if "what have you learned" in text or "what did you learn" in text:
        facts = knowledge.get("facts", [])
        if facts:
            speak(f"I know {len(facts)} facts. Here are some: " + ". ".join(facts[-3:]))
        else:
            speak("I haven't learned anything yet. Try learn mode!")
        return

    # Who do you see
    if "who do you see" in text or "who is there" in text:
        if face_in_view:
            name = "Eamonn" if face_is_eamonn else "a stranger"
            speak(f"I can see {name}. They are facing {face_direction} and looking {gaze_direction}.")
        else:
            speak("I don't see anyone right now.")
        return

    # What do you see
    if "what do you see" in text or "describe" in text:
        with camera_lock:
            frame = latest_camera_frame.copy() if latest_camera_frame is not None else None
        if frame is not None:
            threading.Thread(target=lambda: speak(describe_scene(frame)), daemon=True).start()
        else:
            speak("My camera isn't ready yet.")
        return

    # Navigation
    if "go to" in text or "navigate to" in text:
        dest = text.replace("go to", "").replace("navigate to", "").strip()
        if dest:
            threading.Thread(target=navigate_to, args=(dest,), daemon=True).start()
        return

    # Motor commands
    if "move forward" in text or "go forward" in text:
        send_motor("F"); speak("Moving forward.")
        return
    if "move backward" in text or "go backward" in text:
        send_motor("B"); speak("Moving backward.")
        return
    if "turn left" in text:
        send_motor("L"); speak("Turning left.")
        return
    if "turn right" in text:
        send_motor("R"); speak("Turning right.")
        return
    if "lift up" in text or "raise fork" in text:
        send_motor("U"); speak("Lifting up.")
        return
    if "lift down" in text or "lower fork" in text:
        send_motor("D"); speak("Lowering down.")
        return
    if "stop" in text:
        send_motor("S", 0); speak("Stopping.")
        return

    # Learn mode – store facts
    if learn_mode:
        knowledge.setdefault("facts", []).append(text)
        save_knowledge()
        speak(f"Got it. I'll remember that.")
        return

    # Try to answer from knowledge base first
    facts = knowledge.get("facts", [])
    context = ""
    if facts:
        context = "Facts I know: " + "; ".join(facts[-20:]) + ". "

    prompt = (f"{context}You are Blue Fish, a helpful friendly AI robot built by Eamonn, age 10. "
              f"Answer briefly and clearly. Question: {text}")
    answer = ask_ollama(prompt)
    speak(answer)

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
        buffer = []
        silence_chunks = 0
        speaking_chunks = 0
        in_speech = False
        silence_limit = int(MAX_SILENCE * SAMPLERATE / CHUNK)

        while True:
            try:
                chunk = audio_queue.get(timeout=1)
            except queue.Empty:
                continue

            if speaking:
                buffer.clear()
                silence_chunks = 0
                speaking_chunks = 0
                in_speech = False
                continue

            amplitude = np.abs(chunk).mean()

            if amplitude > SILENCE_THRESHOLD:
                buffer.append(chunk)
                speaking_chunks += 1
                silence_chunks = 0
                in_speech = True
            elif in_speech:
                buffer.append(chunk)
                silence_chunks += 1
                if silence_chunks >= silence_limit:
                    audio_np = np.concatenate(buffer).flatten()
                    if len(audio_np) > SAMPLERATE * 0.5:
                        text = transcribe(audio_np)
                        if text and len(text) > 2:
                            speaker = identify_speaker(audio_np)
                            threading.Thread(
                                target=handle_command,
                                args=(text, speaker),
                                daemon=True
                            ).start()
                    buffer.clear()
                    silence_chunks = 0
                    speaking_chunks = 0
                    in_speech = False

# ── Main ──────────────────────────────────────────────────────────────────────
def main():
    load_knowledge()
    init_serial()

    # Start HTTP stream server first (so port 8080 is ready)
    stream_thread = threading.Thread(target=start_stream, daemon=True)
    stream_thread.start()

    # Start camera
    cam_thread = threading.Thread(target=camera_loop, daemon=True)
    cam_thread.start()

    # Greet
    time.sleep(2)
    speak("Blue Fish online. I'm ready to help, Eamonn!")

    # Start listening (blocks)
    listen_loop()

if __name__ == "__main__":
    main()
