---
type: method
chains: [arbitrum, base, optimism, bsc, polygon, avalanche, hyperevm, elysium]
protocols: []
author: meta/opus
updated: 2026-11-23
---
# Graduation: a winning trial bot becomes a `grad-<target>-<chain>` bot

Decision `decisions/human/2026-11-24-graduate-and-builder-focus.md`. A live trial bot that wins repeatedly is rebuilt as a normal bot with a larger fee and (if it scales) capital budget. The trial stays live until the grad is live; then the human runs `gate stop` on the trial. Trial-slot decisions are unchanged; a grad is a normal bot, not a trial (the trial-slot count is live ids starting `trial-`). At most **5 grads live** at once. Ethereum bots never graduate.

## 1. Candidate (meta lists them every run; paper-reviewer re-checks)

All three:

- live >= 72 h (since the gate wrote `bots/live/<id>/state/executor.json`)
- net since promote >= +1 USD: wallet value now (gate status) minus everything the intermediate sent the bot (native + USDC, top-ups included), native at the current price. This is the watchdog's basis.
- >= 3 sends with `won` in the bot log. One big win alone does not qualify.

Tool (read-only, ~150 CU per bot):

```
python3 /srv/farm/ws/tools/grad-candidates.py          # candidates + every bot with net > 0
python3 /srv/farm/ws/tools/grad-candidates.py --all    # every live trial bot
```

A trial whose grad already exists prints `YES (grad live|paper|archive)` and is not an open candidate. For `(grad archive)` read `bots/archive/grad-<id>/ARCHIVE.md` before any rebuild (grad-peapods-arb-arbitrum: archived 11-23 08:30Z, a <3 s race).

`funded` comes from `alchemy_getAssetTransfers` (intermediate -> bot); a `~` means it fell back to manifest `capital_usd` (transfers unreadable on that chain). Do not use `capital_usd` as the funded amount when the exact number exists: the gate funds native at the promote-time price, so the two differ by up to ~15% (11-23: trial-flatmoney-arbitrum +0.85 vs capital, +1.29 vs transfers). "won" is the bot's own log label (`send_result` lines); check a few `won` hashes (receipt status 1, wallet up) before quoting the count.

## 2. Building the grad (builder)

- New id `grad-<target>-<chain>`, new directory in `bots/paper/`; do not touch the live trial. The manifest may point `executor:` at the trial's artifact if the bytecode is unchanged (grad-peapods-arb-arbitrum did; never clean that scratch directory).
- Limits: `capital_usd` <= 150, `max_loss_per_tx_usd` <= 3. `strategy` does NOT start with `trial:`. All of X, n, L, S, the executor rule and the 30 USD watchdog stop are unchanged.
- README must contain, from the trial's live log:
  1. **Live record**: sends, wins, gross, net, the trial's id and promote time.
  2. **Fee distribution of the winners**: for each won race in the trial window (ours and rivals'), priority fee + builder payment as a share of gross; median and quantiles. The grad's fee cap is chosen from this table and written in `max_loss_guarantee`; **50% of expected gross is the ceiling**, not the default. No table = no increase.
  3. **Why the trial lost**: per lost send, blocks behind the winner, fee short, or revert reason; then what the grad changes.
  4. **Size**: raising capital needs a fork proof that size pays: re-run past winning blocks at 2x and 5x the trial's amount and show gross at each. Fixed-reward types (keeper bounties, poke rewards) keep minimum capital and only raise the fee cap.
- **OP Stack (base, optimism): no fee bidding.** Priority fee does not reorder there; the winner sat at tx index 1 every time (11-20 observation, `pitfalls/opstack-first-block-index.md`). Base and optimism grads keep the trial's fee and the 18 USD native wallet cap.
- Expected value may rest on the trial's live record instead of a 30-day window table.
- **External price routes**: a trial that depends on a keyed or trial service (e.g. the Hermes proxy, key ends ~12-01) needs a route that survives it before a grad is worth building; the human does not buy a Pyth key (11-23).

## 3. Reviewing the grad (paper-reviewer)

A normal review (promote criteria 1-5, read cost, executor shape) with these differences:

- EV evidence may be the trial's live record (sends, wins, gross, gap to rivals) instead of a re-measured 30-day window table; recompute net from the trial log yourself.
- Check the limits above, the fee-distribution table and that the fee cap in code is at or below what the table justifies (and <= 50% of gross); OP Stack chains: no fee increase.
- Capital above the trial's needs the 2x/5x fork proof; reproduce at least one of those runs.
- Count live `grad-` ids in `gate status`: 5 already live = `wait` with the ids in `review.md`.
- After promote, write `inbox/meta/` naming the trial to stop; meta forwards it to `inbox/human/` (the human runs `gate stop`).

## 4. Builder work order (decision section 3)

1. paper bots returned with `decision: fix`; then any lead whose `why` starts `HUMAN REQUEST` (meta forwards the human's builder tasks that way, e.g. lead 436); 2. graduation candidates -> grad; 3. polish live grads (lost-send causes, same type on other pools/assets); 4. scout's `measured` leads; 5. none of these: short report, end. No long censuses or open-ended sweeps. builder-claude runs every 4 h, builder-codex every 3 h.

## History

- 11-23 07:49Z: first grad placed, grad-peapods-arb-arbitrum (builder-claude d83b895c, attempts:4033); archived 08:30Z by the paper-reviewer (<3 s race).
- 11-23 10:5xZ meta run 0d18f9f3: candidates trial-peapods-arb-arbitrum (+1.79, 5/10 won, 87 h) and trial-flatmoney-arbitrum (+1.29, 13/13, 127 h; attaches a Pyth update from the hermes proxy, whose key trial ends ~12-02: a grad needs a keyless or paid price route first); next: trial-ryeth-arb-arbitrum (+8.16, 11/11) reaches 72 h ~11-24 03:2xZ, trial-lester-harvest-base (+1.45, 19/19) at 32 h.
- 11-23 11:17Z grad-flatmoney-arbitrum placed in paper (attempts:4082). 12:52Z human: no Pyth key purchase (Hermes needs a key, plans from 500 USD/month); builder task "does executeOrder pass without a Hermes update" = lead 436.
- 11-23 17:0xZ meta 2f2e8352: 0 open candidates (peapods grad archived, flatmoney grad in paper); trial-ryeth-arb-arbitrum +8.35, 11/11, 72 h at ~11-24 03:2xZ; trial-lester-harvest-base +1.54, 20/20, 38 h.
