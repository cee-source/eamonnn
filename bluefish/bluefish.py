import subprocess
import os
import re
import whisper
import sounddevice as sd
import scipy.io.wavfile as wav
import numpy as np
import threading
import queue
import time
import serial
import serial.tools.list_ports

model = whisper.load_model("tiny")
history = []
is_speaking = False
music_process = None
text_queue = queue.Queue()

SAMPLERATE = 44100
CHUNK_SIZE = int(SAMPLERATE * 0.3)
SILENCE_THRESHOLD = 500
MIN_SPEECH_DURATION = 0.8
MAX_SPEECH_DURATION = 10

# --- Arduino serial connection ---
def find_arduino():
    ports = serial.tools.list_ports.comports()
    for p in ports:
        if "Arduino" in p.description or "ttyACM" in p.device or "ttyUSB" in p.device:
            return p.device
    return None

arduino = None
arduino_port = find_arduino()
if arduino_port:
    try:
        arduino = serial.Serial(arduino_port, 115200, timeout=1)
        time.sleep(2)  # wait for Arduino to reset
        print(f"Arduino connected on {arduino_port}")
    except Exception as e:
        print(f"Arduino connection failed: {e}")
else:
    print("No Arduino found — running without motor control")

def send_to_arduino(cmd):
    if arduino and arduino.is_open:
        try:
            arduino.write((cmd + "\n").encode())
            arduino.readline()  # read OK response
        except Exception as e:
            print(f"Arduino send error: {e}")

# Map Ollama command tags to Arduino serial commands
COMMAND_MAP = {
    "FORWARD":      "F",
    "BACKWARD":     "B",
    "LEFT":         "L",
    "RIGHT":        "R",
    "STRAFE_LEFT":  "SL",
    "STRAFE_RIGHT": "SR",
    "FORK_UP":      "U",
    "FORK_DOWN":    "D",
    "STOP":         "S",
}

def extract_commands(text):
    """Pull [CMD] tags out of Ollama response, return (clean_text, [commands])."""
    tags = re.findall(r'\[([A-Z_]+)\]', text)
    clean = re.sub(r'\[[A-Z_]+\]', '', text).strip()
    cmds = [COMMAND_MAP[t] for t in tags if t in COMMAND_MAP]
    return clean, cmds

def execute_commands(cmds, duration=0.8):
    """Send each command to Arduino, pausing between them."""
    for cmd in cmds:
        send_to_arduino(cmd)
        time.sleep(duration)
    if cmds:
        send_to_arduino("S")  # stop after sequence

# --- Audio ---
def listen_loop():
    while True:
        if is_speaking:
            time.sleep(0.1)
            continue
        chunk = sd.rec(CHUNK_SIZE, samplerate=SAMPLERATE, channels=1, dtype='int16', device=2)
        sd.wait()
        rms = np.sqrt(np.mean(chunk.astype(float)**2))
        if rms > SILENCE_THRESHOLD:
            audio_chunks = [chunk]
            silent_chunks = 0
            while True:
                if is_speaking:
                    break
                chunk = sd.rec(CHUNK_SIZE, samplerate=SAMPLERATE, channels=1, dtype='int16', device=2)
                sd.wait()
                rms = np.sqrt(np.mean(chunk.astype(float)**2))
                audio_chunks.append(chunk)
                total_duration = len(audio_chunks) * 0.3
                if rms < SILENCE_THRESHOLD:
                    silent_chunks += 1
                    if silent_chunks >= 5 or total_duration >= MAX_SPEECH_DURATION:
                        break
                else:
                    silent_chunks = 0
            total_duration = len(audio_chunks) * 0.3
            if total_duration >= MIN_SPEECH_DURATION and not is_speaking:
                full_audio = np.concatenate(audio_chunks)
                wav.write('/tmp/input.wav', SAMPLERATE, full_audio)
                result = model.transcribe('/tmp/input.wav')
                text = result['text'].strip()
                no_speech_prob = result.get('no_speech_prob', 0)
                if not text or no_speech_prob > 0.5:
                    continue
                text_queue.put(text)

def play_music(query):
    global music_process
    stop_music()
    print(f"Searching for: {query}")
    music_process = subprocess.Popen(
        f'yt-dlp "ytsearch1:{query}" -o - -f bestaudio/best -q | ffmpeg -i pipe:0 -f pulse default',
        shell=True
    )

def stop_music():
    global music_process
    if music_process:
        music_process.terminate()
        music_process = None

SYSTEM_PROMPT = """You are Blue Fish, a helpful AI assistant living inside a robot.
You can move the robot by including movement commands in your response using these tags:
[FORWARD] [BACKWARD] [LEFT] [RIGHT] [STRAFE_LEFT] [STRAFE_RIGHT] [FORK_UP] [FORK_DOWN] [STOP]

Only include movement commands when the user's request clearly requires physical movement.
You can chain multiple commands: e.g. [FORWARD][FORK_UP]
Keep your spoken responses short and friendly."""

def ask_bluefish(text):
    if history:
        context = "Previous conversation:\n"
        for user_msg, bf_msg in history:
            context += f"Eamonn: {user_msg}\nBlue Fish: {bf_msg}\n"
        prompt = f"{SYSTEM_PROMPT}\n\n{context}\nEamonn: {text}\nBlue Fish:"
    else:
        prompt = f"{SYSTEM_PROMPT}\n\nEamonn: {text}\nBlue Fish:"

    result = subprocess.run(
        ["ollama", "run", "bluefish", prompt],
        capture_output=True, text=True
    )
    return result.stdout.strip()

def speak(text):
    global is_speaking
    is_speaking = True
    text = text.replace("Eamonn", "A-mun").replace("eamonn", "A-mun")
    os.system(f'echo "{text}" | piper --model /home/fussykitten12/piper_voices/en_US-ryan-medium.onnx --output_raw | aplay -r 22050 -f S16_LE -t raw -')
    time.sleep(1.5)
    is_speaking = False

listener = threading.Thread(target=listen_loop, daemon=True)
listener.start()

print("Blue Fish is ready! Listening...")
print("Press Ctrl+C to quit.")

while True:
    try:
        text = text_queue.get(timeout=1)
        print(f"You said: {text}")
        text_lower = text.lower()

        if text_lower.startswith("play "):
            query = text[5:].strip()
            speak(f"Playing {query}!")
            play_music(query)

        elif any(word in text_lower for word in ["stop music", "stop the music", "stop playing"]):
            stop_music()
            speak("Music stopped!")

        else:
            print("Blue Fish is thinking...")
            response = ask_bluefish(text)
            if response:
                clean_response, cmds = extract_commands(response)
                print(f"Blue Fish: {clean_response}")
                if cmds:
                    print(f"Movement: {cmds}")
                speak(clean_response)
                history.append((text, clean_response))
                # Run movement after speaking so Bluefish talks first then acts
                if cmds:
                    threading.Thread(target=execute_commands, args=(cmds,), daemon=True).start()
            else:
                print("Blue Fish: (no response)")

    except queue.Empty:
        continue
    except KeyboardInterrupt:
        stop_music()
        send_to_arduino("S")
        print("\nBlue Fish signing off!")
        break
