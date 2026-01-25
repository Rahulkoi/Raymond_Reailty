import tempfile
from openai import OpenAI

client = OpenAI()

def speech_to_text(audio_bytes: bytes) -> str:
    """
    Converts microphone audio bytes to text using OpenAI Whisper
    """
    with tempfile.NamedTemporaryFile(suffix=".webm", delete=True) as f:
        f.write(audio_bytes)
        f.flush()

        transcript = client.audio.transcriptions.create(
            file=open(f.name, "rb"),
            model="whisper-1"
        )

        return transcript.text.strip()
