from dotenv import load_dotenv
import os

# Load environment variables from .env
load_dotenv()


def _required(name: str, default: str = None) -> str:
    """Get required env var. If default is provided, use it instead of crashing."""
    value = os.getenv(name)
    if not value:
        if default is not None:
            return default
        # Don't crash on startup - just log warning
        print(f"⚠️ WARNING: Missing environment variable: {name}")
        return ""
    return value


class AppConfig:
    ENV = os.getenv("ENV", "development")
    APP_NAME = os.getenv("APP_NAME", "voice-crm-bot")
    LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO")


class GeminiConfig:
    PROVIDER = "gemini"
    API_KEY = os.getenv("GEMINI_API_KEY")
    LLM_MODEL = os.getenv("GEMINI_LLM_MODEL", "models/gemini-pro")
    EMBEDDING_MODEL = os.getenv("GEMINI_EMBEDDING_MODEL", "models/embedding-001")




class LLMConfig:
    API_KEY = _required("ANTHROPIC_API_KEY")
    MODEL = os.getenv("CLAUDE_MODEL", "claude-3-5-sonnet")
    MAX_INPUT_TOKENS = int(os.getenv("MAX_INPUT_TOKENS", "4000"))
    MAX_OUTPUT_TOKENS = int(os.getenv("MAX_OUTPUT_TOKENS", "1000"))


class VoiceConfig:
    # Twilio
    TWILIO_ACCOUNT_SID = _required("TWILIO_ACCOUNT_SID")
    TWILIO_AUTH_TOKEN = _required("TWILIO_AUTH_TOKEN")
    TWILIO_PHONE_NUMBER = _required("TWILIO_PHONE_NUMBER")

    # ElevenLabs TTS Configuration
    ELEVENLABS_API_KEY = _required("ELEVENLABS_API_KEY")
    ELEVENLABS_VOICE_ID = os.getenv("ELEVENLABS_VOICE_ID", "Rachel")
    ELEVENLABS_MODEL = os.getenv("ELEVENLABS_MODEL", "eleven_multilingual_v2")
    # Voice settings for natural speech
    ELEVENLABS_SPEED = float(os.getenv("ELEVENLABS_SPEED", "1.0"))  # 0.7 - 1.2 range
    ELEVENLABS_STABILITY = float(os.getenv("ELEVENLABS_STABILITY", "0.5"))  # 0.0 - 1.0
    ELEVENLABS_SIMILARITY = float(os.getenv("ELEVENLABS_SIMILARITY", "0.75"))  # 0.0 - 1.0
    # Latency optimization: 0=off, 1-4=increasing optimization (higher = faster but lower quality)
    ELEVENLABS_OPTIMIZE_LATENCY = int(os.getenv("ELEVENLABS_OPTIMIZE_LATENCY", "3"))

    # Supported languages for STT (Whisper auto-detects, but can be forced)
    # Codes: en, hi, ta, te, kn, ml, bn, mr, gu, pa, ur
    DEFAULT_LANGUAGE = os.getenv("DEFAULT_LANGUAGE", None)  # None = auto-detect


class SalesforceConfig:
    USERNAME = _required("SALESFORCE_USERNAME")
    PASSWORD = _required("SALESFORCE_PASSWORD")
    SECURITY_TOKEN = _required("SALESFORCE_SECURITY_TOKEN")
    DOMAIN = os.getenv("SALESFORCE_DOMAIN", "login")


class MCPConfig:
    ENABLED = os.getenv("MCP_ENABLED", "true").lower() == "true"
    ALLOW_WRITES = os.getenv("MCP_ALLOW_WRITES", "false").lower() == "true"
    AUDIT_LOGGING = os.getenv("MCP_AUDIT_LOGGING", "true").lower() == "true"


class OpenAIConfig:
    LLM_MODEL = "gpt-4o-mini"

class Config:
    openai = OpenAIConfig()

config = Config()
