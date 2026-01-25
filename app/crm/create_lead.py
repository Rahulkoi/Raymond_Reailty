import requests
import os


def create_salesforce_lead(payload, access_token, instance_url=None):
    """Create a lead in Salesforce using the WebToLead API."""
    # Use the specific endpoint from env, or fallback to instance_url
    url = os.getenv("SF_CREATE_LEAD_URL")

    if not url and instance_url:
        url = f"{instance_url}/services/apexrest/WebToLead/WebToLeadServices"

    headers = {
        "Authorization": f"Bearer {access_token}",
        "Content-Type": "application/json"
    }

    print(f"Creating Salesforce lead at: {url}")
    print(f"Payload: {payload}")

    response = requests.post(url, json=payload, headers=headers)

    if response.status_code not in (200, 201):
        print(f"Salesforce Lead Error: {response.status_code} - {response.text}")
        raise Exception(
            f"Salesforce Lead Error {response.status_code}: {response.text}"
        )

    print(f"Salesforce Lead Created: {response.text}")
    return response.json() if response.text else {"status": "success"}
