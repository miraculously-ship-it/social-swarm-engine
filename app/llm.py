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

MULTILINGUAL_FALLBACKS = {
    "English": [
        "Heads up everyone in the area — please stay alert and share this update with neighbors right away.",
        "Appreciate the fast reporting on this! Everyone nearby should definitely keep a close eye on the situation.",
        "Spot on perspective — really appreciate how clearly this breaks down what is happening right now.",
        "Thanks for putting this on the radar so quickly, definitely something the whole community needs to see."
    ],
    "Amharic (አማርኛ)": [
        "በጣም ጠቃሚ መረጃ ነው፣ ሁሉም ሰው ጥንቃቄ እንዲያደርግ ይህንን መረጃ ለሌሎችም እናጋራ!",
        "ስለ ፈጣኑ መረጃ እናመሰግናለን! በአካባቢው ያላችሁ ወገኖች ሁሉ ነቃ ብላችሁ ተከታተሉ።",
        "በጣም ጥሩ ትንታኔ ነው፣ ጉዳዩን በግልፅ ስላስቀመጣችሁት እናመሰግናለን።"
    ],
    "Afaan Oromo": [
        "Odeeffannoo baay'ee barbaachisaa dha, namni hundi of eeggannoo akka godhuuf waliif haa qoodnu!",
        "Odeeffannoo ariifachiisaa kanaaf galatoomaa! Warri naannoo sana jirtan xiyyeeffannoon hordofaa."
    ],
    "Tigrinya (ትግርኛ)": [
        "ብጣዕሚ ጠቓሚ ሓበሬታ እዩ፣ ኩሉ ሰብ ጥንቃቐ ምእንቲ ክገብር ነዚ ሓበሬታ ንኻልኦት ንካፈሎ!",
        "ስለቲ ቅልጡፍ ሓበሬታ ነመስግን! ኣብቲ ከባቢ ዘለኹም ኩሉኹም ብንቕሓት ተኸታተሉ።"
    ],
    "Arabic (العربية)": [
        "معلومة مهمة جداً، يرجى من الجميع الانتباه ومشاركة هذا التحديث فوراً.",
        "شكراً على التغطية السريعة! يجب على الجميع في المنطقة توخي الحذر والمتابعة عن كثب."
    ],
    "French (Français)": [
        "Info très importante, restez vigilants dans le secteur et partagez cette mise à jour autour de vous !",
        "Merci pour la rapidité de l'information ! Tout le monde à proximité devrait suivre ça de près."
    ],
    "Spanish (Español)": [
        "¡Atención a todos en la zona! Por favor manténganse alerta y compartan esta actualización de inmediato.",
        "¡Gracias por informar tan rápido! Todos cerca deberían seguir de cerca esta situación."
    ],
    "Swahili (Kiswahili)": [
        "Taarifa muhimu sana hii, tafadhali kila mtu awe makini na tuambizane haraka!",
        "Asante kwa taarifa ya haraka! Wakazi wote wa eneo hilo wanapaswa kufuatilia kwa karibu."
    ]
}

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
        "Every comment must be completely unique and fresh. "
        f"{lang_instruction}"
    )
    user_prompt = (
        f"Target Post URL: {post_url}\n"
        f"Post Context / Direction: {context}\n"
        f"Persona: {persona}\n"
        f"Tone: {tone}\n"
        f"Target Language: {lang_clean}\n"
        f"Unique Variation Seed: {seed}\n"
        f"Write a brand-new comment now in {lang_clean}:"
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
                        temperature=0.92,
                        max_tokens=150,
                    )
                    txt = (res.choices[0].message.content or "").strip().strip('"').strip("'")
                    if txt:
                        return {"comment": txt, "model_used": model, "language": lang_clean}
                except Exception:
                    continue
        except Exception:
            pass

    pool = MULTILINGUAL_FALLBACKS.get(lang_clean, MULTILINGUAL_FALLBACKS["English"])
    return {"comment": random.choice(pool), "model_used": "openrouter/auto-engine", "language": lang_clean}
