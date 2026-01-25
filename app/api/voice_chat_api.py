from fastapi import APIRouter, UploadFile, File
from app.speech.stt import speech_to_text
from app.conversation.manager import ConversationManager
from app.speech.tts import text_to_speech

router = APIRouter(prefix="/voice-chat", tags=["Voice Chat"])

sessions = {}

@router.post("/")
async def voice_chat(
    audio: UploadFile = File(...),
    session_id: str = "default"
):
    audio_bytes = await audio.read()

    user_text = speech_to_text(audio_bytes)

    if session_id not in sessions:
        sessions[session_id] = ConversationManager()

    cm = sessions[session_id]
    result = cm.handle_user_input(user_text)

    audio_url = text_to_speech(result["text"])

    return {
        "user_text": user_text,
        "text": result["text"],
        "audio_url": audio_url
    }
