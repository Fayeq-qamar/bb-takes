# BB Takes

Watch every camera of a Beta Builder take, lined up by sound. Cut between them live, build labelled video sheets,
grab 4K stills, and export full-quality clips. It reads the shoot server directly and runs on your own Mac.

## Get started (no GitHub needed)

1. Get the latest **`BB_Takes_vX.Y.Z.zip`** from the team and unzip it anywhere (e.g. `Documents`).
2. Mount the shoot server in Finder (it shows as `BB_Shoot_Data`).
3. Open the `BB_Takes` folder in **Claude Code** and say: **"Set up BB Takes for me."**
   Claude reads `CLAUDE.md`, runs the setup check and starts the app.
   No Claude handy? Double-click **`Start BB Takes.command`** (first time: right-click › Open).

The app opens in your browser at **http://127.0.0.1:8765**.

You can also just ask Claude for things, for example:
*"Make a 4K video sheet of Sc 217 shot 3, the OK take, cameras A, C and E, from 0:20 to 0:35, labelled by coverage."*

## What's inside

| | |
|---|---|
| **Find** | Type a scene number. Shots and **✓ OK takes** come from the continuity log sheets, with what every camera covers. |
| **Viewer** | All cameras in sync in a grid; `1`–`8` for one camera big. |
| **Switcher** | Live vision-mixer: a big LIVE monitor, all cameras beside it, `1`–`8` to cut, `R` to record your cut. |
| **Video sheet** | Pick cameras, layout, labels, title; the preview is the 4K output. |
| **Still 4K** | `P` saves the current frame at 3840 wide. |
| **Export** | Camera files, sheets, cuts: H.264 or ProRes 422 HQ, from the best copy on the server. |

Everything lands in `~/Movies/BB Takes Exports/`. The shoot server is only ever read, never written.

## Docs

- [docs/SETUP.md](docs/SETUP.md): install, first run, problems
- [docs/USING.md](docs/USING.md): how to use every part of the app
- [docs/HOW_IT_WORKS.md](docs/HOW_IT_WORKS.md): log sheets, takes, sync, previews, exports
- [docs/SHARING_AND_PERMISSIONS.md](docs/SHARING_AND_PERMISSIONS.md): who gets access, and how
- [docs/MAINTAINING.md](docs/MAINTAINING.md): updates, releases, contributing changes
- [CLAUDE.md](CLAUDE.md): what Claude reads when you open this folder

Needs: an Apple Silicon Mac (M1 or newer), macOS with Apple's command line tools (for Python 3), and the shoot server.
