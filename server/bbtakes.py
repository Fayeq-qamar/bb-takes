#!/usr/bin/env python3
"""BB Takes: local multicam review + export tool for the Beta Builder shoot server.

Runs on 127.0.0.1 only. Reads the shoot server (never writes to it), keeps previews in
~/Library/Caches/BB Takes and writes exports to ~/Movies/BB Takes Exports.
Python 3.9+ standard library only. ffmpeg/ffprobe come from ../bin (or PATH).
"""
import array, concurrent.futures, glob, http.server, json, math, os, re, shutil, socketserver
import subprocess, sys, threading, time, traceback, urllib.parse, uuid

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
APP = os.path.join(HERE, "app")
def _bin(name):
    p = os.path.join(HERE, "bin", name)
    return p if os.path.isfile(p) else (shutil.which(name) or name)
FFMPEG, FFPROBE = _bin("ffmpeg"), _bin("ffprobe")
CACHE = os.path.expanduser("~/Library/Caches/BB Takes")
EXPORTS = os.path.expanduser("~/Movies/BB Takes Exports")
PORT = int(os.environ.get("BBTAKES_PORT", "8765"))
try: VERSION = open(os.path.join(HERE, "VERSION")).read().strip()
except OSError: VERSION = "dev"
FONT = "/System/Library/Fonts/Helvetica.ttc"
ROOT_GUESSES = ["/Volumes/BB_Shoot_Data", "/Volumes/T7/BB_Shoot_Data"]
VIDEO_EXT = (".mov", ".mp4", ".mxf")
os.makedirs(CACHE, exist_ok=True); os.makedirs(EXPORTS, exist_ok=True)

# ---------------------------------------------------------------- config
CFG_PATH = os.path.join(CACHE, "config.json")
def load_cfg():
    try: return json.load(open(CFG_PATH))
    except Exception: return {}
CFG = load_cfg()
def save_cfg(): json.dump(CFG, open(CFG_PATH, "w"), indent=1)
def root():
    r = CFG.get("root")
    if r and os.path.isdir(r): return r
    for g in ROOT_GUESSES:
        if os.path.isdir(g): return g
    return r or ROOT_GUESSES[0]

def under(base, p):
    base = os.path.realpath(base); p = os.path.realpath(p)
    return p == base or p.startswith(base + os.sep)

# ---------------------------------------------------------------- jobs
JOBS = {}
JLOCK = threading.Lock()
def new_job(kind, fn, *a):
    jid = uuid.uuid4().hex[:10]
    job = {"id": jid, "kind": kind, "state": "running", "progress": 0.0, "msg": "Starting", "result": None, "error": None}
    with JLOCK: JOBS[jid] = job
    def run():
        try:
            job["result"] = fn(job, *a); job["state"] = "done"; job["progress"] = 1.0; job["msg"] = "Done"
        except Exception as e:
            traceback.print_exc(); job["state"] = "error"; job["error"] = str(e); job["msg"] = "Failed"
    threading.Thread(target=run, daemon=True).start()
    return job

def ff(args, job=None, dur=None, lo=0.0, hi=1.0):
    """Run ffmpeg, updating job progress from -progress output."""
    cmd = [FFMPEG, "-v", "error", "-y", "-nostdin"] + (["-progress", "pipe:1"] if job else []) + args
    p = subprocess.Popen(cmd, stdout=subprocess.PIPE if job else subprocess.DEVNULL, stderr=subprocess.PIPE, text=True)
    if job:
        for line in p.stdout:
            if line.startswith("out_time_us=") and dur:
                try: job["progress"] = lo + (hi - lo) * min(1.0, int(line.split("=")[1]) / 1e6 / dur)
                except ValueError: pass
    err = p.stderr.read(); p.wait()
    if p.returncode != 0:
        raise RuntimeError("ffmpeg failed: " + "\n".join(l for l in err.splitlines() if "Fontconfig" not in l)[-600:])

# ---------------------------------------------------------------- server layout
DAY_RE = re.compile(r"^day[_\s-]*(\d+)$", re.I)
def days():
    r = root(); out = []
    if not os.path.isdir(r): return out
    for n in os.listdir(r):
        m = DAY_RE.match(n)
        if m and os.path.isdir(os.path.join(r, n)): out.append({"day": n, "num": int(m.group(1))})
    return sorted(out, key=lambda d: d["num"])

def proxy_dir(day):
    d = os.path.join(root(), day); best = None
    for n in sorted(os.listdir(d)):
        p = os.path.join(d, n)
        if not os.path.isdir(p) or not re.search(r"proxy|h264", n, re.I): continue
        if not any(x.lower().startswith("cam_") for x in os.listdir(p)): continue
        score = 0 if "h264" in n.lower() else 1  # prefer the non-H264 (ProRes) proxies when both exist
        if best is None or score > best[0]: best = (score, p)
    return best[1] if best else None

def cam_id(folder):
    n = folder
    m = re.match(r"cam[_\s-]*([a-z])$", n, re.I)
    if m: return m.group(1).upper()
    m = re.match(r"gopro[_\s-]*0*(\d+)$", n, re.I)
    if m: return "GP" + m.group(1)
    m = re.match(r"insta360[_\s-]*0*(\d+)$", n, re.I)
    if m: return "360-" + m.group(1)
    return n

def cam_sort(c):
    return (0, c) if len(c) == 1 else (1, c)

# ---------------------------------------------------------------- probing
def parse_rate(r):
    try:
        a, b = r.split("/"); return float(a) / float(b) if float(b) else 25.0
    except Exception: return 25.0

def tc_seconds(tc, fps):
    m = re.match(r"(\d+)[:;](\d+)[:;](\d+)[:;.](\d+)", tc or "")
    if not m: return None
    h, mi, s, f = map(int, m.groups()); return h * 3600 + mi * 60 + s + f / max(1.0, round(fps))

def probe(path):
    j = json.loads(subprocess.check_output([FFPROBE, "-v", "error", "-show_entries",
        "format=duration:format_tags=timecode,creation_time:stream=codec_type,codec_name,width,height,r_frame_rate:stream_tags=timecode",
        "-of", "json", path], timeout=60))
    v = next((s for s in j.get("streams", []) if s.get("codec_type") == "video"), {})
    fps = parse_rate(v.get("r_frame_rate", "25/1"))
    tc = next((s["tags"]["timecode"] for s in j.get("streams", []) if s.get("tags", {}).get("timecode")), None) \
        or j.get("format", {}).get("tags", {}).get("timecode")
    return {"dur": float(j.get("format", {}).get("duration") or 0), "w": v.get("width"), "h": v.get("height"),
            "codec": v.get("codec_name"), "fps": fps, "tc": tc, "tcs": tc_seconds(tc, fps),
            "audio": any(s.get("codec_type") == "audio" for s in j.get("streams", [])),
            "created": j.get("format", {}).get("tags", {}).get("creation_time")}

def scan_day(job, day):
    pd = proxy_dir(day)
    if not pd: raise RuntimeError(f"No proxy folder with Cam_ folders in {day}")
    cache_p = os.path.join(CACHE, "days", day + ".json"); os.makedirs(os.path.dirname(cache_p), exist_ok=True)
    try: old = {c["path"]: c for c in json.load(open(cache_p))["clips"]}
    except Exception: old = {}
    files = []
    for camf in sorted(os.listdir(pd)):
        cp = os.path.join(pd, camf)
        if not os.path.isdir(cp): continue
        for dirpath, _, fns in os.walk(cp):
            for fn in fns:
                if fn.lower().endswith(VIDEO_EXT) and not fn.startswith("."):
                    files.append((cam_id(camf), os.path.join(dirpath, fn)))
    job["msg"] = f"Reading {len(files)} clips"
    clips, done = [], [0]
    def one(item):
        cam, p = item
        st = os.stat(p); o = old.get(p)
        if o and o.get("size") == st.st_size and o.get("mtime") == int(st.st_mtime): return o
        try: info = probe(p)
        except Exception as e: info = {"error": str(e)[:200], "dur": 0, "tcs": None, "audio": False}
        info.update(path=p, cam=cam, name=os.path.splitext(os.path.basename(p))[0], card=os.path.basename(os.path.dirname(p)),
                    size=st.st_size, mtime=int(st.st_mtime))
        return info
    with concurrent.futures.ThreadPoolExecutor(8) as ex:
        for c in ex.map(one, files):
            clips.append(c); done[0] += 1; job["progress"] = done[0] / max(1, len(files))
    json.dump({"day": day, "proxy": pd, "clips": clips}, open(cache_p, "w"))
    return group_takes(day, pd, clips)

def group_takes(day, pd, clips):
    good = [c for c in clips if c.get("dur", 0) > 1 and not c.get("error")]
    with_tc = sorted([c for c in good if c.get("tcs") is not None], key=lambda c: c["tcs"])
    groups, cur, end = [], [], -1e9
    for c in with_tc:
        s, e = c["tcs"], c["tcs"] + c["dur"]
        if cur and s < end - 2.0: cur.append(c); end = max(end, e)
        else:
            if cur: groups.append(cur)
            cur, end = [c], e
    if cur: groups.append(cur)
    takes = []
    for grp in groups:
        bycam = {}
        for c in grp: bycam.setdefault(c["cam"], []).append(c)
        main, extra = [], []
        for cam, cs in bycam.items():
            cs.sort(key=lambda c: -c["dur"]); main.append(cs[0]); extra += cs[1:]
        takes.append(main)
        takes += [[c] for c in extra]
    takes += [[c] for c in good if c.get("tcs") is None]
    out = []
    for t in takes:
        t.sort(key=lambda c: cam_sort(c["cam"]))
        ref = t[0]
        tcs = [c["tcs"] for c in t if c.get("tcs") is not None]
        out.append({"id": f"{day}__{ref['name']}", "day": day, "ref": ref["name"], "cams": [c["cam"] for c in t],
                    "clips": [{"cam": c["cam"], "name": c["name"], "card": c["card"], "dur": round(c["dur"], 2), "tc": c.get("tc"),
                               "w": c.get("w"), "h": c.get("h"), "audio": c.get("audio"), "rel": os.path.relpath(c["path"], root())} for c in t],
                    "start": min(tcs) if tcs else None, "dur": round(max(c["dur"] for c in t), 2)})
    out.sort(key=lambda t: (t["start"] is None, t["start"] or 0, t["ref"]))
    return {"day": day, "proxy": os.path.relpath(pd, root()), "takes": out}

def day_takes_cached(day):
    p = os.path.join(CACHE, "days", day + ".json")
    if not os.path.isfile(p): return None
    d = json.load(open(p)); return group_takes(day, d["proxy"], d["clips"])

# ---------------------------------------------------------------- scenes
SCENE_DIR_RE = re.compile(r"^(sc|scene)(?=[\s_.\-\d])[\s_.-]*", re.I)
def scene_tokens(name):
    s = SCENE_DIR_RE.sub("", name)
    s = re.sub(r"(?i)phase[\s_]*\w+(\s*\+\s*\d+\w*)*|house[\s_]*\d+|_?(ext|int)_(day|night)\w*", " ", s)
    return [norm_scene(t) for t in re.findall(r"(?<![\dA-Za-z])(\d{1,3}[A-Za-z]{0,2})(?![\d])", s)]

def norm_scene(t):
    """'07' -> '7', '02a' -> '2A', 'Sc 217' -> '217'."""
    t = re.sub(r"(?i)^\s*(sc|scene)\s*", "", str(t or "")).strip().upper()
    return t.lstrip("0") or t

SCENES_CACHE = {"t": 0, "data": []}
def scenes():
    if time.time() - SCENES_CACHE["t"] < 300 and SCENES_CACHE["data"]: return SCENES_CACHE["data"]
    out = []
    for d in days():
        dp = os.path.join(root(), d["day"])
        daylogs = [os.path.relpath(p, root()) for p in glob.glob(os.path.join(dp, "*")) if p.lower().endswith(".pdf") and "log" in p.lower()]
        for loc in sorted(os.listdir(dp)):
            lp = os.path.join(dp, loc)
            if not os.path.isdir(lp) or re.search(r"proxy|h264|sound", loc, re.I): continue
            for sc in sorted(os.listdir(lp)):
                sp = os.path.join(lp, sc)
                if not os.path.isdir(sp) or not SCENE_DIR_RE.match(sc): continue
                logs = {}
                for wdir, _, fns in os.walk(sp):
                    if "log sheet" not in wdir.lower(): continue
                    for fn in fns:
                        if fn.lower().endswith((".png", ".jpg", ".jpeg", ".pdf")) and not fn.startswith("."):
                            logs.setdefault(fn.lower(), os.path.relpath(os.path.join(wdir, fn), root()))
                out.append({"day": d["day"], "dayNum": d["num"], "location": loc.strip(), "folder": sc, "tokens": scene_tokens(sc),
                            "logs": sorted(logs.values()) + daylogs})
    SCENES_CACHE.update(t=time.time(), data=out); return out

# ---------------------------------------------------------------- log sheets -> scenes, shots, takes
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import logsheets

def log_index(day):
    for p in (os.path.join(CACHE, "logs", day + ".json"), os.path.join(HERE, "seeds", "logs", day + ".json")):
        if os.path.isfile(p):
            try: return json.load(open(p))
            except Exception: pass
    return None

def read_logs(job, day):
    r = logsheets.index_day(os.path.join(root(), day), progress=lambda f: job.update(progress=f, msg="Reading log sheets"))
    os.makedirs(os.path.join(CACHE, "logs"), exist_ok=True); json.dump(r, open(os.path.join(CACHE, "logs", day + ".json"), "w"))
    return {"rows": len(r["rows"])}

def shot_note(notes, shot):
    m = re.search(r"SHOT\s*%s\b\s*[:.\-]?\s*(.{10,180}?)(?=SHOT\s*\d|NOTE FOR|PAGE\s*N|$)" % re.escape(str(shot)), notes or "", re.I)
    if not m: return ""
    t = re.sub(r"^(COVERAGE\s+IS\s+(OF|FROM)\s+|IS\s+COVERED\s+FROM\s+)", "", m.group(1).strip(), flags=re.I)
    return t[:1].upper() + t[1:].lower()

def scene_view(q):
    q = norm_scene(q)
    folders = [s for s in scenes() if q in s["tokens"]]
    day_list = []
    for s in folders:
        if s["day"] not in day_list: day_list.append(s["day"])
    for d in days():
        li = log_index(d["day"])
        if li and any(norm_scene(r.get("scene")) == q for r in li["rows"]) and d["day"] not in day_list: day_list.append(d["day"])
    out_days = []
    for day in day_list:
        li = log_index(day)
        if not li:
            out_days.append({"day": day, "needsLogs": True, "shots": []}); continue
        notes = {p["file"]: p.get("notes", "") for p in li["pages"]}
        rows = [r for r in li["rows"] if norm_scene(r.get("scene")) == q and r["clips"]]
        shots, order = {}, []
        for r in rows:
            k = r["shot"] or "?"
            if k not in shots: shots[k] = {}; order.append(k)
            cur = shots[k].get(r["card"])
            if not cur or len(r["clips"]) > len(cur["clips"]): shots[k][r["card"]] = {**r, "note": notes.get(r["file"], "")}
        out_shots = []
        order.sort(key=lambda k: (not re.match(r"\d", k), int(re.match(r"\d+", k).group()) if re.match(r"\d", k) else 0, k))
        for k in order:
            rs = sorted(shots[k].values(), key=lambda r: r["cam"])
            prim = next((r for r in rs if r["cam"] == "A" and len(r["clips"]) == max(len(x["clips"]) for x in rs)), None) or max(rs, key=lambda r: len(r["clips"]))
            ntake = max(len(r["clips"]) for r in rs)
            takes = []
            for i in range(ntake):
                clips = {r["cam"]: r["card"] + r["clips"][i] for r in rs if len(r["clips"]) > i}
                votes = [r["clips"][i] in r["ok"] for r in rs if len(r["clips"]) > i]
                ok = (prim["clips"][i] in prim["ok"]) if len(prim["clips"]) > i else (sum(votes) > len(votes) / 2)
                pstem = clips.get(prim["cam"]) or next(iter(clips.values()))
                tid = f"{day}__{pstem}"
                ready = os.path.isfile(os.path.join(CACHE, "takes", re.sub(r"[^\w.-]+", "_", tid), "take.json"))
                takes.append({"n": i + 1, "ok": ok, "clips": clips, "primary": pstem, "ready": ready})
            note = next((shot_note(r["note"], k) for r in rs if shot_note(r["note"], k)), "")
            out_shots.append({"shot": k, "note": note, "cams": [{"cam": r["cam"], "desc": re.sub(r"[\s•·:;,.-]+$", "", r["desc"] or "")} for r in rs], "takes": takes})
        out_days.append({"day": day, "shots": out_shots})
    try: seeds = json.load(open(os.path.join(HERE, "seeds", "known_takes.json")))
    except Exception: seeds = {}
    sd = next((v for k, v in seeds.items() if norm_scene(k) == q), None)
    if isinstance(sd, dict) and not any(d.get("shots") for d in out_days if d["day"] == sd["day"]):
        out_days = [d for d in out_days if d["day"] != sd["day"]]
        shots = []
        for sh in sd["shots"]:
            takes = []
            for i, t in enumerate(sh["takes"]):
                tid = f"{sd['day']}__{t['primary']}"
                ready = os.path.isfile(os.path.join(CACHE, "takes", re.sub(r"[^\w.-]+", "_", tid), "take.json"))
                takes.append({"n": i + 1, "ok": bool(t.get("ok")), "clips": {t["primary"][0]: t["primary"]}, "primary": t["primary"], "auto": True, "ready": ready})
            shots.append({"shot": sh["shot"], "note": sh.get("note", ""), "cams": [], "takes": takes})
        out_days.insert(0, {"day": sd["day"], "shots": shots, "seeded": True})
    return {"scene": q, "folders": folders, "days": out_days}

ALL_CACHE = {"t": 0, "data": []}
def scenes_all():
    """Every scene on the server (scene folders + log sheets + seeds), flagged when log-sheet shots exist."""
    if time.time() - ALL_CACHE["t"] < 300 and ALL_CACHE["data"]: return ALL_CACHE["data"]
    info = {}
    for s in scenes():
        for t in s["tokens"]:
            info.setdefault(t, {"scene": t, "has": False, "where": []})["where"].append(f"{s['day']} · {s['location'].replace('_', ' ').title()}")
    for d in days():
        li = log_index(d["day"])
        if not li: continue
        for r in li["rows"]:
            sc = norm_scene(r.get("scene"))
            if sc and r.get("clips"):
                e = info.setdefault(sc, {"scene": sc, "has": False, "where": []}); e["has"] = True
                if not any(w.startswith(d["day"]) for w in e["where"]): e["where"].append(d["day"])
    try: seeds = json.load(open(os.path.join(HERE, "seeds", "known_takes.json")))
    except Exception: seeds = {}
    for sc, v in seeds.items():
        e = info.setdefault(norm_scene(sc), {"scene": norm_scene(sc), "has": False, "where": []}); e["has"] = True
    def k(t):
        m = re.match(r"(\d+)(.*)", t); return (int(m.group(1)), m.group(2)) if m else (9999, t)
    out = [info[t] for t in sorted(info, key=k)]
    ALL_CACHE.update(t=time.time(), data=out); return out

def stem_path(day, stem):
    pd = proxy_dir(day); cam = stem[0]
    hit = glob.glob(os.path.join(pd, f"Cam_{cam}", f"Card_{stem[:4]}", stem + "_*.*")) or glob.glob(os.path.join(pd, f"Cam_{cam}", "*", stem + "_*.*"))
    return hit[0] if hit else None

def prepare_log(job, day, clips, labels, title, force=False):
    """clips: {cam: stem}. The primary is A (or the first); other cams must overlap it in timecode,
    else their neighbouring clips on the same card are tried (log sheets drift by a few numbers)."""
    auto = len(clips) == 1
    if auto:  # only the primary is known: try the same card/clip number on every other camera, keep what overlaps
        (pc, ps), = clips.items(); pd = proxy_dir(day)
        for camf in os.listdir(pd):
            m = re.match(r"cam[_\s-]*([a-z])$", camf, re.I)
            if m and m.group(1).upper() != pc: clips[m.group(1).upper()] = m.group(1).upper() + ps[1:]
    cams = sorted(clips, key=cam_sort); prim = "A" if "A" in clips else cams[0]
    pp = stem_path(day, clips[prim])
    if not pp: raise RuntimeError(f"Can't find {clips[prim]} on the server")
    pi = probe(pp); t0, t1 = pi["tcs"], (pi["tcs"] or 0) + pi["dur"]
    chosen = {prim: pp}; notes = []
    for cam in cams:
        if cam == prim: continue
        stem = clips[cam]; n = int(stem[5:8]); best = None
        for dn in (0, 1, -1, 2, -2, 3, -3):
            cand = stem_path(day, f"{stem[:5]}{n + dn:03d}")
            if not cand: continue
            ci = probe(cand)
            if t0 is None or ci["tcs"] is None: best = cand; break
            ov = min(t1, ci["tcs"] + ci["dur"]) - max(t0, ci["tcs"])
            if ov > min(5.0, 0.3 * pi["dur"]): best = cand; break
        if best:
            chosen[cam] = best
            got = os.path.basename(best)[:8]
            if got != stem and not auto: notes.append(f"Cam {cam}: log says {stem[4:]}, footage is {got[4:]}")
        elif not auto: notes.append(f"Cam {cam}: {stem[4:]} didn't roll with this take")
    tid = f"{day}__{os.path.splitext(os.path.basename(pp))[0][:8]}"
    man = prepare_paths(job, day, tid, [(c, chosen[c]) for c in sorted(chosen, key=cam_sort)], force)
    man["title"] = title; man["notes"] = notes
    for c in man["cams"]: c["desc"] = labels.get(c["cam"], "")
    return man

# ---------------------------------------------------------------- tags (scene -> clip names)
TAGS_P = os.path.join(CACHE, "tags.json")
def tags():
    t = {}
    for p in (os.path.join(HERE, "seeds", "known_takes.json"), TAGS_P):
        try:
            for sc, names in json.load(open(p)).items(): t.setdefault(sc.upper(), set()).update(names)
        except Exception: pass
    return t
def set_tag(scene, name, on):
    try: t = json.load(open(TAGS_P))
    except Exception: t = {}
    s = set(t.get(scene.upper(), []))
    s.add(name) if on else s.discard(name)
    t[scene.upper()] = sorted(s); json.dump(t, open(TAGS_P, "w"), indent=1)

# ---------------------------------------------------------------- audio sync (pure python)
ENV_HZ = 100
def envelope(path, start=0.0, dur=240.0):
    raw = subprocess.run([FFMPEG, "-v", "error", "-nostdin", "-ss", f"{max(0, start):.3f}", "-t", f"{dur:.3f}", "-i", path, "-vn",
                          "-ac", "1", "-ar", "4000", "-f", "s16le", "-"], capture_output=True).stdout
    a = array.array("h"); a.frombytes(raw[: len(raw) // 2 * 2])
    step = 4000 // ENV_HZ; env = []
    for i in range(0, len(a) - step + 1, step):
        seg = a[i:i + step]; env.append(sum(abs(x) for x in seg) / step)
    # high-pass the envelope (onsets) so mic gain/room tone don't dominate
    out = [0.0] + [max(0.0, env[i] - env[i - 1]) for i in range(1, len(env))]
    m = sum(out) / max(1, len(out)); sd = math.sqrt(sum((x - m) ** 2 for x in out) / max(1, len(out))) or 1.0
    return [(x - m) / sd for x in out]

def best_lag(ref, y, center, radius, step=1):
    """lag L (samples): y[n + L] ~ ref[n]. Returns (L, r)."""
    best = (center, -2.0)
    for L in range(center - radius, center + radius + 1, step):
        a0 = max(0, -L); a1 = min(len(ref), len(y) - L)
        if a1 - a0 < ENV_HZ * 3: continue
        r = sum(map(lambda i: ref[i] * y[i + L], range(a0, a1))) / (a1 - a0)
        if r > best[1]: best = (L, r)
    return best

def sync(clips, job):
    """Return start offset (s) into each clip for common time 0, plus per-clip method."""
    ref_i = next((i for i, c in enumerate(clips) if c.get("audio")), None)
    s = [0.0] * len(clips); how = ["ref"] * len(clips)
    tc_ok = all(c.get("tcs") is not None for c in clips)
    if tc_ok:
        r0 = clips[ref_i if ref_i is not None else 0]["tcs"]
        s = [r0 - c["tcs"] for c in clips]  # clip time = ref time + (ref_tc - clip_tc)
        how = ["timecode"] * len(clips)
    if ref_i is not None and len(clips) > 1:
        how[ref_i] = "ref"; s[ref_i] = 0.0
        ref_env = envelope(sibling(clips[ref_i]["path"], True))
        for i, c in enumerate(clips):
            if i == ref_i or not c.get("audio"): continue
            job["msg"] = f"Syncing Cam {c['cam']} by sound"
            y = envelope(sibling(c["path"], True))
            if tc_ok:
                L0 = int(round(s[i] * ENV_HZ)); L, r = best_lag(ref_env, y, L0, ENV_HZ * 1)
            else:
                Lc, _ = best_lag(ref_env[::5], y[::5], 0, ENV_HZ * 60 // 5); L, r = best_lag(ref_env, y, Lc * 5, 30)
            if r >= 0.25:
                # refine to sub-step by parabola
                s[i] = L / ENV_HZ; how[i] = "audio"
            elif not tc_ok: how[i] = "unsynced"
            job["progress"] = 0.05 + 0.25 * (i + 1) / len(clips)
    return s, how

def sibling(path, want_h264):
    """Same clip in the day's other proxy folder (H.264 for light previews, ProRes for exports), if it exists."""
    rel = os.path.relpath(path, root()).split(os.sep)
    if len(rel) < 5: return path
    day, pf = rel[0], rel[1]
    if ("h264" in pf.lower()) == want_h264: return path
    stem = os.path.splitext(rel[-1])[0]
    for n in os.listdir(os.path.join(root(), day)):
        if n == pf or not re.search(r"proxy|h264", n, re.I) or ("h264" in n.lower()) != want_h264: continue
        hit = glob.glob(os.path.join(root(), day, n, *rel[2:-1], stem + ".*"))
        if hit: return hit[0]
    return path

# ---------------------------------------------------------------- prepare (sync + preview grid)
def take_layout(n):
    cols = 1 if n == 1 else 2 if n <= 4 else 4
    return cols, math.ceil(n / cols)

def prepare(job, day, take_id, force=False):
    td = os.path.join(CACHE, "takes", re.sub(r"[^\w.-]+", "_", take_id)); os.makedirs(td, exist_ok=True)
    man_p = os.path.join(td, "take.json")
    if not force and os.path.isfile(man_p) and os.path.isfile(os.path.join(td, "preview.mp4")):
        return json.load(open(man_p))
    dt = day_takes_cached(day)
    if not dt: raise RuntimeError("Scan the day first")
    t = next((x for x in dt["takes"] if x["id"] == take_id), None)
    if not t: raise RuntimeError("Take not found; rescan the day")
    man = prepare_paths(job, day, take_id, [(c["cam"], os.path.join(root(), c["rel"])) for c in t["clips"]], force)
    man["title"] = t["ref"][:8]; return man

def prepare_paths(job, day, take_id, cam_paths, force=False):
    td = os.path.join(CACHE, "takes", re.sub(r"[^\w.-]+", "_", take_id)); os.makedirs(td, exist_ok=True)
    man_p = os.path.join(td, "take.json")
    if not force and os.path.isfile(man_p) and os.path.isfile(os.path.join(td, "preview.mp4")):
        old = json.load(open(man_p))
        if sorted(c["cam"] for c in old["cams"]) == sorted(c for c, _ in cam_paths) or set(c for c, _ in cam_paths) <= set(c["cam"] for c in old["cams"]) | set(old.get("excluded", [])):
            return old
    clips = []
    for cam, p in cam_paths:
        info = probe(p); info.update(path=p, cam=cam, name=os.path.splitext(os.path.basename(p))[0]); clips.append(info)
    job["msg"] = "Syncing"; s, how = sync(clips, job)
    # action cams (GoPro / 360) only join the grid when their sound confirms the sync
    excluded = [c["cam"] for c, h in zip(clips, how) if len(c["cam"]) > 1 and h not in ("audio", "ref")]
    keep = [i for i, c in enumerate(clips) if c["cam"] not in excluded]
    clips, s, how = [clips[i] for i in keep], [s[i] for i in keep], [how[i] for i in keep]
    T0 = max(0.0, max(-x for x in s)); T1 = min(c["dur"] - x for c, x in zip(clips, s)); dur = T1 - T0
    if dur < 2:  # cameras don't overlap: play each from its start
        s, how, T0, dur = [0.0] * len(clips), ["unsynced"] * len(clips), 0.0, min(c["dur"] for c in clips)
    starts = [x + T0 for x in s]
    n = len(clips); cols, rows = take_layout(n); tw, th = (1280, 720) if n == 1 else (640, 360)
    cmd = []
    for c, st in zip(clips, starts): cmd += ["-hwaccel", "videotoolbox", "-ss", f"{st:.3f}", "-t", f"{dur:.3f}", "-i", sibling(c["path"], True)]
    fl = [f"[{k}:v]fps=25,scale={tw}:{th}:flags=bilinear,setsar=1[v{k}]" for k in range(n)]
    tot = cols * rows
    fl += [f"color=black:s={tw}x{th}:r=25:d={dur:.3f}[v{k}]" for k in range(n, tot)]
    fl.append("[v0]null[g]" if tot == 1 else "".join(f"[v{k}]" for k in range(tot)) + "xstack=inputs=%d:layout=%s[g]" % (
        tot, "|".join(f"{(k % cols) * tw}_{(k // cols) * th}" for k in range(tot))))
    ref_i = next((i for i, c in enumerate(clips) if c.get("audio")), None)
    amap = ["-map", f"{ref_i}:a:0", "-ac", "2", "-c:a", "aac", "-b:a", "128k"] if ref_i is not None else []
    job["msg"] = "Building preview"
    tmp = os.path.join(td, "preview.tmp.mp4")
    ff(cmd + ["-filter_complex", ";".join(fl), "-map", "[g]", *amap, "-c:v", "h264_videotoolbox", "-b:v", "8M",
              "-g", "12", "-pix_fmt", "yuv420p", "-movflags", "+faststart", tmp], job, dur, 0.3, 1.0)
    os.replace(tmp, os.path.join(td, "preview.mp4"))
    man = {"id": take_id, "day": day, "title": take_id.split("__")[-1], "excluded": excluded, "dur": round(dur, 3), "cols": cols, "rows": rows,
           "src": "/cache/takes/" + os.path.basename(td) + "/preview.mp4?v=" + str(int(time.time())),
           "ref": ref_i if ref_i is not None else 0,
           "cams": [{"cam": c["cam"], "clip": c["name"], "label": f"Cam {c['cam']}  {c['name'][-4:]}", "rel": os.path.relpath(c["path"], root()),
                     "start": round(st, 3), "sync": h, "w": c.get("w"), "h": c.get("h")} for c, st, h in zip(clips, starts, how)]}
    json.dump(man, open(man_p, "w"), indent=1)
    return man

# ---------------------------------------------------------------- exports
def safe(s): return re.sub(r"[^\w.+-]+", "_", str(s)).strip("_")[:60]
def tcs(sec):
    f = int(round(sec * 25)); return f"{f // 90000:02d}{f // 1500 % 60:02d}{f // 25 % 60:02d}{f % 25:02d}"
def vcodec(fmt, w):
    if fmt == "prores": return ["-c:v", "prores_videotoolbox", "-profile:v", "hq", "-pix_fmt", "p210le"], ".mov", ["-c:a", "pcm_s24le"]
    return ["-c:v", "h264_videotoolbox", "-b:v", "50M" if (w or 0) > 2000 else "20M", "-pix_fmt", "yuv420p", "-tag:v", "avc1"], ".mp4", ["-c:a", "aac", "-b:a", "320k"]
def esc(t): return t.replace("\\", "\\\\").replace(":", "\\:").replace("'", "’").replace(",", "\\,").replace("%", "\\%")

def export(job, req):
    man = json.load(open(os.path.join(CACHE, "takes", re.sub(r"[^\w.-]+", "_", req["take"]), "take.json")))
    cams = {c["cam"]: c for c in man["cams"]}; ref = man["cams"][man.get("ref", 0)]
    a, b = float(req["in"]), float(req["out"]); d = b - a
    if d <= 0: raise RuntimeError("Out must be after in")
    scene = safe(req.get("scene") or man["day"])
    od = os.path.join(EXPORTS, f"Sc{scene}" if req.get("scene") else man["day"], safe(man["title"])); os.makedirs(od, exist_ok=True)
    stamp = f"{tcs(a)}-{tcs(b)}"; fmt = req.get("format", "h264"); outs = []
    def P(c): return sibling(os.path.join(root(), c["rel"]), False)
    if req["type"] == "cams":
        sel = req["cams"]
        for k, cam in enumerate(sel):
            c = cams[cam]; vc, ext, ac = vcodec(fmt, c.get("w"))
            o = os.path.join(od, f"cam{cam}_{c['clip']}_{stamp}{ext}")
            job["msg"] = f"Cam {cam}"
            ff(["-ss", f"{c['start'] + a:.3f}", "-i", P(c), "-t", f"{d:.3f}", "-map", "0:v:0", "-map", "0:a:0?", *vc, *ac,
                "-movflags", "+faststart", o], job, d, k / len(sel), (k + 1) / len(sel))
            outs.append(o)
    elif req["type"] == "sheet":
        sel = [cams[x] for x in req["cams"]]; cols, rows = int(req["cols"]), int(req["rows"]); W = 3840
        pw = W // cols // 2 * 2; ph = round(pw * 9 / 16 / 2) * 2; tb = round(W * 0.03 / 2) * 2 if req.get("title") else 0
        ins, fl = [], []
        for k, c in enumerate(sel):
            ins += ["-ss", f"{c['start'] + a:.3f}", "-t", f"{d:.3f}", "-i", P(c)]
            lab = req.get("labels", {}).get(c["cam"], "") if isinstance(req.get("labels"), dict) else ""
            dt = (f",drawtext=fontfile={FONT}:text='{esc(lab)}':x={round(pw * .012)}:y={round(pw * .012)}:fontsize={max(14, round(pw * .032))}"
                  f":fontcolor=0xffd400:box=1:boxcolor=black@0.65:boxborderw={max(4, round(pw * .008))}") if lab else ""
            fl.append(f"[{k}:v]fps=25,scale={pw}:{ph}:flags=lanczos,setsar=1{dt}[v{k}]")
        tot = cols * rows
        fl += [f"color=black:s={pw}x{ph}:r=25:d={d:.3f}[v{k}]" for k in range(len(sel), tot)]
        fl.append("[v0]null[g]" if tot == 1 else "".join(f"[v{k}]" for k in range(tot)) + "xstack=inputs=%d:layout=%s[g]" % (
            tot, "|".join(f"{(k % cols) * pw}_{(k // cols) * ph}" for k in range(tot))))
        if tb:
            tt = esc(req.get("titleText") or f"{man['day']}  {man['title']}")
            fl.append(f"[g]pad=iw:ih+{tb}:0:{tb}:black,drawtext=fontfile={FONT}:text='{tt}':x={tb // 2}:y=({tb}-th)/2:fontsize={round(tb * .55)}:fontcolor=white[o]")
        else: fl.append("[g]null[o]")
        vc, ext, ac = vcodec(fmt, W); amap = []
        if req.get("audio"):
            ins += ["-ss", f"{ref['start'] + a:.3f}", "-t", f"{d:.3f}", "-i", P(ref)]; amap = ["-map", f"{len(sel)}:a:0?", *ac]
        o = os.path.join(od, f"sheet_{''.join(c['cam'] for c in sel)}_{stamp}{ext}")
        job["msg"] = "Building sheet"
        ff(ins + ["-filter_complex", ";".join(fl), "-map", "[o]", *amap, *vc, "-movflags", "+faststart", o], job, d)
        outs.append(o)
    elif req["type"] == "cut":
        cuts = req["cuts"]; big = any((cams[x["cam"]].get("w") or 0) > 2000 for x in cuts); W, H = (3840, 2160) if big else (1920, 1080)
        ins, fl = [], []
        for k, x in enumerate(cuts):
            c = cams[x["cam"]]; ins += ["-ss", f"{c['start'] + x['t_in']:.3f}", "-t", f"{x['t_out'] - x['t_in']:.3f}", "-i", P(c)]
            fl.append(f"[{k}:v]fps=25,scale={W}:{H}:flags=lanczos,setsar=1[v{k}]")
        n = len(cuts); a0, a1 = cuts[0]["t_in"], cuts[-1]["t_out"]
        ins += ["-ss", f"{ref['start'] + a0:.3f}", "-t", f"{a1 - a0:.3f}", "-i", P(ref)]
        fl.append("".join(f"[v{k}]" for k in range(n)) + f"concat=n={n}:v=1:a=0[v]")
        vc, ext, ac = vcodec(fmt, W)
        o = os.path.join(od, f"livecut_{''.join(x['cam'] for x in cuts)[:12]}_{tcs(a0)}-{tcs(a1)}{ext}")
        job["msg"] = "Rendering cut"
        ff(ins + ["-filter_complex", ";".join(fl), "-map", "[v]", "-map", f"{n}:a:0?", *vc, *ac, "-shortest", "-movflags", "+faststart", o], job, a1 - a0)
        outs.append(o)
    else: raise RuntimeError("Unknown export type")
    return {"files": outs, "folder": od}

def still(job, a):
    """Frame at take time t: one 3840-wide PNG per camera (upscaled when the source is smaller), or one 4K sheet frame."""
    man = json.load(open(os.path.join(CACHE, "takes", re.sub(r"[^\w.-]+", "_", a["take"]), "take.json")))
    cams = {c["cam"]: c for c in man["cams"]}; t = float(a["t"])
    od = os.path.join(EXPORTS, f"Sc{safe(a['scene'])}" if a.get("scene") else man["day"], safe(man["id"].split("__")[-1]), "stills")
    os.makedirs(od, exist_ok=True); stamp = tcs(t); files, notes = [], []
    if a.get("sheet"):
        req = dict(a["sheet"], take=a["take"], type="sheet", audio=False, scene=a.get("scene"), format="h264")
        req["in"], req["out"] = t, t + 0.2
        src = export(job, req)["files"][0]
        png = os.path.join(od, f"sheet_{''.join(req['cams'])}_{stamp}.png")
        subprocess.check_call([FFMPEG, "-v", "error", "-y", "-nostdin", "-i", src, "-frames:v", "1", png]); os.remove(src)
        files.append(png)
    else:
        for k, cam in enumerate(a["cams"]):
            c = cams[cam]; srcp = sibling(os.path.join(root(), c["rel"]), False)
            w = c.get("w") or 1920
            if w < 3840: notes.append(f"Cam {cam} source is {w} wide, upscaled to 3840")
            png = os.path.join(od, f"cam{cam}_{c['clip'][:8]}_{stamp}.png"); job["msg"] = f"Cam {cam}"
            subprocess.check_call([FFMPEG, "-v", "error", "-y", "-nostdin", "-ss", f"{c['start'] + t:.3f}", "-i", srcp, "-frames:v", "1",
                                   "-vf", "scale=3840:-2:flags=lanczos", "-pix_fmt", "rgb24", png])
            files.append(png); job["progress"] = (k + 1) / len(a["cams"])
    return {"files": files, "folder": od, "notes": notes}

# ---------------------------------------------------------------- HTTP
class H(http.server.SimpleHTTPRequestHandler):
    def log_message(self, *a): pass
    def j(self, obj, code=200):
        b = json.dumps(obj).encode(); self.send_response(code); self.send_header("Content-Type", "application/json")
        self.send_header("Cache-Control", "no-store"); self.send_header("Content-Length", str(len(b))); self.end_headers(); self.wfile.write(b)
    def body(self):
        n = int(self.headers.get("Content-Length") or 0); return json.loads(self.rfile.read(n) or b"{}")
    def file(self, path, ctype=None):
        if not os.path.isfile(path): return self.j({"error": "not found"}, 404)
        size = os.path.getsize(path); ctype = ctype or self.guess_type(path); rng = self.headers.get("Range")
        a, b = 0, size - 1
        m = re.match(r"bytes=(\d*)-(\d*)", rng or "")
        if m:
            if m.group(1): a = int(m.group(1)); b = int(m.group(2)) if m.group(2) else size - 1
            else: a = max(0, size - int(m.group(2)))
            b = min(b, size - 1); self.send_response(206); self.send_header("Content-Range", f"bytes {a}-{b}/{size}")
        else: self.send_response(200)
        self.send_header("Content-Type", ctype); self.send_header("Accept-Ranges", "bytes"); self.send_header("Content-Length", str(b - a + 1))
        self.end_headers()
        with open(path, "rb") as f:
            f.seek(a); left = b - a + 1
            try:
                while left > 0:
                    buf = f.read(min(1 << 16, left))
                    if not buf: break
                    self.wfile.write(buf); left -= len(buf)
            except (BrokenPipeError, ConnectionResetError): pass

    def do_GET(self):
        u = urllib.parse.urlparse(self.path); q = dict(urllib.parse.parse_qsl(u.query)); p = u.path
        try:
            if p == "/" or p == "/index.html": return self.file(os.path.join(APP, "index.html"), "text/html; charset=utf-8")
            if p == "/api/status":
                r = root(); ok = os.path.isdir(r)
                return self.j({"version": VERSION, "root": r, "mounted": ok, "ffmpeg": bool(shutil.which(FFMPEG) or os.path.isfile(FFMPEG)), "exports": EXPORTS,
                               "days": days() if ok else []})
            if p == "/api/scenes":
                qq = (q.get("q") or "").strip().upper().replace("SC", "").strip()
                res = scenes(); tg = tags()
                if qq:
                    exact = [s for s in res if qq in s["tokens"]]
                    pref = [s for s in res if s not in exact and any(t.startswith(qq) for t in s["tokens"])]
                    res = exact + pref
                return self.j({"scenes": res[:80], "tags": {k: sorted(v) for k, v in tg.items() if not qq or k.startswith(qq)}})
            if p == "/api/scene": return self.j(scene_view(q.get("q", "")))
            if p == "/api/scenes_all": return self.j({"scenes": scenes_all()})
            if p == "/api/day":
                d = q["day"]; dt = day_takes_cached(d)
                return self.j(dt or {"day": d, "takes": None})
            if p == "/api/job":
                job = JOBS.get(q.get("id")); return self.j(job or {"error": "no job"}, 200 if job else 404)
            if p == "/api/thumb":
                rel = q["rel"]; src = os.path.join(root(), rel)
                if not under(root(), src): return self.j({"error": "bad path"}, 400)
                t = float(q.get("t", "2")); key = re.sub(r"[^\w.-]+", "_", rel) + f"_{t:.1f}.jpg"
                out = os.path.join(CACHE, "thumbs", key); os.makedirs(os.path.dirname(out), exist_ok=True)
                if not os.path.isfile(out):
                    subprocess.run([FFMPEG, "-v", "error", "-nostdin", "-y", "-ss", f"{t:.2f}", "-i", src, "-frames:v", "1",
                                    "-vf", "scale=320:-2", "-q:v", "5", out], timeout=60)
                return self.file(out, "image/jpeg")
            if p == "/api/serverfile":
                src = os.path.join(root(), q["rel"])
                if not under(root(), src): return self.j({"error": "bad path"}, 400)
                return self.file(src)
            if p.startswith("/cache/"):
                src = os.path.join(CACHE, urllib.parse.unquote(p[len("/cache/"):]))
                if not under(CACHE, src): return self.j({"error": "bad path"}, 400)
                return self.file(src)
            return self.j({"error": "not found"}, 404)
        except Exception as e:
            traceback.print_exc(); return self.j({"error": str(e)}, 500)

    def do_POST(self):
        p = urllib.parse.urlparse(self.path).path
        try:
            b = self.body()
            if p == "/api/root":
                r = os.path.expanduser(b["root"])
                if not os.path.isdir(r): return self.j({"error": "That folder isn't there. Is the server mounted?"}, 400)
                CFG["root"] = r; save_cfg(); SCENES_CACHE["t"] = 0; return self.j({"root": r})
            if p == "/api/scan": return self.j(new_job("scan", scan_day, b["day"]))
            if p == "/api/prepare": return self.j(new_job("prepare", prepare, b["day"], b["take"], bool(b.get("force"))))
            if p == "/api/prepare_log": return self.j(new_job("prepare", prepare_log, b["day"], b["clips"], b.get("labels", {}), b.get("title", ""), bool(b.get("force"))))
            if p == "/api/readlogs": return self.j(new_job("logs", read_logs, b["day"]))
            if p == "/api/export": return self.j(new_job("export", export, b))
            if p == "/api/still": return self.j(new_job("still", still, b))
            if p == "/api/tag": set_tag(b["scene"], b["clip"], bool(b.get("on", True))); return self.j({"ok": True})
            if p == "/api/reveal":
                path = b["path"]
                if under(EXPORTS, path): subprocess.run(["open", "-R", path])
                return self.j({"ok": True})
            if p == "/api/openexports": subprocess.run(["open", EXPORTS]); return self.j({"ok": True})
            return self.j({"error": "not found"}, 404)
        except Exception as e:
            traceback.print_exc(); return self.j({"error": str(e)}, 500)

class Server(socketserver.ThreadingMixIn, http.server.HTTPServer):
    daemon_threads = True; allow_reuse_address = True

if __name__ == "__main__":
    import gate; gate.require()
    srv = Server(("127.0.0.1", PORT), H)
    threading.Thread(target=lambda: os.path.isdir(root()) and scenes_all(), daemon=True).start()  # warm the scene list
    print(f"BB Takes {VERSION} running at http://127.0.0.1:{PORT}  (server root: {root()})", flush=True)
    try: srv.serve_forever()
    except KeyboardInterrupt: pass
