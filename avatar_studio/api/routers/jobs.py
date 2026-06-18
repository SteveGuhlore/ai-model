"""Job status endpoints — poll the progress of async training/generation work."""

from __future__ import annotations

import json

from fastapi import APIRouter, HTTPException

from avatar_studio.api.deps import store
from avatar_studio.store.models import Job

router = APIRouter(tags=["jobs"])


def job_out(job: Job) -> dict:
    try:
        result = json.loads(job.result) if job.result else None
    except json.JSONDecodeError:
        result = None
    return {
        "id": job.id,
        "kind": job.kind,
        "status": job.status.value,
        "persona_id": job.persona_id,
        "result": result,
        "error": job.error,
    }


@router.get("/jobs/{job_id}")
def get_job(job_id: str):
    job = store().get_job(job_id)
    if job is None:
        raise HTTPException(404, "job not found")
    return job_out(job)


@router.get("/jobs")
def list_jobs(persona_id: str | None = None):
    return [job_out(j) for j in store().list_jobs(persona_id)]
