import requests
import os

SF_AUTH_URL = os.getenv("SF_AUTH_URL")
SF_CLIENT_ID = os.getenv("SF_CLIENT_ID")
SF_CLIENT_SECRET = os.getenv("SF_CLIENT_SECRET")
SF_USERNAME = os.getenv("SF_USERNAME")
SF_PASSWORD = os.getenv("SF_PASSWORD")


def get_access_token():
    """Get Salesforce OAuth access token using password grant flow."""
    url = os.getenv("SF_AUTH_URL")

    payload = {
        "grant_type": "password",
        "client_id": os.getenv("SF_CLIENT_ID"),
        "client_secret": os.getenv("SF_CLIENT_SECRET"),
        "username": os.getenv("SF_USERNAME"),
        "password": os.getenv("SF_PASSWORD"),
    }

    response = requests.post(url, data=payload)

    if response.status_code != 200:
        print(f"Salesforce Auth Error: {response.status_code} - {response.text}")
        raise Exception(f"Salesforce authentication failed: {response.text}")

    data = response.json()

    return {
        "access_token": data["access_token"],
        "instance_url": data.get("instance_url", "https://raymondrealty--dev2.sandbox.my.salesforce.com")
    }
