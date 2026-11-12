"""Generate instrumental music beds with Gemini's Lyria model.

Prompts should describe a cinematic, vocal-free film score that matches the
emotional arc of a section (tension, awe, triumph...). Output lands in your
configured music_dir and is referenced by name from a reel's assemble() call.

google-genai is optional; imported lazily.
"""
import os


def generate(cfg, jobs):
    """jobs: dict of {name: prompt}. Writes <music_dir>/<name>.mp3, skipping
    any that already exist."""
    from google import genai
    from google.genai import types
    key = cfg.gemini_key()
    if not key:
        raise RuntimeError("GEMINI_API_KEY not set in environment")
    client = genai.Client(api_key=key)
    os.makedirs(cfg.music_dir, exist_ok=True)
    for name, prompt in jobs.items():
        out = os.path.join(cfg.music_dir, f"{name}.mp3")
        if os.path.exists(out):
            print("skip", name)
            continue
        try:
            r = client.models.generate_content(
                model=cfg.lyria_model, contents=prompt,
                config=types.GenerateContentConfig(response_modalities=["AUDIO"]))
            wrote = False
            for p in r.candidates[0].content.parts:
                if getattr(p, "inline_data", None) and p.inline_data.data:
                    open(out, "wb").write(p.inline_data.data)
                    print("OK", name, len(p.inline_data.data), "bytes")
                    wrote = True
                    break
            if not wrote:
                print("NO_AUDIO", name)
        except Exception as e:
            print("FAILED", name, str(e)[:160])
