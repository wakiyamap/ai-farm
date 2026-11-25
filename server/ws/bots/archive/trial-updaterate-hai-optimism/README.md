# trial-updaterate-hai-optimism

**試行 / TRIAL bot** (decision `decisions/human/2026-11-17-cheap-chain-trials.md`): the race
rule, the EV floor and the paper-capture requirement are waived; the win rate is measured
live. X / n / L / S and the executor rules (one tx, revert unless the balance ends higher)
apply unchanged. Lead 212, attempts:1449.

## Incumbents, last 7 days (optimism, measured 2026-11-16, `scratch/hai-otherjobs-da0f/rate2-out.json`)

| who | wins in the last 24 windows | how | priority fee |
|---|---|---|---|
| EOA `0x9ab1daea841cb6c0c0ac716531f03d50a97b8497` | 9 | direct call to the job | 0.085-0.098 gwei (one at 0.005) |
| EOA `0xd4a2f19220b55f95467980e09a3902e4ce808ecb` via `0x82c1ff92f8c222f6f9e4ca6092f5e934627249fe` | 8 | batch with collateral items, tx index 1 | 0.104-0.174 gwei |
| EOA `0x2d4fcc9d57d6e98b3c1e546a09bfdb9e5a3e1a57` | 7 | direct call | 0.0001 gwei |

3 addresses. Blocks from takeable to taken: **0** on all 168 takes of the 7 days (167 of 167
gaps between takes are exactly 3600 s; 2 s blocks), median = minimum = 0 s. Under the normal
rule (section 3.3) every occurrence is a race and none counts in EV; that is why this is a
trial. The 0.0001 gwei wins are the hours when neither high bidder sent.

## Mechanism

HAI (GEB / Reflexer fork) pays `rewardAmount` = 0.05 HAI (about 0.062 USD) to whoever calls
`OracleJob.workUpdateRate()` after the PIDRateSetter cooldown: `Job.reward()` runs
`stabilityFeeTreasury.pullFunds(msg.sender, rewardAmount)`, which credits SAFEEngine
internal coins. The time is known in advance:
`due = PIDRateSetter.lastUpdateTime() + updateRateDelay (3600 s)`.

The executor (`HaiRateJobTrial.act(jobCall, pool, minProfit)`) does, in one transaction: the
job call, `CoinJoin.exit` of all its internal coins to HAI, a direct UniV3 sell HAI -> WETH on
the pool given as argument, unwrap, pay the wallet in ETH. It reverts when the job reverts
(cooldown not passed, already taken) and unless ETH out >= `minProfit`.

## What the bot does

Timer, no per-block polling. Each hour: read `due`; 20 s before it, quote the expected gross
(reward x pool price x 0.997) and the base fee; send only if expected gross > the signed gas
cap (600,000 gas x maxFee, maxFee <= 0.03 gwei, so cap <= 1.8e-5 ETH against a gross of about
3.37e-5 ETH), with `minProfit = cap + 1` in the calldata. The transaction is handed to the
signer `lead_s` (starts at 1.0 s) before `due` so that it lands in the first block with
timestamp >= due; the lead adjusts itself by 0.2-0.3 s from where the last send landed.
Priority bid: 0.01 gwei fixed, never above 15% of the expected gross. This outbids only the
0.0001 gwei caller; against the two high bidders the send reverts for about 37k gas.

Logged per window (`logs/bot.jsonl`): `window` (quote, fees, send decision), `sim_ok` /
`sim_revert`, live `sent` (send time relative to due, signer latency) and `receipt` (status,
block, `landed_minus_due_s`, gas used, fee), and `window_result`: outcome win / lose, the
taker's address, block, `taker_delay_s`, tx index and priority fee, and our block minus the
taker's block. Paper mode sends nothing: it simulates the executor at head with the block
time overridden to `due` and logs `due_block_seen` (when the due block became visible).

## Numbers

- Fork (`scratch/trial-updaterate-hai/proof.py`): success gas 439,836, gross 3.3686e-5 ETH
  (0.0615 USD), wallet +2.885e-5 ETH after gas at 0.011 gwei; a lost attempt 37,383 gas
  (about 0.0008 USD).
- Whole item: 24 rewards/day = 1.48 USD/day gross. If the 7-of-24 pattern holds and our send
  lands in the first block: about 7 wins/day, +0.36 USD/day; 17 losses cost about 0.014 USD/day.
- Read cost: about 670 relay calls/day, ~18k CU/day = **0.010 USD/day** at 1M CU = 0.53 USD.
  No feed subscription.

- Capital: 5 USD of native gas (not the 20 USD trial maximum). The optimism intermediate
  wallet held 26.7 USD on 2026-11-16, and the other HAI trial asks for 20; 5 USD pays for
  more than 150 sends at the full signed cap and thousands of lost attempts.

## Open points the first live hours answer

1. Whether the signer accepts a transaction that would still revert at head (it is sent
   about 1 s before the due block exists). If it refuses, the bot cannot reach the first
   block and the trial result is `blocked_infra`.
2. The right send lead for the OP sequencer; `landed_minus_due_s` in `receipt` shows it.
3. Whether the low bidder raises its fee once it starts losing.

## Addresses (pinned by `eth_call` in `proof.py` step 0)

OracleJob `0xF4F18205D8D46638489865e42c0a71a3d4F9FC22`; PIDRateSetter
`0x1f76f20c9d9075dc160d0e47cd214df0b7434d2f` (`job.pidRateSetter()`); OracleRelayer
`0x6270403b908505f02da05be5c1956abb59fdb3a6` (emits `UpdateRedemptionRate`);
StabilityFeeTreasury `0xE9E54c55d41D6622933F9F736e0c55484b3c4f6f`; CoinJoin
`0x30Ce72230A47A0967B7e52A1bAE0178DbD7c6eA3`; SAFEEngine
`0x9Ff826860689483181C5FAc9628fd2F70275A700`; HAI
`0x10398AbC267496E49106B07dd6BE13364D10dC71`; WETH
`0x4200000000000000000000000000000000000006`; UniV3 HAI/WETH fee-3000 pool
`0x146b020399769339509c98B7B353d19130C150EC` (token0 = HAI).

No setup transaction: the one-time `SAFEEngine.approveSAFEModification(CoinJoin)` happens
inside the first `act()`.
