import json
import re
import httpx
from pathlib import Path
from typing import Dict, Any, List

ROOT_DIR = Path(__file__).resolve().parent.parent
ACCOUNTS_FILE = ROOT_DIR / "accounts.json"
JOBS_FILE = ROOT_DIR / "jobs.json"

DEFAULT_ACCOUNTS = {
    "fb_agent_alpha": {
        "agent_id": "fb_agent_alpha",
        "account_name": "Unlinked_fb_agent_alpha",
        "fb_uid": "Unlinked",
        "cookie_count": 0,
        "health": "Sandbox Ready",
        "cookies": []
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


def normalize_playwright_cookies(raw_cookies: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """
    Converts Cookie-Editor JSON format into strict Playwright cookie format
    so Chromium never rejects 'sameSite: no_restriction' or 'expirationDate'.
    """
    clean = []
    for c in raw_cookies:
        if not isinstance(c, dict) or not c.get("name") or c.get("value") is None:
            continue
        same_site_raw = str(c.get("sameSite") or "").lower()
        if same_site_raw in ("strict",):
            same_site = "Strict"
        elif same_site_raw in ("lax",):
            same_site = "Lax"
        else:
            same_site = "None"

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


def fetch_fb_profile_name_from_cookies(cookies: List[Dict[str, Any]], fb_uid: str) -> str:
    """
    Attempts to fetch the real Facebook account name using the injected cookies,
    and falls back to 'FB_Account_<c_user>' automatically.
    """
    if fb_uid == "Unlinked":
        return ""
    default_derived = f"FB_Account_{fb_uid}"
    try:
        jar = {c["name"]: str(c["value"]) for c in cookies if isinstance(c, dict) and c.get("name") and c.get("value")}
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
            "Accept-Language": "en-US,en;q=0.9",
        }
        with httpx.Client(cookies=jar, headers=headers, follow_redirects=True, timeout=4.0) as client:
            resp = client.get(f"https://mbasic.facebook.com/{fb_uid}")
            if resp.status_code == 200:
                m = re.search(r"<title>(.*?)</title>", resp.text, re.IGNORECASE | re.DOTALL)
                if m:
                    title = m.group(1).strip()
                    for bad in ("Facebook", "Log in", "Log Into", "Security Check", "Error", "Page Not Found"):
                        if bad.lower() in title.lower():
                            return default_derived
                    clean_title = title.split("|")[0].split("-")[0].strip()
                    if 2 <= len(clean_title) <= 50:
                        return f"{clean_title} ({fb_uid})"
    except Exception:
        pass
    return default_derived


def get_accounts() -> Dict[str, Any]:
    raw = _read_json(ACCOUNTS_FILE, DEFAULT_ACCOUNTS)
    accounts: Dict[str, Any] = {}

    if isinstance(raw, list):
        for item in raw:
            if isinstance(item, dict):
                aid = item.get("agent_id") or item.get("id")
                if aid:
                    accounts[aid] = item
    elif isinstance(raw, dict):
        accounts = raw

    result: Dict[str, Any] = {}
    for aid, default_acc in DEFAULT_ACCOUNTS.items():
        src = accounts.get(aid, {})
        cookies = src.get("cookies", [])
        if not isinstance(cookies, list):
            cookies = []
        fb_uid = extract_uid_from_cookies(cookies)
        cookie_count = len(cookies)

        # Auto-derive account_name from cookie by default
        saved_name = str(src.get("account_name") or src.get("name") or "").strip()
        if fb_uid != "Unlinked":
            if not saved_name or saved_name.startswith("Unlinked") or saved_name in ("Alpha Node", "Beta Node", "Gamma Node", "Alpha Supervisor", "Beta Community", "Gamma Analyst", aid):
                account_name = f"FB_Account_{fb_uid}"
            else:
                account_name = saved_name
            health = "Active Session Armed"
        else:
            account_name = saved_name if saved_name and not saved_name.startswith("FB_Account_") else f"Unlinked_{aid}"
            health = "Sandbox Ready"

        result[aid] = {
            "agent_id": aid,
            "account_name": account_name,
            "fb_uid": fb_uid,
            "cookie_count": cookie_count,
            "health": health,
            "cookies": cookies,
        }

    _write_json(ACCOUNTS_FILE, result)
    return result


def update_account_cookies(agent_id: str, account_name: str, cookies_raw: str) -> Dict[str, Any]:
    accounts = get_accounts()
    if agent_id not in accounts:
        accounts[agent_id] = {
            "agent_id": agent_id,
            "account_name": f"Unlinked_{agent_id}",
            "fb_uid": "Unlinked",
            "cookie_count": 0,
            "health": "Sandbox Ready",
            "cookies": []
        }

    raw_str = (cookies_raw or "").strip()
    if raw_str:
        try:
            parsed = json.loads(raw_str)
            if isinstance(parsed, dict):
                parsed = [parsed]
            if not isinstance(parsed, list):
                raise ValueError("Cookies JSON must be an array of cookie objects.")
        except Exception as e:
            raise ValueError(f"Invalid Cookie JSON: {e}")
    else:
        # Keep existing cookies if user didn't clear them
        parsed = accounts[agent_id].get("cookies", [])

    fb_uid = extract_uid_from_cookies(parsed)
    auto_name = fetch_fb_profile_name_from_cookies(parsed, fb_uid)

    # Always prefer cookie-derived name by default unless user explicitly typed a custom non-default name
    cleaned_input_name = (account_name or "").strip()
    if fb_uid != "Unlinked":
        final_name = auto_name
        if cleaned_input_name and not cleaned_input_name.startswith("Unlinked") and cleaned_input_name not in (accounts[agent_id].get("account_name"), f"FB_Account_{fb_uid}"):
            final_name = cleaned_input_name
    else:
        final_name = cleaned_input_name or f"Unlinked_{agent_id}"

    accounts[agent_id] = {
        "agent_id": agent_id,
        "account_name": final_name,
        "fb_uid": fb_uid,
        "cookie_count": len(parsed),
        "health": "Active Session Armed" if len(parsed) > 0 else "Sandbox Ready",
        "cookies": parsed,
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
