import subprocess
import os

def ask_bluefish(text):
    result = subprocess.run(
        ["ollama", "run", "bluefish", text],
        capture_output=True, text=True
    )
    return result.stdout.strip()

def speak(text):
    text = text.replace("Eamonn", "A-mun").replace("eamonn", "A-mun")
    os.system(f'echo "{text}" | piper --model /home/fussykitten12/piper_voices/en_US-ryan-medium.onnx --output_file /tmp/response.wav && sox /tmp/response.wav /tmp/response_loud.wav gain 10 && aplay -D bluealsa:DEV=71:A5:72:1E:F2:1A /tmp/response_loud.wav')

print("Blue Fish is ready! Type your message and press Enter.")
print("Type 'quit' to exit.")

while True:
    user_input = input("\nYou: ")
    if user_input.lower() == 'quit':
        break
    print("Blue Fish is thinking...")
    response = ask_bluefish(user_input)
    print(f"Blue Fish: {response}")
    speak(response)
