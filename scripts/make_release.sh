#!/bin/bash
# Build the shareable zip: everything in git at HEAD + the bin/ tools. Output: dist/BB_Takes_v<VERSION>.zip
# Usage: bash scripts/make_release.sh
set -e
cd "$(dirname "$0")/.."
V=$(cat VERSION); OUT="dist/BB_Takes_v$V.zip"; TMP=$(mktemp -d)
[ -n "$(git status --porcelain)" ] && echo "Note: uncommitted changes are NOT in the zip (it is built from the last commit)."
for t in ffmpeg ffprobe logocr; do [ -x "bin/$t" ] || { echo "bin/$t missing: put it in bin/ first (see bin/README.md)"; exit 1; }; done
git archive --format=tar --prefix="BB_Takes/" HEAD | tar -x -C "$TMP"
cp bin/ffmpeg bin/ffprobe bin/logocr "$TMP/BB_Takes/bin/"
mkdir -p dist; rm -f "$OUT"
(cd "$TMP" && ditto -c -k --norsrc --noextattr --keepParent BB_Takes "$OLDPWD/$OUT")
rm -rf "$TMP"; ls -la "$OUT"
echo "To publish it for the team:  gh release create v$V \"$OUT\" --title \"BB Takes $V\" --notes-file CHANGELOG.md"
