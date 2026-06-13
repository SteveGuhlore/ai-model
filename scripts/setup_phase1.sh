#!/usr/bin/env bash
# Minimal setup for PHASE 1: train a likeness LoRA + generate images.
# Skips the talking-head (SadTalker) and chat (Ollama) pieces to save time and
# money on an hourly GPU pod. Run from the repo root:
#   bash scripts/setup_phase1.sh
set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$REPO_ROOT"

SUDO=""
if [ "$(id -u)" -ne 0 ] && command -v sudo >/dev/null 2>&1; then
  SUDO="sudo"
fi

echo "==> System packages"
$SUDO apt-get update -y
$SUDO apt-get install -y python3-venv python3-pip git ffmpeg build-essential curl

echo "==> Python environment"
python3 -m venv .venv --system-site-packages
# shellcheck disable=SC1091
source .venv/bin/activate
pip install --upgrade pip wheel
pip install -e ".[ml,ui,dev]"

echo "==> diffusers LoRA trainer"
mkdir -p third_party
[ -d third_party/diffusers ] || git clone --depth 1 https://github.com/huggingface/diffusers third_party/diffusers
pip install -r third_party/diffusers/examples/dreambooth/requirements_sdxl.txt

echo "==> Downloading SDXL base, VAE, and NSFW classifier (several GB)"
python scripts/download_models.py

cat <<'NEXT'

Phase 1 ready. Launch the control panel:

    source .venv/bin/activate
    python -m avatar_studio.ui.studio        # serves on port 7860

Open the pod's port-7860 proxy URL, then:
  Tab 1: upload 15-30 of your photos  ->  click "Train likeness LoRA" (~20-40 min)
  When it finishes, in a terminal:
    export AVATAR_LORA_PATH=$(ls models/likeness-lora/*.safetensors | head -1)
  then restart the UI and use Tab 2 to generate your first faces.

IMPORTANT: download models/likeness-lora/ and outputs/ BEFORE you stop or
terminate the pod, or you'll lose them.
NEXT
