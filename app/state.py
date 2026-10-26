import json
from pathlib import Path
from typing import List, Dict, Any

ROOT_DIR = Path(__file__).resolve().parent.parent
ACCOUNTS_FILE = ROOT_DIR / "accounts.json"
JOBS_FILE = ROOT_DIR / "jobs.json"

DEFAULT_ACCOUNTS = {
    "fb_agent_alpha": {
        "agent_id": "fb_agent_alpha",
        "account_name": "Alpha Supervisor",
        "fb_uid": "Unlinked",
        "cookies": [],
        "cookie_count": 0,
        "health": "Ready"
    },
    "fb_agent_beta": {
        "agent_id": "fb_agent_beta",
        "account_name": "Beta Community",
        "fb_uid": "Unlinked",
        "cookies": [],
        "cookie_count": 0,
        "health": "Ready"
    },
    "fb_agent_gamma": {
        "agent_id": "fb_agent_gamma",
        "account_name": "Gamma Analyst",
        "fb_uid": "Unlinked",
        "cookies": [],
        "cookie_count": 0,
        "health": "Ready"
    }
}

def _read_json(path: Path, default: Any) -> Any:
    if not path.exists():
        _write_json(path, default)
        return default
    try:
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
            if isinstance(data, list):
                converted = DEFAULT_ACCOUNTS.copy()
                for item in data:
                    aid = item.get("agent_id")
                    if aid in converted:
                        converted[aid].update(item)
                return converted
            return data
    except Exception:
        return default

def _write_json(path: Path, data: Any) -> None:
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)

def get_accounts() -> Dict[str, Any]:
    accounts = _read_json(ACCOUNTS_FILE, DEFAULT_ACCOUNTS)
    for aid, acc in accounts.items():
        cookies = acc.get("cookies", [])
        acc["cookie_count"] = len(cookies)
        for c in cookies:
            if c.get("name") == "c_user":
                acc["fb_uid"] = c.get("value")
                break
        if not acc.get("fb_uid"):
            acc["fb_uid"] = "Unlinked"
        if not acc.get("account_name"):
            acc["account_name"] = aid
    return accounts

def update_account_cookies(agent_id: str, account_name: str, cookies_raw: str) -> dict:
    accounts = get_accounts()
    if agent_id not in accounts:
        accounts[agent_id] = {"agent_id": agent_id, "account_name": agent_id, "fb_uid": "Unlinked", "cookies": [], "cookie_count": 0, "health": "Ready"}
    
    parsed_cookies = []
    if cookies_raw.strip():
        try:
            parsed_cookies = json.loads(cookies_raw)
            if not isinstance(parsed_cookies, list):
                parsed_cookies = [parsed_cookies]
        except Exception as e:
            raise ValueError(f"Invalid Cookie JSON format: {e}")

    fb_uid = "Unlinked"
    for c in parsed_cookies:
        if c.get("name") == "c_user":
            fb_uid = c.get("value")
            break

    accounts[agent_id]["cookies"] = parsed_cookies
    accounts[agent_id]["cookie_count"] = len(parsed_cookies)
    accounts[agent_id]["fb_uid"] = fb_uid
    
    # Automatically fetch and derive account name from the cookie (c_user) by default
    if fb_uid != "Unlinked":
        accounts[agent_id]["account_name"] = f"FB User {fb_uid}"
    else:
        accounts[agent_id]["account_name"] = account_name.strip() or f"Agent {agent_id}"

    accounts[agent_id]["health"] = "Active Session Armed" if len(parsed_cookies) > 0 else "Sandbox Ready"

    _write_json(ACCOUNTS_FILE, accounts)
    return accounts[agent_id]
