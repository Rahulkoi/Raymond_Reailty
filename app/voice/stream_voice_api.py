from fastapi import APIRouter, WebSocket
from app.voice.eleven_stream import elevenlabs_stream

router = APIRouter()

@router.websocket("/ws/voice")
async def voice_ws(ws: WebSocket):
    await ws.accept()

    while True:
        text = await ws.receive_text()

        for audio_chunk in elevenlabs_stream(text):
            await ws.send_bytes(audio_chunk)
