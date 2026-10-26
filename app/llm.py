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
        "You are a real human social media power-user leaving a high-value comment on a post.\n"
        "Strict rules:\n"
        "1. Write 1 to 3 concise, natural sentences.\n"
        "2. Sound completely authentic—no hashtags, no emoji spam, no surrounding quotes, and no generic AI openings.\n"
        "3. Directly weave in the operator's post context and match the assigned persona and tone."
    )
    if custom_directive:
        system_prompt += f"\n4. Additional Supervisor Directive: {custom_directive}"

    user_prompt = (
        f"Target Post URL: {post_url}\n"
        f"Post Context / Fill-in Details: {context if context.strip() else 'General community update; provide a sharp, relevant observation.'}\n"
        f"Agent Persona: {persona}\n"
        f"Tone Profile: {tone}\n"
        f"Variation Seed: {seed}\n\n"
        "Output ONLY the final comment text:"
    )

    if api_key:
        client = AsyncOpenAI(
            base_url="https://openrouter.ai/api/v1",
            api_key=api_key,
            default_headers={
                "HTTP-Referer": "https://social-swarm-engine.onrender.com",
                "X-Title": "Social Swarm Supervisor Control Center v4.5",
            },
        )

        for model_slug in OPENROUTER_MODELS:
            try:
                response = await client.chat.completions.create(
                    model=model_slug,
                    messages=[
                        {"role": "system", "content": system_prompt},
                        {"role": "user", "content": user_prompt},
                    ],
                    temperature=0.88,
                    max_tokens=180,
                )
                msg = (response.choices[0].message.content or "").strip().strip('"').strip("'")
                if msg:
                    return {
                        "comment": msg,
                        "model_used": model_slug,
                        "source": "openrouter",
                        "seed": seed,
                    }
            except Exception as err:
                print(f"[!] Model {model_slug} skipped: {err}")
                continue

    subject = context.strip() if context.strip() else "the execution details shared here"
    short_subj = subject[:85]
    templates = [
        f"The breakdown around {short_subj} is spot on. Most teams overlook the operational bottlenecks until they scale, so this is a solid callout.",
        f"Really appreciate the transparency on {short_subj}. We ran into a very similar dynamic recently and focusing on the fundamentals made all the difference.",
        f"Sharp perspective on {short_subj}. Curious how you see this evolving over the next quarter as more operators adopt this workflow?",
        f"This hits the nail on the head regarding {short_subj}. Cutting out the noise and prioritizing real execution is always the winning move."
    ]
    return {
        "comment": templates[seed % len(templates)],
        "model_used": "openrouter/free-shield",
        "source": "fallback",
        "seed": seed,
    }
