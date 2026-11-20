"""Read Beta Builder continuity log sheets (screenshots / PDFs) into rows:
{scene, shot, cam, card, clips[], takes[], ok[], desc, page}
OCR is Apple Vision through ../bin/logocr; parsing uses the table layout (column headers + card rows).
"""
import glob, json, os, re, subprocess

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
LOGOCR = os.path.join(HERE, "bin", "logocr")
IMG_EXT = (".png", ".jpg", ".jpeg", ".pdf")

def fix_digits(s):
    return s.translate(str.maketrans({"O": "0", "o": "0", "I": "1", "l": "1", "|": "1", "S": "5", "B": "8"}))

CARD_RE = re.compile(r"^([A-H])([0-9OoIl]{3})$")
CLIP_RE = re.compile(r"[Cc]([0-9OoIlS]{3})\b")

def log_files(day_dir):
    """Every log sheet image/PDF under a day, de-duplicated by name+size (scene folders hold copies)."""
    seen, out = set(), []
    for dp, dns, fns in os.walk(day_dir):
        low = dp.lower()
        if re.search(r"proxy|h264|sound", os.path.basename(dp), re.I): dns[:] = []; continue
        for fn in fns:
            p = os.path.join(dp, fn)
            if not fn.lower().endswith(IMG_EXT) or fn.startswith("."): continue
            if "log sheet" not in low and not ("log" in fn.lower() and fn.lower().endswith(".pdf")): continue
            key = (fn, os.path.getsize(p))
            if key in seen: continue
            seen.add(key); out.append(p)
    return sorted(out)

def ocr(files, batch=12):
    pages = []
    for i in range(0, len(files), batch):
        out = subprocess.run([LOGOCR, *files[i:i + batch]], capture_output=True, timeout=1800).stdout
        try: pages += json.loads(out or b"[]")
        except ValueError: pass
    return pages

def _hdr(items, *words):
    for it in items:
        t = it["t"].upper()
        if any(w in t for w in words) and it["y"] < 0.2 * 2000: return it
    return None

def parse_page(pg):
    items = pg["items"]; H = pg["h"]
    for it in items: it["cx"] = it["x"] + it["w"] / 2; it["cy"] = it["y"] + it["h"] / 2
    def head(*words, maxy=None):
        c = [it for it in items if any(w in it["t"].upper() for w in words) and it["y"] < (maxy or H * 0.25)]
        return min(c, key=lambda it: it["y"]) if c else None
    hs, hd, hsc = head("SHOT"), head("DESCRIPTION"), head("SCENE")
    head_y = max([h["y"] + h["h"] for h in (hs, hd, hsc) if h] or [0]) + 4
    # columns from the data itself: card numbers (A017…) and the densest column of clip numbers (C004…)
    clip_toks = [it for it in items if re.fullmatch(r"[Cc][0-9OoIlS]{3}", it["t"].strip()) and it["y"] > head_y]
    if not clip_toks: return None
    bins = {}
    for it in clip_toks: bins.setdefault(int(it["cx"] // 40), []).append(it["cx"])
    best = max(bins.values(), key=len); clip_x = sum(best) / len(best)
    ok_x0, ok_x1 = clip_x + 45, clip_x + 200
    card_toks = [it for it in items if CARD_RE.match(it["t"].strip()) and it["y"] > head_y and it["cx"] < clip_x - 45]
    if not card_toks: return None
    xs = sorted(it["cx"] for it in card_toks); card_x = xs[len(xs) // 2]
    pageno = None
    for it in items:
        m = re.search(r"PAGE\s*N[O0]\s*[:.]?\s*(\d+)", it["t"].upper())
        if m: pageno = int(m.group(1))
    cards = []
    for it in items:
        m = CARD_RE.match(it["t"].strip())
        if m and abs(it["cx"] - card_x) < 60 and it["y"] > head_y and it["cx"] < clip_x - 45:
            cards.append({"cam": m.group(1), "card": m.group(1) + fix_digits(m.group(2)), "y": it["cy"]})
    cards.sort(key=lambda c: c["y"])
    if not cards: return {"page": pageno, "rows": [], "scenes": []}
    gaps = [b["y"] - a["y"] for a, b in zip(cards, cards[1:])] or [H * 0.1]
    med = sorted(gaps)[len(gaps) // 2]
    for i, c in enumerate(cards):
        c["y0"] = (cards[i - 1]["y"] + c["y"]) / 2 if i else c["y"] - med / 2
        c["y1"] = (c["y"] + cards[i + 1]["y"]) / 2 if i + 1 < len(cards) else c["y"] + med / 2
    rows = []
    for c in cards:
        band = [it for it in items if c["y0"] <= it["cy"] < c["y1"]]
        clips = []
        for it in sorted([it for it in band if abs(it["cx"] - clip_x) < 40], key=lambda it: it["cy"]):
            for m in CLIP_RE.finditer(it["t"]): clips.append("C" + fix_digits(m.group(1)))
        ok_txt = " ".join(it["t"] for it in sorted([it for it in band if ok_x0 <= it["cx"] <= ok_x1], key=lambda it: it["cy"]))
        ok = ["C" + fix_digits(m.group(1)) for m in CLIP_RE.finditer(ok_txt)]
        if not ok and re.search(r"PRINT\s*ALL|ALL", ok_txt.upper()): ok = list(clips)
        if not ok:
            for m in re.finditer(r"TAKE\s*(\d+)", ok_txt.upper()):
                n = int(m.group(1))
                if 0 < n <= len(clips): ok.append(clips[n - 1])
        shot = None
        x_desc0 = (hd["x"] - 380) if hd else 0
        desc = " ".join(it["t"] for it in sorted([it for it in band if x_desc0 < it["cx"] < card_x - 60 and len(it["t"]) > 2
                                                 and not re.fullmatch(r"[\d\s]+", it["t"])], key=lambda it: it["cy"]))
        rows.append({"cam": c["cam"], "card": c["card"], "clips": list(dict.fromkeys(clips)), "ok": list(dict.fromkeys(ok)),
                     "ok_text": ok_txt.strip(), "shot": shot, "desc": desc.strip(" :"), "y": c["y"]})
    scenes = []
    if hsc:
        for it in items:
            t = it["t"].strip()
            if it["y"] > head_y and it["cx"] < (hs["x"] if hs else hsc["x"] + hsc["w"]) and re.fullmatch(r"\d{2,3}[A-Z]{0,2}", t):
                scenes.append({"scene": t, "y": it["cy"]})
    notes = " ".join(it["t"] for it in items if len(it["t"]) > 40)
    # shot numbers: tokens in the SHOT column; each row takes the nearest one by height. Fallback: "SHOT n" in the notes.
    shots = []
    if hs:
        shots = [(it["cy"], it["t"].strip()) for it in items if it["y"] > head_y and abs(it["cx"] - hs["cx"]) < 45
                 and re.fullmatch(r"\d{1,2}[A-Z]?", it["t"].strip())]
    nm = re.findall(r"SHOT\s*(\d{1,2})", notes.upper())
    for r in rows:
        if shots: r["shot"] = min(shots, key=lambda s: abs(s[0] - r["y"]))[1]
        elif nm: r["shot"] = nm[0]
    return {"page": pageno, "rows": rows, "scenes": sorted(scenes, key=lambda s: s["y"]), "notes": notes}

MON = {"AM": 0, "PM": 12}
def file_time(path):
    """Order key from the capture time in a screenshot/photo file name."""
    n = os.path.basename(path).replace("\u202f", " ")
    m = re.search(r"(\d{4})-(\d{2})-(\d{2}) at (\d{1,2})\.(\d{2})(?:\.(\d{2}))?\s*([AP]M)", n)
    if m:
        y, mo, d, h, mi, se, ap = m.groups(); h = int(h) % 12 + MON[ap]
        return f"{y}{mo}{d}{h:02d}{mi}{se or '00'}"
    m = re.search(r"(\d{2})-(\d{2})-(\d{2}) at (\d{1,2})\.(\d{2})(?:\.(\d{2}))?\s*([AP]M)", n)
    if m:
        d, mo, y, h, mi, se, ap = m.groups(); h = int(h) % 12 + MON[ap]
        return f"20{y}{mo}{d}{h:02d}{mi}{se or '00'}"
    return None

def index_day(day_dir, progress=None):
    files = log_files(day_dir)
    pages = []
    for i in range(0, len(files), 6):
        pages += ocr(files[i:i + 6])
        if progress: progress(min(1.0, (i + 6) / max(1, len(files))))
    parsed = []
    for pg in pages:
        p = parse_page(pg)
        if p: p["file"] = os.path.relpath(pg["file"], os.path.dirname(day_dir)); p["pdfpage"] = pg.get("page", 1); parsed.append(p)
    # order pages by capture time in the file name (true page order), else printed page number; drop exact duplicates
    def key(p):
        t = file_time(p["file"]); return (0, t, p.get("pdfpage", 0)) if t else (1, f"{p['page'] or 0:06d}", p["file"], p.get("pdfpage", 0))
    seen, ordered = [], []
    for p in sorted(parsed, key=key):
        pairs = {(r["card"], c) for r in p["rows"] for c in r["clips"]}
        dup = any(pairs and len(pairs & q) / len(pairs | q) >= 0.6 for q in seen)
        if dup: continue
        if pairs: seen.append(pairs)
        ordered.append(p)
    out, scene, shot = [], None, None
    for p in ordered:
        for r in p["rows"]:
            sc = [s["scene"] for s in p["scenes"] if s["y"] <= r["y"] + 5]
            if sc: scene = sc[-1]
            if r["shot"]: shot = r["shot"]
            out.append({**{k: v for k, v in r.items() if k != "y"}, "scene": scene, "shot": r["shot"] or shot, "page": p["page"], "file": p["file"]})
    return {"rows": out, "pages": [{"page": p["page"], "file": p["file"], "notes": p.get("notes", "")} for p in ordered]}
