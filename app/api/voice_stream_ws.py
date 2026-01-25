from fastapi import WebSocket, APIRouter
import numpy as np
import io
import wave
import json
import time
from openai import OpenAI

from app.conversation.manager import ConversationManager
from app.speech.tts import text_to_speech_bytes, text_to_speech_stream

router = APIRouter()
client = OpenAI()

SAMPLE_RATE = 16000

# PERFORMANCE: Use streaming TTS for faster first-byte response
USE_STREAMING_TTS = True

# Session storage for WebSocket connections
ws_sessions = {}

# Supported languages for STT (Whisper) - Indian regional + English
# Language codes: https://en.wikipedia.org/wiki/List_of_ISO_639-1_codes
SUPPORTED_LANGUAGES = {
    "en": "English",
    "hi": "Hindi",
    "ta": "Tamil",
    "te": "Telugu",
    "kn": "Kannada",
    "ml": "Malayalam",
    "bn": "Bengali",
    "mr": "Marathi",
    "gu": "Gujarati",
    "pa": "Punjabi",
    "ur": "Urdu"
}


@router.websocket("/ws/voice")
async def voice_ws(ws: WebSocket):
    await ws.accept()
    session_id = id(ws)
    pcm_buffer = []
    # Default to auto-detect (None), client can override
    selected_language = None

    # Get or create conversation manager for this session
    if session_id not in ws_sessions:
        ws_sessions[session_id] = {"cm": ConversationManager(), "language": None}
    session = ws_sessions[session_id]
    cm = session["cm"]
    selected_language = session.get("language")

    try:
        while True:
            message = await ws.receive()

            # Handle text messages (control signals)
            if "text" in message:
                text_data = message["text"]

                # Handle language selection from client
                # Format: {"type": "set_language", "language": "hi"}
                try:
                    msg_json = json.loads(text_data)
                    if msg_json.get("type") == "set_language":
                        lang_code = msg_json.get("language")
                        if lang_code in SUPPORTED_LANGUAGES or lang_code is None:
                            selected_language = lang_code
                            session["language"] = lang_code
                            lang_name = SUPPORTED_LANGUAGES.get(lang_code, "Auto-detect")
                            await ws.send_json({
                                "type": "language_set",
                                "language": lang_code,
                                "language_name": lang_name
                            })
                        else:
                            await ws.send_json({
                                "type": "error",
                                "message": f"Unsupported language: {lang_code}. Supported: {list(SUPPORTED_LANGUAGES.keys())}"
                            })
                        continue
                    # Handle get supported languages request
                    if msg_json.get("type") == "get_languages":
                        await ws.send_json({
                            "type": "supported_languages",
                            "languages": SUPPORTED_LANGUAGES,
                            "current": selected_language
                        })
                        continue
                except json.JSONDecodeError:
                    pass  # Not JSON, continue with normal flow

                # Client signals end of turn
                if text_data == "END":
                    if not pcm_buffer:
                        await ws.send_json({"type": "error", "message": "No audio received"})
                        continue

                    turn_start = time.time()

                    # Process complete utterance (STT + LLM)
                    response = await process_turn(pcm_buffer, cm, language=selected_language)
                    pcm_buffer.clear()

                    llm_done = time.time()
                    print(f"⚡ STT+LLM completed in {(llm_done - turn_start)*1000:.0f}ms")

                    # Send transcript with detected language
                    await ws.send_json({
                        "type": "transcript",
                        "text": response["user_text"],
                        "detected_language": response.get("detected_language")
                    })

                    # Send response text
                    await ws.send_json({
                        "type": "response",
                        "text": response["assistant_text"]
                    })

                    # Send property cards if available
                    if response.get("properties"):
                        print(f"📤 Sending {len(response['properties'])} property cards to client")
                        await ws.send_json({
                            "type": "properties",
                            "data": response["properties"]
                        })

                    # STREAMING TTS: Send audio chunks immediately as they arrive
                    if USE_STREAMING_TTS:
                        tts_start = time.time()
                        first_chunk_sent = False
                        total_bytes = 0

                        # Stream TTS chunks directly to client
                        for chunk in text_to_speech_stream(
                            response["assistant_text"],
                            language=response.get("detected_language")
                        ):
                            if not first_chunk_sent:
                                print(f"⚡ First audio chunk sent in {(time.time() - tts_start)*1000:.0f}ms")
                                first_chunk_sent = True
                            await ws.send_bytes(chunk)
                            total_bytes += len(chunk)

                        print(f"⚡ TTS stream complete: {total_bytes} bytes in {(time.time() - tts_start)*1000:.0f}ms")
                    else:
                        # Fallback: Non-streaming (buffer entire response)
                        audio_bytes = text_to_speech_bytes(
                            response["assistant_text"],
                            language=response.get("detected_language")
                        )
                        chunk_size = 8192
                        for i in range(0, len(audio_bytes), chunk_size):
                            chunk = audio_bytes[i:i + chunk_size]
                            await ws.send_bytes(chunk)

                    # Signal end of audio
                    await ws.send_json({"type": "audio_end"})

                    total_time = time.time() - turn_start
                    print(f"⚡ TOTAL turn time: {total_time*1000:.0f}ms")

                    # Check if conversation is ending
                    if response.get("conversation_ended"):
                        print("📤 Sending conversation_ended signal")
                        await ws.send_json({"type": "conversation_ended"})

                continue

            # Handle binary messages (audio data)
            if "bytes" in message:
                data = message["bytes"]
                pcm_f32 = np.frombuffer(data, dtype=np.float32)
                pcm_buffer.append(pcm_f32)

    except Exception as e:
        print(f"WebSocket error: {e}")
    finally:
        # Cleanup session on disconnect
        if session_id in ws_sessions:
            del ws_sessions[session_id]


async def process_turn(pcm_buffer: list, cm: ConversationManager, language: str = None) -> dict:
    """Process a complete voice turn: STT → LLM (TTS is handled separately for streaming)

    Args:
        pcm_buffer: List of audio chunks (float32)
        cm: ConversationManager instance
        language: Optional language code (None for auto-detect)
    """
    stt_start = time.time()

    # Merge all audio chunks
    audio_f32 = np.concatenate(pcm_buffer)

    # Convert Float32 → Int16
    audio_i16 = np.clip(audio_f32, -1.0, 1.0)
    audio_i16 = (audio_i16 * 32767).astype(np.int16)

    # Create WAV file in memory
    wav_io = io.BytesIO()
    with wave.open(wav_io, "wb") as wf:
        wf.setnchannels(1)
        wf.setsampwidth(2)
        wf.setframerate(SAMPLE_RATE)
        wf.writeframes(audio_i16.tobytes())

    wav_io.seek(0)
    wav_io.name = "audio.wav"

    # STT: Transcribe complete utterance
    # If language is specified, use it; otherwise let Whisper auto-detect
    stt_params = {
        "file": wav_io,
        "model": "whisper-1"
    }
    if language:
        stt_params["language"] = language

    transcript = client.audio.transcriptions.create(**stt_params)
    user_text = transcript.text.strip()

    stt_time = time.time() - stt_start
    print(f"⚡ STT completed in {stt_time*1000:.0f}ms")

    # Detect language from transcript if not specified
    detected_language = language or "auto"
    print(f"USER ({detected_language}): {user_text}")

    # Skip empty transcripts
    if not user_text:
        return {
            "user_text": "",
            "assistant_text": "I didn't catch that. Could you please repeat?",
            "detected_language": detected_language
        }

    # LLM: Generate response
    llm_start = time.time()
    result = cm.handle_user_input(user_text)
    assistant_text = result["text"]
    properties = result.get("properties", [])
    conversation_ended = result.get("conversation_ended", False)

    llm_time = time.time() - llm_start
    print(f"⚡ LLM completed in {llm_time*1000:.0f}ms")
    print(f"ASSISTANT: {assistant_text}")

    # NOTE: TTS is now handled separately in WebSocket handler for streaming
    return {
        "user_text": user_text,
        "assistant_text": assistant_text,
        "properties": properties,
        "conversation_ended": conversation_ended,
        "detected_language": detected_language
    }
