#!/usr/bin/env python3
"""Blue Fish v2.2 - Drive Mode (no AI)
Run: python3 drive_mode.py
Open browser: http://<pi-ip>:8080
"""

import glob
import struct
import subprocess
import sys
import threading
import time
from http.server import BaseHTTPRequestHandler, HTTPServer
from socketserver import ThreadingMixIn
from urllib.parse import parse_qs, urlparse

sys.stdout.reconfigure(line_buffering=True)

PORT       = 8080
serial_conn = None
stream_frame = None
stream_lock  = threading.Lock()
sonar_dist   = None
sonar_lock   = threading.Lock()

# ── Camera servo ──────────────────────────────────────────────────────────────
# Pan servo  → GPIO 12  (arrow left/right)
# Tilt servo → GPIO 13  (arrow up/down)
PAN_PIN   = 12
TILT_PIN  = 13
cam_pan   = 0    # degrees, -90 to +90
cam_tilt  = 0    # degrees, -45 to +45
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
            factory = None  # fall back to software PWM
        kwargs = dict(min_pulse_width=0.0006, max_pulse_width=0.0023,
                      min_angle=-90, max_angle=90)
        if factory:
            kwargs["pin_factory"] = factory
        pan_servo  = AngularServo(PAN_PIN,  **kwargs)
        tilt_servo = AngularServo(TILT_PIN, **kwargs)
        pan_servo.angle  = 0
        tilt_servo.angle = 0
        print(f"[Servo] Camera pan/tilt ready (GPIO {PAN_PIN}/{TILT_PIN})")
    except Exception as e:
        print(f"[Servo] Not available: {e}")

def move_camera(dpan=0, dtilt=0):
    global cam_pan, cam_tilt
    with servo_lock:
        cam_pan  = max(-90, min(90,  cam_pan  + dpan))
        cam_tilt = max(-45, min(45,  cam_tilt + dtilt))
        if pan_servo:
            try: pan_servo.angle  = cam_pan
            except Exception: pass
        if tilt_servo:
            try: tilt_servo.angle = cam_tilt
            except Exception: pass
        return cam_pan, cam_tilt

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

# ── Serial / motor ────────────────────────────────────────────────────────────

def init_serial():
    global serial_conn
    try:
        import serial
        ports = glob.glob("/dev/ttyUSB*") + glob.glob("/dev/ttyACM*")
        if not ports:
            print("[Serial] No Arduino found")
            return
        port = ports[0]
        serial_conn = serial.Serial(port, 115200, timeout=1)
        time.sleep(2)
        print(f"[Serial] Connected on {port}")
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
                d = round(sensor.distance * 100, 1)
                with sonar_lock:
                    sonar_dist = d
            except Exception:
                with sonar_lock:
                    sonar_dist = None
            time.sleep(0.1)
    except Exception as e:
        print(f"[Sonar] Not available: {e}")

# ── Microphone stream ─────────────────────────────────────────────────────────

SAMPLE_RATE = 16000

def _wav_header():
    """Streaming WAV header with max data size so browser keeps reading."""
    data_size = 0xFFFFFFFF
    channels, bits = 1, 16
    byte_rate = SAMPLE_RATE * channels * bits // 8
    block_align = channels * bits // 8
    h  = struct.pack('<4sI4s', b'RIFF', data_size + 36, b'WAVE')
    h += struct.pack('<4sIHHIIHH', b'fmt ', 16, 1, channels,
                    SAMPLE_RATE, byte_rate, block_align, bits)
    h += struct.pack('<4sI', b'data', data_size)
    return h

def _find_mic():
    """Return the first USB audio capture device, or 'default'."""
    try:
        out = subprocess.check_output(
            ["arecord", "-l"], stderr=subprocess.DEVNULL, text=True)
        for line in out.splitlines():
            if "USB" in line or "usb" in line:
                # line: "card 1: Device [USB ...], device 0: ..."
                import re
                m = re.search(r'card (\d+):.*device (\d+):', line)
                if m:
                    return f"plughw:{m.group(1)},{m.group(2)}"
    except Exception:
        pass
    return "default"

# ── Camera ────────────────────────────────────────────────────────────────────

def camera_loop():
    global stream_frame
    cmd = ["rpicam-vid", "-t", "0", "--width", "640", "--height", "480",
           "--framerate", "30", "--codec", "mjpeg", "--inline", "-o", "-"]
    while True:
        print("[Camera] Starting...")
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
        except Exception as ex:
            print(f"[Camera] {ex}")
        finally:
            try: proc.kill()
            except Exception: pass
        time.sleep(2)

# ── HTML ──────────────────────────────────────────────────────────────────────

PAGE = """<!DOCTYPE html>
<html>
<head>
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Blue Fish Drive Mode</title>
<style>
  * { box-sizing: border-box; margin: 0; padding: 0; }
  body { background: #111; color: #fff; font-family: monospace;
         display: flex; flex-direction: column; height: 100vh; overflow: hidden; }
  #cam { flex: 1; position: relative; background: #000; }
  #cam img { width: 100%; height: 100%; object-fit: contain; display: block; }
  #sonar {
    position: absolute; bottom: 10px; left: 10px;
    background: rgba(0,0,0,0.6); border: 1px solid #0f0;
    padding: 8px 12px; border-radius: 8px; font-size: 14px; color: #0f0;
  }
  #mic-btn {
    position: absolute; bottom: 10px; right: 10px;
    background: rgba(0,0,0,0.6); border: 1px solid #555;
    padding: 8px 14px; border-radius: 8px; font-size: 14px;
    color: #aaa; cursor: pointer; user-select: none;
  }
  #mic-btn.on { border-color: #f44; color: #f44; }
  #status {
    position: absolute; top: 10px; right: 10px;
    background: rgba(0,0,0,0.6); border: 1px solid #08f;
    padding: 6px 12px; border-radius: 8px; font-size: 13px; color: #08f;
  }
  #controls {
    background: #1a1a1a; padding: 12px; border-top: 1px solid #333;
    display: flex; gap: 12px; justify-content: center; align-items: center;
    flex-wrap: wrap;
  }
  .dpad { display: grid; grid-template-columns: repeat(3, 52px); gap: 4px; }
  .btn {
    width: 52px; height: 52px; border-radius: 10px; border: none;
    font-size: 20px; cursor: pointer; user-select: none;
    background: #2a2a2a; color: #fff; border: 1px solid #444;
    transition: background 0.1s;
  }
  .btn:active, .btn.active { background: #0077cc; border-color: #08f; }
  .btn.empty { background: transparent; border: none; cursor: default; }
  .forkbtns { display: flex; flex-direction: column; gap: 4px; }
  .stop-btn {
    width: 80px; height: 80px; border-radius: 50%; font-size: 13px;
    background: #cc2200; border-color: #f44;
  }
  #labels { font-size: 11px; color: #666; text-align: center; line-height: 1.8; }
</style>
</head>
<body>

<div id="cam">
  <img src="/stream" id="feed">
  <div id="sonar">Sonar: --</div>
  <div id="status">STOPPED</div>
  <div id="mic-btn" onclick="toggleMic()">🎤 Mic: OFF</div>
  <audio id="mic-audio" style="display:none"></audio>
  <div id="cam-pos" style="position:absolute;top:10px;left:10px;background:rgba(0,0,0,0.6);
    border:1px solid #fa0;padding:6px 12px;border-radius:8px;font-size:13px;color:#fa0;">
    Cam pan:0° tilt:0°</div>
</div>

<div id="controls">
  <!-- D-pad -->
  <div class="dpad">
    <div class="btn empty"></div>
    <button class="btn" id="btn-F" data-cmd="F">&#8593;</button>
    <div class="btn empty"></div>
    <button class="btn" id="btn-L" data-cmd="L">&#8592;</button>
    <button class="btn stop-btn" id="btn-S" data-cmd="S">STOP</button>
    <button class="btn" id="btn-R" data-cmd="R">&#8594;</button>
    <div class="btn empty"></div>
    <button class="btn" id="btn-B" data-cmd="B">&#8595;</button>
    <div class="btn empty"></div>
  </div>

  <!-- Fork lift -->
  <div class="forkbtns">
    <button class="btn" id="btn-U" data-cmd="U" style="width:80px">&#8679; Fork</button>
    <button class="btn" id="btn-D" data-cmd="D" style="width:80px">&#8681; Fork</button>
  </div>

  <!-- Camera pan/tilt -->
  <div style="display:flex;flex-direction:column;align-items:center;gap:4px;">
    <div style="font-size:11px;color:#fa0;margin-bottom:2px;">&#128247; Camera</div>
    <div class="dpad">
      <div class="btn empty"></div>
      <button class="btn cam-btn" data-action="up" style="border-color:#fa0">&#8593;</button>
      <div class="btn empty"></div>
      <button class="btn cam-btn" data-action="left" style="border-color:#fa0">&#8592;</button>
      <button class="btn cam-btn" data-action="centre" style="border-color:#fa0;font-size:11px">CTR</button>
      <button class="btn cam-btn" data-action="right" style="border-color:#fa0">&#8594;</button>
      <div class="btn empty"></div>
      <button class="btn cam-btn" data-action="down" style="border-color:#fa0">&#8595;</button>
      <div class="btn empty"></div>
    </div>
  </div>
</div>

<div id="labels">
  WASD = drive &nbsp;|&nbsp; Space = stop &nbsp;|&nbsp; Q/E = forklift &nbsp;|&nbsp; Arrow keys = camera
</div>

<script>
// Mic toggle
var micOn = false;
var micAudio = document.getElementById('mic-audio');
var micBtn   = document.getElementById('mic-btn');
function toggleMic() {
  if (micOn) {
    micAudio.pause();
    micAudio.src = '';
    micBtn.textContent = '🎤 Mic: OFF';
    micBtn.classList.remove('on');
    micOn = false;
  } else {
    micAudio.src = '/audio';
    micAudio.play().catch(function(){});
    micBtn.textContent = '🎤 Mic: ON';
    micBtn.classList.add('on');
    micOn = true;
  }
}

var motorMap = {'w':'F','a':'L','s':'B','d':'R',' ':'S','q':'U','e':'D'};
var camMap   = {'arrowleft':'left','arrowright':'right','arrowup':'up','arrowdown':'down'};

var statusEl = document.getElementById('status');
var sonarEl  = document.getElementById('sonar');
var camEl    = document.getElementById('cam-pos');
var current  = null;

function sendMotor(cmd) {
  fetch('/motor', {method:'POST', body:'cmd='+cmd,
    headers:{'Content-Type':'application/x-www-form-urlencoded'}});
  statusEl.textContent = {F:'FORWARD',B:'BACK',L:'LEFT',R:'RIGHT',
                           S:'STOPPED',U:'FORK UP',D:'FORK DOWN'}[cmd] || cmd;
  current = cmd;
  document.querySelectorAll('.btn').forEach(function(b){b.classList.remove('active')});
  var b = document.getElementById('btn-'+cmd);
  if(b) b.classList.add('active');
}

function stopMotor() {
  if(current && current !== 'S') sendMotor('S');
}

function sendCam(action) {
  fetch('/cam', {method:'POST', body:'action='+action,
    headers:{'Content-Type':'application/x-www-form-urlencoded'}});
}

// Keyboard
var held = {};
document.addEventListener('keydown', function(e) {
  var k = e.key.toLowerCase();
  if(held[k]) return;
  held[k] = true;
  if(motorMap[k]) { e.preventDefault(); sendMotor(motorMap[k]); }
  else if(camMap[k]) { e.preventDefault(); sendCam(camMap[k]); }
});
document.addEventListener('keyup', function(e) {
  var k = e.key.toLowerCase();
  held[k] = false;
  if(motorMap[k] && motorMap[k] !== 'U' && motorMap[k] !== 'D') stopMotor();
});

// Touch buttons — motors
document.querySelectorAll('.btn[data-cmd]').forEach(function(btn) {
  var cmd = btn.dataset.cmd;
  btn.addEventListener('pointerdown', function(e) { e.preventDefault(); sendMotor(cmd); });
  if(cmd !== 'S' && cmd !== 'U' && cmd !== 'D') {
    btn.addEventListener('pointerup',    function(e){ e.preventDefault(); stopMotor(); });
    btn.addEventListener('pointerleave', function(e){ e.preventDefault(); stopMotor(); });
  }
});

// Touch buttons — camera
document.querySelectorAll('.cam-btn[data-action]').forEach(function(btn) {
  var action = btn.dataset.action;
  btn.addEventListener('pointerdown', function(e){ e.preventDefault(); sendCam(action); });
});

// Sonar + cam position polling
setInterval(function() {
  fetch('/sonar').then(function(r){return r.json();}).then(function(d){
    sonarEl.textContent = d.distance !== null ? 'Sonar: '+d.distance+' cm' : 'Sonar: --';
    sonarEl.style.color = d.distance !== null && d.distance < 30 ? '#f80' : '#0f0';
  }).catch(function(){});
  fetch('/cam_pos').then(function(r){return r.json();}).then(function(d){
    camEl.textContent = 'Cam pan:'+d.pan+'° tilt:'+d.tilt+'°';
  }).catch(function(){});
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
            body = PAGE.encode()
            self.send_response(200)
            self.send_header("Content-Type", "text/html")
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
                        header = (
                            b"--frame\r\n"
                            b"Content-Type: image/jpeg\r\n"
                            b"Content-Length: " + str(len(frame)).encode() +
                            b"\r\n\r\n"
                        )
                        self.wfile.write(header + frame + b"\r\n")
                    time.sleep(0.033)
            except Exception:
                pass

        elif path == "/audio":
            self.send_response(200)
            self.send_header("Content-Type", "audio/wav")
            self.send_header("Cache-Control", "no-cache")
            self.send_header("Transfer-Encoding", "chunked")
            self.end_headers()
            self.wfile.write(_wav_header())
            device = _find_mic()
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
            body = f'{{"distance":{d}}}'.encode() if d is not None \
                   else b'{"distance":null}'
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

        else:
            self.send_response(404)
            self.end_headers()

    def do_POST(self):
        path = urlparse(self.path).path
        if path == "/motor":
            length = int(self.headers.get("Content-Length", 0))
            body   = self.rfile.read(length).decode()
            params = parse_qs(body)
            cmd    = params.get("cmd", ["S"])[0].strip().upper()
            if cmd in ("F", "B", "L", "R", "S", "U", "D", "SL", "SR"):
                send_motor(cmd)
            self.send_response(200)
            self.send_header("Content-Length", "0")
            self.end_headers()

        elif path == "/cam":
            length = int(self.headers.get("Content-Length", 0))
            body   = self.rfile.read(length).decode()
            params = parse_qs(body)
            action = params.get("action", [""])[0]
            STEP = 10  # degrees per keypress
            if   action == "left":   move_camera(dpan=-STEP)
            elif action == "right":  move_camera(dpan=+STEP)
            elif action == "up":     move_camera(dtilt=+STEP)
            elif action == "down":   move_camera(dtilt=-STEP)
            elif action == "centre": centre_camera()
            self.send_response(200)
            self.send_header("Content-Length", "0")
            self.end_headers()

        else:
            self.send_response(404)
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
    print("[Drive] WASD = move | Space = stop | Q/E = forklift")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        send_motor("S")
        print("\n[Drive] Stopped")
