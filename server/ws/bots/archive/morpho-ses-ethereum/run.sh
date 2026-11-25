#!/bin/sh
# morpho-ses-ethereum entrypoint: node bot, logs under logs/ (paper and live
# both run this; live mode sends through the signer at $SIGNER_SOCK).
cd "$(dirname "$0")"
exec node bot.js >> logs/bot.log 2>&1
