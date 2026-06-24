#!/usr/bin/env python3
"""Browser-based face enrollment for Blue Fish.
Run this on the Pi, then open http://192.168.0.113:8080 to enroll Eamonn's face."""

import os, sys, time, pickle, threading, subprocess
import numpy as np
from http.server import HTTPServer, BaseHTTPRequestHandler
from socketserver import ThreadingMixIn

FACE_PROFILE = "/home/fussykitten12/face_profile.pkl"
SAMPLES_NEEDED = 10

import cv2
import face_recognition

# Shared state
latest_jpeg   = b""
jpeg_lock     = threading.Lock()
encodings     = []
enc_lock      = threading.Lock()
done          = False

def capture_loop():
    global latest_jpeg, done
    cmd = [
        "rpicam-vid", "-t", "0",
        "--width", "640", "--height", "480",
        "--framerate", "10",
        "--codec", "mjpeg",
        "--inline", "-o", "-"
    ]
    proc = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.DEVNULL, bufsize=0)
    buf = b""
    frame_count = 0
    while not done:
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

            with enc_lock:
                count = len(encodings)

            # Overlay progress
            label = f"Samples: {count}/{SAMPLES_NEEDED}"
            if count >= SAMPLES_NEEDED:
                label = "DONE! Enrolled."
            cv2.putText(frame, label, (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 1.0, (0, 255, 0), 2)

            _, jbuf = cv2.imencode(".jpg", frame, [cv2.IMWRITE_JPEG_QUALITY, 75])
            with jpeg_lock:
                latest_jpeg = jbuf.tobytes()

            # Sample a face every 10 frames
            frame_count += 1
            if frame_count % 10 == 0 and count < SAMPLES_NEEDED:
                threading.Thread(target=sample_face, args=(frame.copy(),), daemon=True).start()

    proc.kill()

def sample_face(frame):
    global done
    rgb  = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
    locs = face_recognition.face_locations(rgb, number_of_times_to_upsample=2, model="hog")
    if not locs:
        return
    encs = face_recognition.face_encodings(rgb, locs)
    if not encs:
        return
    with enc_lock:
        encodings.append(encs[0])
        count = len(encodings)
        print(f"Sample {count}/{SAMPLES_NEEDED}")
        if count >= SAMPLES_NEEDED:
            avg = np.mean(encodings, axis=0)
            with open(FACE_PROFILE, "wb") as f:
                pickle.dump(avg, f)
            print(f"Done! Face enrolled to {FACE_PROFILE}")
            done = True

class Handler(BaseHTTPRequestHandler):
    def log_message(self, fmt, *args):
        pass

    def do_GET(self):
        if self.path == "/frame":
            with jpeg_lock:
                data = latest_jpeg
            self.send_response(200)
            self.send_header("Content-Type", "image/jpeg")
            self.send_header("Content-Length", str(len(data)))
            self.send_header("Cache-Control", "no-cache")
            self.end_headers()
            self.wfile.write(data)
        else:
            html = """<!DOCTYPE html>
<html><head><title>Blue Fish Enrollment</title>
<style>body{background:#111;color:#0f0;font-family:monospace;text-align:center;}
img{max-width:100%;border:2px solid #0f0;}</style>
<meta http-equiv="refresh" content="0.2">
</head><body>
<h2>Face Enrollment - Look at the camera!</h2>
<img src="/frame">
</body></html>"""
            self.send_response(200)
            self.send_header("Content-Type", "text/html")
            self.end_headers()
            self.wfile.write(html.encode())

class ThreadedServer(ThreadingMixIn, HTTPServer):
    daemon_threads = True

if __name__ == "__main__":
    print("Starting face enrollment. Open http://192.168.0.113:8080 in a browser.")
    t = threading.Thread(target=capture_loop, daemon=True)
    t.start()
    server = ThreadedServer(("0.0.0.0", 8080), Handler)
    print("HTTP server on port 8080")
    while not done:
        server.handle_request()
    print("Enrollment complete!")
