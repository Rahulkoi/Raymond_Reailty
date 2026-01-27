"""
ElevenLabs Conversational AI Agent - Signed URL Endpoint
"""

import os
import httpx
from fastapi import APIRouter, HTTPException

router = APIRouter()

DEFAULT_AGENT_ID = "agent_9801kfjxka9ke9fsrfzz3v81vm76"


@router.get("/get-signed-url")
async def get_signed_url():
    """Get a signed WebSocket URL for the ElevenLabs agent."""
    api_key = os.getenv("ELEVENLABS_API_KEY") or os.getenv("ELEVEN_LAB_API_KEY")
    agent_id = os.getenv("ELEVENLABS_AGENT_ID", DEFAULT_AGENT_ID)

    if not api_key:
        raise HTTPException(status_code=500, detail="ElevenLabs API key not configured")

    try:
        async with httpx.AsyncClient() as client:
            response = await client.get(
                f"https://api.elevenlabs.io/v1/convai/conversation/get-signed-url?agent_id={agent_id}",
                headers={"xi-api-key": api_key}
            )

            if response.status_code != 200:
                raise HTTPException(status_code=response.status_code, detail=f"ElevenLabs API error: {response.text}")

            signed_url = response.json().get("signed_url")
            if not signed_url:
                raise HTTPException(status_code=500, detail="No signed_url in response")

            return {"signed_url": signed_url}

    except httpx.RequestError as e:
        raise HTTPException(status_code=500, detail=f"Network error: {str(e)}")
