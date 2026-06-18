"""SQLite-backed store implementing the persona/product/content repositories.

Local-first: stdlib sqlite3 + filesystem media. The repository methods are the
seam a Postgres/object-storage implementation can replace later without touching
callers. Media bytes live on disk under ``media_dir``; rows store relative paths.
"""

from __future__ import annotations

import os
import sqlite3
import threading
from dataclasses import asdict

from avatar_studio.store.models import (
    Content,
    Job,
    JobStatus,
    Persona,
    PersonaStatus,
    Product,
    ReviewStatus,
    SafetyStatus,
    now,
)

_SCHEMA = """
CREATE TABLE IF NOT EXISTS personas (
    id TEXT PRIMARY KEY, name TEXT NOT NULL, brand_voice TEXT, trigger_word TEXT,
    voice_ref TEXT, likeness_lora_url TEXT, consent_attestation INTEGER,
    status TEXT, created_at REAL
);
CREATE TABLE IF NOT EXISTS products (
    id TEXT PRIMARY KEY, name TEXT NOT NULL, category TEXT, source_image TEXT,
    description TEXT, created_at REAL
);
CREATE TABLE IF NOT EXISTS content (
    id TEXT PRIMARY KEY, persona_id TEXT NOT NULL, channel TEXT, kind TEXT,
    safety_status TEXT NOT NULL, prompt TEXT, copy_text TEXT, media_path TEXT,
    aspect_ratio TEXT, product_id TEXT, review_status TEXT, scheduled_at REAL,
    created_at REAL
);
CREATE TABLE IF NOT EXISTS jobs (
    id TEXT PRIMARY KEY, kind TEXT, status TEXT NOT NULL, persona_id TEXT,
    params TEXT, result TEXT, error TEXT, created_at REAL, updated_at REAL
);
"""


def _sqlite_path(db_url: str) -> str:
    # Accept "sqlite:///path" or a bare path.
    if db_url.startswith("sqlite:///"):
        return db_url[len("sqlite:///") :]
    return db_url


class SqliteStore:
    def __init__(self, db_url: str = "sqlite:///creator.db", media_dir: str = "media") -> None:
        self.path = _sqlite_path(db_url)
        self.media_dir = media_dir
        os.makedirs(self.media_dir, exist_ok=True)
        parent = os.path.dirname(self.path)
        if parent:
            os.makedirs(parent, exist_ok=True)
        # check_same_thread=False: the API serves handlers from a threadpool.
        # All access is serialized through self._lock to stay safe.
        self._lock = threading.Lock()
        self._conn = sqlite3.connect(self.path, check_same_thread=False)
        self._conn.row_factory = sqlite3.Row
        with self._lock:
            self._conn.executescript(_SCHEMA)
            self._conn.commit()

    def close(self) -> None:
        self._conn.close()

    # --- personas -------------------------------------------------------
    def create_persona(self, persona: Persona) -> Persona:
        with self._lock:
            self._conn.execute(
                "INSERT INTO personas VALUES (:id,:name,:brand_voice,:trigger_word,"
                ":voice_ref,:likeness_lora_url,:consent_attestation,:status,:created_at)",
                {
                    **asdict(persona),
                    "consent_attestation": int(persona.consent_attestation),
                    "status": persona.status.value,
                },
            )
            self._conn.commit()
        return persona

    def get_persona(self, persona_id: str) -> Persona | None:
        with self._lock:
            row = self._conn.execute(
                "SELECT * FROM personas WHERE id=?", (persona_id,)
            ).fetchone()
        return self._row_to_persona(row) if row else None

    def list_personas(self) -> list[Persona]:
        with self._lock:
            rows = self._conn.execute(
                "SELECT * FROM personas ORDER BY created_at"
            ).fetchall()
        return [self._row_to_persona(r) for r in rows]

    def update_persona(self, persona: Persona) -> Persona:
        with self._lock:
            self._conn.execute(
                "UPDATE personas SET name=:name, brand_voice=:brand_voice,"
                " trigger_word=:trigger_word, voice_ref=:voice_ref,"
                " likeness_lora_url=:likeness_lora_url,"
                " consent_attestation=:consent_attestation, status=:status WHERE id=:id",
                {
                    **asdict(persona),
                    "consent_attestation": int(persona.consent_attestation),
                    "status": persona.status.value,
                },
            )
            self._conn.commit()
        return persona

    @staticmethod
    def _row_to_persona(row: sqlite3.Row) -> Persona:
        return Persona(
            id=row["id"],
            name=row["name"],
            brand_voice=row["brand_voice"] or "",
            trigger_word=row["trigger_word"] or "",
            voice_ref=row["voice_ref"] or "",
            likeness_lora_url=row["likeness_lora_url"] or "",
            consent_attestation=bool(row["consent_attestation"]),
            status=PersonaStatus(row["status"]),
            created_at=row["created_at"],
        )

    # --- products -------------------------------------------------------
    def create_product(self, product: Product) -> Product:
        with self._lock:
            self._conn.execute(
                "INSERT INTO products VALUES (:id,:name,:category,:source_image,"
                ":description,:created_at)",
                asdict(product),
            )
            self._conn.commit()
        return product

    def get_product(self, product_id: str) -> Product | None:
        with self._lock:
            row = self._conn.execute(
                "SELECT * FROM products WHERE id=?", (product_id,)
            ).fetchone()
        if not row:
            return None
        return Product(
            id=row["id"],
            name=row["name"],
            category=row["category"] or "",
            source_image=row["source_image"] or "",
            description=row["description"] or "",
            created_at=row["created_at"],
        )

    # --- content --------------------------------------------------------
    def create_content(self, content: Content) -> Content:
        # safety_status is a required field on Content; this guards the invariant
        # that content is never persisted without a screening verdict recorded.
        if not isinstance(content.safety_status, SafetyStatus):
            raise ValueError("content.safety_status must be a SafetyStatus")
        with self._lock:
            self._conn.execute(
                "INSERT INTO content VALUES (:id,:persona_id,:channel,:kind,"
                ":safety_status,:prompt,:copy_text,:media_path,:aspect_ratio,"
                ":product_id,:review_status,:scheduled_at,:created_at)",
                {
                    **asdict(content),
                    "safety_status": content.safety_status.value,
                    "review_status": content.review_status.value,
                },
            )
            self._conn.commit()
        return content

    def get_content(self, content_id: str) -> Content | None:
        with self._lock:
            row = self._conn.execute(
                "SELECT * FROM content WHERE id=?", (content_id,)
            ).fetchone()
        return self._row_to_content(row) if row else None

    def list_content(
        self, persona_id: str | None = None, review_status: ReviewStatus | None = None
    ) -> list[Content]:
        q = "SELECT * FROM content"
        clauses, params = [], []
        if persona_id:
            clauses.append("persona_id=?")
            params.append(persona_id)
        if review_status:
            clauses.append("review_status=?")
            params.append(review_status.value)
        if clauses:
            q += " WHERE " + " AND ".join(clauses)
        q += " ORDER BY created_at"
        with self._lock:
            rows = self._conn.execute(q, params).fetchall()
        return [self._row_to_content(r) for r in rows]

    def set_review_status(self, content_id: str, status: ReviewStatus) -> None:
        with self._lock:
            self._conn.execute(
                "UPDATE content SET review_status=? WHERE id=?",
                (status.value, content_id),
            )
            self._conn.commit()

    @staticmethod
    def _row_to_content(row: sqlite3.Row) -> Content:
        return Content(
            id=row["id"],
            persona_id=row["persona_id"],
            channel=row["channel"],
            kind=row["kind"],
            safety_status=SafetyStatus(row["safety_status"]),
            prompt=row["prompt"] or "",
            copy_text=row["copy_text"] or "",
            media_path=row["media_path"] or "",
            aspect_ratio=row["aspect_ratio"] or "",
            product_id=row["product_id"],
            review_status=ReviewStatus(row["review_status"]),
            scheduled_at=row["scheduled_at"],
            created_at=row["created_at"],
        )

    # --- jobs -----------------------------------------------------------
    def create_job(self, job: Job) -> Job:
        with self._lock:
            self._conn.execute(
                "INSERT INTO jobs VALUES (:id,:kind,:status,:persona_id,:params,"
                ":result,:error,:created_at,:updated_at)",
                {**asdict(job), "status": job.status.value},
            )
            self._conn.commit()
        return job

    def get_job(self, job_id: str) -> Job | None:
        with self._lock:
            row = self._conn.execute("SELECT * FROM jobs WHERE id=?", (job_id,)).fetchone()
        return self._row_to_job(row) if row else None

    def list_jobs(self, persona_id: str | None = None) -> list[Job]:
        q = "SELECT * FROM jobs"
        params: list = []
        if persona_id:
            q += " WHERE persona_id=?"
            params.append(persona_id)
        q += " ORDER BY created_at DESC"
        with self._lock:
            rows = self._conn.execute(q, params).fetchall()
        return [self._row_to_job(r) for r in rows]

    def update_job(
        self,
        job_id: str,
        *,
        status: JobStatus,
        result: str | None = None,
        error: str | None = None,
    ) -> None:
        with self._lock:
            self._conn.execute(
                "UPDATE jobs SET status=?, result=COALESCE(?,result),"
                " error=COALESCE(?,error), updated_at=? WHERE id=?",
                (status.value, result, error, now(), job_id),
            )
            self._conn.commit()

    @staticmethod
    def _row_to_job(row: sqlite3.Row) -> Job:
        return Job(
            id=row["id"],
            kind=row["kind"],
            status=JobStatus(row["status"]),
            persona_id=row["persona_id"],
            params=row["params"] or "{}",
            result=row["result"] or "",
            error=row["error"] or "",
            created_at=row["created_at"],
            updated_at=row["updated_at"],
        )
