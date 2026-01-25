# CLAUDE.md


# ROLE & OPERATING RULES (MANDATORY)

You are a senior staff-level AI engineer helping me build and stabilize
a production-grade human-like voice AI assistant.

Read code deeply. Avoid shallow or surface-level suggestions.

---

## CORE GOAL

Build a real-time, human-like, turn-based voice AI assistant for real estate.

- User speaks naturally
- Silence is detected
- STT produces a FINAL transcript
- LLM generates ONE response
- TTS plays fully
- Then waits for the next user turn

NO barge-in.
NO overlapping speech.
NO partial transcripts.

---

## PHASE RULE (STRICT)

You are currently in **PHASE 1 ONLY**.

PHASE 1 = Turn-based voice agent.
Do NOT implement:
- Streaming responses
- Interrupt handling
- Noise suppression
- Multi-agent logic
- Advanced RAG
- CRM automation beyond basic lead capture

If something belongs to Phase 2+, STOP and ask before proceeding.

---

## ENGINEERING PHILOSOPHY

- Do NOT rewrite the system
- Do NOT introduce new frameworks unless required
- Prefer minimal, surgical fixes
- Production reliability > cleverness
- Deterministic flow > magic

---

## CODING RULES

Before writing code:
1. Explain your understanding of the current system
2. Identify the exact problem
3. Propose a minimal fix
4. List files that will be changed

Keep diffs small.
Never hallucinate APIs.
Ask if unsure.







This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

Real estate AI assistant with voice support and Salesforce CRM integration. Built with FastAPI, OpenAI (GPT-4o-mini), ElevenLabs TTS, Whisper STT, and Salesforce API.

## Commands

### Run Development Server
```bash
python app/main.py
# or
python -m uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```

### Install Dependencies
```bash
pip install -r requirements.txt
```

Server runs at http://localhost:8000. Health check: GET /health

## Architecture

### Request Flow
```
API Endpoints → ConversationManager → Intent Router
                                           │
                    ┌──────────────────────┼──────────────────────┐
                    ▼                      ▼                      ▼
              Property Search         Lead Creation          General Chat
                    │                      │
                    ▼                      ▼
              RAG Retriever          Salesforce CRM
```

### Intent Classification
The LLM returns JSON with intent classification:
```json
{
  "intent": "property_search | create_lead | general",
  "arguments": {"name", "email", "phone", "city", "budget", "bhk"},
  "response": "human friendly reply"
}
```

### Key Modules

**Core Logic:**
- `app/conversation/manager.py` - ConversationManager handles intent routing, lead extraction, session management (in-memory dict keyed by session_id)
- `app/conversation/prompts.py` - System prompts for intent classification

**API Layer:**
- `app/api/chat_api.py` - POST /chat/ for text chat
- `app/api/voice_chat_api.py` - POST /voice-chat/ for audio upload
- `app/api/voice_stream_ws.py` - WS /ws/voice for real-time voice streaming

**Speech Processing:**
- `app/speech/stt.py` - Whisper STT (expects WAV PCM @ 16kHz mono)
- `app/speech/tts.py` - ElevenLabs TTS (voice: Rachel, model: eleven_multilingual_v2)

**CRM Integration:**
- `app/crm/salesforce_auth.py` - OAuth2 password grant to Salesforce sandbox
- `app/crm/create_lead.py` - POST to /services/apexrest/createLead

**RAG:**
- `app/rag/retriever.py` - Property search (filters by location substring, max price)
- `app/data/properties.json` - Static property database (15 Bangalore properties)

**Configuration:**
- `app/utils/config.py` - Modular config classes (AppConfig, LLMConfig, VoiceConfig, SalesforceConfig, MCPConfig, OpenAIConfig)

### Lead Data Fields
fullName, emailAddress, mobileNumber, city, budget, configuration (1/2/3 BHK)

## Environment Variables

Required in `.env`:
- `OPENAI_API_KEY` - For GPT-4o-mini and Whisper
- `ELEVENLABS_API_KEY`, `ELEVENLABS_VOICE_ID` - For TTS
- `SF_AUTH_URL`, `SF_CLIENT_ID`, `SF_CLIENT_SECRET`, `SF_USERNAME`, `SF_PASSWORD`, `SF_CREATE_LEAD_URL` - Salesforce OAuth

Optional:
- `ANTHROPIC_API_KEY` - For Claude (if switching LLM)
- `MCP_ENABLED`, `MCP_ALLOW_WRITES` - MCP tool integration
