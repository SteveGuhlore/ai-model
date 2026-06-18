"""Async job runner + job store."""

import json

from avatar_studio.jobs.runner import JobRunner
from avatar_studio.store.models import JobStatus
from avatar_studio.store.sqlite_store import SqliteStore


def make_store(tmp_path):
    return SqliteStore(db_url=f"sqlite:///{tmp_path}/c.db", media_dir=str(tmp_path / "m"))


def test_inline_job_succeeds_and_stores_result(tmp_path):
    store = make_store(tmp_path)
    runner = JobRunner(store, inline=True)
    job = runner.submit("demo", lambda: {"answer": 42}, persona_id="p1")
    assert job.status is JobStatus.SUCCEEDED
    got = store.get_job(job.id)
    assert json.loads(got.result) == {"answer": 42}
    assert got.persona_id == "p1"


def test_inline_job_records_failure(tmp_path):
    store = make_store(tmp_path)
    runner = JobRunner(store, inline=True)

    def boom():
        raise RuntimeError("kaboom")

    job = runner.submit("demo", boom)
    got = store.get_job(job.id)
    assert got.status is JobStatus.FAILED
    assert "kaboom" in got.error


def test_threaded_job_eventually_completes(tmp_path):
    import time

    store = make_store(tmp_path)
    runner = JobRunner(store, inline=False, max_workers=1)
    job = runner.submit("demo", lambda: {"ok": True})
    deadline = time.time() + 5
    while time.time() < deadline:
        if store.get_job(job.id).status in (JobStatus.SUCCEEDED, JobStatus.FAILED):
            break
        time.sleep(0.02)
    assert store.get_job(job.id).status is JobStatus.SUCCEEDED
    runner.shutdown()


def test_list_jobs_filters_by_persona(tmp_path):
    store = make_store(tmp_path)
    runner = JobRunner(store, inline=True)
    runner.submit("a", lambda: {}, persona_id="p1")
    runner.submit("b", lambda: {}, persona_id="p2")
    assert len(store.list_jobs(persona_id="p1")) == 1
    assert len(store.list_jobs()) == 2
