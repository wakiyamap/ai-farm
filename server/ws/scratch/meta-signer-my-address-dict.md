---
type: pitfall
chains: [any]
protocols: []
---
# farmbot_signer.my_address() returns a dict, not an address

**Conclusion.** `farmbot_signer.my_address()` (`/opt/farm/lib/farmbot_signer.py`) returns
`{"ok": true, "address": "0x..."}`. Take the string before using it as `from`, a log field or a balance target:

```python
a = farmbot_signer.my_address()
a = a.get("address") if isinstance(a, dict) else a
if not (isinstance(a, str) and len(a) == 42):
    raise SystemExit(f"signer address unusable: {a!r}")
```

Raw socket (JS bots): `{"op": "address"}` answers the same object; use `reply.address` after checking `reply.ok`
(gearbox-v3-watcher-ethereum `bot.js:408-410`, morpho-nextblock-ethereum `bot.js:889-891`).

**Why paper cannot catch it.** Paper runs have no `$SIGNER_SOCK` and simulate from a fixed sim address, so the live
branch never runs before promotion. The first live `eth_call` with `from` = a dict fails (JSON-RPC rejects it) and the
bot never sends. Check the live branch by reading it, in the builder session and in the review.

**Evidence.** 2026-11-16: bold-redeem-tail-ethereum went live with `wallet_address()` returning the dict; the human
patched the live copy (line 98) at 19:00Z before any opportunity send (`inbox/meta/2026-11-17-human-bold-live-patch.md`).
The same hour trial-oraclejob-hai-optimism had it in paper (review.md item, fixed by builder run 4886c647).
Meta check 2026-11-16 21:xxZ: all four live bots (bold, gearbox, morpho-nextblock, trial-updaterate-hai) extract the
string; paper bots trial-aave-arbitrum and trial-oraclejob-hai-optimism do too.

**Tooling.** `tools/manifest-check.py` warns when a bot's code calls `my_address()` with no `["address"]` /
`.get("address")` within 3 lines.
