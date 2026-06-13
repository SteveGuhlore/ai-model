"""Train a likeness LoRA on SDXL from your own photos.

This wraps the official diffusers DreamBooth-LoRA SDXL training script. You
provide ~15-30 varied, well-lit photos of the consenting subject (you), and it
produces a small LoRA that teaches SDXL your likeness without retraining the
whole model.

Only train on a likeness you are authorized to use (yours, or with explicit
written consent). The training script is fetched during VM provisioning; see
scripts/provision_vm.sh and the README.

Run:
    python -m avatar_studio.face.train_lora \
        --instance-data assets/me \
        --output models/likeness-lora \
        --token "a photo of sks person"
"""

from __future__ import annotations

import argparse
import os
import subprocess
import sys
from dataclasses import dataclass


@dataclass
class TrainConfig:
    instance_data_dir: str
    output_dir: str
    instance_prompt: str = "a photo of sks person"
    base_model: str = "stabilityai/stable-diffusion-xl-base-1.0"
    vae: str = "madebyollin/sdxl-vae-fp16-fix"
    resolution: int = 1024
    train_batch_size: int = 1
    learning_rate: float = 1e-4
    max_train_steps: int = 1200
    rank: int = 16
    seed: int = 0
    # Path to diffusers' train_dreambooth_lora_sdxl.py (fetched at provisioning)
    train_script: str = "third_party/diffusers/examples/dreambooth/train_dreambooth_lora_sdxl.py"

    def command(self) -> list[str]:
        return [
            "accelerate",
            "launch",
            self.train_script,
            f"--pretrained_model_name_or_path={self.base_model}",
            f"--pretrained_vae_model_name_or_path={self.vae}",
            f"--instance_data_dir={self.instance_data_dir}",
            f"--output_dir={self.output_dir}",
            f"--instance_prompt={self.instance_prompt}",
            f"--resolution={self.resolution}",
            f"--train_batch_size={self.train_batch_size}",
            f"--learning_rate={self.learning_rate}",
            f"--max_train_steps={self.max_train_steps}",
            f"--rank={self.rank}",
            f"--seed={self.seed}",
            "--gradient_accumulation_steps=1",
            "--lr_scheduler=constant",
            "--lr_warmup_steps=0",
            "--mixed_precision=fp16",
            "--gradient_checkpointing",
            "--use_8bit_adam",
        ]


def train(cfg: TrainConfig) -> str:
    os.makedirs(cfg.output_dir, exist_ok=True)
    if not os.path.isfile(cfg.train_script):
        raise FileNotFoundError(
            f"Training script not found at {cfg.train_script}. "
            "Run scripts/provision_vm.sh (or clone huggingface/diffusers) first."
        )
    subprocess.run(cfg.command(), check=True)
    return cfg.output_dir


def _parse_args(argv: list[str]) -> TrainConfig:
    p = argparse.ArgumentParser(description="Train a likeness LoRA on SDXL.")
    p.add_argument("--instance-data", required=True, help="Folder of subject photos")
    p.add_argument("--output", required=True, help="Output folder for the LoRA")
    p.add_argument("--token", default="a photo of sks person", help="Instance prompt")
    p.add_argument("--steps", type=int, default=1200)
    p.add_argument("--rank", type=int, default=16)
    args = p.parse_args(argv)
    return TrainConfig(
        instance_data_dir=args.instance_data,
        output_dir=args.output,
        instance_prompt=args.token,
        max_train_steps=args.steps,
        rank=args.rank,
    )


if __name__ == "__main__":
    cfg = _parse_args(sys.argv[1:])
    out = train(cfg)
    print(f"LoRA written to: {out}")
