"""Persona-voiced copywriter (captions, hooks, ad copy) — text-gated.

Uses the persona LLM backend (anything with ``reply(message, history) -> str``,
e.g. OllamaPersona). Every generated string is screened with the SFW text gate;
blocked copy is regenerated once, then dropped. Copy never escapes ungated.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol, Sequence

from avatar_studio.safety.screen import screen_text
from avatar_studio.safety.text_filter import TextSafety
from avatar_studio.store.models import Persona

KINDS = ("caption", "hook", "fb_primary_text", "fb_headline", "hashtags")

_KIND_INSTRUCTION = {
    "caption": "Write one short, upbeat social caption (max 2 sentences).",
    "hook": "Write one punchy 1-line video hook that grabs attention in 3 seconds.",
    "fb_primary_text": "Write Facebook ad primary text (max 3 sentences, benefit-led).",
    "fb_headline": "Write a Facebook ad headline (max 8 words).",
    "hashtags": "Write 5-8 relevant, SFW hashtags on one line.",
}


class CopyLLM(Protocol):
    def reply(self, user_message: str, history: Sequence[dict]) -> str: ...


@dataclass
class CopyDraft:
    kind: str
    text: str = ""
    blocked: bool = False
    reason: str = ""


class Copywriter:
    def __init__(self, llm: CopyLLM, text_gate: TextSafety | None = None) -> None:
        self._llm = llm
        self._gate = text_gate or TextSafety()

    def _prompt(self, persona: Persona, kind: str, brief: str) -> str:
        voice = persona.brand_voice or "warm, upbeat, authentic"
        return (
            f"You are writing as {persona.name}, whose brand voice is: {voice}.\n"
            f"{_KIND_INSTRUCTION[kind]}\n"
            f"Topic/brief: {brief}\n"
            "Keep it strictly SFW. Output only the copy, no preamble."
        )

    def write(self, persona: Persona, kind: str, brief: str) -> CopyDraft:
        if kind not in KINDS:
            raise ValueError(f"unknown copy kind {kind!r}")
        prompt = self._prompt(persona, kind, brief)

        for _attempt in range(2):  # generate, then one retry on a block
            text = (self._llm.reply(prompt, []) or "").strip()
            if not screen_text(text, self._gate).blocked:
                return CopyDraft(kind=kind, text=text)
        return CopyDraft(kind=kind, blocked=True, reason="copy blocked by SFW text gate")
