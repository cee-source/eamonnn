#!/usr/bin/env python3
"""Blue Fish v2.2 - Drive Mode
Run: python3 drive_mode.py
Open: http://<pi-ip>:8080
"""

import glob
import json
import os
import re
import struct
import subprocess
import sys
import threading
import time
from http.server import BaseHTTPRequestHandler, HTTPServer
from socketserver import ThreadingMixIn
from urllib.parse import parse_qs, urlparse

sys.stdout.reconfigure(line_buffering=True)

PORT           = 8080
SAMPLE_RATE    = 16000
RECORDINGS_DIR = os.path.expanduser("~/recordings")
os.makedirs(RECORDINGS_DIR, exist_ok=True)

# ── Shared state ──────────────────────────────────────────────────────────────
serial_conn  = None
stream_frame = None
stream_lock  = threading.Lock()
sonar_dist   = None
sonar_lock   = threading.Lock()

# ── Camera servos ─────────────────────────────────────────────────────────────
cam_pan    = 0
cam_tilt   = 0
servo_lock = threading.Lock()
pan_servo  = None
tilt_servo = None

def init_servos():
    global pan_servo, tilt_servo
    try:
        from gpiozero import AngularServo
        from gpiozero.pins.pigpio import PiGPIOFactory
        try:
            factory = PiGPIOFactory()
        except Exception:
            factory = None
        kw = dict(min_pulse_width=0.0006, max_pulse_width=0.0023,
                  min_angle=-90, max_angle=90)
        if factory:
            kw["pin_factory"] = factory
        pan_servo  = AngularServo(12, **kw)
        tilt_servo = AngularServo(13, **kw)
        pan_servo.angle = tilt_servo.angle = 0
        print("[Servo] Camera pan/tilt ready")
    except Exception as e:
        print(f"[Servo] Not available: {e}")

def move_camera(dpan=0, dtilt=0):
    global cam_pan, cam_tilt
    with servo_lock:
        cam_pan  = max(-90, min(90, cam_pan  + dpan))
        cam_tilt = max(-45, min(45, cam_tilt + dtilt))
        if pan_servo:
            try: pan_servo.angle  = cam_pan
            except Exception: pass
        if tilt_servo:
            try: tilt_servo.angle = cam_tilt
            except Exception: pass

def centre_camera():
    global cam_pan, cam_tilt
    with servo_lock:
        cam_pan = cam_tilt = 0
        if pan_servo:
            try: pan_servo.angle  = 0
            except Exception: pass
        if tilt_servo:
            try: tilt_servo.angle = 0
            except Exception: pass

# ── Serial / motors ───────────────────────────────────────────────────────────
def init_serial():
    global serial_conn
    try:
        import serial
        ports = glob.glob("/dev/ttyUSB*") + glob.glob("/dev/ttyACM*")
        if not ports:
            print("[Serial] No Arduino found")
            return
        serial_conn = serial.Serial(ports[0], 115200, timeout=1)
        time.sleep(2)
        print(f"[Serial] Connected on {ports[0]}")
    except Exception as e:
        print(f"[Serial] {e}")

def send_motor(cmd):
    global serial_conn
    for _ in range(3):
        if serial_conn is None:
            init_serial()
            time.sleep(0.5)
        try:
            serial_conn.write(f"{cmd}\n".encode())
            return
        except Exception as e:
            print(f"[Motor] {e}")
            serial_conn = None

# ── Sonar ─────────────────────────────────────────────────────────────────────
def sonar_loop():
    global sonar_dist
    try:
        from gpiozero import DistanceSensor
        sensor = DistanceSensor(echo=24, trigger=23, max_distance=4)
        print("[Sonar] Started")
        while True:
            try:
                with sonar_lock:
                    sonar_dist = round(sensor.distance * 100, 1)
            except Exception:
                with sonar_lock:
                    sonar_dist = None
            time.sleep(0.1)
    except Exception as e:
        print(f"[Sonar] Not available: {e}")

# ── Microphone ────────────────────────────────────────────────────────────────
def find_mic():
    try:
        out = subprocess.check_output(["arecord", "-l"],
                                      stderr=subprocess.DEVNULL, text=True)
        for line in out.splitlines():
            if "USB" in line or "usb" in line:
                m = re.search(r"card (\d+):", line)
                if m:
                    return f"plughw:{m.group(1)},0"
    except Exception:
        pass
    return "default"

# ── Recording ─────────────────────────────────────────────────────────────────
_rec_active     = False
_rec_lock       = threading.Lock()
_rec_video_file = None
_rec_audio_proc = None

def start_recording():
    global _rec_active, _rec_video_file, _rec_audio_proc
    with _rec_lock:
        if _rec_active:
            return False
        try:
            _rec_video_file = open("/tmp/rec_video.mjpeg", "wb")
        except Exception as e:
            print(f"[Record] {e}")
            return False
        _rec_audio_proc = subprocess.Popen(
            ["arecord", "-D", find_mic(), "-f", "S16_LE",
             "-r", "16000", "-c", "1", "/tmp/rec_audio.wav"],
            stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        _rec_active = True
        print("[Record] Started")
        return True

def stop_recording(name):
    global _rec_active, _rec_video_file, _rec_audio_proc
    with _rec_lock:
        if not _rec_active:
            return None
        _rec_active = False
        if _rec_audio_proc:
            _rec_audio_proc.terminate()
            try: _rec_audio_proc.wait(timeout=3)
            except Exception: pass
            _rec_audio_proc = None
        if _rec_video_file:
            _rec_video_file.close()
            _rec_video_file = None

    safe = re.sub(r"[^a-zA-Z0-9_\-]", "_", name).strip("_") or "recording"
    out_dir = os.path.join(RECORDINGS_DIR, safe)
    if os.path.exists(out_dir):
        safe = f"{safe}_{int(time.time())}"
        out_dir = os.path.join(RECORDINGS_DIR, safe)
    os.makedirs(out_dir, exist_ok=True)

    video_src = "/tmp/rec_video.mjpeg"
    audio_src = "/tmp/rec_audio.wav"
    mp4_path  = os.path.join(out_dir, f"{safe}.mp4")

    merged = False
    if os.path.exists(video_src) and os.path.exists(audio_src):
        try:
            subprocess.run(
                ["ffmpeg", "-y", "-i", audio_src,
                 "-f", "mjpeg", "-framerate", "15", "-i", video_src,
                 "-c:v", "copy", "-c:a", "aac", mp4_path],
                timeout=60, check=True,
                stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            merged = True
            print(f"[Record] Saved {mp4_path}")
        except Exception as e:
            print(f"[Record] ffmpeg failed: {e}")

    if not merged:
        for src, dst in [(video_src, os.path.join(out_dir, "video.mjpeg")),
                         (audio_src, os.path.join(out_dir, "audio.wav"))]:
            if os.path.exists(src):
                os.replace(src, dst)

    return safe

# ── Camera loop ───────────────────────────────────────────────────────────────
def camera_loop():
    global stream_frame
    cmd = ["rpicam-vid", "-t", "0", "--width", "640", "--height", "480",
           "--framerate", "15", "--codec", "mjpeg", "--inline", "-o", "-"]
    while True:
        print("[Camera] Starting...")
        proc = None
        try:
            proc = subprocess.Popen(cmd, stdout=subprocess.PIPE,
                                    stderr=subprocess.DEVNULL, bufsize=0)
            buf = b""
            while True:
                chunk = proc.stdout.read(4096)
                if not chunk:
                    break
                buf += chunk
                while True:
                    s = buf.find(b"\xff\xd8")
                    e = buf.find(b"\xff\xd9", s + 2)
                    if s == -1 or e == -1:
                        break
                    frame = buf[s:e+2]
                    buf   = buf[e+2:]
                    with stream_lock:
                        stream_frame = frame
                    if _rec_active and _rec_video_file:
                        try: _rec_video_file.write(frame)
                        except Exception: pass
        except Exception as ex:
            print(f"[Camera] {ex}")
        finally:
            try: proc.kill()
            except Exception: pass
        time.sleep(2)

# ── HTML page ─────────────────────────────────────────────────────────────────
PAGE = """<!DOCTYPE html>
<html>
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Blue Fish Drive Mode</title>
<style>
* { box-sizing: border-box; margin: 0; padding: 0; }
body {
  background: #111; color: #fff; font-family: monospace;
  display: flex; flex-direction: column; height: 100vh; overflow: hidden;
}
#cam {
  flex: 1; position: relative; background: #000; overflow: hidden;
}
#cam img { width: 100%; height: 100%; object-fit: contain; display: block; }
.overlay {
  position: absolute; background: rgba(0,0,0,0.65);
  border-radius: 8px; font-size: 13px; padding: 6px 12px;
}
#sonar   { bottom: 10px; left: 10px; border: 1px solid #0f0; color: #0f0; }
#status  { top: 10px; right: 10px; border: 1px solid #08f; color: #08f; }
#cam-pos { top: 10px; left: 10px; border: 1px solid #fa0; color: #fa0; }
#mic-btn {
  bottom: 10px; right: 10px; border: 1px solid #555;
  color: #888; cursor: pointer; user-select: none;
}
#mic-btn.on { border-color: #f44; color: #f44; }
#rec-dot {
  display: none; top: 46px; right: 10px;
  border: 1px solid #f44; color: #f44;
}
#rec-dot.on { display: block; animation: blink 1s step-start infinite; }
@keyframes blink { 50% { opacity: 0.25; } }
#name-overlay {
  display: none; position: absolute; inset: 0;
  background: rgba(0,0,0,0.85); z-index: 10;
  align-items: center; justify-content: center; flex-direction: column; gap: 14px;
}
#name-overlay.on { display: flex; }
#name-overlay h2 { font-size: 1rem; color: #fff; }
#name-input {
  font-family: monospace; font-size: 1rem;
  padding: 10px 16px; border-radius: 8px;
  border: 2px solid #08f; background: #111; color: #fff;
  width: 260px; text-align: center; outline: none;
}
#name-save {
  padding: 10px 28px; border-radius: 8px; border: none;
  background: #08f; color: #fff; font-size: 1rem;
  cursor: pointer; font-family: monospace;
}
#controls {
  background: #1a1a1a; padding: 12px; border-top: 1px solid #333;
  display: flex; gap: 12px; justify-content: center;
  align-items: center; flex-wrap: wrap;
}
.dpad { display: grid; grid-template-columns: repeat(3, 52px); gap: 4px; }
.btn {
  width: 52px; height: 52px; border-radius: 10px;
  font-size: 18px; cursor: pointer; user-select: none;
  background: #2a2a2a; color: #fff; border: 1px solid #444;
  display: flex; align-items: center; justify-content: center;
}
.btn:active, .btn.active { background: #0077cc; border-color: #08f; }
.empty { background: transparent !important; border: none !important; cursor: default; }
.big { width: 80px; height: 80px; border-radius: 50%; font-size: 13px; }
.stop-btn { background: #3a0000; border-color: #f44; color: #f44; }
.rec-btn  { background: #1a0000; border-color: #944; color: #944; font-size: 12px; }
.rec-btn.on { background: #4a0000; border-color: #f44; color: #f44; }
.col { display: flex; flex-direction: column; gap: 4px; align-items: center; }
.fork-btn { width: 80px; height: 36px; border-radius: 8px; }
#labels { font-size: 11px; color: #555; text-align: center; padding: 4px 0 6px; }
#labels a { color: #08f; text-decoration: none; }
</style>
</head>
<body>

<div id="cam">
  <img src="/stream" id="feed" alt="">

  <div class="overlay" id="sonar">Sonar: --</div>
  <div class="overlay" id="status">STOPPED</div>
  <div class="overlay" id="cam-pos">Cam 0 / 0</div>
  <div class="overlay" id="mic-btn" onclick="toggleMic()">MIC: OFF</div>
  <div class="overlay" id="rec-dot">&#9679; REC</div>

  <div id="name-overlay">
    <h2>Name this recording</h2>
    <input id="name-input" type="text" placeholder="e.g. kitchen_run" maxlength="40">
    <button id="name-save" onclick="saveRecording()">Save</button>
  </div>
</div>

<div id="controls">

  <!-- Drive D-pad -->
  <div class="dpad">
    <div class="btn empty"></div>
    <div class="btn" id="btn-F" data-cmd="F">&#8593;</div>
    <div class="btn empty"></div>
    <div class="btn" id="btn-L" data-cmd="L">&#8592;</div>
    <div class="btn big stop-btn" id="btn-S" data-cmd="S">STOP</div>
    <div class="btn" id="btn-R" data-cmd="R">&#8594;</div>
    <div class="btn empty"></div>
    <div class="btn" id="btn-B" data-cmd="B">&#8595;</div>
    <div class="btn empty"></div>
  </div>

  <!-- Fork + Record -->
  <div class="col">
    <div class="btn fork-btn" id="btn-U" data-cmd="U">&#8679; Fork</div>
    <div class="btn fork-btn" id="btn-D" data-cmd="D">&#8681; Fork</div>
    <div class="btn big rec-btn" id="rec-btn" onclick="toggleRecord()">&#9679; REC</div>
  </div>

  <!-- Camera D-pad -->
  <div class="col">
    <div style="font-size:11px;color:#fa0;">Camera</div>
    <div class="dpad">
      <div class="btn empty"></div>
      <div class="btn cam-btn" data-action="up" style="border-color:#fa0">&#8593;</div>
      <div class="btn empty"></div>
      <div class="btn cam-btn" data-action="left" style="border-color:#fa0">&#8592;</div>
      <div class="btn cam-btn" data-action="centre" style="border-color:#fa0;font-size:10px">CTR</div>
      <div class="btn cam-btn" data-action="right" style="border-color:#fa0">&#8594;</div>
      <div class="btn empty"></div>
      <div class="btn cam-btn" data-action="down" style="border-color:#fa0">&#8595;</div>
      <div class="btn empty"></div>
    </div>
  </div>

</div>

<div id="labels">
  WASD = drive &nbsp;|&nbsp; Space = mic &nbsp;|&nbsp; Enter = record &nbsp;|&nbsp;
  Q/E = fork &nbsp;|&nbsp; Arrows = camera &nbsp;|&nbsp;
  <a href="/recordings" target="_blank">Library</a>
</div>

<script>
"use strict";

// ---- State ----
var motorSuppressed = false;
var motorMuteTimer  = null;
var micMuted        = true;
var recActive       = false;
var heldKeys        = {};
var currentMotor    = null;

// ---- Elements ----
var statusEl  = document.getElementById("status");
var sonarEl   = document.getElementById("sonar");
var camPosEl  = document.getElementById("cam-pos");
var micBtn    = document.getElementById("mic-btn");
var recDot    = document.getElementById("rec-dot");
var recBtn    = document.getElementById("rec-btn");
var nameOver  = document.getElementById("name-overlay");
var nameInput = document.getElementById("name-input");

// ---- Motor ----
function sendMotor(cmd) {
  fetch("/motor", {
    method: "POST",
    headers: {"Content-Type": "application/x-www-form-urlencoded"},
    body: "cmd=" + cmd
  });
  var labels = {F:"FORWARD", B:"BACK", L:"LEFT", R:"RIGHT",
                S:"STOPPED", U:"FORK UP", D:"FORK DOWN"};
  statusEl.textContent = labels[cmd] || cmd;
  currentMotor = cmd;
  document.querySelectorAll(".btn[data-cmd]").forEach(function(b) {
    b.classList.toggle("active", b.dataset.cmd === cmd);
  });
  if (motorMuteTimer) clearTimeout(motorMuteTimer);
  if (cmd === "S") {
    motorMuteTimer = setTimeout(function() { motorSuppressed = false; }, 600);
  } else {
    motorSuppressed = true;
  }
}

function stopMotor() {
  if (currentMotor && currentMotor !== "S") sendMotor("S");
}

// ---- Camera ----
function sendCam(action) {
  fetch("/cam", {
    method: "POST",
    headers: {"Content-Type": "application/x-www-form-urlencoded"},
    body: "action=" + action
  });
}

// ---- Mic (Web Audio API) ----
var micCtx = null;
var micPlayAt = 0;

function initMic() {
  micCtx = new (window.AudioContext || window.webkitAudioContext)({sampleRate: SAMPLE_RATE});
  micPlayAt = micCtx.currentTime + 0.1;
  var leftover = new Uint8Array(0);

  fetch("/audio").then(function(resp) {
    var reader = resp.body.getReader();
    function pump() {
      reader.read().then(function(result) {
        if (result.done) return;
        var incoming = result.value;
        var combined = new Uint8Array(leftover.length + incoming.length);
        combined.set(leftover);
        combined.set(incoming, leftover.length);
        var totalSamples = Math.floor(combined.length / 2);
        var usedBytes    = totalSamples * 2;
        leftover = combined.slice(usedBytes);
        if (totalSamples > 0) {
          if (!micMuted && !motorSuppressed) {
            var buf = micCtx.createBuffer(1, totalSamples, SAMPLE_RATE);
            var f32  = buf.getChannelData(0);
            var view = new DataView(combined.buffer, combined.byteOffset, usedBytes);
            for (var i = 0; i < totalSamples; i++) {
              f32[i] = view.getInt16(i * 2, true) / 32768;
            }
            var src = micCtx.createBufferSource();
            src.buffer = buf;
            src.connect(micCtx.destination);
            var startAt = Math.max(micPlayAt, micCtx.currentTime + 0.02);
            src.start(startAt);
            micPlayAt = startAt + buf.duration;
          } else {
            micPlayAt = Math.max(micPlayAt, micCtx.currentTime) + totalSamples / SAMPLE_RATE;
          }
        }
        pump();
      }).catch(function() {});
    }
    pump();
  }).catch(function(e) { console.error("Mic error:", e); });
}

var SAMPLE_RATE = 16000;

function toggleMic() {
  if (!micCtx) initMic();
  micMuted = !micMuted;
  micBtn.textContent = micMuted ? "MIC: OFF" : "MIC: LIVE";
  micBtn.classList.toggle("on", !micMuted);
}

// ---- Recording ----
function toggleRecord() {
  if (recActive) {
    nameInput.value = "";
    nameOver.classList.add("on");
    setTimeout(function() { nameInput.focus(); }, 50);
  } else {
    fetch("/record/start", {method: "POST"})
      .then(function(r) { return r.json(); })
      .then(function(d) {
        if (d.ok) {
          recActive = true;
          recBtn.classList.add("on");
          recBtn.textContent = "&#9632; STOP";
          recBtn.innerHTML = "&#9632; STOP";
          recDot.classList.add("on");
        }
      });
  }
}

function saveRecording() {
  var name = nameInput.value.trim() || "recording";
  nameOver.classList.remove("on");
  fetch("/record/stop", {
    method: "POST",
    headers: {"Content-Type": "application/x-www-form-urlencoded"},
    body: "name=" + encodeURIComponent(name)
  }).then(function(r) { return r.json(); })
    .then(function(d) {
      recActive = false;
      recBtn.classList.remove("on");
      recBtn.innerHTML = "&#9679; REC";
      recDot.classList.remove("on");
      if (d.ok) alert("Saved: " + d.name + "\n\nSee /recordings to download.");
    });
}

nameInput.addEventListener("keydown", function(e) {
  e.stopPropagation();
  if (e.key === "Enter")  saveRecording();
  if (e.key === "Escape") nameOver.classList.remove("on");
});

// ---- Keyboard ----
var motorKeys = {w:"F", a:"L", s:"B", d:"R", q:"U", e:"D"};
var camKeys   = {arrowleft:"left", arrowright:"right",
                 arrowup:"up", arrowdown:"down"};

document.addEventListener("keydown", function(e) {
  var k = e.key.toLowerCase();
  if (heldKeys[k]) return;
  heldKeys[k] = true;
  if (nameOver.classList.contains("on")) return;
  if (k === " ")      { e.preventDefault(); toggleMic(); }
  else if (k === "enter") { e.preventDefault(); toggleRecord(); }
  else if (motorKeys[k])  { e.preventDefault(); sendMotor(motorKeys[k]); }
  else if (camKeys[k])    { e.preventDefault(); sendCam(camKeys[k]); }
});

document.addEventListener("keyup", function(e) {
  var k = e.key.toLowerCase();
  heldKeys[k] = false;
  if (motorKeys[k] && motorKeys[k] !== "U" && motorKeys[k] !== "D") stopMotor();
});

// ---- Touch: motor buttons ----
document.querySelectorAll(".btn[data-cmd]").forEach(function(btn) {
  var cmd = btn.dataset.cmd;
  btn.addEventListener("pointerdown",  function(e) { e.preventDefault(); sendMotor(cmd); });
  if (cmd !== "S" && cmd !== "U" && cmd !== "D") {
    btn.addEventListener("pointerup",    function(e) { e.preventDefault(); stopMotor(); });
    btn.addEventListener("pointerleave", function(e) { e.preventDefault(); stopMotor(); });
  }
});

// ---- Touch: camera buttons ----
document.querySelectorAll(".cam-btn[data-action]").forEach(function(btn) {
  var action = btn.dataset.action;
  btn.addEventListener("pointerdown", function(e) { e.preventDefault(); sendCam(action); });
});

// ---- Polling ----
setInterval(function() {
  fetch("/sonar")
    .then(function(r) { return r.json(); })
    .then(function(d) {
      if (d.distance !== null) {
        sonarEl.textContent = "Sonar: " + d.distance + " cm";
        sonarEl.style.color = d.distance < 30 ? "#f80" : "#0f0";
        sonarEl.style.borderColor = d.distance < 30 ? "#f80" : "#0f0";
      } else {
        sonarEl.textContent = "Sonar: --";
        sonarEl.style.color = "#0f0";
        sonarEl.style.borderColor = "#0f0";
      }
    }).catch(function() {});

  fetch("/cam_pos")
    .then(function(r) { return r.json(); })
    .then(function(d) {
      camPosEl.textContent = "Cam " + d.pan + " / " + d.tilt;
    }).catch(function() {});
}, 300);
</script>
</body>
</html>"""

# ── HTTP handler ──────────────────────────────────────────────────────────────

class Handler(BaseHTTPRequestHandler):
    def log_message(self, fmt, *args):
        pass

    def do_GET(self):
        path = urlparse(self.path).path

        if path == "/":
            body = PAGE.encode("ascii")
            self.send_response(200)
            self.send_header("Content-Type", "text/html; charset=ascii")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)

        elif path == "/stream":
            self.send_response(200)
            self.send_header("Content-Type",
                             "multipart/x-mixed-replace; boundary=frame")
            self.end_headers()
            try:
                while True:
                    with stream_lock:
                        frame = stream_frame
                    if frame:
                        hdr = (b"--frame\r\nContent-Type: image/jpeg\r\nContent-Length: "
                               + str(len(frame)).encode() + b"\r\n\r\n")
                        self.wfile.write(hdr + frame + b"\r\n")
                    time.sleep(0.033)
            except Exception:
                pass

        elif path == "/audio":
            self.send_response(200)
            self.send_header("Content-Type", "application/octet-stream")
            self.send_header("Cache-Control", "no-cache")
            self.end_headers()
            device = find_mic()
            print(f"[Mic] Streaming from {device}")
            proc = subprocess.Popen(
                ["arecord", "-D", device, "-f", "S16_LE",
                 "-r", str(SAMPLE_RATE), "-c", "1"],
                stdout=subprocess.PIPE, stderr=subprocess.DEVNULL)
            try:
                while True:
                    chunk = proc.stdout.read(2048)
                    if not chunk:
                        break
                    self.wfile.write(chunk)
                    self.wfile.flush()
            except Exception:
                pass
            finally:
                try: proc.kill()
                except Exception: pass

        elif path == "/sonar":
            with sonar_lock:
                d = sonar_dist
            body = (f'{{"distance":{d}}}'.encode() if d is not None
                    else b'{"distance":null}')
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)

        elif path == "/cam_pos":
            with servo_lock:
                body = f'{{"pan":{cam_pan},"tilt":{cam_tilt}}}'.encode()
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)

        elif path in ("/recordings", "/recordings/"):
            rows = ""
            try:
                for name in sorted(os.listdir(RECORDINGS_DIR), reverse=True):
                    d = os.path.join(RECORDINGS_DIR, name)
                    if not os.path.isdir(d):
                        continue
                    links = " ".join(
                        f'<a href="/recordings/{name}/{f}" download="{f}">{f}</a>'
                        for f in sorted(os.listdir(d))
                    )
                    rows += f"<tr><td>{name}</td><td>{links}</td></tr>"
            except Exception as ex:
                rows = f"<tr><td colspan=2>Error: {ex}</td></tr>"
            body = (
                "<!DOCTYPE html><html><head><meta charset=utf-8>"
                "<title>Recordings</title>"
                "<style>body{background:#111;color:#fff;font-family:monospace;padding:24px}"
                "h1{color:#08f;margin-bottom:16px}"
                "table{border-collapse:collapse;width:100%}"
                "th{text-align:left;color:#555;padding:8px 12px;border-bottom:1px solid #333}"
                "td{padding:8px 12px;border-bottom:1px solid #222;vertical-align:top}"
                "a{color:#4af;margin-right:12px}"
                "</style></head><body>"
                "<h1>Blue Fish Recordings</h1>"
                f"<table><tr><th>Name</th><th>Files</th></tr>{rows}</table>"
                "<p style='margin-top:20px'><a href='/'>Back to drive mode</a></p>"
                "</body></html>"
            ).encode()
            self.send_response(200)
            self.send_header("Content-Type", "text/html")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)

        elif path.startswith("/recordings/"):
            parts = path.strip("/").split("/")
            if len(parts) == 3:
                fpath = os.path.join(RECORDINGS_DIR, parts[1], parts[2])
                if os.path.isfile(fpath):
                    with open(fpath, "rb") as f:
                        data = f.read()
                    ext = parts[2].rsplit(".", 1)[-1].lower()
                    ct = {"mp4": "video/mp4", "wav": "audio/wav",
                          "mjpeg": "video/x-mjpeg"}.get(ext, "application/octet-stream")
                    self.send_response(200)
                    self.send_header("Content-Type", ct)
                    self.send_header("Content-Length", str(len(data)))
                    self.send_header("Content-Disposition",
                                     f'attachment; filename="{parts[2]}"')
                    self.end_headers()
                    self.wfile.write(data)
                    return
            self.send_response(404)
            self.end_headers()

        else:
            self.send_response(404)
            self.end_headers()

    def do_POST(self):
        path   = urlparse(self.path).path
        length = int(self.headers.get("Content-Length", 0))
        body   = self.rfile.read(length).decode()
        params = parse_qs(body)

        if path == "/motor":
            cmd = params.get("cmd", ["S"])[0].strip().upper()
            if cmd in ("F", "B", "L", "R", "S", "U", "D", "SL", "SR"):
                send_motor(cmd)

        elif path == "/cam":
            action = params.get("action", [""])[0]
            STEP = 10
            if   action == "left":   move_camera(dpan=-STEP)
            elif action == "right":  move_camera(dpan=+STEP)
            elif action == "up":     move_camera(dtilt=+STEP)
            elif action == "down":   move_camera(dtilt=-STEP)
            elif action == "centre": centre_camera()

        elif path == "/record/start":
            ok = start_recording()
            body = json.dumps({"ok": ok}).encode()
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)
            return

        elif path == "/record/stop":
            name  = params.get("name", ["recording"])[0]
            saved = stop_recording(name)
            body  = json.dumps({"ok": saved is not None, "name": saved}).encode()
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)
            return

        self.send_response(200)
        self.send_header("Content-Length", "0")
        self.end_headers()


class ThreadedServer(ThreadingMixIn, HTTPServer):
    daemon_threads = True


# ── Main ──────────────────────────────────────────────────────────────────────
if __name__ == "__main__":
    init_serial()
    init_servos()
    threading.Thread(target=camera_loop, daemon=True).start()
    threading.Thread(target=sonar_loop,  daemon=True).start()
    server = ThreadedServer(("0.0.0.0", PORT), Handler)
    print(f"[Drive] Ready at http://0.0.0.0:{PORT}")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        send_motor("S")
        print("\n[Drive] Stopped")
