import json
import os
import re
from typing import Any

import httpx


class GroqService:
    def __init__(self) -> None:
        self.api_key = os.environ.get("GROQ_API_KEY")
        self.model = os.environ.get("GROQ_MODEL", "llama-3.3-70b-versatile")
        self.url = "https://api.groq.com/openai/v1/chat/completions"

    def call_json(
        self,
        system_prompt: str,
        user_prompt: str,
        fallback: dict[str, Any] | None = None,
        max_tokens: int = 2000,
    ) -> dict[str, Any]:
        if not self.api_key:
            raise RuntimeError("GROQ_API_KEY environment variable is not set")

        body = {
            "model": self.model,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            "temperature": 0.1,
            "max_tokens": max_tokens,
            "response_format": {"type": "json_object"},
        }
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }

        with httpx.Client(timeout=120) as client:
            response = client.post(self.url, headers=headers, json=body)

        if response.status_code == 429:
            raise RuntimeError("Groq rate limit hit. Wait a minute and try again.")
        if not response.is_success:
            raise RuntimeError(f"Groq API error {response.status_code}: {response.text}")

        content = response.json()["choices"][0]["message"]["content"].strip()
        try:
            return json.loads(content)
        except json.JSONDecodeError:
            cleaned = self._extract_json(content)
            if cleaned:
                return json.loads(cleaned)
            if fallback is not None:
                return fallback
            raise

    @staticmethod
    def _extract_json(content: str) -> str | None:
        fenced = re.search(r"```(?:json)?\s*(.*?)```", content, re.DOTALL)
        if fenced:
            return fenced.group(1).strip()

        start = min(
            [idx for idx in [content.find("{"), content.find("[")] if idx != -1],
            default=-1,
        )
        end = max(content.rfind("}"), content.rfind("]"))
        if start != -1 and end != -1 and end > start:
            return content[start : end + 1]
        return None
