# Using BB Takes

Open the app (double-click `Start BB Takes.command`, or ask Claude). It runs at http://127.0.0.1:8765.

## 1. Find a scene
Type a scene number (`217`, `152A`) and press **Find**.
- You get the scene's location and day, and one **Log sheet** button that opens its pages (‹ › to flip).
- Below that, every **shot** with its coverage note ("start till Ishaan's last line") and what each camera covers
  (A wide · C Jai mid close · D 2-shot babu & Ishaan…).
- Each shot's **takes** are buttons: `T1 T2 T3 ✓T4`.
  - **Green ✓** = OK take on the log sheet.
  - **Dashed** = already prepared on this Mac (opens instantly).
- Scene with no readable log sheet? Open **All clips of a day** at the bottom and pick by time and cameras.

## 2. Open a take
Click a take. The first time, the tool lines up every camera by sound and builds a preview. That takes about
a third of the take's length; after that it opens instantly. Under the player it tells you:
- which cameras synced by sound (and any that only matched by timecode),
- cameras **left out** (usually a GoPro that wasn't rolling),
- **log vs footage** fixes ("log says C013, footage is C016": the right clip was used).

## 3. Watch: Viewer
All cameras in a grid, labelled with their coverage. `1`–`8` puts one camera big, `G` goes back to the grid.

## 4. Cut live: Switcher
Click **Switcher (live cut)** or press `S`. LIVE is the big red monitor; all cameras run beside it.
- `1`–`8` (or click a camera) cuts LIVE to it, on the same frame.
- `R` starts/stops recording your cuts; the coloured strip shows your edit.
- **Play back my cut** replays the take following your cuts.
- Export it from the right panel.

## 5. Build a video sheet
Click **Video sheet**. On the right:
- pick cameras (or press `1`–`8`), layout (auto / one row / 2–4 across),
- edit each panel's label, the title text, title bar and sound on/off.
The preview is exactly what you'll get, at 3840 wide. Set **In** (`I`) and **Out** (`O`) on the timeline.
The length turns red past 30 s, which is too long for one Seedance reference.

## 6. Grab a 4K still
Press **Still 4K** or `P` on the frame you want:
- Viewer with one camera big → that camera; grid → every camera ticked under Export.
- Switcher → the LIVE camera. Video sheet → the whole sheet as one image.
Stills land in `~/Movies/BB Takes Exports/Sc<scene>/<take>/stills/` as PNG. Days 1–4 footage is 1080p on the
server, so those stills are upscaled (the result says so).

## 7. Export
The right panel exports what the current mode shows:
- **Viewer** → the ticked cameras as separate files, In to Out.
- **Switcher** → your recorded cut as one file, with the reference camera's sound.
- **Video sheet** → the sheet, 4K.
Format: H.264 (.mp4) or ProRes 422 HQ (.mov). Exports read the best copy on the server (ProRes when the day has
it). **Show in Finder** opens the file.

## Keys
`Space` play · `←` `→` one frame (`Shift` = 1 s) · `I` / `O` in and out · `1`–`8` camera ·
`G` grid · `S` Switcher · `R` record cut · `P` 4K still.

## Ask Claude instead
With the BB Takes folder open in Claude Code you can just say what you want:
- "What are the OK takes of Sc 187?"
- "Make a sheet of Sc 217 shot 3 take 4, cameras A C E, 0:20 to 0:35, labels from the log."
- "Give me 4K stills of every camera at 00:00:40:20 in Sc 217 shot 1 take 1."
- "Export cameras D and E of Sc 152 take 3 as ProRes, 0:05 to 0:25."
