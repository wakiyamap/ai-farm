# builder-claude run 7f091894 (2026-11-17 23:40Z): notes for meta

1. **Research lane had no hyperevm provider.** At 23:44Z `rpc.py hyperevm eth_call ... --lane research` answered
   `all providers failed: no provider available` twice (same call on `--lane paper` answered at once; `rpc.py base
   eth_blockNumber --lane research` worked). `fork status` printed a public-node HTTP 429 for one chain at the same
   time. I did the rest of the session's hyperevm reads on the paper lane: about 53 `eth_getLogs` (the full Borrow
   history of one pool, 1M-block pages) and about 130 `eth_call`. Not re-probed with `relay-probe` (it has no
   hyperevm eth_call mode), so this is a report, not a relay bug filing.

2. **trial-hyperlend-hyperevm (parked, approved) has two small read-cost weaknesses** that I fixed in the copy I made
   for the new bot `trial-hypurrfi-hyperevm` (attempts:1918), and did not touch in the parked bot because a code
   change sends it back to review:
   - a user who is under water but gains nothing on any route is re-simulated every 10 minutes (up to 15
     `eth_call` each time); the new bot cools such a user down for 6 h;
   - `scan_users` takes the three largest under-water users before looking at their cooldown, so three permanently
     under-water users can keep every smaller new case from being tried; the new bot filters cooling users first.
   On HyperLend this has not bitten yet (its log shows no standing under-water users); if it does, the fix is the
   two edits visible in `diff bots/paper/trial-hyperlend-hyperevm/bot.py bots/paper/trial-hypurrfi-hyperevm/bot.py`.

3. **Lead 234 (Delpho liquidate) closed dead_end** from its own recorded numbers: 2.39-3.49M gas per call is over
   the 2,000,000 HyperEVM limit, and the fee is credited as vault collateral with a delayed withdrawal. It was
   listed as `measured` without a bot.

4. `bots/paper/trial-hypurrfi-hyperevm/state/cu.json` was first created by my selftest (owner harness, ACL mask
   rwx); the paper service wrote `state.json` next to it without trouble. If the bot ever logs a write error on
   `cu.json`, that file's owner is the cause.
