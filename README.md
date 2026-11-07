# my-dream-animation (Shazy ki funny storytelling animation)

RG Bucket List jaisi funny story-time animation: **Shazy** khud ko aur apne doston ko introduce karta hai, phir kahani characters
acting + dialogue ke saath chalti hai. Sab kuch GitHub Actions mein, **sirf 4 secrets**: `GEMINI_API_KEY`, `YOUTUBE_CLIENT_ID`,
`YOUTUBE_CLIENT_SECRET`, `YOUTUBE_REFRESH_TOKEN`. Koi image/video API nahi.

## Kaun kya karta hai
| Cheez | Kaun banata hai |
|---|---|
| Story + dialogue + har line ki directions (emotion, action, effect, sound, prop, location) | Gemini (`script_gen.py`) |
| Characters | **aapki images** `characters/<naam>/idle.png` (puppet animation: saans, bolte waqt uchhal, jump, gir jana, ghoomna, hilna...) |
| Background (10 fixed locations), props (19), effects (!, ?, BOOM...) | code (`world.py`) - **har video mein bilkul same** |
| Awaaz (har character ki alag) | Kokoro / edge-tts (`voice.py`), bina key |
| Music + sound effects | code se (`music.py`) |

## Characters kaise add karein
1. `cast.json` mein naya entry: `name`, `gender`, `age`, `personality`, `speech_style`, `height_cm`, `voice`, `pitch`, `color`.
2. `characters/<naam-lowercase>/idle.png` rakhein. Optional: `happy.png`, `angry.png`, `shocked.png`, `sad.png`, `scared.png`, `excited.png`,
   `confused.png`, `smug.png`, `laugh.png` aur munh-khula `idle_talk.png` (lip sync). Jo nahi hoga uski jagah idle.png + tint/hilna.
3. Image transparent PNG behtar; warna code khud background hata leta hai. Character sheet se ek pose: `python tools/cutout.py sheet.jpg characters/ali/idle.png --crop x0,y0,x1,y1`.

Shazy (`characters/shazy/idle.png`) aapki sheet se already kaata hua rakha hai. Jis character ki image nahi, wo sirf off-screen awaaz (`Voice`) ban sakta hai.
**Dost ka naam/shakhsiyat cast.json mein bharein, taake Gemini unhi ko story mein use kare.**

## Background fixed kaise rehte hain
`world.py` ke upar STYLE BIBLE likha hai. Har location ek function hai jisme har cheez ki jagah/rang/size likha hai (koi random nahi),
isliye room hamesha wahi room hota hai (bed left, PC desk right, SZ poster, skateboard on wall...). Naya location: `draw_<naam>` + `LOCATIONS`/`DRAWERS` mein entry.
Gemini sirf in locations mein se chunta hai, naya nahi banata.

## Modes / settings
`both` (cron): long (~8-9 min, 16:9) + usko promote karne wala Short (9:16, camera bolne wale ko follow karta hai). `short` / `long` bhi chalte hain.
Manual run: Actions > Daily Funny Animation > Run workflow. `upload` band karo to sirf test (video "videos" artifact mein).
`STORY_LANG` (en / hi / ur), `LONG_TARGET_WORDS`, `LONG_SPEED`, `SHORT_SPEED`, `MUSIC_GAIN`, `SFX_GAIN`, `MAX_DELAY_MIN` workflow ke `env:` mein.

## Gemini credit
`both` run: 1 plan + ~8 chapters + 1 teaser = ~10 calls; `short`: 1 call. Baqi sab local CPU par.

## Local test (bina Gemini/Kokoro)
`FAKE_VOICE=1 MODE=short python script_gen.py && FAKE_VOICE=1 MODE=short python render.py` (key na ho to fallback script; `DEBUG_DIR=dbg` set karein to frames save hote hain).
