"""script_*.json -> video. Long: 1920x1080 (16:9). Short: 1080x1920 (9:16, camera bolne wale ko follow karta hai).

Poora visual code se: characters = characters/ folder ki PNG images (puppet.py), background/props/effects = world.py (fixed).
Awaaz: har character ki alag (voice.py). Music + sound effects: music.py (code se, copyright-free).
MODE (env): both | long | short.  Output: output_short.mp4, output_long.mp4, thumbnail.jpg (long ke liye)
"""
import json
import os
import subprocess
import sys
import tempfile
import time
import zlib

import cv2
import numpy as np
from PIL import Image, ImageDraw, ImageFont

import music
import voice
from cast import load_cast
from puppet import Char, Stage, OUTS
from vocab import LANGS

FPS = 30
PROFILES = {
    "short": dict(gap=0.12, speed=float(os.environ.get("SHORT_SPEED", "1.2")),
                  cap=dict(size=84, margin_v=360, margin_h=60, outline=9, words=3, chars=17)),
    "long": dict(gap=0.30, speed=float(os.environ.get("LONG_SPEED", "1.08")),
                 cap=dict(size=56, margin_v=44, margin_h=160, outline=6, words=7, chars=38)),
}
HOLD = {"fail": 0.7, "scratch": 0.5, "dun": 0.6, "crash": 0.5, "tada": 0.5, "bonk": 0.3, "boing": 0.3, "thud": 0.3}


def duration(path):
    out = subprocess.check_output(["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0", path], text=True)
    return float(out.strip())


# ------------------------------------------------------------------ captions
def ass_time(t):
    cs = int(round(t * 100))
    return f"{cs // 360000}:{cs // 6000 % 60:02d}:{cs // 100 % 60:02d}.{cs % 100:02d}"


def ass_col(hexcol):
    h = hexcol.lstrip("#")
    return f"&H00{h[4:6]}{h[2:4]}{h[0:2]}&"


def chunk_words(words, max_words, max_chars):
    chunks, cur = [], []
    for w in words:
        if cur and (len(cur) >= max_words or len(" ".join(cur + [w])) > max_chars):
            chunks.append(cur)
            cur = []
        cur.append(w)
    if cur:
        chunks.append(cur)
    return chunks


def build_ass(kind, lang, lines, colors, path):
    c = PROFILES[kind]["cap"]
    ow, oh = OUTS[kind]
    font = LANGS[lang][4]
    head = (f"[Script Info]\nScriptType: v4.00+\nPlayResX: {ow}\nPlayResY: {oh}\nWrapStyle: 0\n\n"
            "[V4+ Styles]\nFormat: Name,Fontname,Fontsize,PrimaryColour,SecondaryColour,OutlineColour,BackColour,Bold,Italic,"
            "Underline,StrikeOut,ScaleX,ScaleY,Spacing,Angle,BorderStyle,Outline,Shadow,Alignment,MarginL,MarginR,MarginV,Encoding\n"
            f"Style: Cap,{font},{c['size']},&H00FFFFFF,&H00FFFFFF,&H00000000,&H80000000,1,0,0,0,100,100,0,0,1,{c['outline']},2,2,"
            f"{c['margin_h']},{c['margin_h']},{c['margin_v']},1\n\n[Events]\nFormat: Layer,Start,End,Style,Name,MarginL,MarginR,MarginV,Effect,Text\n")
    out = []
    for ln in lines:
        words = [w for w in ln["text"].replace("\n", " ").split() if w]
        if not words:
            continue
        hi = ass_col(colors.get(ln["speaker"], "#FFD23F"))
        weights = [len(w) + (4 if w[-1] in ".,!?;:।۔" else 0) for w in words]
        total, t, starts = sum(weights) or 1, ln["start"], []
        for wt in weights:
            starts.append(t)
            t += ln["speech"] * wt / total
        ends = starts[1:] + [ln["start"] + ln["speech"]]
        idx = 0
        for chunk in chunk_words(words, c["words"], c["chars"]):
            for j, _ in enumerate(chunk):
                g = idx + j
                shown = " ".join(("{\\c" + hi + "}" + w.upper() + "{\\c&HFFFFFF&}") if k == j else w.upper() for k, w in enumerate(chunk))
                out.append(f"Dialogue: 0,{ass_time(starts[g])},{ass_time(ends[g])},Cap,,0,0,0,,{shown}")
            idx += len(chunk)
    with open(path, "w", encoding="utf-8") as f:
        f.write(head + "\n".join(out) + "\n")


def make_thumbnail(frame_bgr, text, out="thumbnail.jpg"):
    img = Image.fromarray(cv2.cvtColor(frame_bgr, cv2.COLOR_BGR2RGB)).resize((1280, 720), Image.LANCZOS)
    d = ImageDraw.Draw(img)
    fp = "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"
    size, font = 120, None
    while size > 60:
        try:
            font = ImageFont.truetype(fp, size)
        except OSError:
            return
        words, lines, cur = text.split(), [], ""
        for w in words:
            trial = (cur + " " + w).strip()
            if d.textlength(trial, font=font) <= 1180 or not cur:
                cur = trial
            else:
                lines.append(cur)
                cur = w
        lines.append(cur)
        if len(lines) <= 2 and max(d.textlength(l, font=font) for l in lines) <= 1180:
            break
        size -= 8
    y = 24
    for line in lines:
        w = d.textlength(line, font=font)
        d.text(((1280 - w) / 2, y), line, font=font, fill=(255, 235, 0), stroke_width=max(8, size // 12), stroke_fill=(0, 0, 0))
        y += int(size * 1.15)
    img.save(out, quality=90)


# ------------------------------------------------------------------ audio helpers
def mouth_envelope(x, n_frames):
    hop = music.SR / FPS
    env = np.zeros(n_frames, np.float32)
    for f in range(n_frames):
        seg = x[int(f * hop):int((f + 1) * hop)]
        env[f] = float(np.sqrt(np.mean(seg ** 2))) if len(seg) else 0.0
    ref = float(np.percentile(env[env > 0.002], 85)) if (env > 0.002).any() else 1.0
    m = np.clip(env / max(ref, 1e-4), 0, 1.0) ** 0.8
    return np.convolve(m, [0.25, 0.5, 0.25], mode="same")


def sfx_for_line(ln, t0, scene_start, cut):
    ev = []
    if cut and abs(t0 - scene_start) < 1e-6 and t0 > 0:
        ev.append((t0, "whoosh", 0.7))
    if ln["sfx"] != "none":
        ev.append((t0 + 0.05, ln["sfx"], 0.9))
    if ln["action"] == "jump" and ln["sfx"] == "none":
        ev.append((t0 + 0.05, "boing", 0.6))
    if ln["action"] == "fall":
        ev.append((t0 + 0.3, "thud", 0.9))
    if ln["prop"] != "none":
        ev.append((t0 + 0.12, "pop", 0.8))
    if ln["fx"] == "boom":
        ev.append((t0 + 0.1, "crash", 0.8))
    return ev


# ------------------------------------------------------------------ timeline
def build_timeline(data, art, narrator, gap):
    prev_loc, prev_on, scenes = None, set(), []
    for sc in data["scenes"]:
        on = [n for n in sc["on"] if n in art]
        if not on:
            on = [narrator if narrator in art else sorted(art)[0]]
        cut = sc["location"] != prev_loc
        enter = {n: ("pop" if cut else "slide") for n in on if cut or n not in prev_on}
        lines = []
        for ln in sc["lines"]:
            ln = dict(ln)
            ln["states"] = {n: ((ln["emotion"], ln["action"]) if n == ln["speaker"] else (ln["listeners"], ln["listeners_action"])) for n in on}
            lines.append(ln)
        scenes.append(dict(loc=sc["location"], on=on, cut=cut, enter=enter, lines=lines))
        prev_loc, prev_on = sc["location"], set(on)
    return scenes


# ------------------------------------------------------------------ main builder
def create_video(kind, data, output_path):
    p = PROFILES[kind]
    lang = data.get("lang", "en")
    narrator, cast = load_cast()
    cdict = {c["name"]: c for c in cast}
    art = {c["name"] for c in cast if c["has_art"]}
    if not art:
        sys.exit("ERROR: characters/ folder mein kisi character ki image nahi (characters/README.md dekhein)")
    stage = Stage(kind, [Char(c) for c in cast if c["has_art"]])
    scenes = build_timeline(data, art, narrator, p["gap"])
    tmp = tempfile.mkdtemp()
    seed = zlib.crc32(data.get("topic", "x").encode()) % 100000
    teaser = bool(data.get("teaser"))
    t_start = time.time()
    flat = [(si, ln) for si, sc in enumerate(scenes) for ln in sc["lines"]]

    # 1) awaaz (har line ki, uske speaker ki awaaz mein)
    wavs = []
    for k, (si, ln) in enumerate(flat):
        ch = cdict.get(ln["speaker"]) or dict(gender="male", voice="kokoro:am_michael", pitch=-2, color="#CCCCCC")
        print(f"[{kind}] voice {k + 1}/{len(flat)} {ln['speaker']}: {ln['text']}", flush=True)
        wp = os.path.join(tmp, f"a{k}.wav")
        voice.synth(ln["text"], wp, voice.resolve(ch, lang), float(ch.get("pitch", 0)), p["speed"], lang)
        x = music.read_wav(wp)
        wavs.append(x)
        ln["speech"] = len(x) / music.SR

    # 2) timeline
    t0 = 0.0
    for k, (si, ln) in enumerate(flat):
        last = k == len(flat) - 1
        pad = (0.5 if teaser else 0.05) if (last and kind == "short") else (0.9 if last else p["gap"] + HOLD.get(ln["sfx"], 0.0))
        ln["start"], ln["dur"] = t0, ln["speech"] + pad
        t0 += ln["dur"]
    total = t0
    for sc in scenes:
        sc["start"], sc["end"] = sc["lines"][0]["start"], sc["lines"][-1]["start"] + sc["lines"][-1]["dur"]
    n_frames = int(round(total * FPS))

    # 3) audio: awaaz + music + sfx
    voice_track = np.zeros(int(total * music.SR) + music.SR, np.float32)
    sfx = []
    for k, (si, ln) in enumerate(flat):
        a = int(ln["start"] * music.SR)
        voice_track[a:a + len(wavs[k])] += wavs[k]
        sfx += sfx_for_line(ln, ln["start"], scenes[si]["start"], scenes[si]["cut"])
    mood = data.get("music_mood", "quirky")
    mixed, credit = music.mix(voice_track[: int(total * music.SR)], total, mood, seed, sfx)
    audio_path = os.path.join(tmp, "mix.wav")
    music.write_wav(audio_path, mixed)
    print(f"[{kind}] audio ready ({total:.1f}s, mood={mood})", flush=True)

    # 4) captions
    colors = {c["name"]: c["color"] for c in cast}
    build_ass(kind, lang, [ln for _, ln in flat], colors, os.path.join(tmp, "cap.ass"))

    # 5) frames -> ffmpeg (pipe)
    OW, OH = OUTS[kind]
    abs_out = os.path.abspath(output_path)
    cmd = ["ffmpeg", "-y", "-loglevel", "error", "-f", "rawvideo", "-pix_fmt", "bgr24", "-s", f"{OW}x{OH}", "-r", str(FPS), "-i", "-",
           "-i", audio_path, "-vf", "subtitles=cap.ass", "-c:v", "libx264", "-preset", "veryfast", "-crf", "20" if kind == "short" else "22",
           "-pix_fmt", "yuv420p", "-c:a", "aac", "-b:a", "192k", "-shortest", "-movflags", "+faststart", abs_out]
    proc = subprocess.Popen(cmd, stdin=subprocess.PIPE, cwd=tmp)
    dbg = os.environ.get("DEBUG_DIR")
    if dbg:
        os.makedirs(dbg, exist_ok=True)
    si_cur, li = -1, 0
    envs = {}
    thumb_done = kind != "long"
    try:
        for f in range(n_frames):
            tg = f / FPS
            si = si_cur
            while si + 1 < len(scenes) and tg >= scenes[si + 1]["start"] - 1e-9:
                si += 1
            si = max(si, 0)
            sc = scenes[si]
            if si != si_cur:
                si_cur, li = si, 0
                stage.begin_scene(sc)
            while li + 1 < len(sc["lines"]) and tg >= sc["lines"][li + 1]["start"] - 1e-9:
                li += 1
            ln = sc["lines"][li]
            key = id(ln)
            if key not in envs:
                envs[key] = mouth_envelope(wavs[flat.index(next(x for x in flat if x[1] is ln))], int(ln["dur"] * FPS) + 3)
            tl = tg - ln["start"]
            env = envs[key]
            speaking = tl < ln["speech"]
            mouth = float(env[min(int(tl * FPS), len(env) - 1)]) if speaking else 0.0
            sprog = (tg - sc["start"]) / max(sc["end"] - sc["start"], 1e-3)
            punch = 0.05 * max(0.0, 1 - tl / 0.35) if (ln["emotion"] == "shocked" or ln["fx"] == "boom") else 0.0
            frame = stage.frame(sc, ln, tg - sc["start"], tl, tg, mouth, speaking, sprog, punch)
            if not thumb_done and si == 0 and tl >= 1.0:
                make_thumbnail(frame, data.get("thumb_text") or data["topic"].upper())
                thumb_done = True
            if dbg and f % 60 == 30:
                cv2.imwrite(os.path.join(dbg, f"{kind}_{f:05d}.jpg"), frame)
            try:
                proc.stdin.write(frame.tobytes())
            except BrokenPipeError:
                break
            if f % 900 == 0:
                print(f"[{kind}] frame {f}/{n_frames} ({time.time() - t_start:.0f}s elapsed)", flush=True)
        proc.stdin.close()
    finally:
        rc = proc.wait()
    if rc != 0:
        sys.exit(f"ERROR: ffmpeg fail hua (code {rc})")
    out_total = duration(abs_out)
    print(f"Video created: {output_path} ({out_total:.1f}s, {len(flat)} lines, {time.time() - t_start:.0f}s lagay)")
    if kind == "short" and out_total > 59:
        print("WARNING: 59s se lamba hai; Short shayad Short na rahe")
    return out_total, credit


def main():
    mode = os.environ.get("MODE", "both").strip().lower()
    jobs = []
    if mode in ("both", "long"):
        jobs.append(("long", "script_long.json", "output_long.mp4"))
    if mode in ("both", "short"):
        jobs.append(("short", "script_short.json", "output_short.mp4"))
    for kind, sj, out in jobs:
        if not os.path.exists(sj):
            print(f"{sj} nahi mila, {kind} skip")
            continue
        with open(sj, encoding="utf-8") as f:
            data = json.load(f)
        if kind == "short" and mode == "both":
            data["teaser"] = True
        _, credit = create_video(kind, data, out)
        if credit:  # CC-BY music ho to credit description mein khud lag jaye
            data["description"] = (data.get("description", "") + "\n\n" + credit).strip()
            with open(sj, "w", encoding="utf-8") as f:
                json.dump(data, f, ensure_ascii=False, indent=2)


if __name__ == "__main__":
    main()
