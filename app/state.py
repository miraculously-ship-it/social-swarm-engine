import json
import re
import time
from datetime import datetime
from pathlib import Path
from typing import Dict, Any, List

ROOT_DIR = Path(__file__).resolve().parent.parent
ACCOUNTS_FILE = ROOT_DIR / "accounts.json"
JOBS_FILE = ROOT_DIR / "jobs.json"
ARCHIVES_FILE = ROOT_DIR / "archives.json"

BAD_NAMES = {
    "facebook", "see owner profile", "your profile", "profile",
    "log in", "login", "log into facebook", "security check",
    "home", "notifications", "error", "page not found", "unlinked"
}

DEFAULT_ACCOUNTS = {
    "fb_agent_alpha": {
        "agent_id": "fb_agent_alpha",
        "account_name": "Mirpap Day",
        "fb_uid": "100062273714859",
        "persona": "Alert Local Community Watcher",
        "tone": "Urgent, alerting, and authentic",
        "proxy": "",
        "cookie_count": 8,
        "health": "Active Session Armed",
        "cookies": []
    },
    "fb_agent_beta": {
        "agent_id": "fb_agent_beta",
        "account_name": "Unlinked Account",
        "fb_uid": "Unlinked",
        "persona": "Helpful Brand Support Specialist",
        "tone": "Warm, authentic, and helpful",
        "proxy": "",
        "cookie_count": 0,
        "health": "Sandbox Ready",
        "cookies": []
    },
    "fb_agent_gamma": {
        "agent_id": "fb_agent_gamma",
        "account_name": "Unlinked Account",
        "fb_uid": "Unlinked",
        "persona": "Insightful News Commentator",
        "tone": "Direct, sharp, and professional",
        "proxy": "",
        "cookie_count": 0,
        "health": "Sandbox Ready",
        "cookies": []
    }
}

_ACCOUNTS_CACHE: Dict[str, Any] = None
_JOBS_CACHE: List[Dict[str, Any]] = None
_ARCHIVES_CACHE: List[Dict[str, Any]] = None

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
    try:
        with open(path, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
    except Exception:
        pass

def is_valid_owner_name(name: str) -> bool:
    if not name:
        return False
    clean = re.sub(r"\(\d+\)", "", name).strip().lower()
    if not clean or len(clean) < 2 or len(clean) > 60:
        return False
    for bad in BAD_NAMES:
        if bad == clean or bad in clean:
            return False
    return True

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
    global _ACCOUNTS_CACHE
    if _ACCOUNTS_CACHE is not None:
        return _ACCOUNTS_CACHE

    raw = _read_json(ACCOUNTS_FILE, DEFAULT_ACCOUNTS)
    accounts = raw if isinstance(raw, dict) and raw else DEFAULT_ACCOUNTS.copy()

    result = {}
    for aid, src in accounts.items():
        if not aid or not isinstance(src, dict):
            continue
        default_meta = DEFAULT_ACCOUNTS.get(aid, {})
        cookies = src.get("cookies", []) if isinstance(src.get("cookies"), list) else []
        fb_uid = extract_uid_from_cookies(cookies)
        saved_name = str(src.get("account_name") or "").strip()

        if fb_uid != "Unlinked":
            if fb_uid == "100062273714859" and (not is_valid_owner_name(saved_name) or saved_name == "Authenticated Owner"):
                owner_name = "Mirpap Day"
            elif is_valid_owner_name(saved_name):
                owner_name = saved_name
            else:
                owner_name = f"FB User ({fb_uid[-4:]})"
            health = "Active Session Armed"
        else:
            owner_name = "Unlinked Account"
            health = "Sandbox Ready"

        result[aid] = {
            "agent_id": aid,
            "account_name": owner_name,
            "fb_uid": fb_uid,
            "persona": str(src.get("persona") or default_meta.get("persona") or "Alert Local Community Watcher").strip(),
            "tone": str(src.get("tone") or default_meta.get("tone") or "Urgent, alerting, and authentic").strip(),
            "proxy": str(src.get("proxy") or "").strip(),
            "cookie_count": len(cookies),
            "health": health,
            "cookies": cookies,
        }
    _ACCOUNTS_CACHE = result
    _write_json(ACCOUNTS_FILE, result)
    return result

def set_detected_account_name(agent_id: str, detected_name: str) -> None:
    global _ACCOUNTS_CACHE
    clean = re.sub(r"\(\d+\)", "", (detected_name or "")).strip()
    if not is_valid_owner_name(clean):
        return
    accounts = get_accounts()
    if agent_id in accounts and accounts[agent_id].get("account_name") != clean:
        accounts[agent_id]["account_name"] = clean
        _ACCOUNTS_CACHE = accounts
        _write_json(ACCOUNTS_FILE, accounts)

def save_or_create_account(
    agent_id: str,
    persona: str = "",
    tone: str = "",
    cookies_raw: str = None,
    proxy: str = "",
) -> Dict[str, Any]:
    global _ACCOUNTS_CACHE
    clean_id = re.sub(r"[^a-zA-Z0-9_-]", "_", (agent_id or "").strip())
    if not clean_id:
        raise ValueError("Agent ID cannot be empty.")

    accounts = get_accounts()
    existing = accounts.get(clean_id, {})

    if cookies_raw is not None:
        raw_str = cookies_raw.strip()
        if raw_str:
            parsed = json.loads(raw_str)
            if isinstance(parsed, dict):
                parsed = [parsed]
            if not isinstance(parsed, list):
                raise ValueError("Cookies JSON must be a JSON array of cookie objects.")
        else:
            parsed = []
    else:
        parsed = existing.get("cookies", [])

    fb_uid = extract_uid_from_cookies(parsed)
    if fb_uid != "Unlinked":
        prev_name = existing.get("account_name", "")
        if fb_uid == "100062273714859":
            owner_name = "Mirpap Day"
        elif existing.get("fb_uid") == fb_uid and is_valid_owner_name(prev_name):
            owner_name = prev_name
        else:
            owner_name = f"FB User ({fb_uid[-4:]})"
    else:
        owner_name = "Unlinked Account"

    accounts[clean_id] = {
        "agent_id": clean_id,
        "account_name": owner_name,
        "fb_uid": fb_uid,
        "persona": (persona or existing.get("persona") or "Alert Local Community Watcher").strip(),
        "tone": (tone or existing.get("tone") or "Urgent, alerting, and authentic").strip(),
        "proxy": (proxy if proxy is not None else existing.get("proxy", "")).strip(),
        "cookie_count": len(parsed),
        "health": "Active Session Armed" if len(parsed) > 0 else "Sandbox Ready",
        "cookies": parsed,
    }
    _ACCOUNTS_CACHE = accounts
    _write_json(ACCOUNTS_FILE, accounts)
    return accounts[clean_id]

def delete_account(agent_id: str) -> bool:
    global _ACCOUNTS_CACHE
    accounts = get_accounts()
    if agent_id not in accounts:
        return False
    if len(accounts) <= 1:
        raise ValueError("Cannot delete the last remaining agent node.")
    del accounts[agent_id]
    _ACCOUNTS_CACHE = accounts
    _write_json(ACCOUNTS_FILE, accounts)
    return True

def get_archives() -> List[Dict[str, Any]]:
    global _ARCHIVES_CACHE
    if _ARCHIVES_CACHE is None:
        raw = _read_json(ARCHIVES_FILE, [])
        _ARCHIVES_CACHE = [a for a in raw if isinstance(a, dict) and a.get("id")]
    return _ARCHIVES_CACHE

def save_archives(archives: List[Dict[str, Any]]) -> None:
    global _ARCHIVES_CACHE
    _ARCHIVES_CACHE = archives
    _write_json(ARCHIVES_FILE, archives)

def upsert_archive(job: Dict[str, Any]) -> None:
    if not isinstance(job, dict) or not job.get("id"):
        return
    archives = get_archives()
    now_str = datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S UTC")
    archive_entry = dict(job)
    archive_entry["archived_at"] = job.get("archived_at") or now_str
    for idx, existing in enumerate(archives):
        if existing.get("id") == job["id"]:
            archives[idx] = archive_entry
            save_archives(archives)
            return
    archives.insert(0, archive_entry)
    save_archives(archives)

def delete_archive(job_id: str) -> bool:
    archives = get_archives()
    save_archives([a for a in archives if a.get("id") != job_id])
    return True

def get_jobs() -> List[Dict[str, Any]]:
    global _JOBS_CACHE
    if _JOBS_CACHE is None:
        raw = _read_json(JOBS_FILE, [])
        _JOBS_CACHE = [j for j in raw if isinstance(j, dict) and j.get("agent_id")]
    return _JOBS_CACHE

def save_jobs(jobs: List[Dict[str, Any]]) -> None:
    global _JOBS_CACHE
    _JOBS_CACHE = jobs
    _write_json(JOBS_FILE, jobs)

def add_job(job: Dict[str, Any]) -> Dict[str, Any]:
    jobs = get_jobs()
    jobs.insert(0, job)
    save_jobs(jobs)
    upsert_archive(job)
    return job

def append_job_log(
    job_id: str,
    line: str,
    status: str = None,
    screenshot: str = None,
    account_name: str = None,
    execution_ms: int = None,
) -> None:
    jobs = get_jobs()
    target_job = None
    for j in jobs:
        if j.get("id") == job_id:
            if line:
                j.setdefault("logs", []).append(line)
            if status:
                j["status"] = status
            if screenshot:
                j["screenshot"] = screenshot
            if account_name:
                j["account_name"] = account_name
            if execution_ms is not None:
                j["execution_ms"] = execution_ms
            target_job = j
            break
    save_jobs(jobs)
    if target_job:
        upsert_archive(target_job)

def update_job(job_id: str, updates: Dict[str, Any]) -> Dict[str, Any]:
    jobs = get_jobs()
    updated_job = {}
    for j in jobs:
        if j.get("id") == job_id:
            j.update(updates)
            updated_job = j
            break
    save_jobs(jobs)
    if updated_job:
        upsert_archive(updated_job)
    else:
        archives = get_archives()
        for a in archives:
            if a.get("id") == job_id:
                a.update(updates)
                save_archives(archives)
                return a
    return updated_job

def delete_job(job_id: str) -> bool:
    jobs = get_jobs()
    save_jobs([j for j in jobs if j.get("id") != job_id])
    return True

def clear_jobs() -> None:
    save_jobs([])
