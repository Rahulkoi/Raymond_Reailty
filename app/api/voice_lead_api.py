"""
Voice Lead Capture API - Extract user info from ElevenLabs conversation and save to Salesforce
"""

import re
from fastapi import APIRouter
from pydantic import BaseModel
from typing import List

router = APIRouter()


class TranscriptMessage(BaseModel):
    role: str  # "user" or "agent"
    text: str


class VoiceLeadRequest(BaseModel):
    session_id: str
    transcript: List[TranscriptMessage]


# Location mappings
LOCATIONS = {
    'bangalore': ['bangalore', 'bengaluru', 'banglore', 'blr'],
    'thane': ['thane', 'thaney'],
    'mumbai': ['mumbai', 'bombay'],
    'whitefield': ['whitefield'],
    'electronic city': ['electronic city'],
    'sarjapur': ['sarjapur'],
    'koramangala': ['koramangala'],
    'indiranagar': ['indiranagar']
}


def extract_user_info(transcript: List[TranscriptMessage]) -> dict:
    """Extract user info from conversation transcript."""
    info = {
        "fullName": None,
        "emailAddress": None,
        "mobileNumber": None,
        "city": None,
        "budget": None,
        "configuration": None
    }

    # Combine all user messages
    user_text = " ".join([m.text for m in transcript if m.role == "user"])
    user_lower = user_text.lower()

    # Extract name
    name_patterns = [
        r"(?:my name is|i am|i'm|this is|call me)\s+([A-Z][a-z]+(?:\s+[A-Z][a-z]+)?)",
        r"(?:name is)\s+([A-Z][a-z]+(?:\s+[A-Z][a-z]+)?)",
    ]
    for pattern in name_patterns:
        match = re.search(pattern, user_text, re.IGNORECASE)
        if match:
            info["fullName"] = match.group(1).strip().title()
            break

    # Extract phone (Indian 10-digit)
    phone_patterns = [
        r'\b([6-9]\d{9})\b',
        r'\+91[\s-]?(\d{10})',
    ]
    for pattern in phone_patterns:
        match = re.search(pattern, user_text)
        if match:
            phone = re.sub(r'[\s-]', '', match.group(1))
            if len(phone) == 10:
                info["mobileNumber"] = phone
                break

    # Extract email
    email_match = re.search(r'[\w.+-]+@[\w-]+\.[\w.-]+', user_text)
    if email_match:
        info["emailAddress"] = email_match.group(0).lower()

    # Extract location
    for city, aliases in LOCATIONS.items():
        if any(alias in user_lower for alias in aliases):
            info["city"] = city.title()
            break

    # Extract budget
    cr_match = re.search(r'(\d+\.?\d*)\s*(?:crore|cr)', user_lower)
    lakh_match = re.search(r'(\d+\.?\d*)\s*(?:lakh|lac)', user_lower)
    if cr_match:
        info["budget"] = f"{cr_match.group(1)} crore"
    elif lakh_match:
        info["budget"] = f"{lakh_match.group(1)} lakh"

    # Extract BHK
    bhk_match = re.search(r'(\d)\s*(?:bhk|bedroom)', user_lower)
    if bhk_match:
        info["configuration"] = f"{bhk_match.group(1)} BHK"

    return info


def save_to_salesforce(info: dict) -> dict:
    """Save lead to Salesforce. Returns result dict with success status and details."""
    result = {"success": False, "error": None, "salesforce_response": None}

    if not info.get("fullName") or not info.get("mobileNumber"):
        result["error"] = "Missing required fields: fullName and mobileNumber"
        print(f"Lead save skipped: {result['error']}")
        return result

    try:
        from app.crm.salesforce_auth import get_access_token
        from app.crm.create_lead import create_salesforce_lead

        print(f"Authenticating with Salesforce...")
        token = get_access_token()
        print(f"Salesforce auth successful. Instance: {token.get('instance_url')}")

        payload = {"wl": {
            "fullName": info.get("fullName", ""),
            "emailAddress": info.get("emailAddress", ""),
            "mobileNumber": info.get("mobileNumber", ""),
            "city": info.get("city", "Bangalore"),
            "budget": str(info.get("budget", "")),
            "configuration": info.get("configuration", ""),
            "source": "Website"
        }}

        print(f"Creating Salesforce lead with payload: {payload}")
        sf_response = create_salesforce_lead(payload, token["access_token"], token["instance_url"])
        print(f"Salesforce response: {sf_response}")

        result["success"] = True
        result["salesforce_response"] = sf_response
        print(f"Lead saved successfully: {info.get('fullName')} - {info.get('mobileNumber')}")
        return result

    except Exception as e:
        result["error"] = str(e)
        print(f"Lead save error: {e}")
        import traceback
        traceback.print_exc()
        return result


@router.post("/capture-lead")
async def capture_voice_lead(req: VoiceLeadRequest):
    """Extract user info from transcript and save to Salesforce."""
    print(f"Processing lead from {len(req.transcript)} messages")

    info = extract_user_info(req.transcript)
    print(f"Extracted info: {info}")

    sf_result = save_to_salesforce(info)

    return {
        "success": sf_result["success"],
        "user_info": info,
        "salesforce_result": sf_result,
        "message": "Lead saved to Salesforce!" if sf_result["success"] else (sf_result.get("error") or "Need name and phone number")
    }


@router.post("/test-lead-capture")
async def test_lead_capture():
    """Test endpoint - simulate lead capture with test data."""
    test_transcript = [
        TranscriptMessage(role="user", text="Hi, I am looking for property in Bangalore"),
        TranscriptMessage(role="agent", text="Great! I can help you. What's your name?"),
        TranscriptMessage(role="user", text="My name is Test User"),
        TranscriptMessage(role="agent", text="Nice to meet you Test User! What's your phone number?"),
        TranscriptMessage(role="user", text="9876543210"),
        TranscriptMessage(role="agent", text="Got it! And your email?"),
        TranscriptMessage(role="user", text="testuser@example.com"),
        TranscriptMessage(role="agent", text="Perfect! Looking for 2 BHK under 1 crore. Goodbye!")
    ]

    info = extract_user_info(test_transcript)

    return {
        "message": "Test lead extraction (NOT saved to Salesforce)",
        "extracted_info": info,
        "note": "This is a dry run. To actually save, use /capture-lead endpoint"
    }


@router.get("/test-salesforce")
async def test_salesforce_connection():
    """Test endpoint to verify Salesforce connection."""
    import os

    env_vars = {
        "SF_AUTH_URL": bool(os.getenv("SF_AUTH_URL")),
        "SF_CLIENT_ID": bool(os.getenv("SF_CLIENT_ID")),
        "SF_CLIENT_SECRET": bool(os.getenv("SF_CLIENT_SECRET")),
        "SF_USERNAME": bool(os.getenv("SF_USERNAME")),
        "SF_PASSWORD": bool(os.getenv("SF_PASSWORD")),
        "SF_CREATE_LEAD_URL": bool(os.getenv("SF_CREATE_LEAD_URL"))
    }

    all_set = all(env_vars.values())

    if not all_set:
        missing = [k for k, v in env_vars.items() if not v]
        return {
            "status": "error",
            "message": "Missing Salesforce environment variables",
            "missing_vars": missing,
            "env_status": env_vars
        }

    # Try to authenticate
    try:
        from app.crm.salesforce_auth import get_access_token
        token = get_access_token()
        return {
            "status": "success",
            "message": "Salesforce connection successful",
            "instance_url": token.get("instance_url"),
            "env_status": env_vars
        }
    except Exception as e:
        return {
            "status": "error",
            "message": f"Salesforce authentication failed: {str(e)}",
            "env_status": env_vars
        }
