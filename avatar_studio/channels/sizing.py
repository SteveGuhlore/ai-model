"""Platform sizing specs.

Maps a named placement to exact 1080-class pixel dimensions and the logical
aspect-ratio string the provider understands (the FalProvider maps that to a
Flux ``image_size`` preset). Flux presets are ~1024px, so ``resize_to`` upscales/
pads generated images to the exact platform target.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class Spec:
    width: int
    height: int
    aspect_ratio: str


# Confirmed targets from reviews/research-fal-meta-tiktok.md.
SPECS: dict[str, Spec] = {
    "tiktok": Spec(1080, 1920, "9:16"),
    "ig_story": Spec(1080, 1920, "9:16"),
    "reels": Spec(1080, 1920, "9:16"),
    "ig_portrait": Spec(1080, 1350, "4:5"),
    "ig_square": Spec(1080, 1080, "1:1"),
    "meta_feed": Spec(1080, 1080, "1:1"),
}


def spec_for(name: str) -> Spec:
    try:
        return SPECS[name]
    except KeyError as exc:  # no silent default
        raise ValueError(f"unknown placement {name!r}") from exc


def resize_to(image_bytes: bytes, spec: Spec) -> bytes:
    """Resize+center-crop an image to the exact platform target (best-effort).

    Used on the real generation path. Raises on a genuinely undecodable image so
    a corrupt provider response surfaces rather than passing through silently.
    """
    import io

    from PIL import Image

    img = Image.open(io.BytesIO(image_bytes)).convert("RGB")
    # cover-fit: scale to fill, then center-crop to target.
    scale = max(spec.width / img.width, spec.height / img.height)
    resized = img.resize((round(img.width * scale), round(img.height * scale)))
    left = (resized.width - spec.width) // 2
    top = (resized.height - spec.height) // 2
    cropped = resized.crop((left, top, left + spec.width, top + spec.height))
    out = io.BytesIO()
    cropped.save(out, format="PNG")
    return out.getvalue()
