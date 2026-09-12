#!/usr/bin/env python3
"""Blue Fish v2.2 - Drive Mode"""

import glob
import json
import os
import re
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

# ---------------------------------------------------------------------------
# Serial / motors
# ---------------------------------------------------------------------------
serial_lock = threading.Lock()
serial_conn = None

def init_serial():
    global serial_conn
    import serial as _serial
    ports = glob.glob("/dev/ttyUSB*") + glob.glob("/dev/ttyACM*")
    if not ports:
        print("[Serial] No port found")
        return
    try:
        serial_conn = _serial.Serial(ports[0], 115200, timeout=1)
        time.sleep(2)
        print(f"[Serial] OK on {ports[0]}")
    except Exception as e:
        print(f"[Serial] {e}")

def send_motor(cmd):
    global serial_conn
    with serial_lock:
        for attempt in range(3):
            if serial_conn is None:
                init_serial()
            if serial_conn is None:
                time.sleep(0.5)
                continue
            try:
                serial_conn.write((cmd + "\n").encode())
                serial_conn.flush()
                print(f"[Motor] sent: {cmd}")
                return
            except Exception as e:
                print(f"[Motor] attempt {attempt+1} failed: {e}")
                try: serial_conn.close()
                except Exception: pass
                serial_conn = None
                time.sleep(0.3)
        print(f"[Motor] gave up on: {cmd}")

def serial_keepalive():
    while True:
        time.sleep(5)
        with serial_lock:
            if serial_conn:
                try:
                    serial_conn.write(b"S\n")
                    serial_conn.flush()
                except Exception as e:
                    print(f"[Serial] keepalive failed: {e}")

# ---------------------------------------------------------------------------
# Camera stream
# ---------------------------------------------------------------------------
stream_frame = None
stream_lock  = threading.Lock()

def camera_loop():
    global stream_frame
    cmd = ["rpicam-vid", "-t", "0", "--width", "640", "--height", "480",
           "--framerate", "15", "--codec", "mjpeg", "--inline", "-o", "-"]
    while True:
        print("[Camera] starting...")
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
                    if _rec_active and _rec_vfile:
                        try: _rec_vfile.write(frame)
                        except Exception: pass
        except Exception as ex:
            print(f"[Camera] {ex}")
        finally:
            try: proc and proc.kill()
            except Exception: pass
        time.sleep(2)

# ---------------------------------------------------------------------------
# Sonar
# ---------------------------------------------------------------------------
sonar_dist = None
sonar_lock = threading.Lock()

def sonar_loop():
    global sonar_dist
    try:
        from gpiozero import DistanceSensor
        sensor = DistanceSensor(echo=24, trigger=23, max_distance=4)
        print("[Sonar] OK")
        while True:
            try:
                with sonar_lock:
                    sonar_dist = round(sensor.distance * 100, 1)
            except Exception:
                with sonar_lock:
                    sonar_dist = None
            time.sleep(0.1)
    except Exception as e:
        print(f"[Sonar] {e}")

# ---------------------------------------------------------------------------
# Microphone
# ---------------------------------------------------------------------------
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

# ---------------------------------------------------------------------------
# Recording
# ---------------------------------------------------------------------------
_rec_active = False
_rec_vfile  = None
_rec_aproc  = None
_rec_lock   = threading.Lock()

def rec_start():
    global _rec_active, _rec_vfile, _rec_aproc
    with _rec_lock:
        if _rec_active:
            return False
        try:
            _rec_vfile = open("/tmp/rec_v.mjpeg", "wb")
        except Exception as e:
            print(f"[Rec] {e}"); return False
        _rec_aproc = subprocess.Popen(
            ["arecord", "-D", find_mic(), "-f", "S16_LE", "-r", "16000", "-c", "1",
             "/tmp/rec_a.wav"],
            stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        _rec_active = True
        print("[Rec] started")
        return True

def rec_stop(name):
    global _rec_active, _rec_vfile, _rec_aproc
    with _rec_lock:
        if not _rec_active:
            return None
        _rec_active = False
        if _rec_aproc:
            _rec_aproc.terminate()
            try: _rec_aproc.wait(timeout=3)
            except Exception: pass
            _rec_aproc = None
        if _rec_vfile:
            _rec_vfile.close()
            _rec_vfile = None
    safe = re.sub(r"[^a-zA-Z0-9_\-]", "_", name).strip("_") or "rec"
    out  = os.path.join(RECORDINGS_DIR, safe)
    if os.path.exists(out):
        safe = f"{safe}_{int(time.time())}"
        out  = os.path.join(RECORDINGS_DIR, safe)
    os.makedirs(out, exist_ok=True)
    mp4 = os.path.join(out, f"{safe}.mp4")
    try:
        subprocess.run(
            ["ffmpeg", "-y", "-i", "/tmp/rec_a.wav",
             "-f", "mjpeg", "-framerate", "15", "-i", "/tmp/rec_v.mjpeg",
             "-c:v", "copy", "-c:a", "aac", mp4],
            timeout=60, check=True,
            stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        print(f"[Rec] saved {mp4}")
    except Exception:
        for src, dst in [("/tmp/rec_v.mjpeg", os.path.join(out, "video.mjpeg")),
                         ("/tmp/rec_a.wav",   os.path.join(out, "audio.wav"))]:
            if os.path.exists(src):
                os.replace(src, dst)
        print(f"[Rec] saved to {out}")
    return safe

# ---------------------------------------------------------------------------
# HTML
# ---------------------------------------------------------------------------
PAGE = b"""<!DOCTYPE html>
<html>
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>Blue Fish</title>
<style>
*{box-sizing:border-box;margin:0;padding:0}
body{background:#000;color:#fff;font-family:monospace;
     display:flex;flex-direction:column;height:100vh}
#cam{flex:1;position:relative;overflow:hidden;min-height:0}
#feed{width:100%;height:100%;object-fit:cover;display:block}
.hud{position:absolute;background:rgba(0,0,0,.6);
     border-radius:6px;padding:5px 10px;font-size:12px}
#sonar {bottom:8px;left:8px;border:1px solid #0f0;color:#0f0}
#status{top:8px;right:8px;border:1px solid #08f;color:#08f}
#rdot  {top:36px;right:8px;border:1px solid #f44;color:#f44;
        display:none;animation:blink 1s step-start infinite}
#rdot.on{display:block}
@keyframes blink{50%{opacity:.2}}
#name-overlay{display:none;position:absolute;inset:0;
  background:rgba(0,0,0,.85);z-index:9;
  align-items:center;justify-content:center;flex-direction:column;gap:12px}
#name-overlay.on{display:flex}
#name-overlay h2{font-size:.95rem}
#ni{font-family:monospace;font-size:1rem;padding:9px 14px;
    border-radius:7px;border:2px solid #08f;background:#111;
    color:#fff;width:240px;text-align:center;outline:none}
#nsave{padding:9px 24px;border-radius:7px;border:none;
       background:#08f;color:#fff;font:1rem monospace;cursor:pointer}
#bar{background:#111;padding:8px 10px;border-top:1px solid #222;
     display:flex;gap:8px;justify-content:center;align-items:center;flex-wrap:wrap}
.dp{display:grid;grid-template-columns:repeat(3,48px);gap:3px}
.b{width:48px;height:48px;border-radius:9px;background:#1e1e1e;
   border:1px solid #333;color:#fff;font-size:16px;cursor:pointer;
   display:flex;align-items:center;justify-content:center;
   user-select:none;-webkit-user-select:none}
.b:active,.b.on{background:#005fa3;border-color:#08f}
.x{background:transparent!important;border:none!important;cursor:default}
.big{width:68px;height:68px;border-radius:50%;font-size:12px}
.stp{background:#2a0000;border-color:#f44;color:#f44}
.rcb{background:#1a0000;border-color:#633;color:#c44;font-size:11px}
.rcb.on{background:#3a0000;border-color:#f44;color:#f44}
.col{display:flex;flex-direction:column;gap:4px;align-items:center}
.fb{width:72px;height:32px;border-radius:7px;font-size:11px}
#tips{font-size:10px;color:#444;text-align:center;padding:3px 0 5px}
#tips a{color:#08f;text-decoration:none}
#mic-btn{top:8px;left:8px;border:1px solid #555;color:#888;cursor:pointer}
#mic-btn.on{border-color:#f44;color:#f44}
</style>
</head>
<body>
<div id="cam">
  <img src="/stream" id="feed" alt="">
  <div class="hud" id="sonar">Sonar: --</div>
  <div class="hud" id="status">STOPPED</div>
  <div class="hud" id="mic-btn" onclick="toggleMic()">MIC OFF</div>
  <div class="hud" id="rdot">&#9679; REC</div>
  <div id="name-overlay">
    <h2>Name this recording</h2>
    <input id="ni" type="text" placeholder="e.g. garden_run" maxlength="40">
    <button id="nsave" onclick="saveRec()">Save</button>
  </div>
</div>

<div id="bar">
  <div class="dp">
    <div class="b x"></div>
    <div class="b" id="bF" data-cmd="F">&#8593;</div>
    <div class="b x"></div>
    <div class="b" id="bL" data-cmd="L">&#8592;</div>
    <div class="b big stp" id="bS" data-cmd="S">STOP</div>
    <div class="b" id="bR" data-cmd="R">&#8594;</div>
    <div class="b x"></div>
    <div class="b" id="bB" data-cmd="B">&#8595;</div>
    <div class="b x"></div>
  </div>
  <div class="col">
    <div class="b fb" id="bU" data-cmd="U">&#8679; Fork</div>
    <div class="b fb" id="bD" data-cmd="D">&#8681; Fork</div>
    <div class="b big rcb" id="rec-btn" onclick="toggleRec()">&#9679; REC</div>
  </div>
  <div class="col">
    <span style="font-size:10px;color:#fa0">Camera</span>
    <div class="dp">
      <div class="b x"></div>
      <div class="b cb" data-a="up" style="border-color:#fa0">&#8593;</div>
      <div class="b x"></div>
      <div class="b cb" data-a="left" style="border-color:#fa0">&#8592;</div>
      <div class="b cb" data-a="centre" style="border-color:#fa0;font-size:9px">CTR</div>
      <div class="b cb" data-a="right" style="border-color:#fa0">&#8594;</div>
      <div class="b x"></div>
      <div class="b cb" data-a="down" style="border-color:#fa0">&#8595;</div>
      <div class="b x"></div>
    </div>
  </div>
</div>
<div id="tips">WASD=drive | Space=mic | Enter=rec | Q/E=fork | Arrows=cam | <a href="/recordings" target="_blank">Library</a></div>

<script>
"use strict";
var SAMPLE_RATE=16000;
var motorSuppressed=false,mTimer=null;
var micMuted=true,micCtx=null,micAt=0;
var recOn=false;
var held={},curMotor=null;
var statusEl=document.getElementById("status");
var sonarEl=document.getElementById("sonar");
var micBtn=document.getElementById("mic-btn");
var rdot=document.getElementById("rdot");
var recBtn=document.getElementById("rec-btn");
var nameOv=document.getElementById("name-overlay");
var ni=document.getElementById("ni");

function post(url,body){
  return fetch(url,{method:"POST",
    headers:{"Content-Type":"application/x-www-form-urlencoded"},body:body});
}

function motor(cmd){
  post("/motor","cmd="+cmd);
  var lb={F:"FWD",B:"BACK",L:"LEFT",R:"RIGHT",S:"STOP",U:"FORK UP",D:"FORK DN"};
  statusEl.textContent=lb[cmd]||cmd;
  curMotor=cmd;
  document.querySelectorAll(".b[data-cmd]").forEach(function(b){
    b.classList.toggle("on",b.dataset.cmd===cmd);
  });
  if(mTimer)clearTimeout(mTimer);
  if(cmd==="S"){mTimer=setTimeout(function(){motorSuppressed=false;},600);}
  else{motorSuppressed=true;}
}
function stopM(){if(curMotor&&curMotor!=="S")motor("S");}
function cam(a){post("/cam","action="+a);}

function initMic(){
  micCtx=new(window.AudioContext||window.webkitAudioContext)({sampleRate:SAMPLE_RATE});
  micAt=micCtx.currentTime+0.1;
  var left=new Uint8Array(0);
  fetch("/audio").then(function(r){
    var rd=r.body.getReader();
    function pump(){rd.read().then(function(res){
      if(res.done)return;
      var inc=res.value,c=new Uint8Array(left.length+inc.length);
      c.set(left);c.set(inc,left.length);
      var n=Math.floor(c.length/2),ub=n*2;
      left=c.slice(ub);
      if(n>0){
        if(!micMuted&&!motorSuppressed){
          var buf=micCtx.createBuffer(1,n,SAMPLE_RATE);
          var f32=buf.getChannelData(0);
          var dv=new DataView(c.buffer,c.byteOffset,ub);
          for(var i=0;i<n;i++)f32[i]=dv.getInt16(i*2,true)/32768;
          var src=micCtx.createBufferSource();
          src.buffer=buf;src.connect(micCtx.destination);
          var t=Math.max(micAt,micCtx.currentTime+0.02);
          src.start(t);micAt=t+buf.duration;
        }else{micAt=Math.max(micAt,micCtx.currentTime)+n/SAMPLE_RATE;}
      }
      pump();
    }).catch(function(){});}
    pump();
  }).catch(function(e){console.error(e);});
}
function toggleMic(){
  if(!micCtx)initMic();
  micMuted=!micMuted;
  micBtn.textContent=micMuted?"MIC OFF":"MIC LIVE";
  micBtn.classList.toggle("on",!micMuted);
}

function toggleRec(){
  if(recOn){
    ni.value="";nameOv.classList.add("on");
    setTimeout(function(){ni.focus();},40);
  }else{
    post("/record/start","").then(function(r){return r.json();}).then(function(d){
      if(d.ok){recOn=true;recBtn.classList.add("on");
        recBtn.innerHTML="&#9632; STOP";rdot.classList.add("on");}
    });
  }
}
function saveRec(){
  var name=ni.value.trim()||"rec";
  nameOv.classList.remove("on");
  post("/record/stop","name="+encodeURIComponent(name))
    .then(function(r){return r.json();}).then(function(d){
      recOn=false;recBtn.classList.remove("on");
      recBtn.innerHTML="&#9679; REC";rdot.classList.remove("on");
      if(d.ok)alert("Saved: "+d.name);
    });
}
ni.addEventListener("keydown",function(e){
  e.stopPropagation();
  if(e.key==="Enter")saveRec();
  if(e.key==="Escape")nameOv.classList.remove("on");
});

var MK={w:"F",a:"L",s:"B",d:"R",q:"U",e:"D"};
var CK={arrowleft:"left",arrowright:"right",arrowup:"up",arrowdown:"down"};
document.addEventListener("keydown",function(e){
  var k=e.key.toLowerCase();
  if(held[k])return;held[k]=true;
  if(nameOv.classList.contains("on"))return;
  if(k===" "){e.preventDefault();toggleMic();}
  else if(k==="enter"){e.preventDefault();toggleRec();}
  else if(MK[k]){e.preventDefault();motor(MK[k]);}
  else if(CK[k]){e.preventDefault();cam(CK[k]);}
});
document.addEventListener("keyup",function(e){
  var k=e.key.toLowerCase();held[k]=false;
  if(MK[k]&&MK[k]!=="U"&&MK[k]!=="D")stopM();
});

document.querySelectorAll(".b[data-cmd]").forEach(function(b){
  var c=b.dataset.cmd;
  b.addEventListener("pointerdown",function(e){e.preventDefault();motor(c);});
  if(c!=="S"&&c!=="U"&&c!=="D"){
    b.addEventListener("pointerup",  function(e){e.preventDefault();stopM();});
    b.addEventListener("pointerleave",function(e){e.preventDefault();stopM();});
  }
});
document.querySelectorAll(".cb[data-a]").forEach(function(b){
  var a=b.dataset.a;
  b.addEventListener("pointerdown",function(e){e.preventDefault();cam(a);});
});


setInterval(function(){
  fetch("/sonar").then(function(r){return r.json();}).then(function(d){
    if(d.distance!==null){
      sonarEl.textContent="Sonar: "+d.distance+" cm";
      sonarEl.style.color=d.distance<30?"#f80":"#0f0";
      sonarEl.style.borderColor=d.distance<30?"#f80":"#0f0";
    }else{sonarEl.textContent="Sonar: --";}
  }).catch(function(){});
},400);
</script>
</body>
</html>"""

# ---------------------------------------------------------------------------
# HTTP handler
# ---------------------------------------------------------------------------
class Handler(BaseHTTPRequestHandler):
    def log_message(self,fmt,*a): pass

    def do_GET(self):
        p = urlparse(self.path).path

        if p == "/":
            self.send_response(200)
            self.send_header("Content-Type","text/html")
            self.send_header("Content-Length",str(len(PAGE)))
            self.end_headers()
            self.wfile.write(PAGE)

        elif p == "/stream":
            self.send_response(200)
            self.send_header("Content-Type",
                             "multipart/x-mixed-replace; boundary=frame")
            self.end_headers()
            try:
                while True:
                    with stream_lock: f = stream_frame
                    if f:
                        h=(b"--frame\r\nContent-Type: image/jpeg\r\nContent-Length: "
                           +str(len(f)).encode()+b"\r\n\r\n")
                        self.wfile.write(h+f+b"\r\n")
                    time.sleep(0.05)
            except Exception: pass

        elif p == "/audio":
            self.send_response(200)
            self.send_header("Content-Type","application/octet-stream")
            self.send_header("Cache-Control","no-cache")
            self.end_headers()
            dev = find_mic()
            print(f"[Mic] streaming from {dev}")
            proc = subprocess.Popen(
                ["arecord","-D",dev,"-f","S16_LE","-r",str(SAMPLE_RATE),"-c","1"],
                stdout=subprocess.PIPE, stderr=subprocess.DEVNULL)
            try:
                while True:
                    chunk = proc.stdout.read(2048)
                    if not chunk: break
                    self.wfile.write(chunk)
                    self.wfile.flush()
            except Exception: pass
            finally:
                try: proc.kill()
                except Exception: pass

        elif p == "/sonar":
            with sonar_lock: d = sonar_dist
            body = (f'{{"distance":{d}}}'.encode() if d is not None
                    else b'{"distance":null}')
            self.send_response(200)
            self.send_header("Content-Type","application/json")
            self.send_header("Content-Length",str(len(body)))
            self.end_headers()
            self.wfile.write(body)

        elif p in ("/recordings","/recordings/"):
            rows=""
            try:
                for n in sorted(os.listdir(RECORDINGS_DIR),reverse=True):
                    d=os.path.join(RECORDINGS_DIR,n)
                    if not os.path.isdir(d): continue
                    lk=" ".join(f'<a href="/recordings/{n}/{f}" download>{f}</a>'
                                for f in sorted(os.listdir(d)))
                    rows+=f"<tr><td>{n}</td><td>{lk}</td></tr>"
            except Exception as ex:
                rows=f"<tr><td colspan=2>{ex}</td></tr>"
            body=(b"<!DOCTYPE html><html><head><meta charset=utf-8>"
                  b"<title>Recordings</title>"
                  b"<style>body{background:#111;color:#fff;font-family:monospace;padding:20px}"
                  b"h1{color:#08f;margin-bottom:14px}"
                  b"table{border-collapse:collapse;width:100%}"
                  b"th{text-align:left;color:#555;padding:7px 10px;border-bottom:1px solid #333}"
                  b"td{padding:7px 10px;border-bottom:1px solid #222}"
                  b"a{color:#4af;margin-right:10px}"
                  b"</style></head><body>"
                  b"<h1>Recordings</h1>"
                  b"<table><tr><th>Name</th><th>Files</th></tr>"
                  +rows.encode()+
                  b"</table><br><a href='/'>Back</a></body></html>")
            self.send_response(200)
            self.send_header("Content-Type","text/html")
            self.send_header("Content-Length",str(len(body)))
            self.end_headers()
            self.wfile.write(body)

        elif p.startswith("/recordings/"):
            parts=p.strip("/").split("/")
            if len(parts)==3:
                fp=os.path.join(RECORDINGS_DIR,parts[1],parts[2])
                if os.path.isfile(fp):
                    with open(fp,"rb") as f: data=f.read()
                    ext=parts[2].rsplit(".",1)[-1].lower()
                    ct={"mp4":"video/mp4","wav":"audio/wav",
                        "mjpeg":"video/x-mjpeg"}.get(ext,"application/octet-stream")
                    self.send_response(200)
                    self.send_header("Content-Type",ct)
                    self.send_header("Content-Length",str(len(data)))
                    self.send_header("Content-Disposition",
                                     f'attachment; filename="{parts[2]}"')
                    self.end_headers()
                    self.wfile.write(data)
                    return
            self.send_response(404); self.end_headers()

        else:
            self.send_response(404); self.end_headers()

    def do_POST(self):
        p      = urlparse(self.path).path
        length = int(self.headers.get("Content-Length",0))
        params = parse_qs(self.rfile.read(length).decode())

        if p == "/motor":
            cmd=params.get("cmd",["S"])[0].strip().upper()
            if cmd in ("F","B","L","R","S","U","D"):
                send_motor(cmd)

        elif p == "/cam":
            a=params.get("action",[""])[0]
            # camera servo pan/tilt (no-op if servos not connected)
            pass

        elif p == "/record/start":
            ok=rec_start()
            body=json.dumps({"ok":ok}).encode()
            self.send_response(200)
            self.send_header("Content-Type","application/json")
            self.send_header("Content-Length",str(len(body)))
            self.end_headers()
            self.wfile.write(body)
            return

        elif p == "/record/stop":
            name=params.get("name",["rec"])[0]
            saved=rec_stop(name)
            body=json.dumps({"ok":saved is not None,"name":saved}).encode()
            self.send_response(200)
            self.send_header("Content-Type","application/json")
            self.send_header("Content-Length",str(len(body)))
            self.end_headers()
            self.wfile.write(body)
            return

        self.send_response(200)
        self.send_header("Content-Length","0")
        self.end_headers()


class ThreadedServer(ThreadingMixIn, HTTPServer):
    daemon_threads = True

# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------
if __name__ == "__main__":
    init_serial()
    threading.Thread(target=camera_loop,     daemon=True).start()
    threading.Thread(target=sonar_loop,      daemon=True).start()
    threading.Thread(target=serial_keepalive, daemon=True).start()
    server = ThreadedServer(("0.0.0.0", PORT), Handler)
    print(f"[Drive] http://0.0.0.0:{PORT}")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        send_motor("S")
        print("\n[Drive] stopped")
