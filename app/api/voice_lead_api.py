"""
Voice Lead Capture API - Extract user info from voice chat transcripts and save to Salesforce
"""

import os
import re
import json
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Optional, List

router = APIRouter()


class TranscriptMessage(BaseModel):
    role: str  # "user" or "agent"
    text: str


class VoiceLeadRequest(BaseModel):
    session_id: str
    transcript: List[TranscriptMessage]


def extract_user_info(transcript: List[TranscriptMessage]) -> dict:
    """Extract user information from voice chat transcript."""
    user_info = {
        "fullName": None,
        "emailAddress": None,
        "mobileNumber": None,
        "city": None,
        "budget": None,
        "configuration": None
    }

    # Combine all user messages
    user_text = " ".join([m.text for m in transcript if m.role == "user"])
    user_text_lower = user_text.lower()

    # Extract name patterns
    name_patterns = [
        r"(?:my name is|i am|i'm|this is|call me)\s+([A-Z][a-z]+(?:\s+[A-Z][a-z]+)?)",
        r"(?:name is|name's)\s+([A-Z][a-z]+(?:\s+[A-Z][a-z]+)?)",
    ]
    for pattern in name_patterns:
        match = re.search(pattern, user_text, re.IGNORECASE)
        if match:
            user_info["fullName"] = match.group(1).strip().title()
            break

    # Extract phone number (Indian format)
    phone_patterns = [
        r'(?:phone|number|mobile|call me at|reach me at|contact)[^\d]*(\d{10})',
        r'(?:^|\s)(\d{10})(?:\s|$)',
        r'(?:^|\s)([6-9]\d{9})(?:\s|$)',  # Indian mobile numbers start with 6-9
        r'\+91[\s-]?(\d{10})',
        r'(\d{5}[\s-]?\d{5})',
    ]
    for pattern in phone_patterns:
        match = re.search(pattern, user_text)
        if match:
            phone = re.sub(r'[\s-]', '', match.group(1))
            if len(phone) == 10 and phone[0] in '6789':
                user_info["mobileNumber"] = phone
                break

    # Extract email
    email_pattern = r'[\w\.-]+@[\w\.-]+\.\w+'
    email_match = re.search(email_pattern, user_text)
    if email_match:
        user_info["emailAddress"] = email_match.group(0).lower()

    # Extract location/city
    locations = {
        'bangalore': ['bangalore', 'bengaluru', 'banglore', 'blr'],
        'thane': ['thane', 'thaney'],
        'mumbai': ['mumbai', 'bombay'],
        'pune': ['pune', 'poona'],
        'whitefield': ['whitefield'],
        'electronic city': ['electronic city', 'ec'],
        'sarjapur': ['sarjapur'],
        'hsr': ['hsr', 'hsr layout'],
        'koramangala': ['koramangala'],
        'indiranagar': ['indiranagar']
    }
    for city, aliases in locations.items():
        if any(alias in user_text_lower for alias in aliases):
            user_info["city"] = city.title()
            break

    # Extract budget
    budget_patterns = [
        (r'(\d+\.?\d*)\s*(?:crore|cr)', 'crore'),
        (r'(\d+\.?\d*)\s*(?:lakh|lac|lakhs)', 'lakh'),
    ]
    for pattern, unit in budget_patterns:
        match = re.search(pattern, user_text_lower)
        if match:
            amount = match.group(1)
            user_info["budget"] = f"{amount} {unit}"
            break

    # Extract BHK configuration
    bhk_match = re.search(r'(\d)\s*(?:bhk|bedroom|bed)', user_text_lower)
    if bhk_match:
        user_info["configuration"] = f"{bhk_match.group(1)} BHK"

    return user_info


def save_lead_to_salesforce(user_info: dict) -> bool:
    """Save extracted user info to Salesforce."""
    # Only save if we have at least name and phone
    if not user_info.get("fullName") or not user_info.get("mobileNumber"):
        print(f"📞 Insufficient data for lead: {user_info}")
        return False

    try:
        from app.crm.salesforce_auth import get_access_token
        from app.crm.create_lead import create_salesforce_lead

        token = get_access_token()

        payload = {
            "wl": {
                "fullName": user_info.get("fullName", ""),
                "emailAddress": user_info.get("emailAddress", ""),
                "mobileNumber": user_info.get("mobileNumber", ""),
                "city": user_info.get("city", "Bangalore"),
                "budget": str(user_info.get("budget", "")),
                "configuration": user_info.get("configuration", ""),
                "source": "AI_VOICE_BOT"
            }
        }

        create_salesforce_lead(
            payload,
            token["access_token"],
            token["instance_url"]
        )

        print(f"✅ Voice lead saved to Salesforce: {user_info.get('fullName')} - {user_info.get('mobileNumber')}")
        return True

    except Exception as e:
        print(f"❌ Error saving voice lead to Salesforce: {e}")
        return False


@router.post("/capture-lead")
async def capture_voice_lead(req: VoiceLeadRequest):
    """Extract user info from voice chat transcript and save to Salesforce."""
    print(f"📞 Processing voice lead for session: {req.session_id}")
    print(f"📞 Transcript has {len(req.transcript)} messages")

    # Extract user info from transcript
    user_info = extract_user_info(req.transcript)
    print(f"📞 Extracted user info: {user_info}")

    # Check what we captured
    captured_fields = [k for k, v in user_info.items() if v]
    missing_fields = [k for k, v in user_info.items() if not v]

    # Save to Salesforce if we have enough info
    saved = False
    if user_info.get("fullName") and user_info.get("mobileNumber"):
        saved = save_lead_to_salesforce(user_info)

    return {
        "success": saved,
        "user_info": user_info,
        "captured_fields": captured_fields,
        "missing_fields": missing_fields,
        "message": "Lead saved to Salesforce!" if saved else "Need at least name and phone number"
    }


@router.post("/extract-info")
async def extract_info_only(req: VoiceLeadRequest):
    """Extract user info from transcript without saving (for real-time display)."""
    user_info = extract_user_info(req.transcript)
    return {
        "user_info": user_info,
        "has_required": bool(user_info.get("fullName") and user_info.get("mobileNumber"))
    }
