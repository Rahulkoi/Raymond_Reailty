import requests
import os
from app.crm.exceptions import SalesforceLeadError

SF_LEAD_URL = os.getenv("SF_CREATE_LEAD_URL")

def create_lead(lead_data: dict, access_token: str):
    headers = {
        "Authorization": f"Bearer {access_token}",
        "Content-Type": "application/json"
    }

    response = requests.post(
        SF_LEAD_URL,
        json={"wl": lead_data},
        headers=headers
    )

    if response.status_code not in (200, 201):
        raise SalesforceLeadError(response.text)

    return response.json()
