# Maintaining BB Takes

## The flow
```
change code  →  test on a real take  →  commit + push  →  bump VERSION + CHANGELOG  →  make_release.sh  →  GitHub release  →  share the zip
```
Users with the repo can update with `bash scripts/update.sh` (it runs `git pull`); zip users get the new zip.

## Making a change
1. `git switch -c fix/<short-name>` (anyone who isn't the maintainer works on a branch).
2. Change the code. Keep it **Python 3.9 standard library only** (it must run on a stock Mac) and keep the server
   **read-only**.
3. Test against the real server:
   - `bash scripts/setup.sh`
   - `/usr/bin/python3 server/bbt_cli.py scene 217` (should list shots 1–8 with OK takes)
   - prepare one take and export a short sheet (see `.claude/skills/bb-takes/SKILL.md`)
   - start the app and click through Viewer / Switcher / Video sheet / Still.
4. `git commit` with a clear message, `git push -u origin HEAD`, open a pull request (`gh pr create`).
5. The maintainer reviews and merges.

Claude can do all of this: open the repo folder and ask, for example, "fix X, test it on Sc 217, and open a PR".

## Releasing
1. Bump `VERSION` (`1.0.0` → `1.0.1` for fixes, `1.1.0` for new features) and add a section to `CHANGELOG.md`.
2. Commit and push to `main`.
3. `bash scripts/make_release.sh` → `dist/BB_Takes_vX.Y.Z.zip` (built from the last commit + `bin/` tools).
4. Publish: `gh release create vX.Y.Z dist/BB_Takes_vX.Y.Z.zip --title "BB Takes X.Y.Z" --notes-file CHANGELOG.md`
5. Share the zip with the team (see `SHARING_AND_PERMISSIONS.md`).

`bin/ffmpeg`, `bin/ffprobe` and `bin/logocr` are not in git. Keep them in your local `bin/` (setup builds
`logocr`; ffmpeg/ffprobe come from any previous release zip: `gh release download vX.Y.Z --pattern '*.zip'`).

## When new shoot days arrive
1. `/usr/bin/python3 server/bbt_cli.py readlogs DAY_16` (reads that day's log sheets into your cache).
2. To ship it to everyone, copy the result into the repo:
   `cp ~/Library/Caches/BB\ Takes/logs/DAY_16.json seeds/logs/` → commit → release.
3. Check a scene from that day with `scene <N>`; if a page reads badly, see `server/logsheets.py`.

## Scenes with no usable log sheet
Add them to `seeds/known_takes.json` (scene → day → shots → takes with a `primary` clip stem and optional
`"ok": true`). The other cameras are found automatically by clip number and timecode.

## Where the logic lives
See `HOW_IT_WORKS.md`. The parts most likely to need care: `logsheets.parse_page` (log layouts),
`bbtakes.prepare_log` (log → clips), `bbtakes.sync` (sound matching), `bbtakes.export` (renders).

## The password gate
`server/gate.py` keeps a salted SHA-256 hash of the team password, never the password itself. Every entry point
(`bbt_cli.py`, the app server, `setup.sh`, `Start BB Takes.command`) refuses to run until `gate.py unlock` has
succeeded on that Mac (valid 12 hours, stored in `~/Library/Caches/BB Takes/unlock.json`).

To change the password: compute the new hash and replace `HASH` in `server/gate.py`, then release:
```
/usr/bin/python3 -c 'import hashlib,getpass; print(hashlib.sha256(("bb-takes/gate/v1:"+getpass.getpass()).encode()).hexdigest())'
```
This is a light gate, not encryption: anyone with the code can remove the check, and a short
password can be guessed from its hash. The repo is public, so treat everything in it as readable by anyone.

