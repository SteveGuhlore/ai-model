"""Background job runner for slow provider work (training, generation batches).

Local-first and dependency-free: a small ThreadPoolExecutor updates a jobs table
in the store as work progresses, so the API can return immediately and the client
polls ``GET /jobs/{id}``. No Redis/Celery — fine for a single-process tool, and the
store serializes its own SQLite access across threads.

``inline=True`` runs the work synchronously inside ``submit`` (used by tests so
job outcomes are deterministic without polling or sleeps).
"""

from __future__ import annotations

import json
from concurrent.futures import ThreadPoolExecutor
from typing import Callable

from avatar_studio.store.models import Job, JobStatus
from avatar_studio.store.sqlite_store import SqliteStore


class JobRunner:
    def __init__(self, store: SqliteStore, inline: bool = False, max_workers: int = 2) -> None:
        self._store = store
        self._inline = inline
        self._pool = None if inline else ThreadPoolExecutor(max_workers=max_workers)

    def submit(
        self,
        kind: str,
        fn: Callable[[], object],
        *,
        persona_id: str | None = None,
        params: dict | None = None,
    ) -> Job:
        job = self._store.create_job(
            Job(kind=kind, persona_id=persona_id, params=json.dumps(params or {}))
        )
        if self._inline:
            self._run(job.id, fn)
        else:
            self._pool.submit(self._run, job.id, fn)
        return self._store.get_job(job.id)

    def _run(self, job_id: str, fn: Callable[[], object]) -> None:
        self._store.update_job(job_id, status=JobStatus.RUNNING)
        try:
            result = fn()
            self._store.update_job(
                job_id, status=JobStatus.SUCCEEDED, result=json.dumps(result or {})
            )
        except Exception as exc:  # any failure is recorded, never crashes the worker
            self._store.update_job(job_id, status=JobStatus.FAILED, error=str(exc))

    def shutdown(self) -> None:
        if self._pool is not None:
            self._pool.shutdown(wait=False)
