# GPU runtime image for Avatar Studio.
# Requires the NVIDIA Container Toolkit on the host (`--gpus all`).
FROM nvidia/cuda:12.1.1-cudnn8-runtime-ubuntu22.04

ENV DEBIAN_FRONTEND=noninteractive \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1

RUN apt-get update && apt-get install -y --no-install-recommends \
        python3 python3-venv python3-pip git git-lfs ffmpeg \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app
COPY pyproject.toml ./
COPY avatar_studio ./avatar_studio
RUN pip install --upgrade pip wheel && pip install -e ".[ml]"

EXPOSE 8000
CMD ["uvicorn", "avatar_studio.api.app:app", "--host", "0.0.0.0", "--port", "8000"]
