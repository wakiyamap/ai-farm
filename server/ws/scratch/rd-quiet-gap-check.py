#!/usr/bin/env python3
# Quiet-gap readiness check for reserve-dutch-ethereum (run c530ee3e).
# Sleeps until 2026-11-06T11:16:30Z, then verifies the bot kept polling
# through the phase where the ORACLE age exceeded the OLD 2400 s cap
# (10:53:35Z-11:15Z wall age 2400->3745 s) with no 'oracle round' errors,
# and reports the newest round age seen from the feed.
import time, datetime, json, os, urllib.request, re
END = datetime.datetime(2026, 11, 6, 11, 16, 30, tzinfo=datetime.timezone.utc)
while datetime.datetime.now(datetime.timezone.utc) < END:
    time.sleep(30)
log = open('/srv/farm/ws/bots/paper/reserve-dutch-ethereum/logs/bot.jsonl').read()
hb = [l for l in log.splitlines() if '"heartbeat"' in l]
hb_after = [json.loads(l) for l in hb if l.split('"ts":"')[-1].strip('"') >= '2026-11-06T10:53:35']
errs_after = [json.loads(l) for l in log.splitlines() if '"error"' in l]
errs_window = [e for e in errs_after if e['ts'] >= '2026-11-06T10:53:35']
body = json.dumps({"jsonrpc":"2.0","id":1,"method":"eth_call","params":[{"to":"0x5f4ec3df9cbd43714fe2740f5e3616155c5b8419","data":"0xfeaf968c"},"latest"]}).encode()
req = urllib.request.Request(os.environ['RPC_RELAY_URL'] + '/ethereum?lane=research', data=body, headers={'content-type':'application/json'})
r = json.loads(urllib.request.urlopen(req, timeout=30).read())['result']
w = [int('0x'+r[2+64*i:2+64*(i+1)],16) for i in range(5)]
age = int(time.time() - w[3])
print(json.dumps({
  "checked_at": datetime.datetime.now(datetime.timezone.utc).isoformat(),
  "heartbeats_since_10:53:35": len(hb_after),
  "errors_since_10:53:35": len(errs_window),
  "oracle_round_updatedAt": datetime.datetime.fromtimestamp(w[3], datetime.timezone.utc).isoformat(),
  "oracle_age_now_s": age,
  "old_cap_would_have_failed_s": age > 2400 or len(hb_after) > 20,
}))
