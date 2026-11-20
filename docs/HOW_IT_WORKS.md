# How BB Takes works

## The shoot server, as BB Takes sees it
```
/Volumes/BB_Shoot_Data/
  Day_01 … Day_05, DAY_06 … DAY_15/
    <Location>/Sc 217 _Int_Day/Project manger/Log Sheet/*.png   ← continuity log sheet screenshots
    <Location>/Scene_16/…                                       ← (later days name folders Scene_NN)
    Proxy_Day_04/ or H264_DAY_04/ or Proxy_Day_06_H264/
      Cam_A … Cam_H, GoPro_01 …/Card_A017/A017C013_261103CB.mov
```
- Days 1–4: 1920×1080 proxies (Day 04 has both ProRes and H.264). Day 05 onward: 3840×2160 H.264.
- All cameras carry timecode; clip names are `<cam letter><card><C clip>`.

## 1. Log sheets → shots and OK takes (`server/logsheets.py`)
- Every log page is read with Apple's built-in text recognition (`bin/logocr`, from `src/logocr.swift`).
- Columns are found from the data itself: card numbers (`A017`) sit left of the densest column of clip numbers
  (`C013`); the OK column is to its right; shot numbers come from the SHOT column or the "SHOT 3 …" note.
- Pages are ordered by the capture time in the screenshot file name (printed page numbers are unreliable).
- Result per row: scene, shot, camera, card, clips, OK clips, coverage description. All days are pre-read
  into `seeds/logs/<Day>.json`; `bbt_cli.py readlogs <Day>` re-reads one into the cache.
- Takes inside a shot are aligned by position: take *n* = the *n*-th clip on each camera's row.

## 2. Takes → actual clips
For a logged take, the tool looks up each camera's clip on the server and checks it **overlaps the main camera
in timecode**. If not, it tries the neighbouring clip numbers (±3); logs often drift on one camera. It reports
every correction. For scenes without a log, `day` groups all of a day's clips into takes by timecode overlap.

## 3. Sync by sound (`sync()` in `server/bbtakes.py`)
- Timecode gives a first guess. Then each camera's sound is turned into an onset envelope (100 per second)
  and matched against the reference camera within ±1 s. A match needs correlation ≥ 0.25, otherwise the camera
  stays on timecode.
- Checked against an independent full-band (PHAT) sync on Sc 217: every camera within 5 ms.
- GoPros / 360 only join when their sound matches.

## 4. Preview
All cameras are trimmed to the common span and tiled (2×2 up to 4×2), 640×360 per camera, hardware-encoded
with a keyframe every 12 frames so scrubbing is snappy. Built from the lightest copy on the server (H.264 when
there is one). Cached in `~/Library/Caches/BB Takes/takes/<take>/` with `take.json` (the sync offsets).

## 5. Exports and stills
Read from the best copy on the server (ProRes sibling when a day has one), cut using the sync offsets in
`take.json`:
- camera files: per camera, In → Out, H.264 (50 Mb/s at 4K, 20 Mb/s at HD) or ProRes 422 HQ;
- sheet: cameras tiled to 3840 wide, Lanczos scaling, labels and title burned in, reference camera's sound;
- cut: segments from your Switcher recording, concatenated, reference camera's sound underneath;
- stills: one frame per camera at 3840 wide (PNG), or one sheet frame.

## Pieces
| File | Job |
|---|---|
| `server/bbtakes.py` | engine + local web server (127.0.0.1 only) |
| `server/logsheets.py` | log sheet reading |
| `server/bbt_cli.py` | command line (used by Claude) |
| `app/index.html` | the web app |
| `seeds/` | pre-read log sheets; takes for scenes with no usable log |
| `bin/` | ffmpeg, ffprobe, logocr |
| `~/Library/Caches/BB Takes/` | `days/` (clip index per day), `logs/`, `takes/` (previews + sync), `thumbs/`, `tags.json`, `config.json` |
