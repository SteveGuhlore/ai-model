"""SFW text moderation — the conversation-side guardrail.

Intentionally dependency-free so it always runs, even before the ML stack is
installed. The keyword screen is a fast first pass and a fail-safe, not a
complete solution: in production, attach a real moderation model via the
`ModerationModel` hook (an open-source content classifier, or a hosted
moderation endpoint) for nuanced coverage.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Protocol


@dataclass(frozen=True)
class SafetyResult:
    allowed: bool
    categories: list[str] = field(default_factory=list)
    reason: str = ""

    @property
    def blocked(self) -> bool:
        return not self.allowed


class ModerationModel(Protocol):
    """Optional ML moderation backend. Returns the category labels that fired."""

    def classify(self, text: str) -> list[str]: ...


# Coarse seed patterns. The goal is to *block* explicit intent, so we keep the
# net wide and lean on a real classifier (the hook above) for precision.
_EXPLICIT_PATTERNS = [
    r"\bn\s*s\s*f\s*w\b",
    r"\bexplicit\b",
    r"\bnude[sd]?\b",
    r"\bnaked\b",
    r"\bporn\w*",
    r"\bsext\w*",
    r"\bxxx\b",
    r"\bonlyfans\b",
    r"\bgenital\w*",
    r"\berotica?\b",
]


class TextSafety:
    """Screens text for sexual/explicit content and returns a SafetyResult."""

    def __init__(
        self,
        model: ModerationModel | None = None,
        extra_patterns: list[str] | None = None,
    ) -> None:
        self._model = model
        patterns = list(_EXPLICIT_PATTERNS)
        if extra_patterns:
            patterns.extend(extra_patterns)
        self._re = re.compile("|".join(patterns), re.IGNORECASE)

    def check(self, text: str) -> SafetyResult:
        categories: list[str] = []
        if self._re.search(text or ""):
            categories.append("sexual_explicit")
        if self._model is not None:
            categories.extend(self._model.classify(text or ""))
        categories = sorted(set(categories))
        if categories:
            return SafetyResult(False, categories, "blocked by SFW policy")
        return SafetyResult(True)
