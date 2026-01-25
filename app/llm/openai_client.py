import os
import time
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

        self.client = OpenAI(api_key=api_key)

    def generate(self, system_prompt: str, user_text: str, history: List[Dict] = None) -> str:
        start = time.time()

        messages = [{"role": "system", "content": system_prompt}]

        # Add conversation history if provided
        if history:
            messages.extend(history)

        # Add current user message
        messages.append({"role": "user", "content": user_text})

        response = self.client.chat.completions.create(
            model="gpt-4o-mini",
            messages=messages,
            # PERFORMANCE: Limit response length for faster generation
            max_tokens=200,
            # PERFORMANCE: Lower temperature = faster, more deterministic
            temperature=0.7,
        )

        result = response.choices[0].message.content
        print(f"⚡ OpenAI API call: {(time.time() - start)*1000:.0f}ms, {len(result)} chars")

        return result
