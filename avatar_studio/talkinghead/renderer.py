"""Lip-synced talking-head video from a still image + speech audio.

Default backend is SadTalker (run as a subprocess against its own checkout,
which keeps its heavy/conflicting deps isolated). LivePortrait or Wav2Lip can
be dropped in behind the same `render(face_image, audio_path, out_path)`
contract if you prefer their quality/latency trade-offs.

SadTalker is cloned during provisioning; see scripts/provision_vm.sh.
"""

from __future__ import annotations

import glob
import os
import shutil
import subprocess
from dataclasses import dataclass


@dataclass
class SadTalkerRenderer:
    sadtalker_dir: str
    device: str = "cuda"
    still: bool = True
    preprocess: str = "full"

    def render(self, face_image: str, audio_path: str, out_path: str) -> str:
        inference = os.path.join(self.sadtalker_dir, "inference.py")
        if not os.path.isfile(inference):
            raise FileNotFoundError(
                f"SadTalker not found at {self.sadtalker_dir}. Run scripts/provision_vm.sh first."
            )

        result_dir = out_path + ".result"
        cmd = [
            "python",
            inference,
            "--driven_audio",
            os.path.abspath(audio_path),
            "--source_image",
            os.path.abspath(face_image),
            "--result_dir",
            os.path.abspath(result_dir),
            "--preprocess",
            self.preprocess,
        ]
        if self.still:
            cmd.append("--still")

        subprocess.run(cmd, check=True, cwd=self.sadtalker_dir)

        produced = sorted(glob.glob(os.path.join(result_dir, "**", "*.mp4"), recursive=True))
        if not produced:
            raise RuntimeError("SadTalker produced no video output")
        shutil.move(produced[-1], out_path)
        shutil.rmtree(result_dir, ignore_errors=True)
        return out_path
