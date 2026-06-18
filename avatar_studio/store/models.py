"""Domain records + status enums for the creator studio.

Plain dataclasses + str enums so the core stays dependency-light (no ORM). The
SQLite store maps these 1:1; a Postgres store can reuse the same records later.
"""

from __future__ import annotations

import time
import uuid
from dataclasses import dataclass, field
from enum import Enum


def new_id(prefix: str) -> str:
    return f"{prefix}_{uuid.uuid4().hex[:12]}"


def now() -> float:
    return time.time()


class PersonaStatus(str, Enum):
    DRAFT = "draft"
    TRAINING = "training"
    READY = "ready"
    FAILED = "failed"


class SafetyStatus(str, Enum):
    PENDING = "pending"
    PASSED = "passed"
    BLOCKED = "blocked"


class ReviewStatus(str, Enum):
    PENDING = "pending"
    APPROVED = "approved"
    REJECTED = "rejected"


@dataclass
class Persona:
    name: str
    brand_voice: str = ""
    trigger_word: str = ""
    voice_ref: str = ""
    likeness_lora_url: str = ""
    consent_attestation: bool = False
    status: PersonaStatus = PersonaStatus.DRAFT
    id: str = field(default_factory=lambda: new_id("persona"))
    created_at: float = field(default_factory=now)


@dataclass
class Product:
    name: str
    category: str = ""
    source_image: str = ""
    description: str = ""
    id: str = field(default_factory=lambda: new_id("product"))
    created_at: float = field(default_factory=now)


@dataclass
class Content:
    persona_id: str
    channel: str  # lifestyle | product_ad | tiktok | meta_ad
    kind: str  # image | video
    safety_status: SafetyStatus  # required — never silently unset
    prompt: str = ""
    copy_text: str = ""
    media_path: str = ""
    aspect_ratio: str = ""
    product_id: str | None = None
    review_status: ReviewStatus = ReviewStatus.PENDING
    scheduled_at: float | None = None
    id: str = field(default_factory=lambda: new_id("content"))
    created_at: float = field(default_factory=now)
