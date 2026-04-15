import subprocess
import os
import whisper
import sounddevice as sd
import scipy.io.wavfile as wav
import numpy as np
import threading
import queue
import time

model = whisper.load_model("tiny")
history = []
is_speaking = False
text_queue = queue.Queue()

SAMPLERATE = 16000
CHUNK_SIZE = int(SAMPLERATE * 0.3)
SILENCE_THRESHOLD = 300
MIN_SPEECH_DURATION = 0.8
MAX_SPEECH_DURATION = 10

def listen_loop():
    while True:
        if is_speaking:
            time.sleep(0.1)
            continue

        chunk = sd.rec(CHUNK_SIZE, samplerate=SAMPLERATE, channels=1, dtype='int16')
        sd.wait()
        rms = np.sqrt(np.mean(chunk.astype(float)**2))

        if rms > SILENCE_THRESHOLD:
            audio_chunks = [chunk]
            silent_chunks = 0

            while True:
                if is_speaking:
                    break
                chunk = sd.rec(CHUNK_SIZE, samplerate=SAMPLERATE, channels=1, dtype='int16')
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
                result = model.transcribe('/tmp/input.wav', word_timestamps=True)
                text = result['text'].strip()
                no_speech_prob = result.get('no_speech_prob', 0)

                if not text or no_speech_prob > 0.5:
                    continue

                text_queue.put(text)

def ask_bluefish(text):
    if history:
        context = "Previous conversation:\n"
        for user_msg, bf_msg in history:
            context += f"Eamonn: {user_msg}\nBlue Fish: {bf_msg}\n"
        prompt = f"{context}\nNow respond to: {text}"
    else:
        prompt = text
    result = subprocess.run(
        ["ollama", "run", "bluefish", prompt],
        capture_output=True, text=True
    )
    return result.stdout.strip()

def speak(text):
    global is_speaking
    is_speaking = True
    text = text.replace("Eamonn", "A-mun").replace("eamonn", "A-mun")
    os.system(f'echo "{text}" | piper --model /home/fussykitten12/piper_voices/en_US-ryan-medium.onnx --sentence-silence 0.5 --output_file /tmp/response.wav && sox /tmp/response.wav -r 48000 -c 2 /tmp/response_final.wav gain -5 && aplay -D bluealsa:DEV=71:A5:72:1E:F2:1A /tmp/response_final.wav')
    is_speaking = False

listener = threading.Thread(target=listen_loop, daemon=True)
listener.start()

print("Blue Fish is ready! Listening...")
print("Press Ctrl+C to quit.")

while True:
    try:
        text = text_queue.get(timeout=1)
        print(f"You said: {text}")
        print("Blue Fish is thinking...")
        response = ask_bluefish(text)
        if response:
            print(f"Blue Fish: {response}")
            speak(response)
            history.append((text, response))
        else:
            print("Blue Fish: (no response)")
    except queue.Empty:
        continue
    except KeyboardInterrupt:
        print("\nBlue Fish signing off!")
        break
