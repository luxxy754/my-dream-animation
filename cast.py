"""cast.json padhta hai (kaun kaun se characters hain, unki shakhsiyat, awaaz) aur check karta hai ke unki image folder mein hai ya nahi."""
import json
import os

HERE = os.path.dirname(os.path.abspath(__file__))
EXTS = (".png", ".webp", ".jpg", ".jpeg")


def char_folder(name):
    return os.path.join(HERE, "characters", name.lower())


def poses_on_disk(name):
    folder = char_folder(name)
    if not os.path.isdir(folder):
        return {}
    return {os.path.splitext(f)[0].lower(): os.path.join(folder, f) for f in sorted(os.listdir(folder))
            if f.lower().endswith(EXTS)}


def load_cast(path=None):
    path = path or os.environ.get("CAST_FILE") or os.path.join(HERE, "cast.json")
    with open(path, encoding="utf-8") as f:
        data = json.load(f)
    chars = []
    for d in data["characters"]:
        d = dict(d)
        d.setdefault("gender", "male")
        d.setdefault("height_cm", 173)
        d.setdefault("voice", "kokoro:am_adam" if d["gender"] == "male" else "kokoro:af_heart")
        d.setdefault("pitch", 0)
        d.setdefault("color", "#FFD23F")
        d["poses"] = poses_on_disk(d["name"])
        d["has_art"] = bool(d["poses"])
        chars.append(d)
    narrator = data.get("narrator") or chars[0]["name"]
    return narrator, chars


def cast_bible(chars):
    out = []
    for c in chars:
        out.append(f"- {c['name']} ({c.get('role', 'character')}; {c.get('age', '?')} yrs; {c['gender']}): "
                   f"{c.get('personality', '')} Speech style: {c.get('speech_style', 'natural')}. "
                   f"{'' if c['has_art'] else '[NO ARTWORK YET: can only speak off-screen]'}")
    return "\n".join(out)
