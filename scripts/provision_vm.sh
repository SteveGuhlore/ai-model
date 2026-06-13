#!/usr/bin/env bash
# Provision a fresh Ubuntu 22.04 GPU VM for Avatar Studio.
# Assumes an NVIDIA GPU with recent drivers + CUDA already present (most cloud
# GPU images ship this). Run from the repo root:  bash scripts/provision_vm.sh
set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$REPO_ROOT"

echo "==> System packages"
sudo apt-get update -y
sudo apt-get install -y python3-venv python3-pip git git-lfs ffmpeg build-essential
git lfs install

echo "==> Python environment"
python3 -m venv .venv
# shellcheck disable=SC1091
source .venv/bin/activate
pip install --upgrade pip wheel
pip install -e ".[ml,ui,dev]"

echo "==> Third-party model repos"
mkdir -p third_party
[ -d third_party/diffusers ]  || git clone --depth 1 https://github.com/huggingface/diffusers third_party/diffusers
[ -d third_party/SadTalker ]  || git clone --depth 1 https://github.com/OpenTalker/SadTalker third_party/SadTalker
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
