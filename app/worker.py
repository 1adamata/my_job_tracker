import asyncio
import json
import os
from datetime import datetime, timezone

import httpx

from .database import connect

OLLAMA_URL = os.getenv("JOB_QUEUE_OLLAMA_URL", "http://127.0.0.1:11434").rstrip("/")
OLLAMA_MODEL = os.getenv("JOB_QUEUE_MODEL", "ministral-3:3b")


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


SCHEMA = {
    "type": "object",
    "properties": {
        "company_name": {"type": ["string", "null"]},
        "role_title": {"type": ["string", "null"]},
        "location": {"type": ["string", "null"]},
        "location_format": {"type": ["string", "null"]},
        "employment_type": {"type": ["string", "null"]},
        "posted_date": {"type": ["string", "null"]},
        "deadline": {"type": ["string", "null"]},
        "visa_sponsorship": {"type": "string", "enum": ["Yes", "No", "Unclear", "Unknown"]},
        "posted_salary": {"type": ["string", "null"]},
        "requirements": {"type": "array", "items": {"type": "string"}},
        "technologies": {"type": "array", "items": {"type": "string"}},
        "evidence": {"type": "array", "items": {"type": "string"}},
        "notes": {"type": ["string", "null"]},
        "confidence": {"anyOf": [{"type": "number"}, {"type": "null"}]},
    },
    "required": [
        "company_name", "role_title", "location", "location_format", "employment_type",
        "posted_date", "deadline", "visa_sponsorship", "posted_salary", "requirements",
               "technologies", "evidence", "notes", "confidence"
    ],
    "additionalProperties": False,
}


SYSTEM_PROMPT = """Extract job-posting facts. Use only supplied evidence; never guess.
Use null or [] when absent. Salary must be employer-posted, not estimated.
Visa sponsorship: Yes/No only with explicit evidence; otherwise Unclear or Unknown.
Dates should be YYYY-MM-DD only when exact. Return schema-valid JSON only."""


def compact_page(page: dict) -> dict:
    metadata = page.get("meta") or {}
    useful_meta = {
        key: value for key, value in metadata.items()
        if any(word in key.lower() for word in ("title", "description", "job", "salary", "location", "date"))
    }
    return {
        "url": page.get("url"),
        "title": page.get("title"),
        "headings": (page.get("headings") or [])[:30],
        "structured": page.get("structured"),
        "meta": useful_meta,
        "text": (page.get("text") or "")[:8500],
    }


async def extract(page: dict) -> dict:
    body = {
        "model": OLLAMA_MODEL,
        "stream": False,
        "format": SCHEMA,
        "options": {"temperature": 0, "num_ctx": 8192, "num_predict": 1400},
        "messages": [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": json.dumps(compact_page(page), ensure_ascii=False)},
        ],
    }
    async with httpx.AsyncClient(timeout=180, trust_env=False) as client:
        response = await client.post(f"{OLLAMA_URL}/api/chat", json=body)
        response.raise_for_status()
        payload = response.json()
    content = payload.get("message", {}).get("content", "").strip()
    return parse_json(content)


def parse_json(content: str) -> dict:
    cleaned = content.removeprefix("```json").removeprefix("```").removesuffix("```").strip()
    try:
        return json.loads(cleaned)
    except json.JSONDecodeError:
        start, end = cleaned.find("{"), cleaned.rfind("}")
        if start >= 0 and end > start:
            return json.loads(cleaned[start:end + 1])
        raise ValueError("Model output was not valid JSON")


def build_result(job_id: str, page: dict, extracted: dict) -> dict:
    return {
        "id": job_id,
        "captured_at": page.get("capturedAt"),
        "updated_at": now_iso(),
        "source_url": page.get("url"),
        "company_name": extracted.get("company_name") or (page.get("structured") or {}).get("hiringOrganization"),
        "role_title": extracted.get("role_title") or (page.get("structured") or {}).get("title") or page.get("title"),
        "status": "To Apply",
        "date_applied": None,
        "job_description_url": page.get("url"),
        "application_portal_username": None,
        "password_hint": None,
        "location": extracted.get("location"),
        "location_format": extracted.get("location_format"),
        "employment_type": extracted.get("employment_type"),
        "posted_date": extracted.get("posted_date"),
        "deadline": extracted.get("deadline"),
        "visa_sponsorship": extracted.get("visa_sponsorship", "Unknown"),
        "posted_salary": extracted.get("posted_salary"),
        "expected_salary": None,
        "requirements": extracted.get("requirements") or [],
        "technologies": extracted.get("technologies") or [],
        "description_text": page.get("text") or "",
        "resume_version_used": None,
        "portfolio_case_study_attached": None,
        "core_competency_highlighted": None,
        "referral_internal_contact": None,
        "last_contact_date": None,
        "next_action": "Review and apply",
        "next_action_deadline": extracted.get("deadline"),
        "notes": extracted.get("notes"),
        "evidence": extracted.get("evidence") or [],
        "extraction": {"model": OLLAMA_MODEL, "confidence": extracted.get("confidence")},
    }


async def process_next() -> bool:
    with connect() as db:
        row = db.execute(
            "SELECT * FROM jobs WHERE processing_status = 'queued' ORDER BY captured_at LIMIT 1"
        ).fetchone()
        if not row:
            return False
        db.execute(
            "UPDATE jobs SET processing_status='processing', processing_error=NULL, attempts=attempts+1, updated_at=? WHERE id=?",
            (now_iso(), row["id"]),
        )
        job_id = row["id"]
        page = json.loads(row["raw_page_json"])

    try:
        extracted = await extract(page)
        result = build_result(job_id, page, extracted)
        with connect() as db:
            db.execute(
                "UPDATE jobs SET processing_status='completed', result_json=?, updated_at=? WHERE id=?",
                (json.dumps(result, ensure_ascii=False), now_iso(), job_id),
            )
    except Exception as exc:
        with connect() as db:
            db.execute(
                "UPDATE jobs SET processing_status='failed', processing_error=?, updated_at=? WHERE id=?",
                (str(exc)[:1000], now_iso(), job_id),
            )
    return True


async def worker_loop(stop_event: asyncio.Event) -> None:
    while not stop_event.is_set():
        processed = await process_next()
        try:
            await asyncio.wait_for(stop_event.wait(), timeout=0.25 if processed else 1.0)
        except asyncio.TimeoutError:
            pass
