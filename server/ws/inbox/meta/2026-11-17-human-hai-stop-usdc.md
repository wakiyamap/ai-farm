# HAI trials stopped, which USDC the gate counts, fork --gas (human, 2026-11-17 18:3x JST)

1. **HAI**: agreed with your report (100 sends, 0 wins, the winner always at tx index 1, ours at 5-70, so
   ordering is not by fee). The human stopped trial-oraclejob-hai-optimism, trial-oraclebatch-hai-optimism and
   trial-updaterate-hai-optimism with `gate stop`. This frees 3 of the 10 trial slots. Record the finding in the
   wiki (OP Stack: a higher priority fee does not move a tx ahead of the slot-1 winner) so builders do not
   build another HAI-style race on optimism or base.
2. **Which USDC counts**: the gate, signer, watchdog and sweep count only the address in gate.json `usdc` for
   the bot's own chain:
   - polygon `0x3c499c542cEF5E3811e1192ce70d8cC03d5c3359` (Circle native USDC, not USDC.e `0x2791...`)
   - optimism `0x0b2C639c533813f4Aa9D7837CAf62653d097Ff85` (Circle native USDC, not bridged USDC.e)
   Read `baseToken()` of the Comet before building. If the polygon market pays in USDC.e,
   trial-cv3-buy-polygon must swap its USDC.e result to native USDC (or to POL) inside the same executor tx
   before the balance check; otherwise its profit is invisible to X and sweep and the balance-grows check sees
   no gain. The same applies to any token other than native gas and the configured USDC.
3. **Freed slots**: your choice of order; the human would start with trial-cv3-buy-optimism (largest measured
   gross over 7 days), then the two hyperevm bots. Keep the cap at 10 for now.
4. **`fork deploy --gas`**: not now. The fork tool is human-side code; if blocked_infra leads keep naming it,
   say so in a report with the lead ids and the human will add it in a phase.
