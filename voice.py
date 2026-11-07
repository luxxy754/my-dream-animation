"""Har character ki apni awaaz: Kokoro (local, free) ya edge-tts (free, bina key). Fail ho to edge-tts backup.

voice spec: "kokoro:am_adam"  |  "edge:en-US-GuyNeural". pitch = semitones (+ patli, - bhaari awaaz), har character ko alag sunai de.
"""
import asyncio
import os
import subprocess

from vocab import LANGS

SPEED = float(os.environ.get("KOKORO_SPEED", "1.12"))
_pipes = {}


def _kokoro(text, path, voice, speed):
    import numpy as np
    import soundfile as sf
    from kokoro import KPipeline

    lang = voice[0]  # a = American, b = British
    if lang not in _pipes:
        _pipes[lang] = KPipeline(lang_code=lang, repo_id="hexgrad/Kokoro-82M")
    parts = []
    for _, _, audio in _pipes[lang](text, voice=voice, speed=speed, split_pattern=r"\n+"):
        if audio is not None:
            parts.append(audio.detach().cpu().numpy() if hasattr(audio, "detach") else np.asarray(audio))
    if not parts:
        raise RuntimeError("kokoro returned no audio")
    sf.write(path, np.concatenate(parts), 24000, format="WAV", subtype="PCM_16")


def _edge(text, path, voice, rate="+6%"):
    import edge_tts

    asyncio.run(edge_tts.Communicate(text, voice=voice, rate=rate).save(path))


def _tighten(src, dst, pitch):
    af = []
    if abs(pitch) > 0.05:
        r = 2 ** (pitch / 12.0)
        af.append(f"aresample=44100,asetrate={int(44100 * r)},aresample=44100,atempo={1 / r:.4f}")
    af.append("silenceremove=start_periods=1:start_threshold=-42dB:start_silence=0.02:stop_periods=-1:stop_duration=0.15:"
              "stop_threshold=-42dB:stop_silence=0.06,areverse,silenceremove=start_periods=1:start_threshold=-42dB:start_silence=0.03,areverse")
    af.append("acompressor=threshold=-18dB:ratio=3:attack=5:release=60,loudnorm=I=-14:TP=-1.5:LRA=7")
    subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-i", src, "-af", ",".join(af), "-ar", "44100", dst], check=True)


def _fake(text, path, pitch=0.0):
    """Sirf local test (FAKE_VOICE=1): awaaz jaisi shor wali dhun, taake lip-sync/timing test ho sake."""
    import wave

    import numpy as np

    dur = max(1, len(text.split())) / 2.9
    sr = 44100
    t = np.arange(int(dur * sr)) / sr
    syl = np.clip(np.sin(2 * np.pi * 4.2 * t) * 0.6 + 0.5, 0, 1)
    f0 = 140 * 2 ** (pitch / 12)
    x = (np.sin(2 * np.pi * f0 * t) + 0.5 * np.sin(2 * np.pi * 2 * f0 * t)) * syl * 0.25
    with wave.open(path, "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(sr)
        w.writeframes((x * 32767).astype(np.int16).tobytes())


def resolve(ch, lang):
    """character dict -> (voice spec). Angrezi ke ilawa zabaan mein gender ke hisaab se edge voice."""
    if lang != "en":
        spec = ch.get(f"voice_{lang}")
        if spec:
            return spec
        names = LANGS[lang]
        return "edge:" + (names[2] if ch.get("gender", "male") == "male" else names[3])
    return ch.get("voice", "kokoro:am_adam")


def synth(text, path, spec="kokoro:am_adam", pitch=0.0, speed=None, lang="en"):
    if os.environ.get("FAKE_VOICE") == "1":
        return _fake(text, path, pitch)
    raw = path + ".raw"
    engine, _, name = spec.partition(":")
    ok = False
    if engine == "kokoro":
        for attempt in (1, 2):
            try:
                _kokoro(text, raw + ".wav", name, speed or SPEED)
                src, ok = raw + ".wav", True
                break
            except Exception as e:  # noqa: BLE001
                print(f"Kokoro failed (attempt {attempt}): {str(e)[:120]}")
    else:
        try:
            _edge(text, raw + ".mp3", name)
            src, ok = raw + ".mp3", True
        except Exception as e:  # noqa: BLE001
            print(f"edge-tts failed: {str(e)[:120]}")
    if not ok:
        print("backup voice use ho raha hai")
        fb = LANGS[lang][2 if (name[:2] != "af" and "Aria" not in name and "Swara" not in name and "Uzma" not in name) else 3]
        _edge(text, raw + ".mp3", fb)
        src = raw + ".mp3"
    _tighten(src, path, pitch)
    for ext in (".wav", ".mp3"):
        if os.path.exists(raw + ext):
            os.remove(raw + ext)
