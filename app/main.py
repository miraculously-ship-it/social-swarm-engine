import time
from pathlib import Path
from typing import Optional
from fastapi import FastAPI, HTTPException
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

from app.state import get_accounts, update_account_cookies, get_jobs, add_job, update_job, delete_job
from app.llm import generate_comment
from app.worker import execute_automation_job

BASE_DIR = Path(__file__).resolve().parent
DASHBOARD_PATH = BASE_DIR / "dashboard.html"
SCREENSHOTS_DIR = BASE_DIR / "screenshots"
SCREENSHOTS_DIR.mkdir(parents=True, exist_ok=True)

app = FastAPI(title="Social Media Support Agent PRO", version="4.5.0")
app.mount("/screenshots", StaticFiles(directory=str(SCREENSHOTS_DIR)), name="screenshots")

class AccountPayload(BaseModel):
    agent_id: str
    account_name: Optional[str] = ""
    cookies_raw: Optional[str] = ""

class PreviewPayload(BaseModel):
    agent_id: Optional[str] = "fb_agent_alpha"
    post_url: str
    post_text: Optional[str] = ""
    persona: Optional[str] = "Community Watcher"
    tone: Optional[str] = "Urgent & Alerting"

class DispatchPayload(BaseModel):
    agent_id: str = "fb_agent_alpha"
    post_url: str
    post_text: Optional[str] = ""
    persona: Optional[str] = "Community Watcher"
    tone: Optional[str] = "Urgent & Alerting"
    do_like: bool = True
    do_comment: bool = True

@app.get("/", response_class=HTMLResponse)
async def serve_dashboard():
    return HTMLResponse(DASHBOARD_PATH.read_text(encoding="utf-8"))

@app.get("/api/accounts")
async def api_get_accounts():
    return get_accounts()

@app.post("/api/accounts")
async def api_save_account(payload: AccountPayload):
    try:
        updated = update_account_cookies(payload.agent_id, payload.account_name or "", payload.cookies_raw or "")
        return {"ok": True, "message": f"Saved {updated['agent_id']} ➔ {updated['account_name']}", "account": updated}
    except Exception as e:
        return {"ok": False, "message": f"Error: {str(e)}"}

@app.get("/api/jobs")
async def api_get_jobs():
    return get_jobs()

@app.post("/api/preview")
async def api_preview(payload: PreviewPayload):
    res = await generate_comment(payload.post_url, payload.post_text or "", payload.persona or "", payload.tone or "")
    return {"ok": True, "comment": res["comment"]}

async def _dispatch_single(agent_id: str, payload: DispatchPayload) -> dict:
    accounts = get_accounts()
    acc = accounts.get(agent_id) or list(accounts.values())[0]

    ai_res = await generate_comment(payload.post_url, payload.post_text or "", payload.persona or "", payload.tone or "")
    comment_text = ai_res.get("comment", "")

    job_id = f"job_{int(time.time() * 1000)}_{agent_id[-5:]}"
    job_record = {
        "id": job_id,
        "agent_id": agent_id,
        "account_name": acc.get("account_name", agent_id),
        "post_url": payload.post_url,
        "comment": comment_text,
        "status": "Running...",
        "logs": [f"[*] Dispatching {agent_id}..."],
        "screenshot": None
    }
    add_job(job_record)

    result = await execute_automation_job(
        job_id=job_id,
        agent_id=agent_id,
        account_name=acc.get("account_name", agent_id),
        fb_uid=acc.get("fb_uid", "Unlinked"),
        post_url=payload.post_url,
        comment_text=comment_text,
        cookies=acc.get("cookies", []),
        do_like=payload.do_like,
        do_comment=payload.do_comment
    )
    return update_job(job_id, result)

@app.post("/api/dispatch")
async def api_dispatch(payload: DispatchPayload):
    job = await _dispatch_single(payload.agent_id, payload)
    return {"ok": True, "message": "Agent dispatched successfully!", "job": job}

@app.post("/api/dispatch-swarm")
async def api_dispatch_swarm(payload: DispatchPayload):
    accounts = get_accounts()
    jobs = []
    for aid in accounts.keys():
        j = await _dispatch_single(aid, payload)
        jobs.append(j)
    return {"ok": True, "message": "Swarm dispatched!", "jobs": jobs}

@app.put("/api/jobs/{job_id}")
async def api_edit_job(job_id: str, payload: dict):
    comment = (payload.get("comment") or "").strip()
    updated = update_job(job_id, {"comment": comment})
    return {"ok": True, "message": "Updated successfully!", "job": updated}

@app.delete("/api/jobs/{job_id}")
async def api_delete_job(job_id: str):
    delete_job(job_id)
    return {"ok": True, "message": "Deleted job log"}
