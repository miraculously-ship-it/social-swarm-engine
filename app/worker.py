import asyncio
import base64
import sys
import time
from pathlib import Path
from playwright.async_api import async_playwright
from app.state import normalize_playwright_cookies, append_job_log, set_detected_account_name, is_valid_owner_name

BASE_DIR = Path(__file__).resolve().parent
SCREENSHOTS_DIR = BASE_DIR / "screenshots"
SCREENSHOTS_DIR.mkdir(parents=True, exist_ok=True)

_PW_INSTANCE = None
_WARM_BROWSER = None
_BROWSER_LOCK = asyncio.Lock()

BLOCKED_RESOURCE_TYPES = {"media", "font", "websocket", "manifest", "other"}
BLOCKED_URL_SUBSTRINGS = (
    ".mp4", ".m4s", ".webm", ".mp3", "video.", "doubleclick.net",
    "googlesyndication", "connect.facebook.net/en_US/fbevents",
    "analytics", "chat-plugin", "lidar"
)

STEALTH_INIT_SCRIPT = """
Object.defineProperty(navigator, 'webdriver', { get: () => undefined });
window.chrome = { runtime: {} };
Object.defineProperty(navigator, 'languages', { get: () => ['en-US', 'en'] });
Object.defineProperty(navigator, 'plugins', { get: () => [1, 2, 3, 4, 5] });
"""

async def ensure_chromium_installed(job_id: str = None) -> None:
    if job_id:
        append_job_log(job_id, "[*] Installing Chromium binary on server...", status="Installing Chromium...")
    proc = await asyncio.create_subprocess_exec(
        sys.executable, "-m", "playwright", "install", "chromium",
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
    )
    await proc.communicate()

async def get_warm_browser():
    global _PW_INSTANCE, _WARM_BROWSER
    async with _BROWSER_LOCK:
        if _WARM_BROWSER and _WARM_BROWSER.is_connected():
            return _WARM_BROWSER
        for attempt in range(2):
            try:
                if _PW_INSTANCE is None:
                    _PW_INSTANCE = await async_playwright().start()
                _WARM_BROWSER = await _PW_INSTANCE.chromium.launch(
                    headless=True,
                    args=[
                        "--no-sandbox",
                        "--disable-setuid-sandbox",
                        "--disable-dev-shm-usage",
                        "--disable-gpu",
                        "--disable-blink-features=AutomationControlled",
                        "--disable-background-networking",
                        "--disable-default-apps",
                        "--disable-extensions",
                        "--disable-sync",
                        "--mute-audio",
                    ],
                )
                return _WARM_BROWSER
            except Exception as e:
                if attempt == 0:
                    await ensure_chromium_installed()
                else:
                    raise e

async def _fast_route_interceptor(route):
    req = route.request
    if req.resource_type in BLOCKED_RESOURCE_TYPES:
        await route.abort()
        return
    url_low = req.url.lower()
    if any(b in url_low for b in BLOCKED_URL_SUBSTRINGS):
        await route.abort()
        return
    await route.continue_()

async def _capture_live_viewport_b64(page, save_path: Path = None) -> str:
    img_bytes = await page.screenshot(
        path=str(save_path) if save_path else None,
        type="jpeg",
        quality=82,
        full_page=False,
    )
    return "data:image/jpeg;base64," + base64.b64encode(img_bytes).decode("ascii")

async def execute_automation_job(
    job_id: str,
    agent_id: str,
    account_name: str,
    fb_uid: str,
    post_url: str,
    comment_text: str,
    cookies: list,
    do_like: bool = True,
    do_comment: bool = True,
    proxy: str = "",
) -> None:
    t0 = time.perf_counter()
    screenshot_name = f"{job_id}_{agent_id}.jpg"
    screenshot_path = SCREENSHOTS_DIR / screenshot_name
    pw_cookies = normalize_playwright_cookies(cookies or [])

    append_job_log(
        job_id,
        f"[*] Armed {len(pw_cookies)} session cookies ({account_name} • {fb_uid}). Opening warm stealth tab...",
        status="Opening Live Tab...",
    )

    context = None
    try:
        browser = await get_warm_browser()
        ctx_kwargs = {
            "viewport": {"width": 1280, "height": 800},
            "user_agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
            "locale": "en-US",
        }
        if proxy and proxy.strip():
            ctx_kwargs["proxy"] = {"server": proxy.strip()}
            append_job_log(job_id, f"[+] Bound residential proxy: {proxy.strip()}")

        context = await browser.new_context(**ctx_kwargs)
        await context.add_init_script(STEALTH_INIT_SCRIPT)
        await context.route("**/*", _fast_route_interceptor)

        if pw_cookies:
            await context.add_cookies(pw_cookies)

        page = await context.new_page()
        append_job_log(job_id, f"[*] Navigating live to {post_url} (blocking heavy video bloat)...", status="Loading Live Facebook...")

        await page.goto(post_url, wait_until="domcontentloaded", timeout=10000)
        await page.wait_for_timeout(600)

        # Stage 1: Dismiss soft popups/dialogs & stream immediate live Stage-1 screenshot to UI
        await page.evaluate("""() => {
            const closeSelectors = [
                'div[aria-label="Close"]',
                'div[role="dialog"] div[aria-label="Close"]',
                'div[aria-label="Decline optional cookies"]',
                'div[aria-label="Allow all cookies"]'
            ];
            for (const sel of closeSelectors) {
                const el = document.querySelector(sel);
                if (el) { try { el.click(); } catch(e) {} }
            }
        }""")

        # Extract real logged-in Facebook owner name if present in DOM
        try:
            detected_owner = await page.evaluate("""() => {
                try {
                    const d = window.require && window.require("CurrentUserInitialData");
                    if (d && d.NAME) return d.NAME;
                } catch (e) {}
                return null;
            }""")
            if detected_owner and is_valid_owner_name(detected_owner):
                account_name = detected_owner.strip()
                set_detected_account_name(agent_id, account_name)
                append_job_log(job_id, f"[+] Live DOM verified account owner: {account_name} ({fb_uid})", account_name=account_name)
        except Exception:
            pass

        # Stream Stage-1 Live Preview Screenshot immediately so user sees the real browser right away!
        stage1_b64 = await _capture_live_viewport_b64(page)
        ms_stage1 = int((time.perf_counter() - t0) * 1000)
        append_job_log(
            job_id,
            f"[📸] Stage 1: Live Facebook viewport loaded in {ms_stage1}ms. Executing actions...",
            status="Interacting on Live Page...",
            screenshot=stage1_b64,
            execution_ms=ms_stage1,
        )

        # Check if Facebook showed a login screen
        login_wall = await page.evaluate("""() => {
            const u = window.location.href.toLowerCase();
            if (u.includes('/login') || u.includes('login.php')) return true;
            const passInputs = document.querySelectorAll('input[type="password"], input[name="pass"]');
            const hasComposer = document.querySelector('div[role="textbox"], [aria-label*="comment" i], [aria-label*="Like" i]');
            return (passInputs.length > 0 && !hasComposer);
        }""")

        if login_wall:
            append_job_log(
                job_id,
                "[!] Notice: Facebook served a login prompt on this IP/cookie session. Refresh cookies or run locally for authenticated state.",
            )

        # Fast Single-Pass Like Execution
        liked_ok = False
        if do_like:
            liked_ok = await page.evaluate("""() => {
                const candidates = [
                    ...document.querySelectorAll('div[aria-label="Like"][role="button"]'),
                    ...document.querySelectorAll('div[aria-label*="Like" i][role="button"]'),
                    ...document.querySelectorAll('span')
                ];
                for (const el of candidates) {
                    const label = (el.getAttribute && el.getAttribute('aria-label')) || '';
                    const txt = (el.innerText || '').trim();
                    if (label === 'Like' || label.startsWith('Like') || txt === 'Like') {
                        const btn = el.closest('[role="button"]') || el;
                        btn.scrollIntoView({block: 'center'});
                        btn.click();
                        return true;
                    }
                }
                return false;
            }""")
            if liked_ok:
                append_job_log(job_id, "[+] Clicked Like button on live Facebook page!")
                await page.wait_for_timeout(350)
            else:
                append_job_log(job_id, "[i] Like button not exposed on current view layout.")

        # Fast Comment Execution (Focus + Keyboard Type + Enter)
        commented_ok = False
        if do_comment and comment_text:
            # First click any "Comment" icon if the textbox is collapsed (e.g., on Reels)
            await page.evaluate("""() => {
                const cBtns = document.querySelectorAll('div[aria-label="Comment"][role="button"], div[aria-label*="Leave a comment" i][role="button"]');
                for (const b of cBtns) {
                    try { b.click(); break; } catch(e) {}
                }
            }""")
            await page.wait_for_timeout(350)

            box_Selectors = [
                'div[role="textbox"][aria-label*="comment" i]',
                'div[role="textbox"][contenteditable="true"]',
                'textarea[placeholder*="comment" i]',
                'div[contenteditable="true"]',
            ]
            for sel in box_Selectors:
                loc = page.locator(sel).first
                if await loc.count() > 0:
                    try:
                        await loc.scroll_into_view_if_needed(timeout=1000)
                        await loc.click(timeout=1200)
                        await page.keyboard.type(comment_text, delay=8)
                        await page.wait_for_timeout(200)
                        await page.keyboard.press("Enter")
                        await page.wait_for_timeout(900)
                        commented_ok = True
                        append_job_log(job_id, "[+] Typed and submitted AI comment on live Facebook page!")
                        break
                    except Exception:
                        continue

            if not commented_ok:
                append_job_log(job_id, "[i] Live comment input box not unlocked on this post view.")

        # Stage 2: Capture Final 100% Real Live Browser Screenshot
        final_b64 = await _capture_live_viewport_b64(page, save_path=screenshot_path)
        total_ms = int((time.perf_counter() - t0) * 1000)

        if liked_ok or commented_ok:
            final_status = f"Completed Live ({total_ms/1000:.1f}s • {account_name})"
        elif login_wall:
            final_status = f"Live Captured (Login Wall • {total_ms/1000:.1f}s)"
        else:
            final_status = f"Live Captured ({total_ms/1000:.1f}s • {account_name})"

        append_job_log(
            job_id,
            f"[📸] Stage 2: Final 100% real live browser screenshot captured in {total_ms}ms!",
            status=final_status,
            screenshot=final_b64,
            execution_ms=total_ms,
        )

    except Exception as err:
        total_ms = int((time.perf_counter() - t0) * 1000)
        append_job_log(
            job_id,
            f"[!] Live Browser Notice ({total_ms}ms): {str(err)[:110]}",
            status=f"Finished ({total_ms/1000:.1f}s)",
            execution_ms=total_ms,
        )
    finally:
        if context:
            try:
                await context.close()
            except Exception:
                pass
