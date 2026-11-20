#!/bin/bash
# BB Takes setup / health check. Safe to run any time. Prints what's ready and what to fix.
# Usage: bash scripts/setup.sh          (from the BB Takes folder)
cd "$(dirname "$0")/.." || exit 1
ok() { printf "  \033[32m✓\033[0m %s\n" "$1"; }
warn() { printf "  \033[33m!\033[0m %s\n" "$1"; }
bad() { printf "  \033[31m✗\033[0m %s\n" "$1"; BLOCK=1; }
BLOCK=0
echo "BB Takes $(cat VERSION 2>/dev/null) setup check"

# 1. Mac + chip
if [ "$(uname)" != "Darwin" ]; then bad "BB Takes runs on macOS only."; fi
ARCH=$(uname -m); [ "$ARCH" = "arm64" ] && ok "Apple Silicon Mac" || warn "Intel Mac: the bundled ffmpeg won't run; ffmpeg from your PATH is needed."

# 2. Python
if /usr/bin/python3 -c 'import sys; assert sys.version_info >= (3, 9)' 2>/dev/null; then ok "Python $(/usr/bin/python3 -c 'import sys; print(sys.version.split()[0])')"
else bad "Python 3 missing. Run:  xcode-select --install   then run this again."; fi

# 3. Unblock bundled tools (downloads get quarantined by macOS)
xattr -dr com.apple.quarantine . 2>/dev/null
chmod +x "Start BB Takes.command" bin/ffmpeg bin/ffprobe bin/logocr scripts/*.sh 2>/dev/null

# 4. ffmpeg / ffprobe
for t in ffmpeg ffprobe; do
  if [ -x "bin/$t" ] && "bin/$t" -version >/dev/null 2>&1; then ok "$t (bundled)"
  elif command -v "$t" >/dev/null 2>&1; then ok "$t ($(command -v $t))"
  else bad "$t not found. Copy bin/ from a BB Takes release zip, or install it (brew install ffmpeg)."; fi
done

# 5. Log sheet reader
if [ -x bin/logocr ]; then ok "log sheet reader"
elif command -v swiftc >/dev/null 2>&1; then
  echo "  … building the log sheet reader"; swiftc -O src/logocr.swift -o bin/logocr 2>/dev/null && ok "log sheet reader (built)" || warn "Couldn't build the log sheet reader; pre-read log sheets still work."
else warn "Log sheet reader missing (needs Apple command line tools). Pre-read log sheets still work."; fi

# 6. Shoot server
ROOT=$(/usr/bin/python3 -c 'import json,os; p=os.path.expanduser("~/Library/Caches/BB Takes/config.json"); print(json.load(open(p)).get("root","")) if os.path.isfile(p) else print("")' 2>/dev/null)
[ -z "$ROOT" ] && ROOT=/Volumes/BB_Shoot_Data
if [ -d "$ROOT" ]; then ok "shoot server at $ROOT"
else warn "Shoot server not mounted at $ROOT. Connect in Finder (Cmd+K), or set the folder in the app (Server folder…)."; fi

# 7. Folders
mkdir -p "$HOME/Library/Caches/BB Takes" "$HOME/Movies/BB Takes Exports" && ok "exports go to ~/Movies/BB Takes Exports"

echo
if [ $BLOCK = 0 ]; then echo "Ready. Start it with:  open \"Start BB Takes.command\"   (or double-click it)"; else echo "Fix the ✗ items above, then run this again."; fi
exit $BLOCK
