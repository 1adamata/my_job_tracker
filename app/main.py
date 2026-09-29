import asyncio
import csv
import io
import json
import uuid
from contextlib import asynccontextmanager
from datetime import datetime, timezone
from pathlib import Path

from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse, Response
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

from .database import connect, decode_job, init_db, import_tracker
from .chat import answer
from .worker import worker_loop

ROOT = Path(__file__).resolve().parent
FRONTEND_DIST = ROOT.parent / "frontend" / "dist"


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


class CapturePayload(BaseModel):
    url: str
    title: str | None = None
    capturedAt: str | None = None
    language: str | None = None
    headings: list[str] = Field(default_factory=list)
    meta: dict = Field(default_factory=dict)
    structured: dict | None = None
    text: str = ""


class JobPatch(BaseModel):
    values: dict


class ChatRequest(BaseModel):
    question: str = Field(min_length=2, max_length=2000)


class ProfilePayload(BaseModel):
    name: str = ""
    headline: str = ""
    location: str = ""
    target_roles: str = ""
    skills: str = ""
    visa_context: str = ""
    summary: str = ""
    cv_text: str = ""


@asynccontextmanager
async def lifespan(_app: FastAPI):
    init_db()
    stop_event = asyncio.Event()
    task = asyncio.create_task(worker_loop(stop_event))
    yield
    stop_event.set()
    await task


app = FastAPI(title="Local Job Queue", version="2.0.0", lifespan=lifespan)
app.add_middleware(
    CORSMiddleware,
    allow_origin_regex=r"^(chrome-extension://.*|moz-extension://.*|http://127\.0\.0\.1(?::\d+)?|http://localhost(?::\d+)?)$",
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)
app.mount("/static", StaticFiles(directory=ROOT / "static"), name="static")
if (FRONTEND_DIST / "assets").exists():
    app.mount("/assets", StaticFiles(directory=FRONTEND_DIST / "assets"), name="react-assets")


@app.get("/")
def dashboard():
    react_index = FRONTEND_DIST / "index.html"
    return FileResponse(react_index if react_index.exists() else ROOT / "static" / "index.html")


@app.get("/api/health")
def health():
    return {"ok": True}


@app.post("/api/capture")
def capture(payload: CapturePayload):
    page = payload.model_dump()
    page["capturedAt"] = page.get("capturedAt") or now_iso()
    timestamp = now_iso()
    with connect() as db:
        existing = db.execute("SELECT id, processing_status FROM jobs WHERE source_url=?", (page["url"],)).fetchone()
        if existing:
            db.execute(
                "UPDATE jobs SET page_title=?, raw_page_json=?, processing_status='queued', processing_error=NULL, updated_at=? WHERE id=?",
                (page.get("title"), json.dumps(page, ensure_ascii=False), timestamp, existing["id"]),
            )
            return {"ok": True, "id": existing["id"], "status": "queued", "duplicate": True}
        job_id = str(uuid.uuid4())
        db.execute(
            "INSERT INTO jobs(id,source_url,page_title,captured_at,updated_at,raw_page_json) VALUES(?,?,?,?,?,?)",
            (job_id, page["url"], page.get("title"), page["capturedAt"], timestamp, json.dumps(page, ensure_ascii=False)),
        )
    return {"ok": True, "id": job_id, "status": "queued", "duplicate": False}


@app.get("/api/jobs")
def list_jobs():
    with connect() as db:
        rows = db.execute("SELECT * FROM jobs ORDER BY captured_at DESC").fetchall()
    return [decode_job(row) for row in rows]


@app.post("/api/import")
async def import_json(request: Request):
    try:
        return {"ok": True, **import_tracker(await request.json())}
    except (ValueError, json.JSONDecodeError) as exc:
        raise HTTPException(400, str(exc)) from exc


@app.post("/api/chat")
async def chat(payload: ChatRequest):
    try:
        with connect() as db:
            row = db.execute("SELECT value_json FROM settings WHERE key='profile'").fetchone()
        profile = json.loads(row["value_json"]) if row else {}
        return await answer(payload.question, profile)
    except Exception as exc:
        raise HTTPException(503, f"AI chat failed: {str(exc)[:500]}") from exc


@app.get("/api/profile")
def get_profile():
    with connect() as db:
        row = db.execute("SELECT value_json FROM settings WHERE key='profile'").fetchone()
    return json.loads(row["value_json"]) if row else ProfilePayload().model_dump()


@app.put("/api/profile")
def put_profile(profile: ProfilePayload):
    payload = json.dumps(profile.model_dump(), ensure_ascii=False)
    with connect() as db:
        db.execute("INSERT OR REPLACE INTO settings(key,value_json,updated_at) VALUES('profile',?,?)", (payload, now_iso()))
    return {"ok": True, "profile": profile.model_dump()}


@app.post("/api/jobs/{job_id}/retry")
def retry(job_id: str):
    with connect() as db:
        result = db.execute(
            "UPDATE jobs SET processing_status='queued', processing_error=NULL, updated_at=? WHERE id=?",
            (now_iso(), job_id),
        )
    if not result.rowcount:
        raise HTTPException(404, "Job not found")
    return {"ok": True}


@app.patch("/api/jobs/{job_id}")
def update_job(job_id: str, patch: JobPatch):
    with connect() as db:
        row = db.execute("SELECT result_json FROM jobs WHERE id=?", (job_id,)).fetchone()
        if not row:
            raise HTTPException(404, "Job not found")
        result = json.loads(row["result_json"]) if row["result_json"] else {}
        allowed = {
            "company_name", "role_title", "status", "date_applied", "location", "location_format",
            "posted_salary", "expected_salary", "resume_version_used", "portfolio_case_study_attached",
            "core_competency_highlighted", "referral_internal_contact", "last_contact_date",
            "next_action", "next_action_deadline", "notes",
        }
        result.update({key: value for key, value in patch.values.items() if key in allowed})
        result["updated_at"] = now_iso()
        db.execute("UPDATE jobs SET result_json=?, updated_at=? WHERE id=?", (json.dumps(result, ensure_ascii=False), now_iso(), job_id))
    return {"ok": True, "result": result}


@app.delete("/api/jobs/{job_id}")
def delete_job(job_id: str):
    with connect() as db:
        result = db.execute("DELETE FROM jobs WHERE id=?", (job_id,))
    if not result.rowcount:
        raise HTTPException(404, "Job not found")
    return {"ok": True}


@app.get("/api/export.json")
def export_json():
    return JSONResponse({"schema_version": 1, "exported_at": now_iso(), "jobs": list_jobs()})


@app.get("/api/export.csv")
def export_csv():
    rows = []
    for job in list_jobs():
        result = job.get("result") or {}
        rows.append({
            "company_name": result.get("company_name"), "role_title": result.get("role_title") or job.get("page_title"),
            "status": result.get("status"), "date_applied": result.get("date_applied"), "location": result.get("location"),
            "location_format": result.get("location_format"), "deadline": result.get("deadline"),
            "visa_sponsorship": result.get("visa_sponsorship"), "posted_salary": result.get("posted_salary"),
            "expected_salary": result.get("expected_salary"), "next_action": result.get("next_action"),
            "next_action_deadline": result.get("next_action_deadline"), "source_url": job.get("source_url"),
            "processing_status": job.get("processing_status"), "captured_at": job.get("captured_at"),
        })
    output = io.StringIO()
    fields = list(rows[0].keys()) if rows else ["company_name", "role_title", "status", "source_url"]
    writer = csv.DictWriter(output, fieldnames=fields)
    writer.writeheader(); writer.writerows(rows)
    return Response(output.getvalue(), media_type="text/csv", headers={"Content-Disposition": "attachment; filename=job-tracker.csv"})
