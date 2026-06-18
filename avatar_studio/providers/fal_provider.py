"""fal.ai implementation of GenerationProvider.

Heavy/IO imports (fal_client, requests) are used lazily so importing the package
stays light. All responses from fal are treated as UNTRUSTED data: shapes are
validated, media is downloaded to bytes, and nothing returned is executed.

Auth: the fal client reads ``FAL_KEY`` from the environment. We never log it and
never pass it to the browser.

Note on sizing: Flux uses ``image_size`` *presets* (or an explicit {width,height}
object), NOT an ``aspect_ratio`` string. We map our logical aspect-ratio strings
to the right preset here; exact 1080-class resizing happens in the channel layer.
"""

from __future__ import annotations

from dataclasses import dataclass

from avatar_studio.providers import fal_models
from avatar_studio.providers.base import ImageResult, LoraResult, VideoResult

# Logical aspect ratio -> Flux image_size (preset string or {width,height}).
_IMAGE_SIZE: dict[str, object] = {
    "1:1": "square_hd",
    "16:9": "landscape_16_9",
    "9:16": "portrait_16_9",
    "4:3": "landscape_4_3",
    "3:4": "portrait_4_3",
    "4:5": {"width": 1024, "height": 1280},
}


def _image_size_for(aspect_ratio: str) -> object:
    try:
        return _IMAGE_SIZE[aspect_ratio]
    except KeyError as exc:  # no silent default — unknown ratios are a bug
        raise ValueError(f"unsupported aspect_ratio {aspect_ratio!r}") from exc


@dataclass
class FalProvider:
    """Production provider backed by fal.ai. Pass a non-default ``client`` only in
    tests; in production it is constructed lazily from the fal SDK."""

    client: object | None = None
    request_timeout: int = 300

    def _fal(self):
        if self.client is None:
            import fal_client  # lazy: only needed when actually calling fal

            self.client = fal_client
        return self.client

    @staticmethod
    def _download(url: str) -> bytes:
        import requests

        if not isinstance(url, str) or not url.startswith(("http://", "https://")):
            raise ValueError("provider returned a non-http media url")
        resp = requests.get(url, timeout=120)
        resp.raise_for_status()
        return resp.content

    def generate_image(
        self,
        prompt,
        *,
        negative,
        aspect_ratio,
        lora_url=None,
        seed=None,
        n=1,
    ) -> list[ImageResult]:
        args: dict = {
            "prompt": prompt,
            "image_size": _image_size_for(aspect_ratio),
            "num_images": n,
        }
        if seed is not None:
            args["seed"] = seed
        model = fal_models.FLUX_TEXT_TO_IMAGE
        if lora_url:
            model = fal_models.FLUX_LORA_INFERENCE
            args["loras"] = [{"path": lora_url, "scale": 1.0}]

        result = self._fal().run(model, arguments=args)
        images = result.get("images") if isinstance(result, dict) else None
        if not isinstance(images, list) or not images:
            raise ValueError("fal image response missing 'images'")
        nsfw_flags = result.get("has_nsfw_concepts") or []
        out: list[ImageResult] = []
        for i, img in enumerate(images):
            if not isinstance(img, dict) or "url" not in img:
                raise ValueError("fal image item missing 'url'")
            out.append(
                ImageResult(
                    data=self._download(img["url"]),
                    seed=result.get("seed") if isinstance(result, dict) else None,
                    nsfw_flag=bool(nsfw_flags[i]) if i < len(nsfw_flags) else False,
                    width=img.get("width"),
                    height=img.get("height"),
                )
            )
        return out

    def image_to_video(self, image, *, prompt, aspect_ratio, duration_s=5):
        # image bytes must be hosted for Kling (image_url). Upload via the fal
        # client's file API, then call the Pro/Master tier that supports 9:16.
        client = self._fal()
        image_url = client.upload(image, "image/png") if hasattr(client, "upload") else None
        if not image_url:
            raise ValueError("fal client cannot host the source image for video")
        args = {
            "prompt": prompt,
            "image_url": image_url,
            "aspect_ratio": aspect_ratio,
            "duration": str(duration_s),
        }
        result = client.run(fal_models.IMAGE_TO_VIDEO_9_16, arguments=args)
        video = result.get("video") if isinstance(result, dict) else None
        if not isinstance(video, dict) or "url" not in video:
            raise ValueError("fal video response missing 'video.url'")
        return VideoResult(data=self._download(video["url"]))

    def train_lora(self, images_zip_url, *, trigger_word, steps=1000):
        args = {
            "images_data_url": images_zip_url,
            "trigger_word": trigger_word,
            "steps": steps,
        }
        result = self._fal().run(fal_models.FLUX_LORA_TRAINING, arguments=args)
        weights = result.get("diffusers_lora_file") if isinstance(result, dict) else None
        if not isinstance(weights, dict) or "url" not in weights:
            raise ValueError("fal training response missing 'diffusers_lora_file.url'")
        return LoraResult(weights_url=weights["url"], config=result.get("config_file") or {})
