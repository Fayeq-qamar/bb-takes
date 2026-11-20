---
name: bb-takes
description: Use BB Takes (this folder) to get things out of the Beta Builder shoot footage — find a scene's shots and OK takes, sync a take's cameras, make a video sheet, a live-style cut, single camera clips or 4K stills, or set the tool up / start it. Use whenever the user asks for takes, sheets, stills, camera clips or coverage of a Beta Builder scene.
---

# BB Takes recipes

Run from the BB Takes folder with `/usr/bin/python3 server/bbt_cli.py …` (sandbox off: it reads the shoot server).
Every command prints JSON. The shoot server is read-only; outputs land in `~/Movies/BB Takes Exports/`.
First time on a Mac: `bash scripts/setup.sh`.

## 1. Find the take
`scene <N>` → `days[].shots[]`: `shot`, `note` (coverage), `cams[]` (`cam`, `desc`), `takes[]` with `n`, `ok`
(✓ on the log sheet), `clips` ({cam: clip stem}), `primary`, `take_id`.
- "the OK take of shot 3" → the take with `ok: true`. Several OK → ask which, or use the last.
- Scene has no shots (no readable log) → `day <Day>` lists every take by timecode and cameras; match the user's
  description (time, cameras) and confirm with them.

## 2. Prepare it (sync + preview), once per take
Write `{day, clips, labels, title}` to a temp JSON file:
- `clips` = the take's `clips`; `labels` = `{cam: desc}` from the shot's `cams`; `title` like `Sc 217 · Shot 3 · Take 4 ✓ OK`.
- For a take from `day`, use `clips: {"A": "<primary>"}`: the other cameras are found automatically.
`prep @file` → `take` (the id to use next), `dur`, `cams` (with `sync`: ref/audio/timecode), `left_out`,
`log_vs_footage`, `preview` (mp4 path to show the user). About a minute the first time, instant after.
Tell the user about anything in `left_out` or `log_vs_footage`.

## 3. Make what they asked for
Times are seconds from the start of the synced take (`0` … `dur`). Convert the user's timecodes; ask if unclear.
- **Camera clips:** `export @{take, type:"cams", in, out, cams:["A","C"], format:"h264"|"prores", scene}`
- **Video sheet (4K):** `export @{take, type:"sheet", in, out, cams:[…], cols, rows, labels:{cam:text},
  title:true, titleText:"Sc 217 shot 3", audio:true, scene, format:"h264"}`.
  Layout: 1–3 cams one row; 4 = 2×2; 5–6 = 3×2; 7–8 = 4×2. Seedance references must be ≤ 30 s.
- **Cut:** `export @{take, type:"cut", cuts:[{cam, t_in, t_out}, …], in, out, scene, format}` (sound from the reference camera).
- **4K still:** `still @{take, t, cams:[…], scene}`, or a sheet frame: `still @{take, t, scene, sheet:{cams, cols, rows, labels, title, titleText}}`.
Results: `files` (full paths). Show them: `open -R "<file>"`. Mention upscaling notes for Days 1–4.

## 4. If the user wants to click around instead
`open "Start BB Takes.command"`. It opens the app at http://127.0.0.1:8765 (Find → Shot → Take; Viewer /
Switcher / Video sheet; Still 4K = P; Export panel on the right). Guide: `docs/USING.md`.

## Problems
- `status` → `server_mounted: false`: ask the user to connect the server in Finder (Cmd+K).
- ffmpeg errors on Intel Macs: install ffmpeg (`brew install ffmpeg`); the bundled one is Apple Silicon only.
- New shoot day / new log pages: `readlogs <Day>` (needs bin/logocr), then `scene` again.
