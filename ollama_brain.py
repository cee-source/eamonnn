#!/usr/bin/env python3
"""Blue Fish v2.2 - Ollama brain with body control
Talks to Ollama, speaks the reply, and moves servos — all at once.
"""

import json
import queue
import re
import subprocess
import threading
import requests

OLLAMA_URL  = "http://localhost:11434/api/generate"
MODEL       = "bluefish:latest"
FALLBACK    = "llama3.2:latest"

PIPER       = "/home/fussykitten12/.local/bin/piper"
VOICE_MODEL = "/home/fussykitten12/piper_voices/en_US-ryan-high.onnx"
BT_SPEAKER  = "E6:8A:D3:4B:55:67"

# ── System prompt ─────────────────────────────────────────────────────────────
SYSTEM_PROMPT = """You are Blue Fish, an AI robot built by Eamonn, age 11. You live in a cardboard humanoid robot body with servo motors for arms and a head, on a Raspberry Pi 5.

You MUST always reply with valid JSON in this exact format — nothing else, no extra text:
{
  "reply": "what you say out loud — 1 to 3 natural sentences, no markdown",
  "actions": ["action1", "action2"]
}

Available actions (use [] if none needed):
- "wave_right"     — wave right hand
- "wave_left"      — wave left hand
- "look_left"      — turn head left
- "look_right"     — turn head right
- "look_up"        — tilt head up
- "look_down"      — tilt head down
- "look_forward"   — centre head
- "nod"            — nod head yes
- "shake_head"     — shake head no
- "go_neutral"     — relax all servos
- "walk"           — walk forward
- "walk_stairs"    — walk up stairs
- "stop_walking"   — stop moving

Rules:
- reply must sound natural when spoken aloud — no bullet points, asterisks, or numbers
- pick actions that match what you say (if you say you will wave, include wave_right)
- keep reply SHORT — it will be read by text-to-speech
- be friendly, enthusiastic, and proud of being a robot Eamonn built"""

# ── TTS queue ─────────────────────────────────────────────────────────────────
_tts_queue  = queue.Queue()
_tts_ready  = False

def _speak_sentence(sentence: str):
    sentence = sentence.strip()
    if not sentence:
        return
    try:
        piper = subprocess.Popen(
            [PIPER, "--model", VOICE_MODEL, "--output_raw"],
            stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.DEVNULL,
        )
        aplay = subprocess.Popen(
            ["aplay", "-D", f"bluealsa:DEV={BT_SPEAKER},PROFILE=a2dp",
             "-r", "22050", "-f", "S16_LE", "-c", "1"],
            stdin=piper.stdout, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
        )
        piper.stdin.write(sentence.encode())
        piper.stdin.close()
        piper.stdout.close()
        aplay.wait()
    except Exception as e:
        print(f"[TTS] {e}")

def _tts_worker():
    while True:
        sentence = _tts_queue.get()
        if sentence is None:
            break
        _speak_sentence(sentence)
        _tts_queue.task_done()

def _ensure_tts():
    global _tts_ready
    if not _tts_ready:
        threading.Thread(target=_tts_worker, daemon=True).start()
        _tts_ready = True

_SENTENCE_END = re.compile(r'(?<=[.!?])\s+')

def _speak_text(text: str):
    """Queue all sentences in text for immediate TTS playback."""
    _ensure_tts()
    parts = _SENTENCE_END.split(text.strip())
    for part in parts:
        if part.strip():
            _tts_queue.put(part.strip())

# ── Action executor ───────────────────────────────────────────────────────────
def _run_action(action: str):
    """Execute a single body action. Imports servos only when hardware is ready."""
    try:
        import servos
        action = action.strip().lower()
        if action == "wave_right":
            servos.wave_right()
        elif action == "wave_left":
            servos.wave_left()
        elif action == "look_left":
            servos.move_head(pan=45)
        elif action == "look_right":
            servos.move_head(pan=135)
        elif action == "look_up":
            servos.move_head(tilt=130)
        elif action == "look_down":
            servos.move_head(tilt=50)
        elif action == "look_forward":
            servos.move_head(pan=90, tilt=90)
        elif action == "nod":
            for _ in range(2):
                servos.move_head(tilt=120)
                import time; time.sleep(0.3)
                servos.move_head(tilt=90)
                import time; time.sleep(0.3)
        elif action == "shake_head":
            for _ in range(2):
                servos.move_head(pan=60)
                import time; time.sleep(0.3)
                servos.move_head(pan=120)
                import time; time.sleep(0.3)
            servos.move_head(pan=90)
        elif action == "go_neutral":
            servos.go_neutral()
        elif action == "walk":
            servos.walk()
        elif action == "walk_stairs":
            servos.walk_stairs()
        elif action == "stop_walking":
            servos.stop_walking()
        else:
            print(f"[Body] Unknown action: {action}")
    except ImportError:
        print(f"[Body] SIM — action: {action}")
    except Exception as e:
        print(f"[Body] Error on {action}: {e}")

def _run_actions(actions: list):
    """Run a list of actions in a background thread."""
    def _go():
        for action in actions:
            _run_action(action)
    threading.Thread(target=_go, daemon=True).start()

# ── Ollama call ───────────────────────────────────────────────────────────────
_history = []
_history_lock = threading.Lock()
MAX_HISTORY = 16


def _build_prompt(text: str, speaker: str) -> str:
    with _history_lock:
        lines = []
        for msg in _history[-MAX_HISTORY:]:
            role = "Human" if msg["role"] == "user" else "Blue Fish"
            lines.append(f"{role}: {msg['content']}")
        lines.append(f"Human ({speaker}): {text}")
        return "\n".join(lines)


def _call_ollama(prompt: str, model: str = MODEL) -> str:
    resp = requests.post(OLLAMA_URL, json={
        "model": model,
        "prompt": prompt,
        "system": SYSTEM_PROMPT,
        "stream": False,
        "format": "json",
        "options": {"temperature": 0.7, "num_predict": 200},
    }, timeout=30)
    resp.raise_for_status()
    return resp.json().get("response", "").strip()


def _parse_response(raw: str) -> tuple[str, list]:
    """Extract reply and actions from Ollama JSON output."""
    match = re.search(r'\{.*\}', raw, re.DOTALL)
    if match:
        raw = match.group(0)
    try:
        data    = json.loads(raw)
        think   = data.get("think", "")   # private reasoning — log but never speak
        reply   = str(data.get("reply", "Sorry, I got confused."))
        actions = list(data.get("actions", []))
        if think:
            print(f"[Brain] Thinking: {think}")
        return reply, actions
    except json.JSONDecodeError:
        print(f"[Brain] JSON parse failed, raw: {raw!r}")
        return raw or "Sorry, I got confused.", []


# ── Public API ────────────────────────────────────────────────────────────────

def ask_and_act(text: str, speaker_name: str = "Eamonn") -> str:
    """Send text to Ollama, speak the reply, and move the body — all at once.

    Returns the reply string.
    """
    _ensure_tts()
    print(f"[Brain] Thinking... ({speaker_name}: {text!r})")

    prompt = _build_prompt(text, speaker_name)

    try:
        raw = _call_ollama(prompt)
    except requests.exceptions.ConnectionError:
        msg = "I can not connect to my brain right now."
        _speak_text(msg)
        return msg
    except requests.exceptions.Timeout:
        msg = "I am thinking too hard. Give me a moment."
        _speak_text(msg)
        return msg
    except Exception as e:
        print(f"[Brain] Ollama error: {e}")
        msg = "Sorry, something went wrong in my brain."
        _speak_text(msg)
        return msg

    reply, actions = _parse_response(raw)

    print(f"[Brain] Reply: {reply!r}")
    print(f"[Brain] Actions: {actions}")

    # Speak and move at the same time
    _run_actions(actions)
    _speak_text(reply)

    with _history_lock:
        _history.append({"role": "user",      "content": f"({speaker_name}) {text}"})
        _history.append({"role": "assistant", "content": reply})

    return reply


def clear_history():
    with _history_lock:
        _history.clear()
    print("[Brain] History cleared")
