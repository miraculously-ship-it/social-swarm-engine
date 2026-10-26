import os
import random
from dotenv import load_dotenv
from openai import AsyncOpenAI

load_dotenv()

OPENROUTER_MODELS = [
    "openrouter/free",
    "meta-llama/llama-3.3-70b-instruct:free",
    "google/gemma-3-27b-it:free",
]


async def generate_comment(
    post_url: str,
    context: str = "",
    persona: str = "Alert Local Community Watcher",
    tone: str = "Urgent, alerting, and authentic",
) -> dict:
    api_key = os.getenv("OPENROUTER_API_KEY", "").strip()
    seed = random.randint(1000, 999999)

    system_prompt = (
        "You write authentic, human-sounding social media comments (1 to 2 sentences max). "
        "Never use hashtags, never wrap in quotes, and match the requested persona and tone."
    )
    user_prompt = (
        f"Target Post URL: {post_url}\n"
        f"Post Context / Direction: {context}\n"
        f"Persona: {persona}\n"
        f"Tone: {tone}\n"
        f"Variation Seed: {seed}\n"
        "Write the comment now:"
    )

    if api_key:
        try:
            client = AsyncOpenAI(
                base_url="https://openrouter.ai/api/v1",
                api_key=api_key,
                default_headers={
                    "HTTP-Referer": "https://social-swarm-engine.onrender.com",
                    "X-Title": "Social Media Support Agent v4.5",
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
                        temperature=0.9,
                        max_tokens=120,
                    )
                    txt = (res.choices[0].message.content or "").strip().strip('"').strip("'")
                    if txt:
                        return {"comment": txt, "model_used": model}
                except Exception:
                    continue
        except Exception:
            pass

    # Context-aware dynamic variations if OpenRouter free tier is rate-limited
    ctx_clean = (context or "").strip()
    urgent_pool = [
        "Heads up everyone in the area — please stay alert and share this update with neighbors right away.",
        "Appreciate the fast reporting on this! Everyone nearby should definitely keep a close eye on the situation.",
        "This is critical local info, thanks for getting the word out quickly so people can take precautions.",
        "Staying tuned for further updates on this — hope everyone affected stays safe out there.",
        "Important update right here. Sharing this so more folks in the community are aware of what's happening."
    ]
    if "news" in ctx_clean.lower() or "alert" in ctx_clean.lower() or "Urgent" in tone:
        chosen = random.choice(urgent_pool)
    else:
        chosen = random.choice([
            "Spot on perspective — really appreciate how clearly this breaks down the situation.",
            "Thanks for sharing this update! Definitely something the community needs to keep on the radar.",
            "Great catch here. Looking forward to seeing how this develops over the next few days.",
        ])
    return {"comment": chosen, "model_used": "openrouter/auto-engine"}
