import subprocess
import os
import speech_recognition as sr

recognizer = sr.Recognizer()
mic = sr.Microphone()

def listen():
    with mic as source:
        print("Listening... (speak now)")
        recognizer.adjust_for_ambient_noise(source, duration=0.5)
        try:
            audio = recognizer.listen(source, timeout=5, phrase_time_limit=10)
        except sr.WaitTimeoutError:
            return None
    try:
        text = recognizer.recognize_google(audio)
        return text
    except sr.UnknownValueError:
        return None
    except sr.RequestError:
        return None

def ask_bluefish(text):
    result = subprocess.run(
        ["ollama", "run", "bluefish", text],
        capture_output=True, text=True
    )
    return result.stdout.strip()

def speak(text):
    text = text.replace("Eamonn", "A-mun").replace("eamonn", "A-mun")
    os.system(f'echo "{text}" | piper --model /home/fussykitten12/piper_voices/en_US-ryan-medium.onnx --output_file /tmp/response.wav && sox /tmp/response.wav /tmp/response_loud.wav gain 10 && aplay -D bluealsa:DEV=71:A5:72:1E:F2:1A /tmp/response_loud.wav')

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
        else:
            print("Blue Fish: (no response)")
    else:
        print("Didn't catch that, try again.")
