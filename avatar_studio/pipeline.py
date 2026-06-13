"""Avatar turn orchestration.

Pure orchestration with no heavy ML imports, so it stays unit-testable. The
real backends (persona LLM, TTS, talking-head renderer, media safety) are
injected; production wiring lives in avatar_studio.api.app.

Flow for one turn:
  1. screen the user's message (SFW text gate)         -> block if explicit
  2. persona generates a candidate reply
  3. screen the reply (SFW text gate)                  -> block if explicit
  4. synthesize speech audio from the reply
  5. render the lip-synced talking-head video
  6. screen the rendered media (SFW media gate)        -> block if NSFW
"""

from __future__ import annotations

import os
import uuid
from dataclasses import dataclass
from typing import Protocol, Sequence

from avatar_studio.safety.text_filter import TextSafety

Message = dict

SAFE_FALLBACK = (
    "I keep things friendly and non-explicit — let's talk about something else! "
    "What else is on your mind?"
)


class PersonaBackend(Protocol):
    def reply(self, user_message: str, history: Sequence[Message]) -> str: ...


class TTSBackend(Protocol):
    def synthesize(self, text: str, out_path: str) -> str: ...


class TalkingHeadBackend(Protocol):
    def render(self, face_image: str, audio_path: str, out_path: str) -> str: ...


class MediaSafety(Protocol):
    def is_sfw(self, media_path: str) -> bool: ...


@dataclass
class TurnResult:
    text: str
    audio_path: str | None = None
    video_path: str | None = None
    blocked: bool = False
    block_reason: str = ""


@dataclass
class AvatarPipeline:
    persona: PersonaBackend
    tts: TTSBackend
    head: TalkingHeadBackend
    face_image: str
    text_safety: TextSafety
    media_safety: MediaSafety
    work_dir: str = "outputs"

    def handle_turn(
        self,
        user_message: str,
        history: Sequence[Message] | None = None,
        render_video: bool = True,
    ) -> TurnResult:
        history = list(history or [])

        inbound = self.text_safety.check(user_message)
        if inbound.blocked:
            return TurnResult(
                text=SAFE_FALLBACK,
                blocked=True,
                block_reason=f"input:{','.join(inbound.categories)}",
            )

        candidate = self.persona.reply(user_message, history)

        outbound = self.text_safety.check(candidate)
        if outbound.blocked:
            return TurnResult(
                text=SAFE_FALLBACK,
                blocked=True,
                block_reason=f"output:{','.join(outbound.categories)}",
            )

        os.makedirs(self.work_dir, exist_ok=True)
        token = uuid.uuid4().hex[:12]

        audio_path = os.path.join(self.work_dir, f"{token}.wav")
        self.tts.synthesize(candidate, audio_path)

        video_path = None
        if render_video:
            video_path = os.path.join(self.work_dir, f"{token}.mp4")
            self.head.render(self.face_image, audio_path, video_path)
            if not self.media_safety.is_sfw(video_path):
                return TurnResult(
                    text=SAFE_FALLBACK,
                    blocked=True,
                    block_reason="output:media_nsfw",
                )

        return TurnResult(text=candidate, audio_path=audio_path, video_path=video_path)
