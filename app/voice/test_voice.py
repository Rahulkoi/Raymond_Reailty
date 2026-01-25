from fastapi import APIRouter, Response
from app.voice.elevenlabs import text_to_speech

router = APIRouter()

@router.post("/chat-voice")
def chat_to_voice(payload: dict):
    text = payload.get("message", "Hello")
    audio = text_to_speech(text)
    return Response(content=audio, media_type="audio/mpeg")
