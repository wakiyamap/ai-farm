#!/bin/bash
# swell-fee-auction-ethereum: one entry point for paper and live (BOT_MODE). Standard library only, no venv.
cd "$(dirname "$0")"
mkdir -p logs state
exec python3 -u bot.py
