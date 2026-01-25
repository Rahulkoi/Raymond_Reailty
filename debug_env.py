from dotenv import load_dotenv
import os

load_dotenv()

print("ELEVEN:", os.getenv("ELEVENLABS_API_KEY"))
