"""Deterministic anti-hallucination guardrail for AI-generated catalog text.

Generalised from a real failure: Gemini kept inventing plausible Chinese
signage on dark footage shot BEFORE the trip ever reached China. No prompt
tuning fully stopped it. The fix is deterministic: a token (e.g. any CJK
character) is only legitimate from a given date onward; in any earlier file it
is a hallucination and gets neutralised to "illegible", and a USE verdict on
that line is downgraded to DISCARD.

Configure in config.yaml -> guardrail:
  token_regex         regex matching the impossible token class (blank = off)
  allowed_from_date   YYYYMMDD; tokens allowed from this date on
  filename_date_regex how to read the date out of a filename
"""
import os
import re
import glob


def _date8(name, date_re):
    m = re.search(date_re, name)
    return m.group(1) if m else "99999999"


def clean_line(line, token_re):
    """Neutralise fabricated tokens in one catalog line; downgrade USE->DISCARD."""
    # quoted / parenthesised groups that contain the token -> 'illegible'
    def repl(m):
        return "illegible" if token_re.search(m.group(0)) else m.group(0)
    line = re.sub(r"\([^()]*\)", repl, line)
    for q in [r'"[^"]*"', r"“[^”]*”", r"«[^»]*»", r"'[^']*'"]:
        line = re.sub(q, repl, line)
    # leftover raw runs of the token
    line = token_re.sub("illegible", line)
    # hygiene
    line = re.sub(r"\billegible(\s+illegible)+", " illegible", line)
    line = re.sub(r"  +", " ", line)
    # a USE verdict justified by fake signage becomes DISCARD
    line = re.sub(r"\|\s*USE\s*$", "| DISCARD  # hallucinated token neutralised", line)
    return line


def process_dir(cfg, dirpath, apply=False):
    """Scan *.txt in dirpath; neutralise impossible tokens in pre-date files.
    Returns (files_touched, lines_changed). apply=False is a dry run."""
    if not cfg.guard_token_regex:
        print("guardrail disabled (guardrail.token_regex is blank)")
        return 0, 0
    token_re = re.compile(cfg.guard_token_regex)
    files = sorted(glob.glob(os.path.join(dirpath, "*.txt")))
    hit_files = hit_lines = 0
    for f in files:
        if _date8(os.path.basename(f), cfg.guard_filename_date) >= cfg.guard_from_date:
            continue  # token legitimate from here on
        lines = open(f, encoding="utf-8", errors="replace").read().splitlines()
        changed, out = False, []
        for ln in lines:
            if ln and not ln.startswith("#") and token_re.search(ln):
                cl = clean_line(ln, token_re)
                if cl != ln:
                    changed = True
                    hit_lines += 1
                    out.append(cl)
                    continue
            out.append(ln)
        if changed:
            hit_files += 1
            if apply:
                open(f, "w", encoding="utf-8").write("\n".join(out) + "\n")
    print(f"guardrail: {hit_files} files, {hit_lines} lines {'FIXED' if apply else '(dry-run)'}")
    return hit_files, hit_lines
