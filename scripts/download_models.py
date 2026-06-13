"""Pre-download the model weights so first request isn't a cold start.

Pulls the SDXL base, the SDXL fp16 VAE, and the NSFW image classifier into the
local Hugging Face cache. XTTS-v2 downloads on first synth via the TTS library.
Run after installing the `ml` extra (see scripts/provision_vm.sh).
"""

from __future__ import annotations

from avatar_studio.config import Settings


def main() -> None:
    settings = Settings.from_env()

    from huggingface_hub import snapshot_download

    print(f"==> SDXL base: {settings.sdxl_base}")
    snapshot_download(settings.sdxl_base)

    print("==> SDXL fp16 VAE: madebyollin/sdxl-vae-fp16-fix")
    snapshot_download("madebyollin/sdxl-vae-fp16-fix")

    print(f"==> NSFW classifier: {settings.nsfw_classifier}")
    snapshot_download(settings.nsfw_classifier)

    print("Done. (XTTS-v2 voice model downloads on first synthesis.)")


if __name__ == "__main__":
    main()
