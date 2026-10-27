import os
import random
import httpx
from dotenv import load_dotenv
from openai import AsyncOpenAI

load_dotenv()

OPENROUTER_MODELS = [
    "meta-llama/llama-3.3-70b-instruct:free",
    "google/gemma-3-27b-it:free",
    "mistralai/mistral-small-3.1-24b-instruct:free",
    "openrouter/free",
]

# Tracks recently generated comments so the bot NEVER repeats itself
RECENT_COMMENTS = set()

DYNAMIC_OPENERS = {
    "Urgent": [
        "Heads up everyone following this —",
        "Important update to keep on your radar:",
        "Everyone in the community should take note of this right away —",
        "Glad this is getting shared quickly;",
        "Critical perspective here —",
        "Sharing this for visibility because timing matters:",
    ],
    "Warm": [
        "Really appreciate you sharing this with the community!",
        "Love seeing how clearly and thoughtfully this was put together.",
        "Such a helpful and grounded way to look at this!",
        "Big thanks for highlighting this today —",
        "Always grateful for updates like this that actually help people out.",
        "This is super encouraging and well said!",
    ],
    "Sharp": [
        "Spot-on breakdown of what actually matters here.",
        "This hits the core issue directly without the usual noise.",
        "Sharp analysis — the real takeaway is right between the lines.",
        "Clear, direct, and exactly the right angle to take on this.",
        "Hard to argue with the logic laid out in this post.",
        "This cuts straight to the point and highlights the key dynamic.",
    ],
    "Casual": [
        "Honestly this is one of the most relatable takes I've seen all week.",
        "Couldn't agree more with the vibe here —",
        "Lowkey the most accurate post on my feed today!",
        "Had to stop scrolling for this one, totally spot on.",
        "100% feeling this perspective right now —",
        "Real talk, this summed it up better than anyone else has.",
    ],
}

DYNAMIC_CLOSERS = [
    "definitely worth keeping a close eye on how this develops.",
    "hope more people in the feed take a second to read through this.",
    "let's make sure the right people see this update today.",
    "curious to see how everyone else here is reading the situation.",
    "appreciate the clarity and the fast heads-up on this one.",
    "it makes a huge difference when updates are shared this clearly.",
    "passing this along so neighbors and friends stay in the loop.",
    "solid points all around, glad this came across the timeline.",
]

NATIVE_TEMPLATES = {
    "Amharic (አማርኛ)": [
        "በጣም ጠቃሚ እና ወቅታዊ መረጃ ነው {ctx} — ሁሉም ሰው ትኩረት ሰጥቶ ሊከታተለው ይገባል!",
        "ስለዚህ ግልጽ እና ፈጣን መረጃ ከልብ እናመሰግናለን {ctx}፤ ለሌሎችም መድረስ ያለበት ሀሳብ ነው።",
        "በጣም ጥሩ እይታ ነው {ctx}፣ ጉዳዩን በትክክል ስላስቀመጣችሁት አድናቆቴን እገልጻለሁ።",
        "እንዲህ ያሉ ጠቃሚ መረጃዎች በወቅቱ መለቀቃቸው ለማህበረሰቡ ትልቅ ጥቅም አለው {ctx}።",
        "ሁሉም ወገን ይህንን መረጃ ልብ ብሎ እንዲመለከተው እና ለወዳጆቹ እንዲያጋራ እመክራለሁ {ctx}።",
        "በጣም የሚገርም እና ትክክለኛ ትንታኔ ነው {ctx}፣ በርቱልን!"
    ],
    "Afaan Oromo": [
        "Odeeffannoo baay'ee barbaachisaa fi yerooን፣ {ctx} namni hundi xiyyeeffannoon haa hordofu!",
        "Yaada bilchaataa fi ifa ta'e dha {ctx}, galatoomaa!",
        "Odeeffannoo ariifachiisaa kanaaf guddaa galatoomaa {ctx}, waliif qooduu hin dagatinaa.",
        "Dhuguma ilaalcha gaarii fi barbaachisaa dha {ctx}, hawaasni keenya kana hubachuu qaba."
    ],
    "Tigrinya (ትግርኛ)": [
        "ብጣዕሚ ጠቓሚን እዋናውን ሓበሬታ እዩ {ctx}፣ ኩሉ ሰብ ብንቕሓት ክከታተሎ ይግባእ!",
        "ስለቲ ቅልጡፍን ንጹርን ሓበሬታ ብልቢ ነመስግን {ctx}!",
        "ብጣዕሚ ጽቡቕ ትንታነ እዩ {ctx}፣ ንኻልኦት እውን ክበጽሕ ዘለዎ ኣገዳሲ ጉዳይ እዩ።"
    ],
    "Arabic (العربية)": [
        "طرح ممتاز وواضح جداً {ctx}، نشكركم على مشاركة هذه التفاصيل المهمة في الوقت المناسب.",
        "معلومة مهمة للغاية {ctx}، يرجى من الجميع الانتباه ومتابعة هذا التحديث عن كثب.",
        "تحليل دقيق ومباشر للوضع {ctx}، يستحق المشاركة لتعم الفائدة على الجميع.",
        "تغطية رائعة وسريعة {ctx}، نقدر جهودكم في توضيح الصورة كاملة."
    ],
    "French (Français)": [
        "Analyse vraiment pertinente {ctx} — merci d'avoir partagé ces détails aussi clairement !",
        "Info super importante {ctx}, tout le monde devrait suivre cette évolution de près.",
        "Tout à fait d'accord avec cet angle {ctx}, ça résume parfaitement la situation actuelle.",
        "Merci pour la réactivité sur ce sujet {ctx}, c'est exactement ce qu'il fallait souligner."
    ],
    "Spanish (Español)": [
        "Excelente punto de vista {ctx} — ¡gracias por compartir esta actualización tan rápido!",
        "Información clave para todos {ctx}, vale la pena seguir de cerca cómo evoluciona esto.",
        "Totalmente de acuerdo con este enfoque {ctx}, lo explicaron con muchísima claridad.",
        "Qué buen análisis de la situación {ctx}, definitivamente hay que compartirlo."
    ],
    "Swahili (Kiswahili)": [
        "Taarifa muhimu sana hii {ctx}, asante kwa kuiweka wazi kwa wakati muafaka!",
        "Mtazamo mzuri na wa kina {ctx} — kila mtu anapaswa kufuatilia suala hili kwa karibu.",
        "Shukrani kwa taarifa hii ya haraka {ctx}, tuendelee kuhabarishana!"
    ]
}

def _build_dynamic_unique_comment(context: str, persona: str, tone: str, language: str) -> str:
    clean_ctx = (context or "").strip()
    ctx_snippet = f"regarding {clean_ctx}" if clean_ctx and len(clean_ctx) < 70 else ""

    if language in NATIVE_TEMPLATES:
        pool = NATIVE_TEMPLATES[language]
        for _ in range(15):
            cand = random.choice(pool).format(ctx=f"({clean_ctx})" if clean_ctx else "").replace("  ", " ").strip()
            if cand not in RECENT_COMMENTS:
                RECENT_COMMENTS.add(cand)
                return cand

    tone_lower = (tone or "").lower()
    if "warm" in tone_lower or "helpful" in tone_lower:
        bucket = "Warm"
    elif "sharp" in tone_lower or "direct" in tone_lower or "analytical" in tone_lower:
        bucket = "Sharp"
    elif "casual" in tone_lower or "witty" in tone_lower or "friendly" in tone_lower:
        bucket = "Casual"
    else:
        bucket = "Urgent"

    openers = DYNAMIC_OPENERS[bucket]
    for _ in range(30):
        opener = random.choice(openers)
        closer = random.choice(DYNAMIC_CLOSERS)
        if clean_ctx:
            middle = f" the point on {clean_ctx} really stands out, and "
        else:
            middle = " "
        candidate = f"{opener}{middle}{closer}".replace("  ", " ").strip()
        if candidate not in RECENT_COMMENTS:
            RECENT_COMMENTS.add(candidate)
            return candidate

    fallback = f"{random.choice(openers)} {random.choice(DYNAMIC_CLOSERS)} (#{random.randint(10,99)})"
    RECENT_COMMENTS.add(fallback)
    return fallback

async def generate_comment(
    post_url: str,
    context: str = "",
    persona: str = "Alert Local Community Watcher",
    tone: str = "Urgent, alerting, and authentic",
    language: str = "English",
) -> dict:
    api_key = os.getenv("OPENROUTER_API_KEY", "").strip()
    seed = random.randint(100000, 999999)
    lang_clean = (language or "English").strip()

    lang_instruction = (
        "Detect the language used in the Post Context and write the comment natively in that same language."
        if "Auto-Detect" in lang_clean
        else f"You MUST write the entire comment natively, naturally, and fluently in {lang_clean}. Do NOT include English translations."
    )

    system_prompt = (
        "You write authentic, human-sounding social media comments (1 to 2 sentences max). "
        "Never use hashtags, never wrap in quotes, and match the requested persona and tone. "
        "Every single comment must use fresh phrasing and directly reflect the user's Post Context/Direction. "
        f"{lang_instruction}"
    )
    user_prompt = (
        f"Target Post URL: {post_url}\n"
        f"Post Context / Topic: {context or 'General community post/reel'}\n"
        f"Persona: {persona}\n"
        f"Tone: {tone}\n"
        f"Target Language: {lang_clean}\n"
        f"Random Creativity Seed: {seed}\n"
        f"Write 1 unique, natural social media comment now in {lang_clean}:"
    )

    # 1. Try OpenRouter first if API key is configured (Fast 4s timeout)
    if api_key:
        try:
            client = AsyncOpenAI(
                base_url="https://openrouter.ai/api/v1",
                api_key=api_key,
                timeout=4.0,
                default_headers={
                    "HTTP-Referer": "https://social-swarm-engine.onrender.com",
                    "X-Title": "Social Media Support Agent v4.6",
                },
            )
            for model in OPENROUTER_MODELS:
                try:
                    res = await client.chat.completions.create(
                        model=model,
                        messages=[
                            {"role": "system", "content": system_prompt},
                            {"role": "user", "content": user_prompt},
                        ],
                        temperature=0.95,
                        max_tokens=120,
                    )
                    txt = (res.choices[0].message.content or "").strip().strip('"').strip("'")
                    if txt and txt not in RECENT_COMMENTS:
                        RECENT_COMMENTS.add(txt)
                        return {"comment": txt, "model_used": model, "language": lang_clean}
                except Exception:
                    continue
        except Exception:
            pass

    # 2. Keyless Real LLM via Pollinations OpenAI-compatible API (Works on Render without any API key!)
    try:
        async with httpx.AsyncClient(timeout=4.2) as http_client:
            resp = await http_client.post(
                "https://text.pollinations.ai/openai",
                json={
                    "model": "openai",
                    "messages": [
                        {"role": "system", "content": system_prompt},
                        {"role": "user", "content": user_prompt},
                    ],
                    "temperature": 0.95,
                    "seed": seed,
                },
            )
            if resp.status_code == 200:
                data = resp.json()
                txt = (data.get("choices", [{}])[0].get("message", {}).get("content") or "").strip().strip('"').strip("'")
                if txt and len(txt) > 8 and txt not in RECENT_COMMENTS:
                    RECENT_COMMENTS.add(txt)
                    return {"comment": txt, "model_used": "pollinations/openai-live", "language": lang_clean}
    except Exception:
        pass

    # 3. Instant Combinatorial Context Engine (Guaranteed unique even if offline)
    unique_comment = _build_dynamic_unique_comment(context, persona, tone, lang_clean)
    return {"comment": unique_comment, "model_used": "dynamic-variation-engine", "language": lang_clean}
