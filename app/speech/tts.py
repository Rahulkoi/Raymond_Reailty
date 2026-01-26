import os
import uuid
import time
from typing import Generator
from elevenlabs.client import ElevenLabs
from elevenlabs import VoiceSettings


def get_elevenlabs_api_key():
    """Get API key - supports both naming conventions."""
    return os.getenv("ELEVENLABS_API_KEY") or os.getenv("ELEVEN_LAB_API_KEY")


def get_elevenlabs_voice_id():
    """Get Voice ID - supports both naming conventions."""
    return os.getenv("ELEVENLABS_VOICE_ID") or os.getenv("ELEVEN_LAB_VOICE_ID") or "Rachel"


def get_client():
    """Get ElevenLabs client - creates at runtime to ensure env vars are loaded."""
    return ElevenLabs(api_key=get_elevenlabs_api_key())


AUDIO_DIR = "static/audio"
os.makedirs(AUDIO_DIR, exist_ok=True)

# Voice configuration from environment
VOICE_ID = None  # Will be set at runtime

# PERFORMANCE: Use turbo model for English (2-3x faster), multilingual for other languages
# Options: eleven_turbo_v2_5 (fastest), eleven_turbo_v2, eleven_multilingual_v2
MODEL_ID = os.getenv("ELEVENLABS_MODEL", "eleven_turbo_v2_5")

# PERFORMANCE: Slightly faster speech sounds more natural and reduces total audio duration
VOICE_SPEED = float(os.getenv("ELEVENLABS_SPEED", "1.1"))

VOICE_STABILITY = float(os.getenv("ELEVENLABS_STABILITY", "0.5"))
VOICE_SIMILARITY = float(os.getenv("ELEVENLABS_SIMILARITY", "0.75"))

# Latency optimization: 0=off, 4=maximum (trades quality for speed)
# PERFORMANCE: Set to 4 for fastest first-byte response
OPTIMIZE_LATENCY = int(os.getenv("ELEVENLABS_OPTIMIZE_LATENCY", "4"))


def _get_voice_settings() -> VoiceSettings:
    """Get voice settings for natural-sounding speech."""
    return VoiceSettings(
        stability=VOICE_STABILITY,
        similarity_boost=VOICE_SIMILARITY,
        style=0.0,
        use_speaker_boost=True,
        speed=VOICE_SPEED
    )


def text_to_speech(text: str, language: str = None) -> str:
    """Convert text to speech and return URL path to audio file.

    Args:
        text: Text to convert to speech
        language: Optional language code (e.g., 'hi' for Hindi, 'ta' for Tamil)
    """
    client = get_client()
    voice_id = get_elevenlabs_voice_id()

    audio = client.text_to_speech.convert(
        voice_id=voice_id,
        model_id=MODEL_ID,
        text=text,
        voice_settings=_get_voice_settings(),
        optimize_streaming_latency=OPTIMIZE_LATENCY
    )
    audio_bytes = b"".join(audio)

    filename = f"{uuid.uuid4()}.mp3"
    filepath = os.path.join(AUDIO_DIR, filename)

    with open(filepath, "wb") as f:
        f.write(audio_bytes)

    return f"/static/audio/{filename}"


def text_to_speech_bytes(text: str, language: str = None) -> bytes:
    """Convert text to speech and return raw audio bytes (for WebSocket streaming).

    Args:
        text: Text to convert to speech
        language: Optional language code (e.g., 'hi' for Hindi, 'ta' for Tamil)
    """
    start = time.time()
    client = get_client()
    voice_id = get_elevenlabs_voice_id()

    # Use multilingual model for non-English to preserve accent quality
    model = MODEL_ID
    if language and language not in ('en', 'auto', None):
        model = "eleven_multilingual_v2"

    audio = client.text_to_speech.convert(
        voice_id=voice_id,
        model_id=model,
        text=text,
        voice_settings=_get_voice_settings(),
        optimize_streaming_latency=OPTIMIZE_LATENCY
    )
    result = b"".join(audio)

    print(f"⚡ TTS completed in {(time.time() - start)*1000:.0f}ms ({len(result)} bytes)")
    return result


def text_to_speech_stream(text: str, language: str = None) -> Generator[bytes, None, None]:
    """STREAMING: Convert text to speech and yield audio chunks as they arrive.

    This enables the client to start playing audio immediately without waiting
    for the complete TTS response. Critical for reducing perceived latency.

    Args:
        text: Text to convert to speech
        language: Optional language code
    Yields:
        Audio chunks as they arrive from ElevenLabs
    """
    start = time.time()
    first_chunk_time = None
    total_bytes = 0
    client = get_client()
    voice_id = get_elevenlabs_voice_id()

    # Use multilingual model for non-English
    model = MODEL_ID
    if language and language not in ('en', 'auto', None):
        model = "eleven_multilingual_v2"

    # Get streaming generator from ElevenLabs
    audio_stream = client.text_to_speech.convert(
        voice_id=voice_id,
        model_id=model,
        text=text,
        voice_settings=_get_voice_settings(),
        optimize_streaming_latency=OPTIMIZE_LATENCY
    )

    # Yield chunks as they arrive
    for chunk in audio_stream:
        if first_chunk_time is None:
            first_chunk_time = time.time()
            print(f"⚡ TTS first chunk in {(first_chunk_time - start)*1000:.0f}ms")

        total_bytes += len(chunk)
        yield chunk

    total_time = time.time() - start
    print(f"⚡ TTS stream complete in {total_time*1000:.0f}ms ({total_bytes} bytes)")
