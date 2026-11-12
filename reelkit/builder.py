"""The reel builder: turn a list of shots into a finished master.

A reel script is just a Python list of shot dicts (see examples/example_reel.py).
Shot kinds:

  {"kind":"title", "title":"RUSSIA", "subtitle":"PART 1", "dur":3.0}
  {"kind":"card",  "main":"TO BE CONTINUED", "sub":"PART 3", "dur":3.5}
  {"kind":"photo", "img":"/path/photo.jpg", "dur":3.2, "sub":"caption"}
  {"kind":"clip",  "cam":"pov", "src":"CLIP_BASENAME", "ss":10, "dur":8,
                   "grade":"dlog",            # a grade name from config (optional)
                   "sub":"one caption"         # str, OR a list of timed segments:
                   # "sub":[(0.2,4.0,"line one"),(4.2,8.0,"line two")],
                   "angle":"hero",             # sphere360 cameras only
                   "audio_from":("pov","OTHER_CLIP",405),  # borrow another cam's mic
                   "blur":[(x,y,w,h), ...]}    # blur boxes (number plates etc.)

Design choices that encode hard-won lessons:
  * Every segment is memoised on disk by a hash of the shot, so re-runs don't
    re-read the (often flaky, external) footage disk. Delete tmp_dir to force a
    rebuild.
  * Shots are joined with crossfades (xfade/acrossfade), never hard cuts.
  * A music bed is side-chain ducked under the program audio (your voice).
  * Text is PIL PNG overlays; concatenation uses the concat *filter*.
"""
import os
import hashlib
import subprocess

from . import ffmpeg_helpers as ff
from . import text_overlay as tx
from .reframe360 import angle_filter


class Builder:
    def __init__(self, cfg):
        self.cfg = cfg
        self.tmp = cfg.tmp_dir
        self._cache = {}

    # -- small helpers -------------------------------------------------------
    def _sig(self, shot):
        return "|".join(f"{k}={shot[k]}" for k in sorted(shot))

    def _hash(self, shot):
        return hashlib.md5(self._sig(shot).encode()).hexdigest()[:10]

    def _scale_crop(self, grade_name):
        parts = [f"scale={self.cfg.W}:{self.cfg.H}:force_original_aspect_ratio=increase",
                 f"crop={self.cfg.W}:{self.cfg.H}"]
        g = self.cfg.grade(grade_name)
        if g:
            parts.append(g)
        parts.append("format=yuv420p")
        return ",".join(parts)

    # -- text/card segments --------------------------------------------------
    def _still_to_clip(self, png, dur, outp, fade):
        """Turn a still PNG into a silent video segment of length `dur`.
        fade: 'in' | 'out' | None (crossfades handle the rest)."""
        vf = f"scale={self.cfg.W}:{self.cfg.H}"
        if fade == "in":
            vf += ",fade=t=in:d=0.6"
        elif fade == "out":
            vf += f",fade=t=out:st={dur-0.6:.2f}:d=0.6"
        vf += ",format=yuv420p"
        ff.run(["ffmpeg", "-y", "-loop", "1", "-t", str(dur), "-i", png,
                "-f", "lavfi", "-i", "anullsrc=r=48000:cl=stereo", "-shortest",
                "-r", str(self.cfg.FPS), "-vf", vf] + ff.SEG_VCODEC + ff.SEG_ACODEC + [outp],
               timeout=120)

    # -- overlays ------------------------------------------------------------
    def _overlay_subs(self, src, sub, dur, outp):
        segs = [(0.0, dur, sub)] if isinstance(sub, str) else list(sub)
        inputs = ["-i", src]
        fc = ""
        lab = "0:v"
        for i, (t0, t1, txt) in enumerate(segs):
            png = os.path.join(self.tmp, "_sub_%s.png" % hashlib.md5((txt + str(i)).encode()).hexdigest()[:8])
            tx.subtitle_png(self.cfg, txt, png)
            inputs += ["-loop", "1", "-i", png]
            out = f"so{i}"
            fc += f"[{lab}][{i+1}:v]overlay=0:0:enable='between(t,{t0:.2f},{t1:.2f})'[{out}];"
            lab = out
        fc = fc.rstrip(";")
        ff.run(["ffmpeg", "-y"] + inputs + ["-filter_complex", fc, "-map", f"[{lab}]",
                "-map", "0:a?", "-t", str(dur)] + ff.SEG_VCODEC + ff.SEG_ACODEC + [outp], timeout=200)
        return ff.ok_file(outp)

    def _blur_boxes(self, src, boxes, dur, outp):
        parts = []
        lab = "0:v"
        for i, (bx, by, bw, bh) in enumerate(boxes):
            out = "v" if i == len(boxes) - 1 else f"ov{i}"
            parts.append(f"[{lab}]split[b{i}][t{i}];[t{i}]crop={bw}:{bh}:{bx}:{by},"
                         f"avgblur=24,avgblur=24[bl{i}];[b{i}][bl{i}]overlay={bx}:{by}[{out}]")
            lab = out
        ff.run(["ffmpeg", "-y", "-i", src, "-filter_complex", ";".join(parts),
                "-map", "[v]", "-map", "0:a?", "-t", str(dur)] + ff.SEG_VCODEC + ff.SEG_ACODEC + [outp],
               timeout=200)
        return ff.ok_file(outp)

    # -- per-shot render -----------------------------------------------------
    def render_shot(self, shot):
        sig = self._sig(shot)
        if sig in self._cache:
            return self._cache[sig]
        h = self._hash(shot)
        outp = os.path.join(self.tmp, f"s_{h}.mp4")
        base_mp4 = os.path.join(self.tmp, f"s_{h}_b.mp4")
        # disk cache: a previously rendered segment is reused (no re-read of footage)
        for c in (outp, base_mp4):
            if ff.ok_file(c):
                res = (c, float(shot.get("dur", ff.probe_duration(c))))
                self._cache[sig] = res
                return res

        kind = shot["kind"]
        dur = float(shot.get("dur", 4))

        if kind == "title":
            png = os.path.join(self.tmp, f"_title_{h}.png")
            tx.title_png(self.cfg, shot["title"], shot.get("subtitle", ""), png)
            self._still_to_clip(png, dur, outp, fade="in")
            return self._done(sig, outp, dur)

        if kind == "card":
            png = os.path.join(self.tmp, f"_card_{h}.png")
            tx.card_png(self.cfg, shot["main"], shot.get("sub", ""), png)
            self._still_to_clip(png, dur, outp, fade="out")
            return self._done(sig, outp, dur)

        if kind == "photo":
            frames = int(dur * self.cfg.FPS)
            W, H = self.cfg.W, self.cfg.H
            vf = (f"scale={int(W*1.25)}:{int(H*1.25)}:force_original_aspect_ratio=increase,"
                  f"zoompan=z='min(zoom+0.0006,1.12)':d={frames}:"
                  f"x='iw/2-(iw/zoom/2)':y='ih/2-(ih/zoom/2)':s={W}x{H}:fps={self.cfg.FPS},format=yuv420p")
            ff.run(["ffmpeg", "-y", "-loop", "1", "-t", str(dur), "-i", shot["img"],
                    "-f", "lavfi", "-i", "anullsrc=r=48000:cl=stereo", "-shortest",
                    "-r", str(self.cfg.FPS), "-vf", vf] + ff.SEG_VCODEC + ff.SEG_ACODEC + [base_mp4],
                   timeout=200)
            return self._finish(sig, base_mp4, shot, dur, outp)

        if kind == "clip":
            cam = self.cfg.camera(shot["cam"])
            src = cam.resolve(shot["src"])
            if not src:
                print(f"  !! clip not found: cam={shot['cam']} src={shot['src']}")
                return (None, dur)
            ss = shot.get("ss", 0)
            af = self.cfg.ambient_filter
            audio_from = shot.get("audio_from")

            if cam.type == "sphere360":
                vf = f"{angle_filter(self.cfg, shot.get('angle','hero'))},"
                vf += (self.cfg.grade(shot["grade"]) + ",") if shot.get("grade") else ""
                vf += "format=yuv420p"
            else:  # pov / flat
                vf = self._scale_crop(shot.get("grade"))

            if audio_from:
                acam, asrc, ass = audio_from
                av = self.cfg.camera(acam).resolve(asrc)
                args = ["ffmpeg", "-y", "-ss", str(ss), "-i", src, "-ss", str(ass), "-i", av,
                        "-t", str(dur), "-r", str(self.cfg.FPS), "-vf", vf,
                        "-map", "0:v:0", "-map", "1:a:0?", "-af", self.cfg.voice_filter]
            else:
                use_af = self.cfg.voice_filter if cam.has_mic and cam.type != "sphere360" else af
                args = ["ffmpeg", "-y", "-ss", str(ss), "-i", src, "-t", str(dur),
                        "-r", str(self.cfg.FPS), "-vf", vf,
                        "-map", "0:v:0", "-map", "0:a:0?", "-af", use_af]
            ff.run(args + ff.SEG_VCODEC + ff.SEG_ACODEC + [base_mp4], timeout=300)
            return self._finish(sig, base_mp4, shot, dur, outp)

        raise ValueError(f"unknown shot kind: {kind}")

    def _finish(self, sig, src, shot, dur, outp):
        """Apply optional blur boxes and subtitles, then cache."""
        if not ff.ok_file(src):
            return (None, dur)
        if shot.get("blur"):
            blurred = src.replace("_b.mp4", "_bl.mp4")
            if self._blur_boxes(src, shot["blur"], dur, blurred):
                src = blurred
        if shot.get("sub") and self._overlay_subs(src, shot["sub"], dur, outp):
            return self._done(sig, outp, dur)
        return self._done(sig, src, dur)

    def _done(self, sig, path, dur):
        self._cache[sig] = (path, dur)
        return self._cache[sig]

    # -- assembly: crossfades + ducked music bed -----------------------------
    def assemble(self, shots, outname, music=None):
        items = [self.render_shot(s) for s in shots]
        paths = [p for p, _ in items if p and ff.ok_file(p)]
        n = len(paths)
        print(f"shots ok: {n}/{len(shots)}")
        if n == 0:
            print("nothing rendered; check camera paths / clip names")
            return None
        durs = [ff.probe_duration(p) for p in paths]
        XF = self.cfg.XF

        inp = []
        for p in paths:
            inp += ["-i", p]
        music_path = self.cfg.music_path(music)
        have_music = bool(music_path and os.path.exists(music_path))
        if have_music:
            inp += ["-stream_loop", "-1", "-i", music_path]

        # video crossfade chain
        vparts = []
        lab = "0:v"
        cum = durs[0]
        for j in range(1, n):
            off = cum - XF
            out = f"vx{j}"
            vparts.append(f"[{lab}][{j}:v]xfade=transition=fade:duration={XF}:offset={off:.3f}[{out}]")
            lab = out
            cum = cum + durs[j] - XF
        vfinal = lab

        # audio crossfade chain
        aparts = []
        alab = "0:a"
        for j in range(1, n):
            out = f"ax{j}"
            aparts.append(f"[{alab}][{j}:a]acrossfade=d={XF}[{out}]")
            alab = out
        afinal = alab

        if have_music:
            dk = self.cfg.duck
            music_mix = (
                f"[{afinal}]asplit=2[acm][acx];[{n}:a]volume={self.cfg.music_volume}[mv];"
                f"[mv][acm]sidechaincompress=threshold={dk['threshold']}:ratio={dk['ratio']}:"
                f"attack={dk['attack']}:release={dk['release']}[md];"
                f"[acx][md]amix=inputs=2:duration=first:normalize=0[aout]")
            amap = "[aout]"
            fc = ";".join(vparts + aparts + [music_mix])
        else:
            amap = f"[{afinal}]"
            fc = ";".join(vparts + aparts)

        final = os.path.join(self.cfg.output_dir, outname)
        if fc:
            maps = ["-filter_complex", fc, "-map", f"[{vfinal}]", "-map", amap]
        else:
            # single shot, no music: no filtergraph, map the input streams directly
            maps = ["-map", "0:v:0", "-map", "0:a:0?"]
        r = subprocess.run(["ffmpeg", "-y"] + inp + maps + ff.FINAL_VCODEC + ff.FINAL_ACODEC + [final],
                           stderr=subprocess.PIPE, stdout=subprocess.DEVNULL, timeout=1800)
        if r.returncode == 0:
            print(f"OK  {outname}  dur={ff.probe_duration(final):.0f}s  shots={n}  -> {final}")
            return final
        print("FAILED:", r.stderr.decode()[-800:])
        return None
