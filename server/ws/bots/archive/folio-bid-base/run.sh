#!/bin/sh
cd "$(dirname "$0")"
mkdir -p logs state
exec python3 bot.py
