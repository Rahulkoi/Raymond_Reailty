from pydantic import BaseModel
from typing import Optional

class LeadExtraction(BaseModel):
    full_name: Optional[str] = None
    mobile_number: Optional[str] = None
    email: Optional[str] = None
    city: Optional[str] = None
    budget: Optional[str] = None
    project_interest: Optional[str] = None
