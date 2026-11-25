import json, subprocess
out = subprocess.run(["kb","query","--json","SELECT next_steps FROM leads WHERE id=165"], capture_output=True, text=True, cwd="/srv/farm/ws").stdout.strip()
r = json.loads(out)
ns = r["next_steps"] if isinstance(r, dict) else r[0]["next_steps"]
i = ns.index("BACKFILL LIVE 2026-11-12T20:1xZ")
new = ("BACKFILL COMPLETE 2026-11-12T21:29Z run cfd43e82: stakedao_v2.harvest cursor reached head "
       "26401501 verified=1 after ~33k backfill blocks (burst pace, cursor 26381066 at "
       "20:42Z -> 26401501 at 21:29Z); full-window ledger breadth 1187 Harvest events / 74 tx_from "
       "(26351035-26401299), 236 events in last 24h; incumbent 0xec58746c...996 takes 728/1187 (61 pct) "
       "- concentration unchanged, fee level unchanged, dead_end stands with cursor-at-head confirmed. "
       "Interpret ledger zeros freely from now; re-check tools/ledger-source-coverage.py after daemon restarts.")
patch = {"next_steps": ns[:i] + new}
with open("/srv/farm/ws/scratch/lead165_patch.json", "w") as f:
    json.dump(patch, f)
print(len(patch["next_steps"]))
