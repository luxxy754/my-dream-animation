"""Gemini se funny storytelling script banata hai (RG Bucket List jaisi): cast.json ke characters, fixed locations, har line ki animation directions.

MODE (env):  both  -> script_long.json (~8-9 min, landscape) + script_short.json (long ko promote karne wala teaser Short)
             long  -> sirf script_long.json     short -> sirf script_short.json (standalone mini story)
STORY_LANG (env): en (default) | hi (Hindi, Devanagari) | ur (Urdu)
Flow (long): 1) plan (idea/title/chapters)  2) har chapter alag call (lambai + quality)  3) saaf-safai (cleaning) taake renderer kabhi na atke.
"""
import datetime
import json
import os
import random
import re
import sys
import time

import requests

from cast import cast_bible, load_cast
from vocab import ACTIONS, EMOTIONS, FX, LANGS, LOCATIONS, MOODS, PROPS, SFX
import world

API_KEY = os.environ.get("GEMINI_API_KEY")
MODE = os.environ.get("MODE", "both").strip().lower()
LANG = os.environ.get("STORY_LANG", "en").strip().lower()
MODELS = [m for m in [os.environ.get("GEMINI_MODEL"), "gemini-2.5-flash", "gemini-flash-latest", "gemini-2.5-flash-lite"] if m]
HISTORY = "history.json"
LONG_TARGET_WORDS = int(os.environ.get("LONG_TARGET_WORDS", "1300"))  # ~8-9 min
N_CHAPTERS = max(6, min(10, round(LONG_TARGET_WORDS / 170)))
LANG_NAME, LANG_SCRIPT = LANGS.get(LANG, LANGS["en"])[:2]

THEMES = [
    "an embarrassing school or classroom incident that spiralled out of control",
    "a bet or dare between friends that went hilariously wrong",
    "a 'bucket list' challenge the friends tried (something silly and ambitious) and how it fell apart",
    "a coding / tech disaster (wrong file deleted, phone vs. password, wifi gone before a deadline) with funny consequences",
    "a skateboarding plan or stunt that went wrong in the funniest possible way",
    "a misunderstanding (wrong text sent, wrong person, wrong order) that kept growing",
    "trying to hide a small mistake from parents or a teacher, with escalating lies",
    "a food adventure gone wrong (street food, cooking experiment, pizza order mix-up)",
    "a lazy day plan that accidentally turned into a huge adventure",
    "a prank that backfired on the pranker",
    "a school exam or project panic night and the crazy last-minute solution",
    "a lost-and-found chase: someone loses something important and the search gets absurd",
    "an attempt to earn quick money or start a business that went comically wrong",
    "a haunted-house / night walk that turned out to have a silly explanation",
    "the day everything that could go wrong in a tiny errand did",
]

STYLE = """STORYTELLING STYLE (funny animated storytime, like the YouTube channel RG Bucket List - this decides whether people keep watching):
- Shazy tells a funny, relatable, true-feeling story from his life with his friends; the characters act it out on screen with real back-and-forth dialogue.
- Comedy formula: relatable setup -> silly plan or dare -> escalating chaos (every beat funnier/worse than the last) -> unexpected twist punchline -> quick button joke. Use callbacks to earlier jokes, rule of three, exaggeration, deadpan reactions, interruptions.
- Mix short punchy dialogue lines with Shazy talking to the viewer ("guys", "so basically"). NEVER a lecture or list of facts.
- Family-friendly: no swearing/slurs, no violence against people, no attacking real people or brands, nothing sexual.
- Each line max 22 words, plain spoken text only (no emojis, hashtags, stage directions, speaker names inside the text).
- Use sfx/fx/prop on punchlines and reactions (bonk, boing, fail, crash, exclaim, question, boom...). Show a prop only when the line talks about that object.
- Vary emotion and action; never the same action twice in a row (use idle most of the time). Use listeners/listeners_action so the others react when someone speaks (laugh, shocked, confused...).
- Write ONLY in {lang} ({script} script){extra}.""".format(
    lang=LANG_NAME, script=LANG_SCRIPT,
    extra=(". Write numbers as spoken words (\"seventeen\")" if LANG == "en" else ". Casual spoken style; character names stay in the same spelling as in the cast list"))

CTA = {"en": "Want the full story? Watch the full video on my channel. It's linked in the description.",
       "hi": "पूरी कहानी चाहिए? मेरे चैनल पर पूरा वीडियो देखो, लिंक डिस्क्रिप्शन में है।",
       "ur": "پوری کہانی چاہیے؟ میرے چینل پر پوری ویڈیو دیکھو، لنک ڈسکرپشن میں ہے۔"}


def S(t, **kw):
    return {"type": t, **kw}


def enum(vals):
    return S("STRING", enum=list(vals))


def scenes_schema(names):
    line = S("OBJECT", properties={
        "speaker": enum(list(names) + ["Voice"]), "text": S("STRING"), "emotion": enum(EMOTIONS), "action": enum(ACTIONS),
        "fx": enum(FX), "sfx": enum(SFX), "prop": enum(["none"] + PROPS), "listeners": enum(EMOTIONS),
        "listeners_action": enum(ACTIONS)},
        required=["speaker", "text", "emotion", "action", "fx", "sfx", "prop", "listeners", "listeners_action"])
    scene = S("OBJECT", properties={"location": enum(LOCATIONS), "on": S("ARRAY", items=enum(names)),
                                    "lines": S("ARRAY", items=line)}, required=["location", "on", "lines"])
    return S("ARRAY", items=scene)


# ------------------------------------------------------------------ Gemini
def load_history():
    try:
        with open(HISTORY, encoding="utf-8") as f:
            return json.load(f)
    except Exception:  # noqa: BLE001
        return []


def ask_gemini(prompt, sch=None, max_out=8192):
    last = None
    for model in MODELS:
        url = f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent"
        cfg = {"temperature": 1.0 if sch else 0.8, "maxOutputTokens": max_out}
        if sch:
            cfg["responseMimeType"] = "application/json"
            cfg["responseSchema"] = sch
        if "2.5-flash" in model:
            cfg["thinkingConfig"] = {"thinkingBudget": 0}
        body = {"contents": [{"parts": [{"text": prompt}]}], "generationConfig": cfg}
        for _ in range(2):
            try:
                r = requests.post(url, headers={"x-goog-api-key": API_KEY}, json=body, timeout=180)
                if r.status_code == 200:
                    parts = r.json()["candidates"][0]["content"]["parts"]
                    return "".join(p.get("text", "") for p in parts)
                last = f"{model}: HTTP {r.status_code} {r.text[:200]}"
                if r.status_code == 429:
                    time.sleep(20)
            except Exception as e:  # noqa: BLE001
                last = f"{model}: {e}"
            time.sleep(4)
    raise RuntimeError(last)


def parse(text):
    return json.loads(re.sub(r"^```(?:json)?|```$", "", text.strip(), flags=re.M).strip())


def with_retries(label, fn, tries=3):
    for attempt in range(tries):
        try:
            return fn()
        except Exception as e:  # noqa: BLE001
            print(f"{label} attempt {attempt + 1} failed: {str(e)[:200]}")
            time.sleep(3)
    return None


# ------------------------------------------------------------------ cleaning
AUTO_FX = {"shocked": "exclaim", "confused": "question", "scared": "sweat", "angry": "anger"}


def pick(v, allowed, default):
    return v if v in allowed else default


def clean_scenes(scenes, names, narrator):
    out, last_fx, last_act = [], None, None
    for sc in scenes or []:
        loc = pick(sc.get("location"), LOCATIONS, "room")
        on = []
        for n in sc.get("on", []):
            if n in names and n not in on:
                on.append(n)
        lines = []
        for ln in sc.get("lines", []):
            txt = re.sub(r"\s+", " ", str(ln.get("text", ""))).strip()
            if not txt:
                continue
            spk = ln.get("speaker") if (ln.get("speaker") in names or ln.get("speaker") == "Voice") else narrator
            emo = pick(ln.get("emotion"), EMOTIONS, "neutral")
            act = pick(ln.get("action"), ACTIONS, "idle")
            if act == last_act and act != "idle":
                act = "idle"
            fx = pick(ln.get("fx"), FX, "none")
            if fx == "none" and emo in AUTO_FX and last_fx != AUTO_FX[emo]:
                fx = AUTO_FX[emo]
            last_fx, last_act = fx, act
            lines.append(dict(speaker=spk, text=txt, emotion=emo, action=act, fx=fx, sfx=pick(ln.get("sfx"), SFX, "none"),
                              prop=pick(ln.get("prop"), PROPS, "none"), listeners=pick(ln.get("listeners"), EMOTIONS, "neutral"),
                              listeners_action=pick(ln.get("listeners_action"), ACTIONS, "idle")))
        if not lines:
            continue
        for ln in lines:
            if ln["speaker"] != "Voice" and ln["speaker"] not in on:
                on.append(ln["speaker"])
        if not on:
            on = [narrator]
        spk_set = {ln["speaker"] for ln in lines}
        while len(on) > 4:  # 4 se zyada ek saath nahi
            drop = next((n for n in reversed(on) if n not in spk_set), on[-1])
            on.remove(drop)
        out.append(dict(location=loc, on=on, lines=lines))
    return out


def words(scenes):
    return sum(len(ln["text"].split()) for sc in scenes for ln in sc["lines"])


# ------------------------------------------------------------------ prompts
def loc_text():
    return "\n".join(f"- {k}: {v}" for k, v in world.LOCATIONS.items())


def plan_long(chars, narrator, theme, recent):
    bible = cast_bible(chars)
    prompt = f"""You are the head writer of a funny 2D animated YouTube series.
CAST (use ONLY these names; "Voice" = an unnamed off-screen voice such as a teacher, phone call or announcer):
{bible}
LOCATIONS you may use: 
{loc_text()}

Pick ONE fresh, specific story idea in this theme: {theme}.
Do NOT repeat or resemble these earlier topics: {recent}.
Random seed: {random.randint(1, 10**7)}.
Return JSON with: topic (3-8 words, English), logline (one sentence including the twist, English), title (max 70 chars, funny and curious, no lies, in {LANG_NAME}), thumb_text (2-4 short words, ALL CAPS, in {LANG_NAME}), description (2-3 sentences + 3 hashtags, in {LANG_NAME}), tags (6-10 English tags), music_mood (one of {', '.join(MOODS)}), cast_used (names), chapters: exactly {N_CHAPTERS} objects each with summary (2 sentences: what happens and how it escalates; English) and location (from the list).
Chapter 1 = {narrator} introduces himself, the friends involved (by name) and hooks the story. Last chapter = the twist punchline then {narrator}'s short outro. Every chapter in between escalates the chaos."""
    sch = S("OBJECT", properties={
        "topic": S("STRING"), "logline": S("STRING"), "title": S("STRING"), "thumb_text": S("STRING"), "description": S("STRING"),
        "tags": S("ARRAY", items=S("STRING")), "music_mood": enum(MOODS), "cast_used": S("ARRAY", items=S("STRING")),
        "chapters": S("ARRAY", items=S("OBJECT", properties={"summary": S("STRING"), "location": enum(LOCATIONS)},
                                       required=["summary", "location"]))},
        required=["topic", "logline", "title", "thumb_text", "description", "tags", "music_mood", "chapters"])
    return parse(ask_gemini(prompt, sch, 4096))


def write_chapter(plan, i, chars, narrator, prev_lines):
    names = [c["name"] for c in chars]
    n = len(plan["chapters"])
    per = max(80, LONG_TARGET_WORDS // n)
    if i == 0:
        special = (f"This is the OPENING: first scene in location room with only {narrator}. He greets the viewers, says who he is and "
                   "introduces the friends who appear in this story by name (one funny line about each), then hooks the story with a teaser.")
    elif i == n - 1:
        special = (f"This is the FINAL chapter: the twist punchline lands, one last button joke, then {narrator} signs off to the viewers "
                   "(thank them for watching, ask them to like and subscribe in a funny way, say bye).")
    else:
        special = "End the chapter with a small hook or a worse problem so viewers keep watching."
    chapters = "\n".join(f"{k + 1}. {c['summary']}" for k, c in enumerate(plan["chapters"]))
    prompt = f"""{STYLE}

CAST:
{cast_bible(chars)}
LOCATIONS:
{loc_text()}

STORY: {plan['title']} - {plan['logline']}
ALL CHAPTERS:
{chapters}
{('LAST LINES SO FAR: ' + ' | '.join(prev_lines[-6:])) if prev_lines else ''}

Write chapter {i + 1} of {n}: {plan['chapters'][i]['summary']}
{special}
About {per} words in total, roughly {max(8, per // 11)} dialogue lines, spread over 1 to 3 scenes. Each scene: location from the list, "on" = the characters visible (1-4, must include everyone speaking in that scene except Voice), then its lines in order. Keep the same location unless the story really moves.
Return the JSON array of scenes."""
    return parse(ask_gemini(prompt, scenes_schema(names), 6000))


def common(plan):
    return dict(topic=plan.get("topic", "story"), title=plan.get("title", "My story"), thumb_text=plan.get("thumb_text", ""),
                description=plan.get("description", ""), tags=plan.get("tags") or ["funny", "animation"],
                music_mood=pick(plan.get("music_mood"), MOODS, "quirky"), lang=LANG)


def gen_long(chars, narrator, theme, recent):
    plan = with_retries("plan", lambda: plan_long(chars, narrator, theme, recent))
    if not plan or len(plan.get("chapters", [])) < 3:
        return None
    names = [c["name"] for c in chars]
    scenes, prev = [], []
    for i in range(len(plan["chapters"])):
        sc = with_retries(f"chapter {i + 1}", lambda: clean_scenes(write_chapter(plan, i, chars, narrator, prev), names, narrator))
        if not sc:
            print(f"chapter {i + 1} skip")
            continue
        scenes += sc
        prev = [ln["text"] for s in sc for ln in s["lines"]]
        print(f"chapter {i + 1}/{len(plan['chapters'])}: {words(sc)} words")
    if words(scenes) < LONG_TARGET_WORDS * 0.5:
        return None
    d = common(plan)
    d["logline"] = plan.get("logline", "")
    d["scenes"] = scenes
    return d


def gen_short(chars, narrator, theme, recent, long=None):
    names = [c["name"] for c in chars]
    if long:
        task = (f"Write a 40-50 second TEASER for the long video '{long['title']}' ({long.get('logline', '')}). {narrator} hooks the viewer in the room, "
                "acts out the funniest setup moment with the friends (cut it off right before the twist), then says the call to action: "
                f"\"{CTA[LANG]}\" (translate faithfully if the language differs)." )
    else:
        task = (f"Write a complete 40-50 second funny mini story (theme: {theme}). Do NOT repeat earlier topics: {recent}. "
                f"Start with a hook line by {narrator}, escalate quickly, end with a punchline that loops back to the opening line.")
    prompt = f"""{STYLE}

CAST:
{cast_bible(chars)}
LOCATIONS:
{loc_text()}

{task}
About 110-130 words in total, 10-14 lines, 1 or 2 scenes. Return JSON with: topic (3-8 words English), title (max 80 chars in {LANG_NAME}), description (1-2 sentences + 3 hashtags), tags (6 English tags), music_mood, scenes."""
    sch = S("OBJECT", properties={"topic": S("STRING"), "title": S("STRING"), "description": S("STRING"),
                                  "tags": S("ARRAY", items=S("STRING")), "music_mood": enum(MOODS), "scenes": scenes_schema(names)},
            required=["topic", "title", "description", "tags", "music_mood", "scenes"])
    d = with_retries("short", lambda: parse(ask_gemini(prompt, sch, 4096)))
    if not d:
        return None
    d["scenes"] = clean_scenes(d.get("scenes"), names, narrator)
    if not d["scenes"]:
        return None
    out = common(d)
    out["scenes"] = d["scenes"]
    if long:
        out["topic"] = long["topic"]
    return out


def fallback(narrator):
    L = lambda t, e="neutral", a="idle", fx="none", sfx="none", prop="none": dict(speaker=narrator, text=t, emotion=e, action=a, fx=fx, sfx=sfx, prop=prop, listeners="neutral", listeners_action="idle")
    return dict(topic="Shazy test story", title="Shazy and the Wifi Disaster #Shorts", thumb_text="WIFI GONE", description="Shazy vs the wifi. #Shorts #funny #animation",
                tags=["funny", "animation", "shorts"], music_mood="quirky", lang="en", scenes=[dict(location="room", on=[narrator], lines=[
                    L("Guys, I have a coding deadline in ten minutes. And my wifi just died.", "scared", "tremble", "sweat", "dun", "laptop"),
                    L("So I did what any genius does. I stood on the desk and held the router above my head.", "excited", "jump", "none", "boing"),
                    L("Plot twist. The router was never plugged in.", "shocked", "idle", "exclaim", "scratch"),
                    L("Ten minutes later I plugged it in. Wifi back. Deadline? Gone.", "sad", "slump", "none", "fail", "clock"),
                    L("Lesson learned. Always check the plug first. Follow for more disasters.", "smug", "point", "sparkle", "tada")])])


def save_history(hist, d, mode):
    hist.append({"topic": d["topic"], "title": d["title"], "date": datetime.date.today().isoformat(), "mode": mode})
    with open(HISTORY, "w", encoding="utf-8") as f:
        json.dump(hist[-250:], f, ensure_ascii=False, indent=1)


def dump(d, path):
    with open(path, "w", encoding="utf-8") as f:
        json.dump(d, f, ensure_ascii=False, indent=2)


def main():
    if MODE not in ("both", "long", "short"):
        sys.exit(f"MODE '{MODE}' galat hai (both / long / short)")
    if LANG not in LANGS:
        sys.exit(f"STORY_LANG '{LANG}' galat hai ({' / '.join(LANGS)})")
    narrator, chars = load_cast()
    for p in ("script_long.json", "script_short.json"):
        if os.path.exists(p):
            os.remove(p)
    hist = load_history()
    recent = [h.get("topic", "") for h in hist[-60:]]
    theme = random.choice(THEMES)
    print("Theme:", theme)
    long = None
    if MODE in ("both", "long"):
        if not API_KEY:
            sys.exit("GEMINI_API_KEY missing - long video ke liye zaroori hai")
        long = gen_long(chars, narrator, theme, recent)
        if not long:
            sys.exit("Gemini long script fail - kuch post nahi kiya (dobara run karein)")
        dump(long, "script_long.json")
        print("LONG :", long["title"], f"({words(long['scenes'])} words)")
    short = None
    if MODE == "both":
        short = gen_short(chars, narrator, theme, recent, long=long)
        if short:
            dump(short, "script_short.json")
            print("SHORT:", short["title"])
        else:
            print("WARNING: teaser Short script nahi bana - sirf long video post hogi")
    elif MODE == "short":
        short = gen_short(chars, narrator, theme, recent) if API_KEY else None
        if not short:
            print("Gemini unavailable -> fallback script")
            short = fallback(narrator)
        dump(short, "script_short.json")
        print("SHORT:", short["title"])
    main_script = long or short
    save_history(hist, main_script, MODE)
    print("Topic:", main_script["topic"])


if __name__ == "__main__":
    main()
