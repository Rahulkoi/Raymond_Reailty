import os
import requests


def get_elevenlabs_api_key():
    """Get API key - supports both naming conventions."""
    return os.getenv("ELEVENLABS_API_KEY") or os.getenv("ELEVEN_LAB_API_KEY")


def get_elevenlabs_voice_id():
    """Get Voice ID - supports both naming conventions."""
    return os.getenv("ELEVENLABS_VOICE_ID") or os.getenv("ELEVEN_LAB_VOICE_ID") or "Rachel"


def elevenlabs_stream(text: str):
    voice_id = get_elevenlabs_voice_id()
    url = f"https://api.elevenlabs.io/v1/text-to-speech/{voice_id}/stream?output_format=mp3_44100"

    headers = {
        "xi-api-key": get_elevenlabs_api_key(),
        "Content-Type": "application/json"
    }

    payload = {
        "text": text,
        "model_id": "eleven_monolingual_v1"
    }

    response = requests.post(url, headers=headers, json=payload, stream=True)
    response.raise_for_status()

    for chunk in response.iter_content(chunk_size=4096):
        if chunk:
            yield chunk


