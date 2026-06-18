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

# Provider media is served from fal's CDN. Restrict downloads to these apexes so a
# compromised/spoofed provider response can't point _download at internal hosts
# (SSRF). Confirm against fal's CDN docs if hosts change.
_ALLOWED_DOWNLOAD_APEXES = ("fal.media", "fal.run", "fal.ai")
_MAX_DOWNLOAD_BYTES = 64 * 1024 * 1024  # cap response size to avoid OOM DoS


def _host_allowed(host: str) -> bool:
    """Pure hostname allowlist (no DNS): host must be (or be a subdomain of) a fal
    apex. Raw IP literals are NEVER allowed — a bare IP can't be a fal CDN host, and
    auto-allowing public IPs would defeat the allowlist (SSRF). DNS-resolution
    validation (rebinding defense) happens in _resolve_safe at download time."""
    import ipaddress

    host = (host or "").lower().strip("[]")  # strip IPv6 brackets
    try:
        ipaddress.ip_address(host)
        return False
    except ValueError:
        pass  # not an IP literal — apply the apex allowlist
    return any(host == a or host.endswith("." + a) for a in _ALLOWED_DOWNLOAD_APEXES)


def _resolve_safe(host: str) -> bool:
    """Resolve host and reject if ANY address is internal (DNS-rebinding defense)."""
    import ipaddress
    import socket

    try:
        infos = socket.getaddrinfo(host, None)
    except socket.gaierror:
        return False
    for info in infos:
        try:
            ip = ipaddress.ip_address(info[4][0].split("%")[0])
        except ValueError:
            return False
        if (
            ip.is_private
            or ip.is_loopback
            or ip.is_link_local
            or ip.is_reserved
            or ip.is_multicast
            or ip.is_unspecified
        ):
            return False
    return True

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
    def _download(
        url: str, *, max_bytes: int = _MAX_DOWNLOAD_BYTES, max_redirects: int = 5
    ) -> bytes:
        import urllib.parse

        import requests

        # Redirects are followed MANUALLY with full re-validation each hop —
        # requests' default redirect following would let a 302 -> 169.254.169.254
        # bypass the allowlist (SSRF).
        current = url
        for _hop in range(max_redirects + 1):
            if not isinstance(current, str) or not current.startswith("https://"):
                raise ValueError("provider returned a non-https media url")
            host = urllib.parse.urlparse(current).hostname or ""
            if not _host_allowed(host) or not _resolve_safe(host):
                raise ValueError(f"refusing to download from disallowed host {host!r}")

            resp = requests.get(current, timeout=120, stream=True, allow_redirects=False)
            if resp.is_redirect or resp.status_code in (301, 302, 303, 307, 308):
                location = resp.headers.get("Location")
                resp.close()
                if not location:
                    raise ValueError("redirect with no Location header")
                current = urllib.parse.urljoin(current, location)
                continue

            # Terminal response — stream with a hard size cap (Content-Length is
            # attacker-controlled, so count bytes as they arrive).
            with resp:
                resp.raise_for_status()
                chunks, total = [], 0
                for chunk in resp.iter_content(chunk_size=65536):
                    total += len(chunk)
                    if total > max_bytes:
                        raise ValueError("provider media exceeds max download size")
                    chunks.append(chunk)
            return b"".join(chunks)
        raise ValueError("too many redirects")

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
            # Per-image seed if fal returns one; the batch seed only describes the
            # first image, so don't mislabel the rest with it.
            if "seed" in img:
                img_seed = img.get("seed")
            elif i == 0:
                img_seed = result.get("seed")
            else:
                img_seed = None
            out.append(
                ImageResult(
                    data=self._download(img["url"]),
                    seed=img_seed,
                    # nsfw_flag is a cheap pre-gate hint only; the media gate is the
                    # authoritative fail-closed screen, so an absent flag (False
                    # here) still gets caught downstream.
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
        # Pass through the provider NSFW hint when present (cheap early drop; the
        # media gate frame-samples the video regardless).
        nsfw_flags = result.get("has_nsfw_concepts") or []
        return VideoResult(
            data=self._download(video["url"]),
            nsfw_flag=bool(nsfw_flags[0]) if nsfw_flags else False,
        )

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
