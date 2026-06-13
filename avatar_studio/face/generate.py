"""SFW likeness image generation: SDXL base + your trained likeness LoRA.

Two things keep output SFW:
  1. a safety-tuned base model (not an 'uncensored' checkpoint), and
  2. a standing negative prompt that steers away from explicit content.
Pair this with the media safety classifier (safety/image_filter.py) for
defense in depth before anything is shown or saved.

Heavy imports are lazy so the package stays importable without a GPU.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

SFW_NEGATIVE = (
    "nsfw, nude, nudity, naked, explicit, sexual, suggestive, lingerie, "
    "underwear, cleavage, low quality, blurry, deformed, extra limbs, "
    "extra fingers, watermark, signature, text"
)


@dataclass
class FaceGenerator:
    base_model: str
    lora_path: Optional[str] = None
    device: str = "cuda"
    _pipe: Optional[object] = None

    def _load(self):
        if self._pipe is None:
            import torch
            from diffusers import StableDiffusionXLPipeline

            pipe = StableDiffusionXLPipeline.from_pretrained(
                self.base_model,
                torch_dtype=torch.float16,
                use_safetensors=True,
            )
            if self.lora_path:
                pipe.load_lora_weights(self.lora_path)
            self._pipe = pipe.to(self.device)
        return self._pipe

    def generate(
        self,
        prompt: str,
        out_path: str,
        steps: int = 30,
        guidance: float = 6.0,
        seed: Optional[int] = None,
    ) -> str:
        import torch

        pipe = self._load()
        generator = None
        if seed is not None:
            generator = torch.Generator(device=self.device).manual_seed(seed)

        image = pipe(
            prompt=prompt,
            negative_prompt=SFW_NEGATIVE,
            num_inference_steps=steps,
            guidance_scale=guidance,
            generator=generator,
        ).images[0]
        image.save(out_path)
        return out_path
