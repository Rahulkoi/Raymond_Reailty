from dotenv import load_dotenv
load_dotenv()

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.api.chat_api import router as chat_router
from fastapi.staticfiles import StaticFiles
from pathlib import Path
from app.api.voice_chat_api import router as voice_chat_router
from app.api.voice_stream_ws import router as voice_ws_router
from app.api.elevenlabs_agent import router as elevenlabs_router
from app.api.property_search import router as property_search_router

app = FastAPI(title="AI Chat + CRM Bot")

# CORS for ElevenLabs agent integration
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# API Routers
app.include_router(chat_router)
app.include_router(voice_chat_router)
BASE_DIR = Path(__file__).resolve().parent.parent
app.include_router(voice_ws_router)
app.include_router(elevenlabs_router, prefix="/elevenlabs", tags=["ElevenLabs Agent"])
app.include_router(property_search_router, prefix="/api/properties", tags=["Property Search"])


app.mount("/static", StaticFiles(directory="static"), name="static")

@app.get("/health")
def health():
    return {"status": "ok"}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("app.main:app", host="0.0.0.0", port=8000, reload=True)
