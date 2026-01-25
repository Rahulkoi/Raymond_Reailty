import json
from pathlib import Path

DATA_PATH = Path(__file__).parent.parent / "data" / "properties.json"

def load_properties():
    with open(DATA_PATH, "r", encoding="utf-8") as f:
        return json.load(f)
