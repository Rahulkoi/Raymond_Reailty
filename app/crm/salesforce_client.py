import requests

def create_lead(payload, token):
    url = "https://YOUR_DOMAIN/services/apexrest/createLead"

    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json"
    }

    response = requests.post(url, json=payload, headers=headers)

    print("🔥 SALESFORCE STATUS:", response.status_code)
    print("🔥 SALESFORCE RESPONSE:", response.text)

    response.raise_for_status()  # ❗ crash if SF fails

    return response.json()
