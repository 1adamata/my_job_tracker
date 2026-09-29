import hashlib
import json
import math
import os
from collections import Counter

import httpx

from .database import connect, decode_job

OLLAMA_URL = os.getenv("JOB_QUEUE_OLLAMA_URL", "http://127.0.0.1:11434").rstrip("/")
CHAT_MODEL = os.getenv("JOB_QUEUE_MODEL", "ministral-3:3b")
EMBED_MODEL = os.getenv("JOB_QUEUE_EMBED_MODEL", "nomic-embed-text:latest")


def document(result: dict) -> str:
    fields = [
        result.get("company_name"), result.get("role_title"), result.get("location"),
        result.get("location_format"), result.get("employment_type"), result.get("visa_sponsorship"),
        result.get("posted_salary"), " ".join(result.get("requirements") or []),
        " ".join(result.get("technologies") or []), (result.get("description_text") or "")[:6000],
    ]
    return "\n".join(str(value) for value in fields if value)


async def ollama_embeddings(inputs: list[str]) -> list[list[float]]:
    async with httpx.AsyncClient(timeout=180, trust_env=False) as client:
        response = await client.post(f"{OLLAMA_URL}/api/embed", json={"model": EMBED_MODEL, "input": inputs})
        response.raise_for_status()
        return response.json()["embeddings"]


def cosine(a: list[float], b: list[float]) -> float:
    dot = sum(x*y for x,y in zip(a,b)); na = math.sqrt(sum(x*x for x in a)); nb = math.sqrt(sum(y*y for y in b))
    return dot / (na * nb) if na and nb else 0.0


async def retrieve(question: str, jobs: list[dict], limit: int = 5) -> list[tuple[float, dict]]:
    missing = []
    stored = {}
    with connect() as db:
        for job in jobs:
            result = job.get("result") or {}; text = document(result); digest = hashlib.sha256(text.encode()).hexdigest()
            row = db.execute("SELECT * FROM embeddings WHERE job_id=?", (job["id"],)).fetchone()
            if row and row["model"] == EMBED_MODEL and row["content_hash"] == digest:
                stored[job["id"]] = json.loads(row["vector_json"])
            else: missing.append((job["id"], digest, text))
    for start in range(0, len(missing), 8):
        batch = missing[start:start+8]; vectors = await ollama_embeddings([x[2] for x in batch])
        with connect() as db:
            for (job_id,digest,_),vector in zip(batch,vectors):
                stored[job_id] = vector
                db.execute("INSERT OR REPLACE INTO embeddings(job_id,model,content_hash,vector_json,updated_at) VALUES(?,?,?,?,datetime('now'))", (job_id,EMBED_MODEL,digest,json.dumps(vector)))
    query = (await ollama_embeddings([question]))[0]
    return sorted(((cosine(query, stored[j["id"]]), j) for j in jobs if j["id"] in stored), reverse=True, key=lambda x:x[0])[:limit]


def analytics(jobs: list[dict]) -> dict:
    results=[j.get("result") or {} for j in jobs]
    return {
        "total":len(results),
        "status":dict(Counter(r.get("status") or "Unknown" for r in results)),
        "format":dict(Counter(r.get("location_format") or "Unknown" for r in results)),
        "sponsorship":dict(Counter(r.get("visa_sponsorship") or "Unknown" for r in results)),
        "with_salary":sum(bool(r.get("posted_salary")) for r in results),
        "with_deadline":sum(bool(r.get("deadline")) for r in results),
    }


async def answer(question: str, profile: dict | None = None) -> dict:
    with connect() as db:
        jobs=[decode_job(row) for row in db.execute("SELECT * FROM jobs WHERE processing_status='completed' ORDER BY captured_at DESC").fetchall()]
    if not jobs: return {"answer":"There are no completed jobs to search yet.","sources":[]}
    fit_words = ("fit", "match", "best", "suitable", "profile", "background", "cv", "resume", "align")
    retrieval_query = question
    if profile and any(word in question.lower() for word in fit_words):
        retrieval_query += "\nCandidate target roles: " + str(profile.get("target_roles", ""))
        retrieval_query += "\nCandidate skills: " + str(profile.get("skills", ""))
        retrieval_query += "\nCandidate summary: " + str(profile.get("summary", ""))
        retrieval_query += "\nCandidate CV: " + str(profile.get("cv_text", ""))[:2500]
    ranked=await retrieve(retrieval_query,jobs)
    catalog=[{"company":(j.get("result") or {}).get("company_name"),"role":(j.get("result") or {}).get("role_title"),"status":(j.get("result") or {}).get("status"),"location":(j.get("result") or {}).get("location"),"deadline":(j.get("result") or {}).get("deadline"),"salary":(j.get("result") or {}).get("posted_salary"),"visa":(j.get("result") or {}).get("visa_sponsorship")} for j in jobs[:100]]
    sources=[]; passages=[]
    for index,(score,job) in enumerate(ranked,1):
        r=job.get("result") or {}; ref=f"J{index}"
        sources.append({"ref":ref,"id":job["id"],"company_name":r.get("company_name"),"role_title":r.get("role_title"),"source_url":job.get("source_url"),"score":round(score,3)})
        passages.append({"ref":ref,"company":r.get("company_name"),"role":r.get("role_title"),"location":r.get("location"),"salary":r.get("posted_salary"),"visa":r.get("visa_sponsorship"),"requirements":(r.get("requirements") or [])[:12],"description":(r.get("description_text") or "")[:1200]})
    prompt=f"""Answer the user's question using only the supplied tracker data and user profile. Cite retrieved jobs as [J1], [J2], etc. If data is absent, say so. Do not invent deadlines, salaries, sponsorship, experience, or application events. For exact totals use SERVER_ANALYTICS. When comparing fit, distinguish evidence from recommendations. Keep the answer concise and actionable.\nQUESTION: {question}\nUSER_PROFILE: {json.dumps(profile or {},ensure_ascii=False)}\nSERVER_ANALYTICS: {json.dumps(analytics(jobs))}\nJOB_CATALOG: {json.dumps(catalog,ensure_ascii=False)}\nRETRIEVED_JOBS: {json.dumps(passages,ensure_ascii=False)}"""
    async with httpx.AsyncClient(timeout=180,trust_env=False) as client:
        response=await client.post(f"{OLLAMA_URL}/api/chat",json={"model":CHAT_MODEL,"stream":False,"options":{"temperature":0.1,"num_ctx":8192,"num_predict":900},"messages":[{"role":"user","content":prompt}]})
        response.raise_for_status(); text=response.json().get("message",{}).get("content","")
    return {"answer":text,"sources":sources,"models":{"chat":CHAT_MODEL,"embedding":EMBED_MODEL}}
