# Changelog

## 1.1.0 (2026-11-20)
- Team password gate: Claude asks for the password before using BB Takes; the app, command line and setup stay
  locked until it's entered (unlocks the Mac for 12 hours). Only a hash of the password is stored.
- Strip of every scene on the server under the search box (bright = log sheet shots, dim = folder only).
- Scenes with no readable log sheet: "List <day>'s takes" right in the scene panel.
- Scene numbers with leading zeros ("7" finds Scene_07); "Phase 01+02" no longer read as scene 02.
- Links straight to a scene: http://127.0.0.1:8765/#217

## 1.0.0 (2026-11-20)
First release for the BB team.
- Find any scene on the shoot server; shots, coverage and ✓ OK takes read from the continuity log sheets
  (all shoot days pre-read).
- Takes synced by sound (timecode as cross-check); log clip-number drift corrected automatically.
- Viewer, Switcher (live cut with record/playback), Video sheet (4K, editable labels and title), Still 4K.
- Exports: camera files, sheets, cuts; H.264 or ProRes 422 HQ.
- Command line (`server/bbt_cli.py`) and Claude instructions (`CLAUDE.md`, `bb-takes` skill).
