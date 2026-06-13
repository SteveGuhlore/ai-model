"""Avatar Studio — a self-hosted, SFW talking-avatar pipeline.

Components:
  - face/        likeness image generation (SDXL + your LoRA)
  - voice/       text-to-speech with optional voice cloning (XTTS)
  - talkinghead/ audio-driven lip-synced video (SadTalker)
  - persona/     the conversational "brain" (local LLM via Ollama)
  - safety/      SFW guardrails for text and generated media
  - pipeline     orchestrates a single conversational turn end to end

The pipeline and safety/text layers are dependency-light and unit-tested.
The model wrappers lazily import the heavy ML stack so the package stays
importable (and testable) without a GPU.
"""

__version__ = "0.1.0"
