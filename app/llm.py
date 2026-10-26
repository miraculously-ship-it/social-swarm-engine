import os
import random
from dotenv import load_dotenv
from openai import AsyncOpenAI

load_dotenv()

OPENROUTER_MODELS = [
    "openrouter/free",
    "openrouter/auto",
    "meta-llama/llama-3.3-70b-instruct",
    "google/gemma-3-27b-it",
    "mistralai/mistral-small-3.1-24b-instruct",
]


async def generate_comment(
    post_url: str,
    context: str = "",
    persona: str = "Constructive industry peer",
    tone: str = "Engaging & Natural",
    custom_directive: str = "",
    variation_seed: int = 0
) -> dict:
    api_key = os.getenv("OPENROUTER_API_KEY", "").strip()
    seed = variation_seed or random.randint(1000, 99999)

    system_prompt = (
        "You are a real human social media user leaving a high-value comment.\n"
        "Rules: Write 1-3 natural sentences. No hashtags, no quotes, no robotic AI phrasing."
    )
    if custom_directive:
        system_prompt += f"\nDirective: {custom_directive}"

    user_prompt = f"URL: {post_url}\nContext: {context}\nPersona: {persona}\nTone: {tone}\nComment:"

    if api_key:
        client = AsyncOpenAI(
            base_url="https://openrouter.ai/api/v1",
            api_key=api_key,
            default_headers={"HTTP-Referer": "https://social-swarm-engine.onrender.com", "X-Title": "Supervisor v4.5"},
        )
        for model in OPENROUTER_MODELS:
            try:
                res = await client.chat.completions.create(
                    model=model,
                    messages=[{"role": "system", "content": system_prompt}, {"role": "user", "content": user_prompt}],
                    temperature=0.85,
                    max_tokens=150,
                )
                txt = (res.choices[0].message.content or "").strip().strip('"').strip("'")
                if txt:
                    return {"comment": txt, "model_used": model, "source": "openrouter"}
            except Exception:
                continue

    fallbacks = [
        "Really appreciate the insights here. The operational focus makes total sense.",
        "Solid breakdown! We noticed a similar pattern when scaling this workflow.",
        "Curious how you plan to measure the impact of this over the next quarter?"
    ]
    return {"comment": fallbacks[seed % len(fallbacks)], "model_used": "local-fallback", "source": "fallback"}
