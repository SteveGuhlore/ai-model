"""Text-to-speech via Coqui XTTS-v2, with optional voice cloning.

Voice cloning requires a short reference clip (`voice_sample`). Only clone a
voice you have the right to use — i.e. your own, or one with explicit, written
consent from the speaker. Do not clone third parties without permission.

The heavy import is lazy so this module can be imported without the ML stack.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Optional


@dataclass
class VoiceCloneTTS:
    model_name: str
    voice_sample: str
    language: str = "en"
    device: str = "cuda"
    _tts: Optional[object] = None

    def _load(self):
        if self._tts is None:
            from TTS.api import TTS  # lazy: requires the `ml` extra

            self._tts = TTS(self.model_name).to(self.device)
        return self._tts

    def synthesize(self, text: str, out_path: str) -> str:
        tts = self._load()
        tts.tts_to_file(
            text=text,
            speaker_wav=self.voice_sample,
            language=self.language,
            file_path=out_path,
        )
        return out_path
