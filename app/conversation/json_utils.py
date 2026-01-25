# app/conversation/json_utils.py

import json

def parse_json_safe(text: str):
    try:
        return json.loads(text)
    except Exception:
        return None
