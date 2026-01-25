import openai
import os
import uuid

openai.api_key = os.getenv("OPENAI_API_KEY")

UPLOAD_DIR = "static/uploads"
os.makedirs(UPLOAD_DIR, exist_ok=True)

def speech_to_text(audio_bytes: bytes) -> str:
    filename = f"{uuid.uuid4()}.wav"
    path = os.path.join(UPLOAD_DIR, filename)

    with open(path, "wb") as f:
        f.write(audio_bytes)

    with open(path, "rb") as audio_file:
        transcript = openai.audio.transcriptions.create(
            file=audio_file,
            model="whisper-1"
        )

    return transcript.text
