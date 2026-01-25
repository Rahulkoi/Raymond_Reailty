import os
import requests

ELEVENLABS_API_KEY = os.getenv("ELEVENLABS_API_KEY")

def text_to_speech(text: str) -> bytes:
    url = "https://api.elevenlabs.io/v1/text-to-speech/EXAVITQu4vr4xnSDxMaL"

    headers = {
        "xi-api-key": ELEVENLABS_API_KEY,
        "Content-Type": "application/json"
    }

    payload = {
        "text": text,
        "voice_settings": {
            "stability": 0.5,
            "similarity_boost": 0.5
        }
    }

    response = requests.post(url, json=payload, headers=headers)

    if response.status_code != 200:
        raise RuntimeError(f"ElevenLabs error: {response.text}")

    return response.content
