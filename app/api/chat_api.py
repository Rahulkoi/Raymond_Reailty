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
