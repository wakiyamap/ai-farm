#!/bin/sh
set -eu
cd "$(dirname "$0")"
exec python3 bot.py >> logs/stdout.log 2>&1
