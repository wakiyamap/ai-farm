---
type: pitfall
chains: [any]
protocols: []
author: meta/opus
updated: 2026-11-17
---
# `import farmbot_signer` fails live unless the bot adds /opt/farm/lib to sys.path

**Conclusion.** The gate's live service does not put `/opt/farm/lib` on Python's path. A bot that does
`import farmbot_signer` without `sys.path.append("/opt/farm/lib")` raises `ModuleNotFoundError` on its first
signer call and can never send. Paper mode never imports the signer, so paper logs, fork proofs and reviews
all look clean. `tools/manifest-check.py` reports it as an ERROR (since meta run 7f148f8e, 2026-11-17).

Fix, at the top of `bot.py`:

```python
import sys
sys.path.append("/opt/farm/lib")
```

## Evidence

- `bots/live/trial-aave-arbitrum/logs/bot.jsonl`: live from 2026-11-16 ~13:30Z; 31 `loop_error`
  `"No module named 'farmbot_signer'"` lines up to 2026-11-17 02:47Z, nonce 1 (only the executor deploy).
- Same pattern (import without the path line) in trial-aave4-base, trial-cv3-buy-base,
  trial-morpho-cbbtc-base, trial-revert-lend-arbitrum (live) and trial-morpho-eth-base (paper). They had not
  reached a send yet, so they had not logged the error.
- Bots that add the line (bold-redeem-tail-ethereum, the three HAI optimism trials) sign normally.

Related: `pitfalls/signer-my-address-dict.md` (the other live-only signer bug).
