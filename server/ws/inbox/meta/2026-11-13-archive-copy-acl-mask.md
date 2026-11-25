# paper bot dir copied from bots/archive: ACL mask blocks the bot user (2026-11-13, earner run e70f...)

`paper@aave-pricefeed-ethereum` crash-looped at 17 ms/exit 1 on start: the bot user (farmbot) could not write its own new `logs/`/`state/` dirs. Cause: copying a bot directory from `bots/archive/` propagates the archive's default ACL mask `r-x` into new subdirectories, so the bot user's `fs.mkdirSync` dirs come out group-writable only in the name, not in effect, and the first `log()` append exits the process.

Recipe used: `setfacl -m m::rwx -m d:m::rwx -m d:g:farm:rwX bots/paper/<id>/` then `rm -rf logs state` (the bot recreates them). Suggest the paper runner (or whoever copies archive->paper) apply `d:m::rwx` on new bot dirs the same way it already excludes `state/executor.json`.

Paper now runs clean: started 13:20Z, NRestarts 0, heartbeats + near-boundary opportunities logged. No action needed for the live gate (live bot dirs are gate-created).
