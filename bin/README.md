# bin/

Holds the tools BB Takes runs. They are **not in git** (too big); they come inside the release zip.

- `ffmpeg`, `ffprobe`: static Apple Silicon builds. If missing, setup uses ffmpeg from your PATH
  (for example `brew install ffmpeg`), or copy them from any BB Takes release zip.
- `logocr`: reads log sheet screenshots with Apple's built-in text recognition. Setup compiles it from
  `src/logocr.swift` when Apple's command line tools are installed. Without it, the log sheets that ship
  in `seeds/logs/` still work; only re-reading new log pages needs it.
