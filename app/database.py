import json
import os
import sqlite3
import uuid
from datetime import datetime, timezone
from contextlib import contextmanager
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DATA_DIR = Path(os.getenv("JOB_QUEUE_DATA_DIR", str(ROOT / "data")))
DB_PATH = DATA_DIR / "jobs.db"


def init_db() -> None:
    DATA_DIR.mkdir(exist_ok=True)
    with connect() as db:
        db.executescript(
            """
            CREATE TABLE IF NOT EXISTS jobs (
                id TEXT PRIMARY KEY,
                source_url TEXT NOT NULL UNIQUE,
                page_title TEXT,
                captured_at TEXT NOT NULL,
                updated_at TEXT NOT NULL,
                processing_status TEXT NOT NULL DEFAULT 'queued',
                processing_error TEXT,
                raw_page_json TEXT NOT NULL,
                result_json TEXT,
                attempts INTEGER NOT NULL DEFAULT 0
            );
            CREATE INDEX IF NOT EXISTS idx_jobs_processing
            ON jobs(processing_status, captured_at);
            CREATE TABLE IF NOT EXISTS embeddings (
                job_id TEXT PRIMARY KEY,
                model TEXT NOT NULL,
                content_hash TEXT NOT NULL,
                vector_json TEXT NOT NULL,
                updated_at TEXT NOT NULL,
                FOREIGN KEY(job_id) REFERENCES jobs(id) ON DELETE CASCADE
            );
            CREATE TABLE IF NOT EXISTS settings (
                key TEXT PRIMARY KEY,
                value_json TEXT NOT NULL,
                updated_at TEXT NOT NULL
            );
            """
        )
        db.execute(
            "UPDATE jobs SET processing_status='queued', processing_error='Recovered after application restart' "
            "WHERE processing_status='processing'"
        )


@contextmanager
def connect():
    DATA_DIR.mkdir(exist_ok=True)
    db = sqlite3.connect(DB_PATH, timeout=20)
    db.row_factory = sqlite3.Row
    db.execute("PRAGMA foreign_keys = ON")
    try:
        yield db
        db.commit()
    finally:
        db.close()


def decode_job(row: sqlite3.Row) -> dict:
    item = dict(row)
    item["raw_page"] = json.loads(item.pop("raw_page_json"))
    result_json = item.pop("result_json")
    item["result"] = json.loads(result_json) if result_json else None
    return item


def import_tracker(data: dict | list) -> dict:
    source_jobs = data.get("jobs", []) if isinstance(data, dict) else data
    if not isinstance(source_jobs, list):
        raise ValueError("Expected a JSON object containing a jobs list")
    inserted = updated = skipped = 0
    with connect() as db:
        for source in source_jobs:
            if not isinstance(source, dict):
                skipped += 1; continue
            result = source.get("result") if isinstance(source.get("result"), dict) else source
            url = result.get("source_url") or source.get("source_url") or result.get("job_description_url")
            if not url:
                skipped += 1; continue
            job_id = source.get("id") or result.get("id") or str(uuid.uuid4())
            captured = source.get("captured_at") or result.get("captured_at") or datetime.now(timezone.utc).isoformat()
            title = result.get("role_title") or source.get("page_title")
            raw_page = source.get("raw_page") if isinstance(source.get("raw_page"), dict) else {
                "url": url, "title": title, "capturedAt": captured,
                "text": result.get("description_text") or "", "headings": [], "meta": {}, "structured": None,
            }
            existing = db.execute("SELECT id FROM jobs WHERE source_url=?", (url,)).fetchone()
            payload = json.dumps(result, ensure_ascii=False)
            raw_payload = json.dumps(raw_page, ensure_ascii=False)
            if existing:
                db.execute(
                    "UPDATE jobs SET page_title=?, raw_page_json=?, result_json=?, processing_status='completed', updated_at=? WHERE id=?",
                    (title, raw_payload, payload, datetime.now(timezone.utc).isoformat(), existing["id"]),
                )
                db.execute("DELETE FROM embeddings WHERE job_id=?", (existing["id"],))
                updated += 1
            else:
                db.execute(
                    "INSERT INTO jobs(id,source_url,page_title,captured_at,updated_at,processing_status,raw_page_json,result_json) VALUES(?,?,?,?,?,'completed',?,?)",
                    (job_id, url, title, captured, datetime.now(timezone.utc).isoformat(), raw_payload, payload),
                )
                inserted += 1
    return {"inserted": inserted, "updated": updated, "skipped": skipped, "total": len(source_jobs)}
