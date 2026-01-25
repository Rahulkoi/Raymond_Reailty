from typing import List, Dict


class LLMClient:
    def generate(self, system_prompt: str, user_text: str, history: List[Dict] = None) -> str:
        raise NotImplementedError
