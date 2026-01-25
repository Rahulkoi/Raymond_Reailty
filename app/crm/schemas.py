from pydantic import BaseModel, EmailStr
from typing import Optional

class LeadPayload(BaseModel):
    fullName: str
    emailAddress: EmailStr
    mobileNumber: str
    city: str
    country: str = "India"
    projectInterested: str
    budget: Optional[str] = None
