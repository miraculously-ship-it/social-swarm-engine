import asyncio
import time
from datetime import datetime
from pathlib import Path
from typing import Optional
from fastapi import FastAPI, HTTPException
from fastapi.responses import HTMLResponse, Response
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

from app.state import (
    get_accounts,
    save_or_create_account,
    delete_account,
    get_jobs,
    add_job,
    update_job,
    delete_job,
    clear_jobs,
    get_archives,
    upsert_archive,
    delete_archive,
)
from app.llm import generate_comment
from app.worker import execute_automation_job, ensure_chromium_installed

BASE_DIR = Path(__file__).resolve().parent
DASHBOARD_PATH = BASE_DIR / "dashboard.html"
SCREENSHOTS_DIR = BASE_DIR / "screenshots"
SCREENSHOTS_DIR.mkdir(parents=True, exist_ok=True)

app = FastAPI(title="Social Media Support Agent — Supervisor Suite v4.5", version="4.5.0")
app.mount("/screenshots", StaticFiles(directory=str(SCREENSHOTS_DIR)), name="screenshots")

@app.on_event("startup")
async def startup_event():
    for existing_job in get_jobs():
        upsert_archive(existing_job)
    # Background check to ensure Chromium is ready on Render startup
    asyncio.create_task(ensure_chromium_installed())

class AccountSavePayload(BaseModel):
    agent_id: str
    persona: Optional[str] = "Alert Local Community Watcher"
    tone: Optional[str] = "Urgent, alerting, and authentic"
    cookies_raw: Optional[str] = None

class PreviewPayload(BaseModel):
    agent_id: Optional[str] = "fb_agent_alpha"
    post_url: str
    post_text: Optional[str] = ""
    persona: Optional[str] = "Alert Local Community Watcher"
    tone: Optional[str] = "Urgent, alerting, and authentic"
    language: Optional[str] = "English"

class DispatchPayload(BaseModel):
    agent_id: str = "fb_agent_alpha"
    post_url: str
    post_text: Optional[str] = ""
    persona: Optional[str] = ""
    tone: Optional[str] = ""
    language: Optional[str] = "English"
    do_like: bool = True
    do_comment: bool = True
    auto_failover: bool = True

@app.get("/", response_class=HTMLResponse)
async def serve_dashboard():
    return HTMLResponse(DASHBOARD_PATH.read_text(encoding="utf-8"))

@app.get("/favicon.ico", include_in_schema=False)
async def favicon():
    return Response(status_code=204)

@app.get("/api/accounts")
async def api_get_accounts():
    return get_accounts()

@app.post("/api/accounts")
async def api_save_account(payload: AccountSavePayload):
    try:
        updated = save_or_create_account(
            agent_id=payload.agent_id,
            persona=payload.persona or "Alert Local Community Watcher",
            tone=payload.tone or "Urgent, alerting, and authentic",
            cookies_raw=payload.cookies_raw,
        )
        return {
            "ok": True,
            "message": f"Saved {updated['agent_id']} ➔ {updated['account_name']} ({updated['cookie_count']} cookies)",
            "account": updated,
        }
    except Exception as e:
        return {"ok": False, "message": f"Error: {str(e)}"}

@app.delete("/api/accounts/{agent_id}")
async def api_delete_account(agent_id: str):
    try:
        delete_account(agent_id)
        return {"ok": True, "message": f"Removed agent node {agent_id}"}
    except Exception as e:
        return {"ok": False, "message": str(e)}

@app.get("/api/jobs")
async def api_get_jobs():
    return get_jobs()

@app.get("/api/archives")
async def api_get_archives():
    return get_archives()

@app.delete("/api/archives/{job_id}")
async def api_delete_archive(job_id: str):
    delete_archive(job_id)
    return {"ok": True, "message": f"Removed {job_id} from archive"}

@app.post("/api/preview")
async def api_preview(payload: PreviewPayload):
    res = await generate_comment(
        post_url=payload.post_url,
        context=payload.post_text or "",
        persona=payload.persona or "Alert Local Community Watcher",
        tone=payload.tone or "Urgent, alerting, and authentic",
        language=payload.language or "English",
    )
    return {
        "ok": True,
        "comment": res["comment"],
        "model_used": res.get("model_used", "ai"),
        "language": res.get("language", payload.language),
    }

async def _queue_agent_job(agent_id: str, payload: DispatchPayload, use_agent_own_profile: bool = False) -> dict:
    accounts = get_accounts()
    acc = accounts.get(agent_id) or list(accounts.values())[0]
    chosen_lang = payload.language or "English"

    if use_agent_own_profile:
        chosen_persona = acc.get("persona") or "Alert Local Community Watcher"
        chosen_tone = acc.get("tone") or "Urgent, alerting, and authentic"
    else:
        chosen_persona = (payload.persona or acc.get("persona") or "Alert Local Community Watcher").strip()
        chosen_tone = (payload.tone or acc.get("tone") or "Urgent, alerting, and authentic").strip()

    ai_res = await generate_comment(
        post_url=payload.post_url,
        context=payload.post_text or "",
        persona=chosen_persona,
        tone=chosen_tone,
        language=chosen_lang,
    )
    comment_text = ai_res.get("comment", "")

    now_ms = int(time.time() * 1000)
    job_id = f"job_{now_ms}_{agent_id[-6:]}"
    job_record = {
        "id": job_id,
        "timestamp": now_ms,
        "archived_at": datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S UTC"),
        "agent_id": agent_id,
        "account_name": acc.get("account_name", agent_id),
        "fb_uid": acc.get("fb_uid", "Unlinked"),
        "post_url": payload.post_url,
        "post_text": payload.post_text or "",
        "persona": chosen_persona,
        "tone": chosen_tone,
        "language": chosen_lang,
        "do_like": payload.do_like,
        "do_comment": payload.do_comment,
        "comment": comment_text,
        "status": "Starting Agent...",
        "logs": [
            f"[*] Dispatched {agent_id} ({acc.get('account_name')}) for {payload.post_url}",
            f"[*] Persona: {chosen_persona} | Tone: {chosen_tone} | Language: {chosen_lang}"
        ],
        "screenshot": None,
    }
    add_job(job_record)

    asyncio.create_task(
        execute_automation_job(
            job_id=job_id,
            agent_id=agent_id,
            account_name=acc.get("account_name", agent_id),
            fb_uid=acc.get("fb_uid", "Unlinked"),
            post_url=payload.post_url,
            comment_text=comment_text,
            cookies=acc.get("cookies", []),
            do_like=payload.do_like,
            do_comment=payload.do_comment,
            auto_failover=payload.auto_failover,
        )
    )
    return job_record

@app.post("/api/dispatch")
async def api_dispatch(payload: DispatchPayload):
    job = await _queue_agent_job(payload.agent_id, payload, use_agent_own_profile=False)
    return {"ok": True, "message": f"Agent {payload.agent_id} launched & archived!", "job": job}

@app.post("/api/dispatch-swarm")
async def api_dispatch_swarm(payload: DispatchPayload):
    accounts = get_accounts()
    jobs = []
    for aid in accounts.keys():
        job = await _queue_agent_job(aid, payload, use_agent_own_profile=True)
        jobs.append(job)
    return {"ok": True, "message": f"Swarm launched across all {len(jobs)} agents!", "jobs": jobs}

@app.put("/api/jobs/{job_id}")
async def api_edit_job(job_id: str, payload: dict):
    new_comment = (payload.get("comment") or "").strip()
    if not new_comment:
        return {"ok": False, "message": "Comment cannot be empty."}
    updated = update_job(job_id, {"comment": new_comment})
    if not updated:
        raise HTTPException(status_code=404, detail="Job not found")
    return {"ok": True, "message": "Comment updated in Feed & Archive!", "job": updated}

@app.delete("/api/jobs/{job_id}")
async def api_delete_job(job_id: str):
    delete_job(job_id)
    return {"ok": True, "message": f"Removed {job_id} from live feed (kept in Archive)"}

@app.delete("/api/jobs")
async def api_clear_all_jobs():
    clear_jobs()
    return {"ok": True, "message": "Live feed cleared! All records remain safely in Archive."}
