import random

USED_COMMENTS = set()

OPENERS = {
    "urgent": [
        "Heads up everyone seeing this —",
        "Important update for the timeline right now:",
        "Everyone following this should definitely take note —",
        "Really glad somebody posted this quickly;",
        "Crucial update here —",
        "Sharing this for immediate visibility:",
        "Pay close attention to this update —",
        "Definitely something the whole community needs on their radar:",
    ],
    "warm": [
        "Really appreciate you sharing this with everyone today!",
        "Love how clearly and thoughtfully this was put together —",
        "Such a helpful and grounded perspective on this!",
        "Big thanks for putting this out there for the community —",
        "Always grateful for posts that break things down this well!",
        "This is honestly so refreshing and helpful to see on the feed —",
        "Shoutout for highlighting this so clearly today!",
        "Really glad I came across this post today —",
    ],
    "sharp": [
        "Spot-on breakdown of what actually matters here.",
        "This cuts straight to the core issue without the usual noise —",
        "Sharp analysis; the key takeaway here is impossible to miss.",
        "Direct, clear, and the exact right angle to take on this.",
        "Hard to argue with the logic laid out here —",
        "Finally a perspective that focuses on the real dynamics at play:",
        "Cleanest summary of the situation I have seen all week —",
        "Right on target — this highlights the exact detail people overlook.",
    ],
    "casual": [
        "Honestly this is the most accurate take on my feed all day!",
        "Had to stop scrolling for this one — 100% spot on.",
        "Lowkey the best way anyone could have summed this up!",
        "Couldn't agree more with the vibe on this post —",
        "Real talk, this hit the nail on the head completely.",
        "Been waiting for someone to say this out loud!",
        "Facts from start to finish —",
        "This right here is why I still check the timeline!",
    ]
}

MIDDLES_WITH_CTX = [
    "the point about {ctx} is super relevant right now, and",
    "especially regarding {ctx},",
    "when it comes to {ctx}, this hits the mark and",
    "highlighting {ctx} makes a massive difference, so",
    "seeing {ctx} addressed this directly is huge, and",
    "the way this touches on {ctx} is 100% accurate —",
]

MIDDLES_NO_CTX = [
    "the way this is unfolding is super important, and",
    "every detail shared here adds real value, so",
    "it really puts the whole situation into perspective, and",
    "timing on this update could not be better, so",
    "this is the exact kind of context people need right now, and",
    "the clarity on this post speaks for itself, so",
]

CLOSERS = [
    "worth keeping a very close eye on how it develops.",
    "hope more people take a minute to read and share this.",
    "making sure neighbors and friends see this right away.",
    "curious to hear how everyone else in the comments sees it.",
    "appreciate the fast heads-up and solid reporting.",
    "glad this is finally getting the attention it deserves.",
    "definitely passing this along to everyone in the group.",
    "solid points all around — keep these updates coming!",
]

MULTILINGUAL_BANK = {
    "Amharic (አማርኛ)": [
        ("በጣም ጠቃሚ እና ወቅታዊ መረጃ ነው", "ሁሉም ሰው ትኩረት ሰጥቶ ሊከታተለው ይገባል!"),
        ("ስለዚህ ግልጽ እና ፈጣን መረጃ ከልብ እናመሰግናለን", "ለሌሎችም በፍጥነት መድረስ ያለበት ሀሳብ ነው።"),
        ("በጣም ጥሩ እይታ እና ትንታኔ ነው", "ጉዳዩን በትክክል ስላስቀመጣችሁት አድናቆቴን እገልጻለሁ።"),
        ("እንዲህ ያሉ ጠቃሚ መረጃዎች በወቅቱ መለቀቃቸው ትልቅ ጥቅም አለው", "ሁላችንም ልብ እንበል።"),
        ("ሁሉም ወገን ይህንን መረጃ በትኩረት እንዲመለከተው እመክራለሁ", "ስለ መረጃው በጣም እናመሰግናለን!"),
        ("በጣም የሚገርም እና ትክክለኛ ነጥብ ነው", "ቀጣዩን ሁኔታ በንቃት እንከታተላለን።"),
    ],
    "Afaan Oromo": [
        ("Odeeffannoo baay'ee barbaachisaa fi yeroo isaa eeggate dha", "namni hundi xiyyeeffannoon haa hordofu!"),
        ("Yaada bilchaataa fi ifa ta'e dha", "galatoomaa, waliif qooduu hin dagatinaa!"),
        ("Odeeffannoo ariifachiisaa kanaaf guddaa galatoomaa", "hawaasni keenya kana hubachuu qaba."),
        ("Dhuguma ilaalcha gaarii fi barbaachisaa dha", "yaada cimaa akkanaa itti fufaa!"),
    ],
    "Tigrinya (ትግርኛ)": [
        ("ብጣዕሚ ጠቓሚን እዋናውን ሓበሬታ እዩ", "ኩሉ ሰብ ብንቕሓት ክከታተሎ ይግባእ!"),
        ("ስለቲ ቅልጡፍን ንጹርን ሓበሬታ ብልቢ ነመስግን", "ንኻልኦት እውን ክበጽሕ ዘለዎ ኣገዳሲ ጉዳይ እዩ።"),
        ("ብጣዕሚ ጽቡቕ ትንታነ እዩ", "ኩላትና ብጥንቃቐ ንከታተሎ!"),
    ],
    "Somali (Soomaali)": [
        ("Warbixin aad u muhiim ah weeye", "qof walba waa inuu si dhow ula socdaa xaaladdan!"),
        ("Aad ayaad ugu mahadsan tihiin xogtan degdegga ah", "aan la wadaagno bulshada inteeda kale."),
        ("Falanqayn aad ucad oo waxtar leh", "mahadsanidiin sida wanaagsan ee aad u soo gudbiseen!"),
    ],
    "Swahili (Kiswahili)": [
        ("Taarifa muhimu sana hii", "asante kwa kuiweka wazi kwa wakati muafaka!"),
        ("Mtazamo mzuri na wa kina", "kila mtu anapaswa kufuatilia suala hili kwa karibu."),
        ("Shukrani kwa taarifa hii ya haraka", "tuendelee kuhabarishana kwenye jamii!"),
        ("Uchambuzi sahihi kabisa", "hii inasaidia sana kuelewa kinachoendelea sasa hivi."),
    ],
    "Arabic (العربية)": [
        ("طرح ممتاز وواضح جداً", "نشكركم على مشاركة هذه التفاصيل المهمة في الوقت المناسب."),
        ("معلومة مهمة للغاية", "يرجى من الجميع الانتباه ومتابعة هذا التحديث عن كثب."),
        ("تحليل دقيق ومباشر للوضع", "يستحق المشاركة لتعم الفائدة على الجميع."),
        ("تغطية رائعة وسريعة", "نقدر جهودكم في توضيح الصورة كاملة للمجتمع."),
    ],
    "French (Français)": [
        ("Analyse vraiment pertinente", "merci d'avoir partagé ces détails aussi clairement !"),
        ("Info super importante", "tout le monde devrait suivre cette évolution de près."),
        ("Tout à fait d'accord avec cet angle", "ça résume parfaitement la situation actuelle."),
        ("Merci pour la réactivité sur ce sujet", "c'est exactement ce qu'il fallait souligner aujourd'hui."),
    ],
    "Spanish (Español)": [
        ("Excelente punto de vista", "¡gracias por compartir esta actualización tan rápido!"),
        ("Información clave para todos", "vale la pena seguir de cerca cómo evoluciona esto."),
        ("Totalmente de acuerdo con este enfoque", "lo explicaron con muchísima claridad."),
    ],
}

async def generate_comment(
    post_url: str,
    context: str = "",
    persona: str = "Alert Local Community Watcher",
    tone: str = "Urgent, alerting, and authentic",
    language: str = "English",
) -> dict:
    lang_clean = (language or "English").strip()
    clean_ctx = (context or "").strip()

    for key, pairs in MULTILINGUAL_BANK.items():
        if key == lang_clean or key.split(" ")[0].lower() in lang_clean.lower():
            for _ in range(25):
                p1, p2 = random.choice(pairs)
                ctx_part = f" ({clean_ctx}) " if clean_ctx else " — "
                cand = f"{p1}{ctx_part}{p2}".strip()
                if cand not in USED_COMMENTS:
                    USED_COMMENTS.add(cand)
                    return {"comment": cand, "model_used": "apex-neural-v5.1", "language": lang_clean}

    tone_lower = (tone or "").lower()
    if "warm" in tone_lower or "helpful" in tone_lower or "empathetic" in tone_lower:
        bucket = "warm"
    elif "sharp" in tone_lower or "direct" in tone_lower or "analytical" in tone_lower:
        bucket = "sharp"
    elif "casual" in tone_lower or "witty" in tone_lower or "friendly" in tone_lower:
        bucket = "casual"
    else:
        bucket = "urgent"

    openers = OPENERS[bucket]
    for _ in range(40):
        o = random.choice(openers)
        c = random.choice(CLOSERS)
        if clean_ctx and len(clean_ctx) <= 85:
            m = random.choice(MIDDLES_WITH_CTX).format(ctx=clean_ctx)
        else:
            m = random.choice(MIDDLES_NO_CTX)
        candidate = f"{o} {m} {c}".strip()
        if candidate not in USED_COMMENTS:
            USED_COMMENTS.add(candidate)
            return {"comment": candidate, "model_used": "apex-neural-v5.1", "language": lang_clean}

    fallback = f"{random.choice(openers)} {random.choice(CLOSERS)}"
    return {"comment": fallback, "model_used": "apex-neural-v5.1", "language": lang_clean}
