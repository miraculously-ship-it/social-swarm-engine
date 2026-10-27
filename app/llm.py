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

async def generate_comment(post_url: str, context: str = "", persona: str = "Community Watcher", tone: str = "Urgent & Alerting") -> dict:
    api_key = os.getenv("OPENROUTER_API_KEY", "").strip()
    system_prompt = "Write an authentic, human-sounding social media comment (1-2 sentences). No hashtags, no quotes."
    user_prompt = f"URL: {post_url}\nContext: {context}\nPersona: {persona}\nTone: {tone}\nComment:"

    if api_key:
        try:
            client = AsyncOpenAI(base_url="https://openrouter.ai/api/v1", api_key=api_key)
            for model in OPENROUTER_MODELS:
                try:
                    res = await client.chat.completions.create(
                        model=model,
                        messages=[{"role": "system", "content": system_prompt}, {"role": "user", "content": user_prompt}],
                        temperature=0.85,
                        max_tokens=100
                    )
                    txt = (res.choices[0].message.content or "").strip().strip('"').strip("'")
                    if txt:
                        return {"comment": txt, "model_used": model}
                except Exception:
                    continue
        except Exception:
            pass

    fallbacks = [
        "Heads up everyone in the area — please stay alert and share this update.",
        "Appreciate the fast reporting on this! Everyone nearby should keep an eye out.",
        "Critical local info, thanks for getting the word out quickly."
    ]
    return {"comment": random.choice(fallbacks), "model_used": "fallback-engine"}
