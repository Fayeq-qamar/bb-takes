#!/bin/bash
# Update BB Takes. Your previews, tags and exports live outside this folder, so updating never loses them.
cd "$(dirname "$0")/.." || exit 1
OLD=$(cat VERSION)
if [ -d .git ]; then
  git pull --ff-only && echo "Updated: $OLD -> $(cat VERSION)" && bash scripts/setup.sh
else
  echo "This copy came from a zip (no git). To update:"
  echo "  1. Get the newest BB_Takes_v*.zip from whoever maintains BB Takes."
  echo "  2. Unzip it and replace this BB_Takes folder with the new one."
  echo "  3. Run: bash scripts/setup.sh"
  echo "Your previews, tags and exports are kept (they live in ~/Library/Caches/BB Takes and ~/Movies/BB Takes Exports)."
fi
