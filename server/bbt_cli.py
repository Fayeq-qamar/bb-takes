#!/usr/bin/env python3
"""BB Takes command line: everything the web app does, for Claude (or you) to run directly.

Usage (run from the repo folder with system Python 3.9+):
  python3 server/bbt_cli.py status
  python3 server/bbt_cli.py scene 217                 shots, takes, OK marks, camera coverage for a scene
  python3 server/bbt_cli.py prep  '<json>'|@file      sync a take, build its preview  {day, clips:{cam:stem}, labels, title}
  python3 server/bbt_cli.py day   Day_04              group every clip of a day into takes by timecode (slow first time)
  python3 server/bbt_cli.py export '<json>'|@file     {take, type: cams|sheet|cut, in, out, ...}  (take must be prepped)
  python3 server/bbt_cli.py still  '<json>'|@file     {take, t, cams:[..]} or {take, t, sheet:{cams, cols, rows, labels, title, titleText}}
  python3 server/bbt_cli.py readlogs Day_04           re-read a day's log sheets (after new pages land on the server)

Every command prints one JSON object on stdout (progress goes to stderr).
Times (in, out, t) are seconds from the start of the synced take.
"""
import json, os, re, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import bbtakes as B

class Job(dict):
    def __init__(self): super().__init__(progress=0.0, msg="")
    def update(self, *a, **k):
        super().update(*a, **k)
        if "msg" in k: print(f"... {k['msg']}", file=sys.stderr, flush=True)

def key_of(take_id): return re.sub(r"[^A-Za-z0-9_.-]+", "_", take_id)
def out(obj): print(json.dumps(obj, indent=1))

def arg_json(s):
    if s.startswith("@"): return json.load(open(s[1:]))
    if s == "-": return json.load(sys.stdin)
    return json.loads(s)

def status(_):
    r = B.root()
    out({"version": B.VERSION, "server_root": r, "server_mounted": os.path.isdir(r), "ffmpeg": B.FFMPEG, "ffprobe": B.FFPROBE,
         "logocr": os.path.isfile(os.path.join(B.HERE, "bin", "logocr")), "cache": B.CACHE, "exports": B.EXPORTS,
         "days": [d["day"] for d in B.days()] if os.path.isdir(r) else []})

def scene(q):
    v = B.scene_view(q)
    for d in v["days"]:
        for s in d.get("shots", []):
            for t in s["takes"]:
                t["take_id"] = f"{d['day']}__{t['primary']}"
    out(v)

def prep(a):
    man = B.prepare_log(Job(), a["day"], dict(a["clips"]), a.get("labels", {}), a.get("title", ""), bool(a.get("force")))
    out({"take": man["id"], "title": man.get("title", ""), "dur": man["dur"], "preview": os.path.join(B.CACHE, "takes", key_of(man["id"]), "preview.mp4"),
         "cams": [{"cam": c["cam"], "clip": c["clip"], "start": c["start"], "sync": c["sync"], "desc": c.get("desc", "")} for c in man["cams"]],
         "left_out": man.get("excluded", []), "log_vs_footage": man.get("notes", [])})

def day(d):
    r = B.scan_day(Job(), d)
    out({"day": d, "takes": [{"primary": t["ref"][:8], "start_tc": B.tcs(t["start"]) if t["start"] is not None else None, "dur": t["dur"], "cams": t["cams"]}
                             for t in r["takes"] if t["dur"] >= 8]})

def export(a):
    res = B.export(Job(), a); out(res)

def still(a):
    out(B.still(Job(), a))

def readlogs(d):
    out(B.read_logs(Job(), d))

if __name__ == "__main__":
    if len(sys.argv) < 2 or sys.argv[1] in ("-h", "--help", "help"): print(__doc__); sys.exit(0)
    cmd = sys.argv[1]; arg = sys.argv[2] if len(sys.argv) > 2 else ""
    plain = {"status": status, "scene": scene, "day": day, "readlogs": readlogs}
    js = {"prep": prep, "export": export, "still": still}
    if cmd in plain: plain[cmd](arg)
    elif cmd in js: js[cmd](arg_json(arg))
    else: print(__doc__); sys.exit(2)
