"""
ElevenLabs Conversational AI Agent - Signed URL Endpoint
Keeps API key secure on server side.
"""

import os
import httpx
from fastapi import APIRouter, HTTPException

router = APIRouter()

AGENT_ID = os.getenv("ELEVENLABS_AGENT_ID", "agent_9801kfjxka9ke9fsrfzz3v81vm76")
ELEVENLABS_API_KEY = os.getenv("ELEVENLABS_API_KEY")


@router.get("/get-signed-url")
async def get_signed_url():
    """Get a signed WebSocket URL for the ElevenLabs agent."""
    if not ELEVENLABS_API_KEY:
        raise HTTPException(status_code=500, detail="ElevenLabs API key not configured")

    try:
        async with httpx.AsyncClient() as client:
            response = await client.get(
                f"https://api.elevenlabs.io/v1/convai/conversation/get-signed-url?agent_id={AGENT_ID}",
                headers={"xi-api-key": ELEVENLABS_API_KEY}
            )

            if response.status_code != 200:
                raise HTTPException(status_code=response.status_code, detail=response.text)

            return {"signed_url": response.json().get("signed_url")}

    except httpx.RequestError as e:
        raise HTTPException(status_code=500, detail=str(e))
