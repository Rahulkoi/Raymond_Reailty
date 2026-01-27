from dotenv import load_dotenv
load_dotenv()

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from pathlib import Path

from app.api.chat_api import router as chat_router
from app.api.voice_chat_api import router as voice_chat_router
from app.api.voice_stream_ws import router as voice_ws_router
from app.api.elevenlabs_agent import router as elevenlabs_router
from app.api.voice_lead_api import router as voice_lead_router
from app.api.property_api import router as property_router

app = FastAPI(title="Raymond Voice Bot")

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Routes
app.include_router(chat_router)
app.include_router(voice_chat_router)
app.include_router(voice_ws_router)
app.include_router(elevenlabs_router, prefix="/elevenlabs", tags=["ElevenLabs"])
app.include_router(voice_lead_router, prefix="/api/voice", tags=["Voice Lead"])
app.include_router(property_router, prefix="/api/properties", tags=["Properties"])

@app.get("/")
def root():
    return {"message": "Raymond Voice Bot API", "docs": "/docs"}

@app.get("/health")
def health():
    return {"status": "ok"}

# Static files
BASE_DIR = Path(__file__).resolve().parent.parent
static_dir = BASE_DIR / "static"
if static_dir.exists():
    app.mount("/static", StaticFiles(directory=static_dir), name="static")
