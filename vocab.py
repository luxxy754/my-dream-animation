"""Script (Gemini) aur renderer ke darmiyan common lafz. Gemini sirf inhi mein se chun sakta hai."""
import world

LOCATIONS = list(world.LOCATIONS)
PROPS = list(world.PROPS)
FX = ["none"] + list(world.FX)
EMOTIONS = ["neutral", "happy", "sad", "angry", "shocked", "scared", "excited", "confused", "smug", "laugh"]
ACTIONS = ["idle", "jump", "hop", "walk", "run", "shake", "spin", "fall", "dance", "point", "nod", "dizzy", "float",
           "tremble", "slump"]
SFX = ["none", "boing", "bonk", "fail", "ding", "whoosh", "thud", "pop", "scratch", "dun", "tada", "crash", "slide"]
MOODS = ["quirky", "mysterious", "epic", "chill"]

LANGS = {  # code: (naam, script, edge male, edge female, caption font)
    "en": ("English", "Latin", "en-US-AndrewNeural", "en-US-AriaNeural", "DejaVu Sans"),
    "hi": ("Hindi", "Devanagari", "hi-IN-MadhurNeural", "hi-IN-SwaraNeural", "Noto Sans Devanagari"),
    "ur": ("Urdu", "Urdu (Arabic script)", "ur-PK-AsadNeural", "ur-PK-UzmaNeural", "Noto Naskh Arabic"),
}
