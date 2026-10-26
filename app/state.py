import json
from pathlib import Path
from typing import List, Dict, Any

ROOT_DIR = Path(__file__).resolve().parent.parent
ACCOUNTS_FILE = ROOT_DIR / "accounts.json"
JOBS_FILE = ROOT_DIR / "jobs.json"

DEFAULT_ACCOUNTS = [
    {
        "id": "fb_agent_alpha",
        "name": "Alpha Supervisor Node",
        "handle": "@alpha.ops.node",
        "platform": "Facebook",
        "persona": "Pragmatic tech founder and systems architect. Writes sharp, constructive, high-signal insights.",
        "status": "Active",
        "cookies_loaded": True,
        "cookies": [{"name": "c_user", "value": "100098412001", "domain": ".facebook.com", "path": "/"}]
    },
    {
        "id": "fb_agent_beta",
        "name": "Beta Community Node",
        "handle": "@beta.community.hub",
        "platform": "Facebook",
        "persona": "Warm community builder and growth operator. Encouraging, conversational, and relatable.",
        "status": "Active",
        "cookies_loaded": True,
        "cookies": [{"name": "c_user", "value": "100098412002", "domain": ".facebook.com", "path": "/"}]
    },
    {
        "id": "fb_agent_gamma",
        "name": "Gamma Analyst Node",
        "handle": "@gamma.research.io",
        "platform": "Facebook",
        "persona": "Curious market analyst who highlights overlooked nuances and asks engaging follow-up questions.",
        "status": "Standby",
        "cookies_loaded": False,
        "cookies": []
    }
]


def _read_json(path: Path, default: Any) -> Any:
    if not path.exists():
        _write_json(path, default)
        return default
    try:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return default


def _write_json(path: Path, data: Any) -> None:
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)


def get_accounts() -> List[Dict[str, Any]]:
    return _read_json(ACCOUNTS_FILE, DEFAULT_ACCOUNTS)


def get_account_by_id(agent_id: str) -> Dict[str, Any]:
    for acc in get_accounts():
        if acc.get("id") == agent_id:
            return acc
    return DEFAULT_ACCOUNTS[0]


def update_account(agent_id: str, updates: Dict[str, Any]) -> Dict[str, Any]:
    accounts = get_accounts()
    for acc in accounts:
        if acc.get("id") == agent_id:
            if "cookies" in updates and isinstance(updates["cookies"], list):
                acc["cookies"] = updates["cookies"]
                acc["cookies_loaded"] = len(updates["cookies"]) > 0
                acc["status"] = "Active" if acc["cookies_loaded"] else "Standby"
            if "persona" in updates and updates["persona"]:
                acc["persona"] = updates["persona"]
            if "name" in updates and updates["name"]:
                acc["name"] = updates["name"]
            if "status" in updates and updates["status"]:
                acc["status"] = updates["status"]
            _write_json(ACCOUNTS_FILE, accounts)
            return acc
    raise ValueError(f"Agent '{agent_id}' not found")


def get_jobs() -> List[Dict[str, Any]]:
    return _read_json(JOBS_FILE, [])


def add_job(job: Dict[str, Any]) -> Dict[str, Any]:
    jobs = get_jobs()
    jobs.insert(0, job)
    _write_json(JOBS_FILE, jobs)
    return job


def update_job(job_id: str, updates: Dict[str, Any]) -> Dict[str, Any]:
    jobs = get_jobs()
    for job in jobs:
        if job.get("id") == job_id:
            job.update(updates)
            _write_json(JOBS_FILE, jobs)
            return job
    return {}


def delete_job(job_id: str) -> bool:
    jobs = get_jobs()
    new_jobs = [j for j in jobs if j.get("id") != job_id]
    if len(new_jobs) == len(jobs):
        return False
    _write_json(JOBS_FILE, new_jobs)
    return True


def clear_all_jobs() -> int:
    jobs = get_jobs()
    count = len(jobs)
    _write_json(JOBS_FILE, [])
    return count
