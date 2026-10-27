import json
from pathlib import Path
from typing import Dict, Any, List

ROOT_DIR = Path(__file__).resolve().parent.parent
ACCOUNTS_FILE = ROOT_DIR / "accounts.json"
JOBS_FILE = ROOT_DIR / "jobs.json"

DEFAULT_ACCOUNTS = {
    "fb_agent_alpha": {
        "agent_id": "fb_agent_alpha",
        "account_name": "FB_Account_100062273714859",
        "fb_uid": "100062273714859",
        "cookie_count": 8,
        "health": "Active Session Armed",
        "cookies": [
            {
                "domain": ".facebook.com",
                "expirationDate": 1827524050.913142,
                "hostOnly": False,
                "httpOnly": True,
                "name": "datr",
                "path": "/",
                "sameSite": "None",
                "secure": True,
                "value": "0nXeavhEVLESek5ND743HgTd"
            },
            {
                "domain": ".facebook.com",
                "expirationDate": 1824501095.930178,
                "hostOnly": False,
                "httpOnly": False,
                "name": "c_user",
                "path": "/",
                "sameSite": "None",
                "secure": True,
                "value": "100062273714859"
            },
            {
                "domain": ".facebook.com",
                "expirationDate": 1824501095.930623,
                "hostOnly": False,
                "httpOnly": True,
                "name": "xs",
                "path": "/",
                "sameSite": "None",
                "secure": True,
                "value": "11%3AMUwWDDhnukyifA%3A2%3A1792965084%3A-1%3A-1%3A%3AAcynGzl3knPiSvN4LnhIApTDZ6VY5hWzASdfcRpu_w"
            }
        ]
    },
    "fb_agent_beta": {
        "agent_id": "fb_agent_beta",
        "account_name": "Unlinked_fb_agent_beta",
        "fb_uid": "Unlinked",
        "cookie_count": 0,
        "health": "Sandbox Ready",
        "cookies": []
    },
    "fb_agent_gamma": {
        "agent_id": "fb_agent_gamma",
        "account_name": "Unlinked_fb_agent_gamma",
        "fb_uid": "Unlinked",
        "cookie_count": 0,
        "health": "Sandbox Ready",
        "cookies": []
    }
}

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

def get_accounts() -> Dict[str, Any]:
    raw = _read_json(ACCOUNTS_FILE, DEFAULT_ACCOUNTS)
    accounts = {}
    if isinstance(raw, list):
        for item in raw:
            aid = item.get("agent_id") or item.get("id")
            if aid:
                accounts[aid] = item
    elif isinstance(raw, dict):
        accounts = raw

    result = {}
    for aid, default_acc in DEFAULT_ACCOUNTS.items():
        src = accounts.get(aid, default_acc)
        cookies = src.get("cookies", [])
        if not isinstance(cookies, list):
            cookies = []
        
        fb_uid = "Unlinked"
        for c in cookies:
            if isinstance(c, dict) and c.get("name") == "c_user" and c.get("value"):
                fb_uid = str(c["value"]).strip()
                break

        saved_name = str(src.get("account_name") or src.get("name") or "").strip()
        if fb_uid != "Unlinked":
            account_name = saved_name if saved_name and not saved_name.startswith("Unlinked") else f"FB_Account_{fb_uid}"
            health = "Active Session Armed"
        else:
            account_name = saved_name if saved_name and not saved_name.startswith("FB_Account_") else f"Unlinked_{aid}"
            health = "Sandbox Ready"

        result[aid] = {
            "agent_id": aid,
            "account_name": account_name,
            "fb_uid": fb_uid,
            "cookie_count": len(cookies),
            "health": health,
            "cookies": cookies
        }
    _write_json(ACCOUNTS_FILE, result)
    return result

def update_account_cookies(agent_id: str, account_name: str, cookies_raw: str) -> Dict[str, Any]:
    accounts = get_accounts()
    if agent_id not in accounts:
        accounts[agent_id] = {"agent_id": agent_id, "account_name": f"Unlinked_{agent_id}", "fb_uid": "Unlinked", "cookie_count": 0, "health": "Sandbox Ready", "cookies": []}

    parsed = []
    raw_str = (cookies_raw or "").strip()
    if raw_str:
        try:
            parsed = json.loads(raw_str)
            if isinstance(parsed, dict):
                parsed = [parsed]
        except Exception as e:
            raise ValueError(f"Invalid Cookie JSON: {e}")
    else:
        parsed = accounts[agent_id].get("cookies", [])

    fb_uid = "Unlinked"
    for c in parsed:
        if isinstance(c, dict) and c.get("name") == "c_user" and c.get("value"):
            fb_uid = str(c["value"]).strip()
            break

    final_name = f"FB_Account_{fb_uid}" if fb_uid != "Unlinked" else (account_name.strip() or f"Unlinked_{agent_id}")

    accounts[agent_id] = {
        "agent_id": agent_id,
        "account_name": final_name,
        "fb_uid": fb_uid,
        "cookie_count": len(parsed),
        "health": "Active Session Armed" if len(parsed) > 0 else "Sandbox Ready",
        "cookies": parsed
    }
    _write_json(ACCOUNTS_FILE, accounts)
    return accounts[agent_id]

def get_jobs() -> List[Dict[str, Any]]:
    jobs = _read_json(JOBS_FILE, [])
    return jobs if isinstance(jobs, list) else []

def save_jobs(jobs: List[Dict[str, Any]]) -> None:
    _write_json(JOBS_FILE, jobs)

def add_job(job: Dict[str, Any]) -> Dict[str, Any]:
    jobs = get_jobs()
    jobs.insert(0, job)
    save_jobs(jobs)
    return job

def update_job(job_id: str, updates: Dict[str, Any]) -> Dict[str, Any]:
    jobs = get_jobs()
    for j in jobs:
        if j.get("id") == job_id:
            j.update(updates)
            save_jobs(jobs)
            return j
    return {}

def delete_job(job_id: str) -> bool:
    jobs = get_jobs()
    new_jobs = [j for j in jobs if j.get("id") != job_id]
    save_jobs(new_jobs)
    return len(new_jobs) < len(jobs)
