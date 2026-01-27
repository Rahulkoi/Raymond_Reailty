import os
import time
import httpx
from typing import List, Dict
from dotenv import load_dotenv
from openai import OpenAI

from app.llm.base import LLMClient

load_dotenv()


class OpenAIClient(LLMClient):
    def __init__(self):
        api_key = os.getenv("OPENAI_API_KEY")

        assert api_key and api_key.strip().startswith("sk-"), \
            "OPENAI_API_KEY is missing or invalid"

        # PERFORMANCE: Use custom httpx client with optimized timeouts
        http_client = httpx.Client(
            timeout=httpx.Timeout(30.0, connect=5.0),
            limits=httpx.Limits(max_keepalive_connections=5, max_connections=10)
        )
        self.client = OpenAI(api_key=api_key, http_client=http_client)

    def generate(self, system_prompt: str, user_text: str, history: List[Dict] = None) -> str:
        start = time.time()

        messages = [{"role": "system", "content": system_prompt}]

        # Add conversation history if provided (limit to last 4 messages for speed)
        if history:
            messages.extend(history[-4:])

        # Add current user message
        messages.append({"role": "user", "content": user_text})

        response = self.client.chat.completions.create(
            model="gpt-4o-mini",
            messages=messages,
            # PERFORMANCE: Very short responses for voice
            max_tokens=80,
            # PERFORMANCE: Lower temperature = faster, more deterministic
            temperature=0.3,
        )

        result = response.choices[0].message.content
        print(f"⚡ OpenAI API call: {(time.time() - start)*1000:.0f}ms, {len(result)} chars")

        return result
