import subprocess
import os
from duckduckgo_search import DDGS

DIRECTION_KEYWORDS = ["directions to", "how to get to", "navigate to", "route to", "drive to", "walk to"]

def is_directions_query(text):
    text_lower = text.lower()
    return any(keyword in text_lower for keyword in DIRECTION_KEYWORDS)

def search_web(query):
    try:
        with DDGS() as ddgs:
            results = ddgs.text(query, max_results=5)
            # Filter out Reddit
            filtered = [r for r in results if "reddit.com" not in r.get("href", "")]
            if not filtered:
                return None
            # Build a summary of results
            summary = ""
            for r in filtered[:3]:
                summary += f"- {r['title']}: {r['body']}\n"
            return summary
    except Exception:
        return None

def ask_bluefish(text, search_results=None):
    if search_results:
        prompt = f"Here are some real facts from the web to help you answer:\n{search_results}\nNow answer this question using only the above facts, do not add anything extra: {text}"
    else:
        prompt = text
    result = subprocess.run(
        ["ollama", "run", "bluefish", prompt],
        capture_output=True, text=True
    )
    return result.stdout.strip()

def speak(text):
    text = text.replace("Eamonn", "A-mun").replace("eamonn", "A-mun")
    os.system('aplay -D bluealsa /tmp/silence.wav 2>/dev/null')
    os.system(f'echo "{text}" | piper --model /home/fussykitten12/piper_voices/en_US-lessac-medium.onnx --output_file /tmp/response.wav && sox /tmp/response.wav /tmp/response_loud.wav gain 10 && aplay -D bluealsa /tmp/response_loud.wav')

print("Blue Fish is ready! Type your message and press Enter.")
print("Type 'quit' to exit.")

while True:
    user_input = input("\nYou: ")
    if user_input.lower() == 'quit':
        break
    print("Blue Fish is thinking...")

    if is_directions_query(user_input):
        search_results = None
    else:
        print("Blue Fish is searching the web...")
        search_results = search_web(user_input)

    response = ask_bluefish(user_input, search_results)
    print(f"Blue Fish: {response}")
    speak(response)
