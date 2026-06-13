"""Media-side SFW guardrail: classify generated images/video frames as NSFW.

This is the last line of defense before any generated media is returned. It
fails closed: if frames can't be read or the model can't load, media is
treated as unsafe.

For video, frames are sampled at 1 fps via ffmpeg and each is checked. Heavy
imports are lazy so the package stays importable without the ML stack.
"""

from __future__ import annotations

import glob
import os
import subprocess
import tempfile
from dataclasses import dataclass
from typing import Optional

_IMAGE_EXTS = {".png", ".jpg", ".jpeg", ".webp", ".bmp"}


@dataclass
class NSFWImageClassifier:
    model_name: str
    threshold: float = 0.7
    device: str = "cuda"
    _clf: Optional[object] = None

    def _load(self):
        if self._clf is None:
            from transformers import pipeline

            self._clf = pipeline(
                "image-classification",
                model=self.model_name,
                device=0 if self.device == "cuda" else -1,
            )
        return self._clf

    def _frames(self, media_path: str):
        from PIL import Image

        ext = os.path.splitext(media_path)[1].lower()
        if ext in _IMAGE_EXTS:
            return [Image.open(media_path).convert("RGB")]

        tmp = tempfile.mkdtemp()
        subprocess.run(
            ["ffmpeg", "-i", media_path, "-vf", "fps=1", os.path.join(tmp, "f_%04d.png")],
            check=True,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
        paths = sorted(glob.glob(os.path.join(tmp, "*.png")))
        return [Image.open(p).convert("RGB") for p in paths]

    def is_sfw(self, media_path: str) -> bool:
        try:
            frames = self._frames(media_path)
        except Exception:
            return False  # fail closed on any extraction error

        if not frames:
            return False

        clf = self._load()
        for frame in frames:
            for result in clf(frame):
                if result["label"].lower() == "nsfw" and result["score"] >= self.threshold:
                    return False
        return True
