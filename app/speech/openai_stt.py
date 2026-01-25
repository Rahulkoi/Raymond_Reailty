import io
import openai
import wave
import numpy as np
import os

openai.api_key = os.getenv("OPENAI_API_KEY")

SAMPLE_RATE = 16000


def pcm_to_wav_bytes(pcm_bytes: bytes) -> bytes:
    audio = np.frombuffer(pcm_bytes, dtype=np.int16)

    buffer = io.BytesIO()
    with wave.open(buffer, "wb") as wf:
        wf.setnchannels(1)
        wf.setsampwidth(2)
        wf.setframerate(SAMPLE_RATE)
        wf.writeframes(audio.tobytes())

    buffer.seek(0)
    return buffer.read()


def transcribe_pcm(pcm_bytes: bytes) -> str | None:
    if not pcm_bytes:
        return None

    wav_bytes = pcm_to_wav_bytes(pcm_bytes)

    response = openai.audio.transcriptions.create(
        file=io.BytesIO(wav_bytes),
        model="gpt-4o-transcribe",
    )

    return response.text.strip() if response.text else None
