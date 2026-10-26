import json
from pathlib import Path
from typing import Dict, Any, List

ROOT_DIR = Path(__file__).resolve().parent.parent
ACCOUNTS_FILE = ROOT_DIR / "accounts.json"
JOBS_FILE = ROOT_DIR / "jobs.json"

DEFAULT_ACCOUNTS = {
    "fb_agent_alpha": {"agent_id": "fb_agent_alpha", "account_name": "Unlinked_fb_agent_alpha", "fb_uid": "Unlinked", "cookie_count": 0, "health": "Sandbox Ready", "cookies": []},
    "fb_agent_beta": {"agent_id": "fb_agent_beta", "account_name": "Unlinked_fb_agent_beta", "fb_uid": "Unlinked", "cookie_count": 0, "health": "Sandbox Ready", "cookies": []},
    "fb_agent_gamma": {"agent_id": "fb_agent_gamma", "account_name": "Unlinked_fb_agent_gamma", "fb_uid": "Unlinked", "cookie_count": 0, "health": "Sandbox Ready", "cookies": []}
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

def normalize_playwright_cookies(raw_cookies: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    clean = []
    for c in raw_cookies:
        if not isinstance(c, dict) or not c.get("name") or c.get("value") is None:
            continue
        same_site_raw = str(c.get("sameSite") or "").lower()
        same_site = "Strict" if same_site_raw == "strict" else ("Lax" if same_site_raw == "lax" else "None")
        pw_cookie = {
            "name": str(c["name"]),
            "value": str(c["value"]),
            "domain": str(c.get("domain") or ".facebook.com"),
            "path": str(c.get("path") or "/"),
            "secure": bool(c.get("secure", True)),
            "httpOnly": bool(c.get("httpOnly", False)),
            "sameSite": same_site,
        }
        exp = c.get("expires") or c.get("expirationDate")
        if exp and not c.get("session", False):
            try:
                pw_cookie["expires"] = float(exp)
            except Exception:
                pass
        clean.append(pw_cookie)
    return clean

def extract_uid_from_cookies(cookies: List[Dict[str, Any]]) -> str:
    for c in cookies:
        if isinstance(c, dict) and c.get("name") == "c_user" and c.get("value"):
            return str(c["value"]).strip()
    return "Unlinked"

def get_accounts() -> Dict[str, Any]:
    raw = _read_json(ACCOUNTS_FILE, DEFAULT_ACCOUNTS)
    accounts = raw if isinstance(raw, dict) else DEFAULT_ACCOUNTS.copy()
    result = {}
    for aid, default_acc in DEFAULT_ACCOUNTS.items():
        src = accounts.get(aid, {})
        cookies = src.get("cookies", []) if isinstance(src.get("cookies"), list) else []
        fb_uid = extract_uid_from_cookies(cookies)
        saved_name = str(src.get("account_name") or "").strip()
        if fb_uid != "Unlinked":
            account_name = saved_name if (saved_name and not saved_name.startswith("Unlinked")) else f"FB_Account_{fb_uid}"
            health = "Active Session Armed"
        else:
            account_name = f"Unlinked_{aid}"
            health = "Sandbox Ready"
        result[aid] = {
            "agent_id": aid,
            "account_name": account_name,
            "fb_uid": fb_uid,
            "cookie_count": len(cookies),
            "health": health,
            "cookies": cookies,
        }
    _write_json(ACCOUNTS_FILE, result)
    return result

def set_detected_account_name(agent_id: str, detected_name: str) -> None:
    if not detected_name:
        return
    accounts = get_accounts()
    if agent_id in accounts:
        accounts[agent_id]["account_name"] = detected_name
        _write_json(ACCOUNTS_FILE, accounts)

def update_account_cookies(agent_id: str, account_name: str, cookies_raw: str) -> Dict[str, Any]:
    accounts = get_accounts()
    raw_str = (cookies_raw or "").strip()
    if raw_str:
        parsed = json.loads(raw_str)
        if isinstance(parsed, dict):
            parsed = [parsed]
        if not isinstance(parsed, list):
            raise ValueError("Cookies JSON must be a list of objects.")
    else:
        parsed = []

    fb_uid = extract_uid_from_cookies(parsed)
    auto_name = f"FB_Account_{fb_uid}" if fb_uid != "Unlinked" else f"Unlinked_{agent_id}"

    accounts[agent_id] = {
        "agent_id": agent_id,
        "account_name": auto_name,
        "fb_uid": fb_uid,
        "cookie_count": len(parsed),
        "health": "Active Session Armed" if len(parsed) > 0 else "Sandbox Ready",
        "cookies": parsed,
    }
    _write_json(ACCOUNTS_FILE, accounts)
    return accounts[agent_id]

def get_jobs() -> List[Dict[str, Any]]:
    jobs = _read_json(JOBS_FILE, [])
    return [j for j in jobs if isinstance(j, dict) and j.get("agent_id")]

def save_jobs(jobs: List[Dict[str, Any]]) -> None:
    _write_json(JOBS_FILE, jobs)

def add_job(job: Dict[str, Any]) -> Dict[str, Any]:
    jobs = get_jobs()
    jobs.insert(0, job)
    save_jobs(jobs)
    return job

def append_job_log(job_id: str, line: str, status: str = None, screenshot: str = None, account_name: str = None) -> None:
    jobs = get_jobs()
    for j in jobs:
        if j.get("id") == job_id:
            j.setdefault("logs", []).append(line)
            if status:
                j["status"] = status
            if screenshot:
                j["screenshot"] = screenshot
            if account_name:
                j["account_name"] = account_name
            break
    save_jobs(jobs)

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

def clear_jobs() -> None:
    save_jobs([])
