from fastapi import APIRouter
from pydantic import BaseModel
from typing import Optional
from app.conversation.manager import ConversationManager

router = APIRouter(prefix="/chat", tags=["Chat"])

sessions = {}

class ChatRequest(BaseModel):
    message: str
    session_id: Optional[str] = "default"

@router.post("/")
def chat(req: ChatRequest):
    if req.session_id not in sessions:
        sessions[req.session_id] = ConversationManager()

    cm = sessions[req.session_id]
    return cm.handle_user_input(req.message)


@router.get("/test")
def test_chat():
    """Test endpoint to verify ConversationManager is working correctly."""
    cm = ConversationManager()

    # Test 1: Property query
    r1 = cm.handle_user_input("Show me property in Bangalore")

    # Test 2: Provide name
    r2 = cm.handle_user_input("My name is Rahul")

    # Test 3: Provide phone
    r3 = cm.handle_user_input("9876543210")

    # Test 4: Provide email
    r4 = cm.handle_user_input("rahul@gmail.com")

    # Test 5: End conversation
    r5 = cm.handle_user_input("Thanks bye")

    return {
        "version": "ConversationManager v3.0",
        "test_results": [
            {"input": "Show me property in Bangalore", "response": r1.get("text"), "has_properties": "properties" in r1},
            {"input": "My name is Rahul", "response": r2.get("text"), "has_properties": "properties" in r2},
            {"input": "9876543210", "response": r3.get("text"), "has_properties": "properties" in r3},
            {"input": "rahul@gmail.com", "response": r4.get("text"), "has_properties": "properties" in r4},
            {"input": "Thanks bye", "response": r5.get("text"), "has_properties": "properties" in r5},
        ],
        "lead_data": cm.lead,
        "expected_flow": "Properties should ONLY appear in test 5 (thanks bye)"
    }
