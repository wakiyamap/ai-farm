# bold-redeem-tail-ethereum: live code patched by the human; signer address pitfall (human, 2026-11-17)

## What the human did (2026-11-16 19:00Z)

- The paper-reviewer's urgent note (`inbox/live/2026-11-16-bold-live-from-object.md`, now in `inbox/live/done/`) was
  right: `bot.py:wallet_address()` returned `farmbot_signer.my_address()` unchanged, a dict
  `{"ok": true, "address": "0x..."}`, and `act()` put it in `eth_call.from`, so every live simulation would fail.
- The human edited the live copy directly (one line, line 98) and ran `gate restart`:
  ```
  a = farmbot_signer.my_address()
  return a["address"] if isinstance(a, dict) else a
  ```
  The start line after the restart shows `"from": "0x2d2F2247db7Bfc92a4111505F03533D6AcbF85d2"` (a string).
  The original file is kept by the human outside the workspace. Nothing else changed: same executor, same wallet,
  same manifest. No opportunity send had happened before the patch.
- Why not stop and re-review: the fix is the same extraction `trial-updaterate-hai-optimism` already does, and a stop
  plus a new promotion would have cost another executor deployment (about 2.6 USD) and hours of the bot's window.

## For the paper-reviewer

- The code hash of `bots/live/bold-redeem-tail-ethereum/bot.py` no longer matches your snapshot. This change is the
  human's and is accepted. Please record the new hash and do not treat it as tampering.
- The paper copy in `bots/archive/` or any earlier draft still has the old line; a copy made from it must take the fix.

## The pitfall (please make it permanent)

`farmbot_signer.my_address()` returns a dict, not a string. Paper runs never call it (they use a fixed sim address),
so the bug shows only after promotion. Two bots in one hour had it (bold-redeem-tail-ethereum live,
trial-oraclejob-hai-optimism in paper review).

1. Add a wiki page `pitfalls/signer-my-address-dict.md`: the return shape, the one-line extraction, and that paper
   cannot catch it.
2. Add one line to earner.md where the live branch is described (the signer item in section 5), and move the same
   number of bytes to the wiki (earner.md is at 55,873).
3. `tools/manifest-check.py`: warn when a bot's code calls `my_address()` and no line nearby reads `["address"]` or
   `.get("address")`. A warning is enough.
4. paper-reviewer.md: before promoting, check how the live branch builds `from` (and any other value taken from the
   signer), since the paper run cannot show it.
5. Check the other live bots (gearbox-v3-watcher-ethereum, morpho-nextblock-ethereum, trial-updaterate-hai-optimism)
   once and say in your next report whether any of them has the same line. Do not edit live copies; report to
   inbox/human.
