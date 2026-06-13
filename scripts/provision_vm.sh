#!/usr/bin/env bash
# Provision a GPU box for Avatar Studio (a RunPod/Vast pod or an Ubuntu/Debian
# GPU VM). Assumes an NVIDIA GPU with recent drivers + CUDA already present
# (cloud GPU images and PyTorch pod templates ship this).
# Run from the repo root:  bash scripts/provision_vm.sh
set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$REPO_ROOT"

# Use sudo only when present and not already root (pods run as root).
SUDO=""
if [ "$(id -u)" -ne 0 ] && command -v sudo >/dev/null 2>&1; then
  SUDO="sudo"
fi

echo "==> System packages"
$SUDO apt-get update -y
$SUDO apt-get install -y python3-venv python3-pip git git-lfs ffmpeg build-essential curl
git lfs install

echo "==> Python environment"
# --system-site-packages reuses a pod template's preinstalled CUDA PyTorch
# (avoids re-downloading a possibly CPU-only torch into the venv).
python3 -m venv .venv --system-site-packages
# shellcheck disable=SC1091
source .venv/bin/activate
pip install --upgrade pip wheel
pip install -e ".[ml,ui,dev]"

echo "==> Third-party model repos"
mkdir -p third_party
[ -d third_party/diffusers ]  || git clone --depth 1 https://github.com/huggingface/diffusers third_party/diffusers
[ -d third_party/SadTalker ]  || git clone --depth 1 https://github.com/OpenTalker/SadTalker third_party/SadTalker
# Extra deps the diffusers DreamBooth-LoRA SDXL trainer expects (ftfy, tensorboard, ...)
pip install -r third_party/diffusers/examples/dreambooth/requirements_sdxl.txt
pip install -r third_party/SadTalker/requirements.txt

echo "==> SadTalker checkpoints"
( cd third_party/SadTalker && bash scripts/download_models.sh )

echo "==> Ollama (local LLM brain)"
if ! command -v ollama >/dev/null 2>&1; then
  curl -fsSL https://ollama.com/install.sh | sh
fi
ollama pull "${OLLAMA_MODEL:-llama3.1:8b-instruct-q4_K_M}" || true

echo "==> Diffusion / TTS / NSFW-classifier weights"
python scripts/download_models.py

cat <<'NEXT'

Provisioning complete.

Easiest path — launch the clickable control panel:
    source .venv/bin/activate
    python -m avatar_studio.ui.studio
Then from your laptop:  ssh -L 7860:localhost:7860 user@this-vm
and open http://localhost:7860  (Tab 1 upload+train, Tab 2 face, Tab 3 chat).

Prefer the command line?
  1) Put 15-30 of YOUR photos in assets/me/ and a ~10s voice clip at
     assets/voice_ref.wav  (only your own likeness / consented voice).
  2) python -m avatar_studio.face.train_lora --instance-data assets/me \
       --output models/likeness-lora   (then set AVATAR_LORA_PATH)
  3) Generate a reference face and save it as assets/face.png.
  4) uvicorn avatar_studio.api.app:app --host 0.0.0.0 --port 8000
NEXT
