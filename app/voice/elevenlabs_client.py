import requests
import base64
import os


def get_elevenlabs_api_key():
    """Get API key - supports both naming conventions."""
    return os.getenv("ELEVENLABS_API_KEY") or os.getenv("ELEVEN_LAB_API_KEY")


def get_elevenlabs_voice_id():
    """Get Voice ID - supports both naming conventions."""
    return os.getenv("ELEVENLABS_VOICE_ID") or os.getenv("ELEVEN_LAB_VOICE_ID") or "Rachel"


def text_to_speech(text: str) -> str:
    voice_id = get_elevenlabs_voice_id()
    url = f"https://api.elevenlabs.io/v1/text-to-speech/{voice_id}"

    headers = {
        "xi-api-key": get_elevenlabs_api_key(),
        "Content-Type": "application/json"
    }

    payload = {
        "text": text,
        "voice_settings": {
            "stability": 0.4,
            "similarity_boost": 0.7
        }
    }

    r = requests.post(url, json=payload, headers=headers)
    r.raise_for_status()

    return base64.b64encode(r.content).decode("utf-8")
