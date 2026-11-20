#!/usr/bin/env python3
"""BB Takes password gate.

The tool stays locked until someone enters the team password. A correct password unlocks this Mac
for 12 hours (stored in ~/Library/Caches/BB Takes/unlock.json). Only a salted hash is kept here.

  python3 server/gate.py status          -> prints "unlocked" / "locked", exit 0 / 1
  python3 server/gate.py unlock <pw>     -> exit 0 if correct
  python3 server/gate.py lock            -> lock again now
  python3 server/gate.py prompt          -> ask in the terminal (used by Start BB Takes.command)
"""
import getpass, hashlib, json, os, sys, time

SALT = "bb-takes/gate/v1"
HASH = "1a573df9b11123f14d1fe366a27ce3546c4e4da82e1817091afd7e7e1636ee68"
HOURS = 12
PATH = os.path.expanduser("~/Library/Caches/BB Takes/unlock.json")

def _h(pw): return hashlib.sha256((SALT + ":" + pw.strip()).encode()).hexdigest()

def unlocked():
    try: return json.load(open(PATH)).get("until", 0) > time.time()
    except Exception: return False

def unlock(pw):
    if _h(pw) != HASH: return False
    os.makedirs(os.path.dirname(PATH), exist_ok=True)
    json.dump({"until": time.time() + HOURS * 3600}, open(PATH, "w")); return True

def lock():
    try: os.remove(PATH)
    except OSError: pass

def require():
    """Call at the start of any entry point. Exits with a clear message when locked."""
    if not unlocked():
        print("BB Takes is locked. Ask the user for the BB Takes password, then run:\n"
              "  /usr/bin/python3 server/gate.py unlock <password>", file=sys.stderr)
        sys.exit(3)

if __name__ == "__main__":
    cmd = sys.argv[1] if len(sys.argv) > 1 else "status"
    if cmd == "status":
        print("unlocked" if unlocked() else "locked"); sys.exit(0 if unlocked() else 1)
    if cmd == "unlock":
        ok = unlock(sys.argv[2] if len(sys.argv) > 2 else "")
        print(f"unlocked for {HOURS} hours" if ok else "wrong password"); sys.exit(0 if ok else 1)
    if cmd == "lock":
        lock(); print("locked"); sys.exit(0)
    if cmd == "prompt":
        if unlocked(): sys.exit(0)
        for _ in range(3):
            if unlock(getpass.getpass("BB Takes password: ")): print(f"Unlocked for {HOURS} hours."); sys.exit(0)
            print("Wrong password.")
        sys.exit(1)
    print(__doc__); sys.exit(2)
