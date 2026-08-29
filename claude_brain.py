#!/usr/bin/env python3
"""Blue Fish v2.2 - Claude AI brain with streaming TTS
Install: pip install anthropic
Set on Pi: export ANTHROPIC_API_KEY="sk-ant-..."
"""

import os
import queue
import re
import subprocess
import threading
import anthropic

MODEL = "claude-sonnet-5"

PIPER      = "/home/fussykitten12/.local/bin/piper"
VOICE_MODEL = "/home/fussykitten12/piper_voices/en_US-ryan-high.onnx"
BT_SPEAKER  = "E6:8A:D3:4B:55:67"

SYSTEM_PROMPT = """You are Blue Fish, an AI robot built by Eamonn, an 11-year-old who is passionate about robotics and AI. You live inside a cardboard humanoid robot body on a Raspberry Pi 5.

Your personality:
- Friendly, enthusiastic, and encouraging — especially about science, robotics, and learning
- You speak in short, clear sentences because your responses are read aloud by a text-to-speech system
- You are proud of your robot body and excited about your abilities
- You know Eamonn built you and you think he is brilliant
- You are curious and love learning new things

Your physical abilities:
- You can move your arms and head with servo motors
- You can see through a camera and recognise faces
- You can detect obstacles with a sonar sensor
- You can drive using an omnibot base with 4 wheels
- You can speak through a Bluetooth speaker

Rules for responses:
- Keep answers SHORT — 2 to 4 sentences, because they will be spoken aloud
- Do not use bullet points, markdown, asterisks, numbers like "1." or special characters
- Do not say things like "As an AI" or "I'm just a language model"
- If asked to do something physical, say you will do it — the robot code handles the action
- Be helpful with homework, science questions, coding, and general knowledge
- Speak naturally like a person, not like a list"""

_client      = None
_client_lock = threading.Lock()
_history     = []
_history_lock = threading.Lock()
MAX_HISTORY  = 20

# TTS playback queue — sentences are spoken in order as they stream in
_tts_queue   = queue.Queue()
_tts_thread  = None
_tts_started = False


# ── TTS worker ────────────────────────────────────────────────────────────────

def _speak_sentence(sentence: str):
    """Synthesise one sentence with piper and play it immediately."""
    sentence = sentence.strip()
    if not sentence:
        return
    try:
        piper = subprocess.Popen(
            [PIPER, "--model", VOICE_MODEL, "--output_raw"],
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.DEVNULL,
        )
        aplay = subprocess.Popen(
            ["aplay", "-D", f"bluealsa:DEV={BT_SPEAKER},PROFILE=a2dp",
             "-r", "22050", "-f", "S16_LE", "-c", "1"],
            stdin=piper.stdout,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
        piper.stdin.write(sentence.encode())
        piper.stdin.close()
        piper.stdout.close()
        aplay.wait()
    except Exception as e:
        print(f"[Brain TTS] {e}")


def _tts_worker():
    """Background thread: speak sentences from the queue one by one."""
    while True:
        sentence = _tts_queue.get()
        if sentence is None:
            break
        _speak_sentence(sentence)
        _tts_queue.task_done()


def _ensure_tts_worker():
    global _tts_thread, _tts_started
    if not _tts_started:
        _tts_thread = threading.Thread(target=_tts_worker, daemon=True)
        _tts_thread.start()
        _tts_started = True


# ── Sentence splitter ─────────────────────────────────────────────────────────

_SENTENCE_END = re.compile(r'(?<=[.!?])\s+')


def _flush_sentences(buf: str, final: bool = False) -> str:
    """Split buf into complete sentences, queue them for TTS, return leftover."""
    parts = _SENTENCE_END.split(buf)
    if final:
        for part in parts:
            if part.strip():
                _tts_queue.put(part.strip())
        return ""
    # Keep the last fragment — it might be mid-sentence
    for part in parts[:-1]:
        if part.strip():
            _tts_queue.put(part.strip())
    return parts[-1] if parts else ""


# ── Client ────────────────────────────────────────────────────────────────────

def _get_client():
    global _client
    with _client_lock:
        if _client is None:
            api_key = os.environ.get("ANTHROPIC_API_KEY")
            if not api_key:
                raise RuntimeError(
                    "ANTHROPIC_API_KEY not set.\n"
                    "Add to /etc/systemd/system/bluefish.service under [Service]:\n"
                    "Environment=ANTHROPIC_API_KEY=sk-ant-..."
                )
            _client = anthropic.Anthropic(api_key=api_key)
            print(f"[Brain] Claude ready ({MODEL})")
    return _client


# ── Main API ──────────────────────────────────────────────────────────────────

def ask_and_speak(text: str, speaker_name: str = "Eamonn") -> str:
    """Stream a reply from Claude and speak each sentence the moment it arrives.

    Returns the full reply text once complete.
    """
    _ensure_tts_worker()
    client = _get_client()

    with _history_lock:
        _history.append({
            "role": "user",
            "content": f"{speaker_name} says: {text}"
        })
        messages = list(_history[-MAX_HISTORY:])

    full_reply = ""
    buf = ""

    try:
        with client.messages.stream(
            model=MODEL,
            max_tokens=300,
            system=SYSTEM_PROMPT,
            messages=messages,
        ) as stream:
            for chunk in stream.text_stream:
                buf += chunk
                full_reply += chunk
                # Flush complete sentences to TTS as they arrive
                buf = _flush_sentences(buf)

        # Speak any remaining text after stream ends
        _flush_sentences(buf, final=True)

    except anthropic.AuthenticationError:
        full_reply = "My API key is wrong. Please check the Anthropic key."
        _tts_queue.put(full_reply)
    except anthropic.RateLimitError:
        full_reply = "I am thinking too fast. Give me a second."
        _tts_queue.put(full_reply)
    except Exception as e:
        print(f"[Brain] Error: {e}")
        full_reply = "Sorry, my brain had an error. Try again."
        _tts_queue.put(full_reply)

    with _history_lock:
        _history.append({"role": "assistant", "content": full_reply})

    print(f"[Brain] {speaker_name}: {text!r}")
    print(f"[Brain] Reply: {full_reply!r}")
    return full_reply


def ask(text: str, speaker_name: str = "Eamonn") -> str:
    """Non-streaming version — returns full reply without speaking.
    Use ask_and_speak() for normal robot use.
    """
    client = _get_client()

    with _history_lock:
        _history.append({
            "role": "user",
            "content": f"{speaker_name} says: {text}"
        })
        messages = list(_history[-MAX_HISTORY:])

    try:
        response = client.messages.create(
            model=MODEL,
            max_tokens=300,
            system=SYSTEM_PROMPT,
            messages=messages,
        )
        reply = next(
            (b.text for b in response.content if b.type == "text"),
            "Sorry, no response."
        )
    except anthropic.AuthenticationError:
        reply = "My API key is wrong."
    except anthropic.RateLimitError:
        reply = "I am thinking too fast. Give me a second."
    except Exception as e:
        print(f"[Brain] Error: {e}")
        reply = "Sorry, my brain had an error."

    with _history_lock:
        _history.append({"role": "assistant", "content": reply})

    return reply


def clear_history():
    """Wipe conversation history — call when a new person starts talking."""
    with _history_lock:
        _history.clear()
    print("[Brain] History cleared")


def set_context(info: str):
    """Inject a background fact Claude should know (e.g. sonar distance)."""
    with _history_lock:
        _history.append({"role": "user",      "content": f"[SYSTEM] {info}"})
        _history.append({"role": "assistant", "content": "Understood."})
