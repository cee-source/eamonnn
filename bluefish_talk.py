import subprocess
import os
import whisper
import sounddevice as sd
import scipy.io.wavfile as wav

model = whisper.load_model("tiny")
history = []

def listen():
    print("Listening... (speak now)")
    samplerate = 16000
    audio = sd.rec(int(5 * samplerate), samplerate=samplerate, channels=1, dtype='int16')
    sd.wait()
    wav.write('/tmp/input.wav', samplerate, audio)
    result = model.transcribe('/tmp/input.wav')
    text = result['text'].strip()
    return text if text else None

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
    text = text.replace("Eamonn", "A-mun").replace("eamonn", "A-mun")
    os.system(f'echo "{text}" | piper --model /home/fussykitten12/piper_voices/en_US-ryan-medium.onnx --sentence-silence 0.5 --output_file /tmp/response.wav && sox /tmp/response.wav -r 48000 -c 2 /tmp/response_final.wav gain -5 && aplay -D bluealsa:DEV=71:A5:72:1E:F2:1A /tmp/response_final.wav')

print("Blue Fish is ready!")
print("Press Enter to talk, type 'quit' to exit.")

while True:
    user_input = input("\nPress Enter to talk: ")
    if user_input.lower() == 'quit':
        break
    text = listen()
    if text:
        print(f"You said: {text}")
        print("Blue Fish is thinking...")
        response = ask_bluefish(text)
        if response:
            print(f"Blue Fish: {response}")
            speak(response)
            history.append((text, response))
        else:
            print("Blue Fish: (no response)")
    else:
        print("Didn't catch that, try again.")
