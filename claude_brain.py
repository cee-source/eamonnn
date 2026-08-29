#!/usr/bin/env python3
"""Blue Fish v2.2 - Claude AI brain
Install: pip install anthropic
Set on Pi: export ANTHROPIC_API_KEY="sk-ant-..."
"""

import os
import threading
import anthropic

MODEL = "claude-sonnet-5"

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
- Keep answers SHORT — 1 to 3 sentences maximum, because they will be spoken aloud
- Do not use bullet points, markdown, asterisks, or special characters
- Do not say things like "As an AI" or "I'm just a language model"
- If asked to do something physical (wave, walk, look left), say you will do it — the robot code handles the action separately
- Be helpful with homework, science questions, coding, and general knowledge
- If you don't know something, say so honestly and suggest where to find out"""

_client = None
_client_lock = threading.Lock()
_history = []
_history_lock = threading.Lock()
MAX_HISTORY = 20  # keep last 20 exchanges to avoid token buildup


def _get_client():
    global _client
    with _client_lock:
        if _client is None:
            api_key = os.environ.get("ANTHROPIC_API_KEY")
            if not api_key:
                raise RuntimeError(
                    "ANTHROPIC_API_KEY not set. "
                    "Add it to /etc/systemd/system/bluefish.service under [Service]:\n"
                    "Environment=ANTHROPIC_API_KEY=sk-ant-..."
                )
            _client = anthropic.Anthropic(api_key=api_key)
            print(f"[Brain] Claude client ready (model: {MODEL})")
    return _client


def ask(text: str, speaker_name: str = "Eamonn") -> str:
    """Send a message to Claude and get a spoken reply.

    Args:
        text: What the user said
        speaker_name: Who is speaking (from face recognition)

    Returns:
        Claude's reply as a plain string ready for TTS
    """
    client = _get_client()

    with _history_lock:
        _history.append({
            "role": "user",
            "content": f"{speaker_name} says: {text}"
        })
        # Trim history to avoid token buildup
        messages = _history[-MAX_HISTORY:]

    try:
        response = client.messages.create(
            model=MODEL,
            max_tokens=256,   # short for TTS
            system=SYSTEM_PROMPT,
            messages=messages,
            thinking={"type": "adaptive"},
        )

        reply = next(
            (block.text for block in response.content if block.type == "text"),
            "Sorry, I didn't get a response."
        )

        with _history_lock:
            _history.append({"role": "assistant", "content": reply})

        print(f"[Brain] {speaker_name}: {text!r} -> {reply!r}")
        return reply

    except anthropic.AuthenticationError:
        return "My API key is wrong. Please check the Anthropic API key."
    except anthropic.RateLimitError:
        return "I'm thinking too fast. Give me a second."
    except Exception as e:
        print(f"[Brain] Error: {e}")
        return "Sorry, my brain had an error. Try again."


def clear_history():
    """Wipe conversation history — useful when a new person starts talking."""
    with _history_lock:
        _history.clear()
    print("[Brain] Conversation history cleared")


def set_context(info: str):
    """Inject a system-level note into the conversation (e.g. sensor readings)."""
    with _history_lock:
        _history.append({
            "role": "user",
            "content": f"[SYSTEM NOTE] {info}"
        })
        _history.append({
            "role": "assistant",
            "content": "Understood."
        })
