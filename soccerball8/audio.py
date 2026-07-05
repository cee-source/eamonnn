"""Captures a spoken question from the USB microphone and transcribes it.

Transcription uses Google's free Web Speech API via the `speech_recognition`
package - the heavy lifting happens in the cloud, which matters on a Pi Zero
that has nowhere near enough CPU for a local speech model.
"""

from typing import Optional

import speech_recognition as sr


def listen_for_question(
    mic_device_index: Optional[int] = None,
    phrase_time_limit: float = 8.0,
    ambient_duration: float = 0.6,
) -> Optional[str]:
    """Records one phrase from the mic and returns the transcribed text, or
    None if nothing intelligible was heard."""
    recognizer = sr.Recognizer()
    microphone = sr.Microphone(device_index=mic_device_index)

    with microphone as source:
        recognizer.adjust_for_ambient_noise(source, duration=ambient_duration)
        audio = recognizer.listen(source, phrase_time_limit=phrase_time_limit)

    try:
        return recognizer.recognize_google(audio)
    except sr.UnknownValueError:
        return None
    except sr.RequestError as exc:
        raise RuntimeError(f"Speech recognition service error: {exc}") from exc


def list_microphones() -> list:
    """Handy for finding MIC_DEVICE_INDEX - run `python -m soccerball8.audio`."""
    return sr.Microphone.list_microphone_names()


if __name__ == "__main__":
    for index, name in enumerate(list_microphones()):
        print(f"{index}: {name}")
