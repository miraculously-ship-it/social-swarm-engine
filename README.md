# Social Media Support Agent — Supervisor Control Center v4.5

Autonomous web-based supervisor suite for managing multi-agent social media accounts, synthesizing context-aware AI comments via OpenRouter (`openrouter/free`), and safely executing browser automation tasks via Playwright with an automatic failover sandbox shield.

## Stack
- **Backend**: Python, FastAPI, Uvicorn
- **Browser Engine**: Playwright (Chromium Headless + Stealth Args + Persistent Profiles + Auto-Failover Sandbox)
- **AI Engine**: OpenAI SDK + OpenRouter (`openrouter/free` auto-router + fallback cascade)
- **Frontend**: HTML5, Tailwind CSS v4 CDN, FontAwesome 6, Multi-Theme Cyberpunk/Tactical UI
- **Persistence**: Local JSON state engines (`accounts.json`, `jobs.json`, `cookies.json`)

## Run Locally
```bash
pip install -r requirements.txt
playwright install chromium
uvicorn app.main:app --host 0.0.0.0 --port 10000 --reload
cat << 'EOF' > accounts.json
[
{
"id": "fb_agent_alpha",
"name": "Alpha Supervisor Node",
"handle": "@alpha.ops.node",
"platform": "Facebook",
"persona": "Pragmatic tech founder and systems architect. Writes sharp, constructive, high-signal insights.",
"status": "Active",
"cookies_loaded": true,
"cookies": [
{"name": "c_user", "value": "100098412001", "domain": ".facebook.com", "path": "/"}
]
},
{
"id": "fb_agent_beta",
"name": "Beta Community Node",
"handle": "@beta.community.hub",
"platform": "Facebook",
"persona": "Warm community builder and growth operator. Encouraging, conversational, and relatable.",
"status": "Active",
"cookies_loaded": true,
"cookies": [
{"name": "c_user", "value": "100098412002", "domain": ".facebook.com", "path": "/"}
]
},
{
"id": "fb_agent_gamma",
"name": "Gamma Analyst Node",
"handle": "@gamma.research.io",
"platform": "Facebook",
"persona": "Curious market analyst who highlights overlooked nuances and asks engaging follow-up questions.",
"status": "Standby",
"cookies_loaded": false,
"cookies": []
}
]
