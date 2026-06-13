"""Local LLM persona backend via Ollama.

Keeps the 'brain' self-hosted on the same VM (no external API). Swap this for
any object exposing `reply(message, history) -> str` to use a different model
provider; the pipeline only depends on that structural contract.
"""

from __future__ import annotations

from typing import Sequence

import requests

from avatar_studio.persona.base import Message, build_system_prompt


class OllamaPersona:
    def __init__(
        self,
        url: str,
        model: str,
        persona_name: str,
        timeout: int = 120,
    ) -> None:
        self.url = url.rstrip("/")
        self.model = model
        self.system = build_system_prompt(persona_name)
        self.timeout = timeout

    def reply(self, user_message: str, history: Sequence[Message]) -> str:
        messages = [{"role": "system", "content": self.system}]
        messages.extend(dict(m) for m in history)
        messages.append({"role": "user", "content": user_message})

        resp = requests.post(
            f"{self.url}/api/chat",
            json={"model": self.model, "messages": messages, "stream": False},
            timeout=self.timeout,
        )
        resp.raise_for_status()
        return resp.json()["message"]["content"].strip()
