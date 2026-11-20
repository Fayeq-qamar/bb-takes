#!/bin/bash
# Double-click to start BB Takes. Keep this window open while you use it; close it to stop.
cd "$(dirname "$0")"
PORT=${BBTAKES_PORT:-8765}
if curl -s -m 2 "http://127.0.0.1:$PORT/api/status" >/dev/null 2>&1; then open "http://127.0.0.1:$PORT"; exit 0; fi
bash scripts/setup.sh || { read -n 1 -s -r -p "Press any key to close"; exit 1; }
( sleep 1.5; open "http://127.0.0.1:$PORT" ) &
exec /usr/bin/python3 server/bbtakes.py
