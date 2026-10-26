import json
from pathlib import Path
from typing import List, Dict, Any

ROOT_DIR = Path(__file__).resolve().parent.parent
ACCOUNTS_FILE = ROOT_DIR / "accounts.json"
JOBS_FILE = ROOT_DIR / "jobs.json"

DEFAULT_ACCOUNTS = [
    {
        "id": "fb_agent_alpha",
        "name": "Alpha Node",
        "account_handle": "unassigned",
        "platform": "Facebook",
        "persona": "Tech-savvy industry expert and community builder",
        "status": "Standby",
        "cookies_loaded": False,
        "cookies": []
    },
    {
        "id": "fb_agent_beta",
        "name": "Beta Node",
        "account_handle": "unassigned",
        "platform": "Facebook",
        "persona": "Engaging community builder",
        "status": "Standby",
        "cookies_loaded": False,
        "cookies": []
    },
    {
        "id": "fb_agent_gamma",
        "name": "Gamma Node",
        "account_handle": "unassigned",
        "platform": "Facebook",
        "persona": "Market analyst",
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
    accounts = _read_json(ACCOUNTS_FILE, DEFAULT_ACCOUNTS)
    for acc in accounts:
        cookies = acc.get("cookies", [])
        acc["cookies_loaded"] = len(cookies) > 0
        acc["status"] = "Active" if acc["cookies_loaded"] else "Standby"
    return accounts

def get_account_by_id(agent_id: str) -> Dict[str, Any]:
    for acc in get_accounts():
        if acc.get("id") == agent_id:
            return acc
    return DEFAULT_ACCOUNTS[0]

def update_account(agent_id: str, updates: Dict[str, Any]) -> Dict[str, Any]:
    accounts = _read_json(ACCOUNTS_FILE, DEFAULT_ACCOUNTS)
    for acc in accounts:
        if acc.get("id") == agent_id:
            if "cookies" in updates and isinstance(updates["cookies"], list):
                acc["cookies"] = updates["cookies"]
                acc["cookies_loaded"] = len(updates["cookies"]) > 0
                acc["status"] = "Active" if acc["cookies_loaded"] else "Standby"
                
                # Auto-detect Facebook c_user cookie to set handle if not provided
                for cookie in updates["cookies"]:
                    if cookie.get("name") == "c_user" and cookie.get("value"):
                        detected_id = cookie.get("value")
                        if not acc.get("account_handle") or acc.get("account_handle") == "unassigned":
                            acc["account_handle"] = f"fb_user_{detected_id}"
                        break

            if "account_handle" in updates and updates["account_handle"]:
                handle_val = updates["account_handle"].strip()
                if handle_val:
                    acc["account_handle"] = handle_val

            _write_json(ACCOUNTS_FILE, accounts)
            return get_account_by_id(agent_id)
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
    new_jobs = [j for j in jobs if j.get("id"] != job_id]
    if len(new_jobs) == len(jobs):
        return False
    _write_json(JOBS_FILE, new_jobs)
    return True

def clear_all_jobs() -> int:
    jobs = get_jobs()
    _write_json(JOBS_FILE, [])
    return len(jobs)
