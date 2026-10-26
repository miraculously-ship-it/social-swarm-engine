import time
from pathlib import Path
from typing import List, Dict, Any, Optional
from fastapi import FastAPI, HTTPException
from fastapi.responses import HTMLResponse, Response
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

from app.state import (
    get_accounts,
    get_account_by_id,
    update_account,
    get_jobs,
    add_job,
    update_job,
    delete_job,
    clear_all_jobs,
)
from app.llm import generate_comment
from app.worker import execute_automation_job

BASE_DIR = Path(__file__).resolve().parent
DASHBOARD_PATH = BASE_DIR / "dashboard.html"
SCREENSHOTS_DIR = BASE_DIR / "screenshots"
SCREENSHOTS_DIR.mkdir(parents=True, exist_ok=True)

app = FastAPI(title="Social Swarm Supervisor v4.5", version="4.5.0")
app.mount("/screenshots", StaticFiles(directory=str(SCREENSHOTS_DIR)), name="screenshots")


class PreviewPayload(BaseModel):
    post_url: str
    context: Optional[str] = ""
    agent_id: Optional[str] = "fb_agent_alpha"
    persona: Optional[str] = ""
    tone: Optional[str] = "Engaging & Natural"
    custom_directive: Optional[str] = ""
    variation_seed: Optional[int] = 0


class DispatchPayload(BaseModel):
    post_url: str
    context: Optional[str] = ""
    action_type: str = "comment"
    comment: Optional[str] = ""
    agent_id: str = "fb_agent_alpha"
    safe_mode: bool = True


class AccountUpdatePayload(BaseModel):
    name: Optional[str] = None
    account_handle: Optional[str] = None
    persona: Optional[str] = None
    status: Optional[str] = None
    cookies: Optional[List[Dict[str, Any]]] = None


@app.api_route("/", methods=["GET", "HEAD"], response_class=HTMLResponse)
async def serve_dashboard():
    if not DASHBOARD_PATH.exists():
        return HTMLResponse("<h1>Dashboard file missing</h1>", status_code=500)
    return HTMLResponse(DASHBOARD_PATH.read_text(encoding="utf-8"))


@app.get("/favicon.ico", include_in_schema=False)
async def favicon():
    return Response(status_code=204)


@app.get("/api/accounts")
async def api_list_accounts():
    return get_accounts()


@app.post("/api/accounts/{agent_id}")
async def api_update_account(agent_id: str, payload: AccountUpdatePayload):
    try:
        updates = {k: v for k, v in payload.model_dump().items() if v is not None}
        updated = update_account(agent_id, updates)
        return {"ok": True, "account": updated}
    except ValueError as err:
        raise HTTPException(status_code=404, detail=str(err))


@app.get("/api/jobs")
async def api_list_jobs():
    return get_jobs()


@app.post("/api/preview")
async def api_preview(payload: PreviewPayload):
    acc = get_account_by_id(payload.agent_id or "fb_agent_alpha")
    persona_to_use = payload.persona.strip() if payload.persona else acc.get("persona", "Constructive peer")

    return await generate_comment(
        post_url=payload.post_url,
        context=payload.context or "",
        persona=persona_to_use,
        tone=payload.tone or "Engaging & Natural",
        custom_directive=payload.custom_directive or "",
        variation_seed=payload.variation_seed or int(time.time() * 1000) % 100000,
    )


@app.post("/api/dispatch")
async def api_dispatch(payload: DispatchPayload):
    now_ms = int(time.time() * 1000)
    job_id = f"job_{now_ms}"
    acc = get_account_by_id(payload.agent_id)
    account_handle = acc.get("account_handle", payload.agent_id)

    job_entry = {
        "id": job_id,
        "timestamp": now_ms,
        "agent_id": payload.agent_id,
        "account_handle": account_handle,
        "post_url": payload.post_url,
        "context": payload.context or "",
        "action_type": payload.action_type,
        "comment": payload.comment if payload.action_type == "comment" else "[Like Automation Action]",
        "status": f"Executing {payload.action_type.capitalize()}...",
        "screenshot": None,
    }
    add_job(job_entry)

    try:
        result = await execute_automation_job(
            job_id=job_id,
            agent_id=payload.agent_id,
            account_handle=account_handle,
            post_url=payload.post_url,
            action_type=payload.action_type,
            comment_text=payload.comment or "",
            context_text=payload.context or "",
            cookies=acc.get("cookies", []),
            safe_mode=payload.safe_mode,
        )
        return update_job(job_id, result)
    except Exception as err:
        return update_job(job_id, {"status": f"Failed: {str(err)[:90]}"})


@app.delete("/api/jobs/{job_id}")
async def api_remove_job(job_id: str):
    if not delete_job(job_id):
        raise HTTPException(status_code=404, detail="Job not found")
    return {"ok": True, "deleted": job_id}


@app.delete("/api/jobs")
async def api_clear_jobs():
    count = clear_all_jobs()
    return {"ok": True, "cleared": count}
