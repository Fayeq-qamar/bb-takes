# Setting up BB Takes

## What you need
- An **Apple Silicon Mac** (M1 or newer). Intel Macs work only with ffmpeg installed separately.
- **Python 3**, which comes with Apple's command line tools. If you've never installed them, run
  `xcode-select --install` in Terminal once.
- The **shoot server** mounted (Finder › Go › Connect to Server, or Cmd+K). It normally shows as `/Volumes/BB_Shoot_Data`.
- About 5 GB free for previews (they build up as you open takes; safe to delete any time).

Nothing else gets installed. ffmpeg comes inside the zip.

## The password
BB Takes is locked with a team password (ask the BB Takes maintainer for it). Claude asks you for it when you
start; double-clicking `Start BB Takes.command` asks in its window. One correct entry unlocks that Mac for 12 hours.
To lock again early: `/usr/bin/python3 server/gate.py lock`.

## Route A: with Claude (recommended)
1. Unzip `BB_Takes_vX.Y.Z.zip` somewhere you'll find it (e.g. `~/Documents/BB_Takes`).
2. Open that folder in Claude Code (desktop app: open folder; terminal: `cd` into it and run `claude`).
3. Say **"Set up BB Takes for me."** Claude runs the setup check, fixes what it can, tells you anything it
   can't (like mounting the server), and starts the app.

## Route B: by hand
1. Unzip it.
2. In Terminal: `cd` into the folder, then `bash scripts/setup.sh`. Fix anything marked ✗ (it says how).
3. Double-click **`Start BB Takes.command`**. The first time, macOS may block it: right-click › Open › Open.
4. Your browser opens at http://127.0.0.1:8765. Keep the small Terminal window open while you work; close it to stop.

## Route C: from GitHub (people with repo access)
```
gh repo clone <owner>/bb-takes ~/Developer/bb-takes
cd ~/Developer/bb-takes && bash scripts/setup.sh
```
A clone has no ffmpeg in `bin/` (it's too big for git). Setup uses ffmpeg from your PATH if you have it;
otherwise copy `bin/ffmpeg` and `bin/ffprobe` from any release zip (or `gh release download --pattern '*.zip'`).
Setup builds the log sheet reader itself if Apple's command line tools are installed.

## Where things live
| What | Where |
|---|---|
| The tool | wherever you unzipped it |
| Exports, sheets, stills | `~/Movies/BB Takes Exports/Sc<scene>/<take>/` |
| Previews, day index, your tags, settings | `~/Library/Caches/BB Takes/` (safe to delete; rebuilds) |

Updating the tool (replacing its folder) never touches your exports or previews.

## Problems
| Symptom | Fix |
|---|---|
| "Server not found" in the app | Mount the server in Finder. If it mounts under another name, use **Server folder…** in the app. |
| `Python 3 missing` | `xcode-select --install`, then run setup again. |
| macOS says the app or ffmpeg "can't be opened" | Run `bash scripts/setup.sh` (removes the download block), or right-click › Open. |
| Port 8765 busy | Start with another port: `BBTAKES_PORT=8766 /usr/bin/python3 server/bbtakes.py` |
| A day takes long to open the first time | Normal: it reads every clip once (about 2 minutes), then it's instant. |
