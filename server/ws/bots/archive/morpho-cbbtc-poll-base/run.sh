#!/bin/sh
set -e
exec /opt/node/bin/node bot.js >> logs/stdout.log 2>&1
