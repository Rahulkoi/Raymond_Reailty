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
from app.api.property_search import router as property_search_router
from app.api.voice_lead_api import router as voice_lead_router

app = FastAPI(title="AI Chat + CRM Bot")

# ---------------- CORS ----------------
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ---------------- ROUTERS ----------------
app.include_router(chat_router)
app.include_router(voice_chat_router)
app.include_router(voice_ws_router)
app.include_router(elevenlabs_router, prefix="/elevenlabs", tags=["ElevenLabs Agent"])
app.include_router(property_search_router, prefix="/api/properties", tags=["Property Search"])
app.include_router(voice_lead_router, prefix="/api/voice", tags=["Voice Lead Capture"])

# ---------------- ROOT ROUTE (FIX #1) ----------------
@app.get("/")
def root():
    return {
        "message": "Raymond Bot backend is running 🚀",
        "docs": "/docs",
        "health": "/health"
    }

# ---------------- HEALTH CHECK ----------------
@app.get("/health")
def health():
    return {"status": "ok"}


# ---------------- DEBUG: Check ENV VARS (remove in production) ----------------
@app.get("/debug/env")
def debug_env():
    """Debug endpoint to verify environment variables are loaded. REMOVE IN PRODUCTION."""
    import os
    elevenlabs_key = os.getenv("ELEVENLABS_API_KEY") or os.getenv("ELEVEN_LAB_API_KEY")
    elevenlabs_voice = os.getenv("ELEVENLABS_VOICE_ID") or os.getenv("ELEVEN_LAB_VOICE_ID")
    return {
        "ELEVENLABS_API_KEY": "SET" if elevenlabs_key else "NOT SET",
        "ELEVENLABS_VOICE_ID": elevenlabs_voice or "NOT SET (will use default: Rachel)",
        "ELEVENLABS_AGENT_ID": os.getenv("ELEVENLABS_AGENT_ID", "using default"),
        "OPENAI_API_KEY": "SET" if os.getenv("OPENAI_API_KEY") else "NOT SET",
        "SF_CLIENT_ID": "SET" if os.getenv("SF_CLIENT_ID") else "NOT SET",
        "env_var_count": len([k for k in os.environ.keys()]),
        "note": "Now supports both ELEVENLABS_API_KEY and ELEVEN_LAB_API_KEY naming"
    }

# ---------------- STATIC FILES (FIX #2) ----------------
BASE_DIR = Path(__file__).resolve().parent.parent
static_dir = BASE_DIR / "static"

if static_dir.exists():
    app.mount("/static", StaticFiles(directory=static_dir), name="static")
