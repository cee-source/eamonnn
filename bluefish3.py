#!/usr/bin/env python3
"""Blue Fish v3.0 — Stage 1: Brain"""

import os, sys, json, time, threading, subprocess, queue, secrets
sys.stdout.reconfigure(line_buffering=True)

import numpy as np
import sounddevice as sd
import whisper
import urllib.request
from http.server import HTTPServer, BaseHTTPRequestHandler
from socketserver import ThreadingMixIn
from urllib.parse import parse_qs, urlparse

# ── Config ────────────────────────────────────────────────────────────────────
HOME         = os.path.expanduser("~")
PIPER        = f"{HOME}/.local/bin/piper"
VOICE_MODEL  = f"{HOME}/piper_voices/en_US-ryan-high.onnx"
OLLAMA_MODEL = "bluefish"
OWNER_EMAIL  = "ehmcdermott77@gmail.com"
OWNER_PASS   = "7807809"
WEB_PORT     = 8080

# ── Audio config ──────────────────────────────────────────────────────────────
CHUNK             = 1024
SILENCE_THRESHOLD = 100
MAX_SILENCE       = 1.5

try:
    _devs = sd.query_devices()
    MIC_DEVICE = next(
        (i for i, d in enumerate(_devs)
         if "usb" in d["name"].lower() and d["max_input_channels"] > 0),
        None
    )
    if MIC_DEVICE is None:
        MIC_DEVICE = sd.default.device[0]
    _dev       = sd.query_devices(MIC_DEVICE, "input")
    SAMPLERATE = int(_dev["default_samplerate"])
    MIC_CH     = max(1, int(_dev["max_input_channels"]))
    print(f"[Mic] {_dev['name']} — {SAMPLERATE}Hz")
except Exception as e:
    MIC_DEVICE = None
    SAMPLERATE = 44100
    MIC_CH     = 1
    print(f"[Mic] detection failed: {e}")

# ── State ─────────────────────────────────────────────────────────────────────
speaking       = False
conversation   = []            # grows as chat goes — Blue Fish remembers everything
valid_sessions = set()
sessions_lock  = threading.Lock()
audio_queue    = queue.Queue()

# ── TTS (Piper) ───────────────────────────────────────────────────────────────
def speak(text):
    global speaking
    speaking = True
    print(f"Blue Fish: {text}")
    try:
        proc = subprocess.Popen(
            [PIPER, "--model", VOICE_MODEL, "--output_raw"],
            stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.DEVNULL
        )
        raw, _ = proc.communicate(text.encode())
        subprocess.run(
            ["aplay", "-r", "22050", "-f", "S16_LE", "-c", "1"],
            input=raw, capture_output=True, timeout=30
        )
    except Exception as e:
        print(f"[TTS error] {e}")
    finally:
        speaking = False

# ── Ollama ────────────────────────────────────────────────────────────────────
def ask_ollama(user_text):
    conversation.append({"role": "user", "content": user_text})
    payload = json.dumps({
        "model": OLLAMA_MODEL,
        "messages": conversation,
        "stream": False
    }).encode()
    try:
        req = urllib.request.Request(
            "http://localhost:11434/api/chat",
            data=payload,
            headers={"Content-Type": "application/json"}
        )
        with urllib.request.urlopen(req, timeout=30) as r:
            reply = json.loads(r.read())["message"]["content"].strip()
    except Exception as e:
        print(f"[Ollama] {e}")
        reply = "I'm thinking..."
    conversation.append({"role": "assistant", "content": reply})
    return reply

# ── Whisper STT ───────────────────────────────────────────────────────────────
print("[Whisper] Loading...")
whisper_model = whisper.load_model("tiny")
print("[Whisper] Ready")

def transcribe(audio_np):
    audio_f32 = audio_np.astype(np.float32) / 32768.0
    if SAMPLERATE != 16000:
        import scipy.signal
        audio_f32 = scipy.signal.resample_poly(
            audio_f32, 16000, SAMPLERATE).astype(np.float32)
    return whisper_model.transcribe(audio_f32, fp16=False, language="en")["text"].strip()

# ── Microphone loop ───────────────────────────────────────────────────────────
def audio_callback(indata, frames, time_info, status):
    mono = indata.mean(axis=1).astype(np.int16) if indata.shape[1] > 1 else indata[:, 0]
    audio_queue.put(mono.copy())

def listen_loop():
    print("[Listen] Microphone ready — say something!")
    with sd.InputStream(samplerate=SAMPLERATE, device=MIC_DEVICE,
                        channels=MIC_CH, dtype="int16",
                        blocksize=CHUNK, callback=audio_callback):
        buf           = []
        silence_chunks = 0
        in_speech     = False
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
                                print(f"You: {text}")
                                reply = ask_ollama(text)
                                speak(reply)
                        threading.Thread(target=_process, daemon=True).start()

# ── Web chat server ───────────────────────────────────────────────────────────
class ChatHandler(BaseHTTPRequestHandler):
    def log_message(self, fmt, *args):
        pass

    def _check_session(self):
        for part in self.headers.get("Cookie", "").split(";"):
            k, _, v = part.strip().partition("=")
            if k.strip() == "bf_session":
                with sessions_lock:
                    return v.strip() in valid_sessions
        return False

    def _send_html(self, html, status=200):
        body = html.encode()
        self.send_response(status)
        self.send_header("Content-Type", "text/html")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def _send_json(self, data):
        body = json.dumps(data).encode()
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def _login_page(self, error=False):
        err = '<p style="color:#f55;margin-bottom:12px;">Wrong email or password.</p>' if error else ""
        self._send_html(f"""<!DOCTYPE html><html><head><title>Blue Fish</title>
<style>*{{box-sizing:border-box;margin:0;padding:0;}}
body{{background:#0d1117;display:flex;align-items:center;
  justify-content:center;min-height:100dvh;font-family:monospace;}}
.box{{background:#161b22;border:1px solid #30363d;border-radius:12px;
  padding:36px;width:300px;text-align:center;}}
h2{{color:#38bdf8;letter-spacing:3px;margin-bottom:24px;font-size:18px;}}
input{{display:block;width:100%;background:#0d1117;color:#e6edf3;
  border:1px solid #30363d;border-radius:6px;padding:10px 14px;
  font-family:monospace;font-size:14px;margin-bottom:12px;outline:none;}}
input:focus{{border-color:#38bdf8;}}
button{{width:100%;background:#38bdf8;color:#0d1117;border:none;
  border-radius:6px;padding:11px;font-family:monospace;font-size:14px;
  font-weight:700;cursor:pointer;letter-spacing:1px;}}
</style></head><body><div class="box">
<h2>🐟 BLUE FISH v3</h2>{err}
<form method="POST" action="/login">
  <input name="email" type="email" placeholder="Email" required autocomplete="email">
  <input name="password" type="password" placeholder="Password" required>
  <button type="submit">ENTER</button>
</form></div></body></html>""")

    def do_GET(self):
        path = urlparse(self.path).path
        if path == "/login":
            self._login_page(); return
        if not self._check_session():
            self._login_page(); return
        if path == "/history":
            self._send_json(conversation); return
        self._chat_page()

    def do_POST(self):
        length = int(self.headers.get("Content-Length", 0))
        raw    = self.rfile.read(length).decode()
        params = parse_qs(raw)
        path   = urlparse(self.path).path

        if path == "/login":
            email = params.get("email", [""])[0].strip().lower()
            pw    = params.get("password", [""])[0]
            if email == OWNER_EMAIL.lower() and pw == OWNER_PASS:
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
            self.send_response(403); self.send_header("Content-Length","0"); self.end_headers(); return

        if path == "/chat":
            msg = params.get("msg", [""])[0].strip()
            if msg:
                def _reply():
                    reply = ask_ollama(msg)
                    speak(reply)
                threading.Thread(target=_reply, daemon=True).start()
            self._send_json({"ok": True})
        else:
            self.send_response(404); self.send_header("Content-Length","0"); self.end_headers()

    def _chat_page(self):
        self._send_html("""<!DOCTYPE html><html><head>
<title>Blue Fish v3</title>
<meta name="viewport" content="width=device-width,initial-scale=1">
<style>
*{box-sizing:border-box;margin:0;padding:0;}
body{background:#0d1117;color:#e6edf3;font-family:monospace;
  display:flex;flex-direction:column;height:100dvh;}
header{padding:14px 16px;border-bottom:1px solid #30363d;
  color:#38bdf8;font-size:16px;font-weight:700;letter-spacing:2px;
  display:flex;align-items:center;gap:10px;}
#log{flex:1;overflow-y:auto;padding:16px;display:flex;flex-direction:column;gap:10px;}
.msg{max-width:80%;padding:10px 14px;border-radius:12px;
  line-height:1.5;font-size:14px;word-break:break-word;}
.user{background:#21262d;align-self:flex-end;border:1px solid #30363d;}
.bot{background:#0c2d4a;align-self:flex-start;border:1px solid #1f4e79;color:#7dd3fc;}
.typing{color:#484f58;font-style:italic;}
form{display:flex;gap:8px;padding:12px 16px;border-top:1px solid #30363d;}
input{flex:1;background:#161b22;color:#e6edf3;border:1px solid #30363d;
  border-radius:8px;padding:10px 14px;font-family:monospace;font-size:14px;outline:none;}
input:focus{border-color:#38bdf8;}
button{background:#38bdf8;color:#0d1117;border:none;border-radius:8px;
  padding:10px 18px;font-family:monospace;font-size:14px;font-weight:700;cursor:pointer;}
button:active{background:#0ea5e9;}
</style></head><body>
<header>🐟 BLUE FISH v3.0</header>
<div id="log"></div>
<form id="f">
  <input id="i" placeholder="Type a message..." autocomplete="off">
  <button type="submit">Send</button>
</form>
<script>
var pending = false;

function addMsg(text, cls) {
  var log = document.getElementById('log');
  var m = document.createElement('div');
  m.className = 'msg ' + cls;
  m.textContent = text;
  log.appendChild(m);
  log.scrollTop = log.scrollHeight;
  return m;
}

document.getElementById('f').addEventListener('submit', function(e) {
  e.preventDefault();
  if (pending) return;
  var msg = document.getElementById('i').value.trim();
  if (!msg) return;
  addMsg(msg, 'user');
  document.getElementById('i').value = '';
  pending = true;

  var typing = addMsg('thinking...', 'bot typing');

  fetch('/chat', {method:'POST',
    headers:{'Content-Type':'application/x-www-form-urlencoded'},
    body:'msg=' + encodeURIComponent(msg)});

  var known = document.querySelectorAll('.bot:not(.typing)').length;

  function poll() {
    fetch('/history').then(r => r.json()).then(h => {
      var bots = h.filter(m => m.role === 'assistant');
      if (bots.length > known) {
        typing.remove();
        addMsg(bots[bots.length - 1].content, 'bot');
        pending = false;
      } else {
        setTimeout(poll, 500);
      }
    });
  }
  setTimeout(poll, 600);
});
</script>
</body></html>""")

class ThreadedHTTPServer(ThreadingMixIn, HTTPServer):
    daemon_threads = True

def start_web():
    server = ThreadedHTTPServer(("0.0.0.0", WEB_PORT), ChatHandler)
    print(f"[Web] Open http://<your-pi-ip>:{WEB_PORT} in a browser")
    server.serve_forever()

# ── Main ──────────────────────────────────────────────────────────────────────
def main():
    threading.Thread(target=start_web, daemon=True).start()
    time.sleep(1)
    speak("Blue Fish version 3 online. I am ready!")
    listen_loop()

if __name__ == "__main__":
    main()
