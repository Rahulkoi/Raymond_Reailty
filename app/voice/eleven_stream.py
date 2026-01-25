import os
import requests

ELEVENLABS_API_KEY = os.getenv("ELEVENLABS_API_KEY")
VOICE_ID = os.getenv("ELEVENLABS_VOICE_ID")

def elevenlabs_stream(text: str):
    url = f"https://api.elevenlabs.io/v1/text-to-speech/{VOICE_ID}/stream?output_format=mp3_44100"

    headers = {
        "xi-api-key": ELEVENLABS_API_KEY,
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


