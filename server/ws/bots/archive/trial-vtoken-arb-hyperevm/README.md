trial

# trial-vtoken-arb-hyperevm

**Read first.** `attempts:3106` (run cdd0d3e7, 2026-11-20 night) found this same class ("LiquidV vTokens") and closed
it without building: about 0.25 USD a day net for the one taker, router unverified, "reopen only if the vTokens grow
or the router source is published". Neither happened. This run (3c67964f) found the class again through its own burn
census and built the bot before seeing that row. New since then: a fork-proven take (+0.098832 USDC for 587,818 gas)
and the taker measured as slow and not bidding. The class is still small (about 1.7 USD a day gross for everyone), so
this is a low-priority candidate for a live trial slot.

vTokens on HyperEVM (vANSEM, vJASPER, vFLOOD, vSMARTEST and 11 more) are tokens backed by an ERC-4626 vault whose
NAV comes from HyperCore. Anyone can mint one with USDC or redeem it for USDC through the protocol router
`0x3de2ba3712035fbabd90803813b2afe9eb1ab2ba`; each also trades on a small vToken/USDC V3 pool. When the pool price is
away from the NAV by more than the fees (pool 0.05 % or 0.3 %, mint fee 0.8 %), one transaction closes the gap and
keeps the difference in USDC.

## What one transaction does

Executor `TrialVTokenArb.run(Route)` (source `scratch/trial-vtoken-arb-hyperevm/contracts/src/TrialVTokenArb.sol`):

1. `vault.sync()` (public; the incumbent calls it first too).
2. `pool.swap(...)` with a price limit = current price moved by the route's band. The pool pays first.
3. In `uniswapV3SwapCallback`:
   - redeem side: approve the vToken to the router, `router.0x18ffbeca(vToken, amount, 0, executor, deadline)`
     (burns the vToken, redeems the vault shares for USDC), pay the pool the USDC it is owed;
   - mint side: quote the router (`0x95b6d8ab`), `router.0xda2550b5(vToken, usdcIn, owed, executor, deadline)`, pay
     the pool the vToken it is owed.
4. Revert `NoProfit()` unless the executor's USDC balance grew by `minProfit`; pay all USDC to the bot wallet.

No flash lender and no principal: the pool's own swap funds the trade. A lost attempt costs gas only.

## Bot loop

- Every 27 s: one `eth_call` of `probe()` with 24 candidates: vANSEM and vJASPER every poll, the other 13 tokens two
  per poll in rotation (each about every 3 min); per token 2 directions x 3 price bands (0.3 / 1 / 3 %), amount cap
  40 USDC.
- If the best gain is at least 0.01 USDC: read the gas price and the HYPE price (WHYPE/USDT0 pool), estimate gas, and
  send only if the gain is above the send's gas cap (gas limit x maxFeePerGas at HYPE price x 1.15; gas limit =
  estimate x 1.15, maxFeePerGas = base fee x 1.2 + bid) and the cap is under 0.95 USD. `minProfit` = the gas cap in
  USDC. Priority-fee bid: at most 5 % of the simulated gain (the incumbent does not bid).
- Every send logs `send_result` with won / lost, gas used and the nearest block where someone else minted or redeemed
  the same vToken at the router (`winner_block`, `blocks_after_winner`).
- `BOT_MODE=paper`: same reads against `latest` with the fork runtime as a code override, nothing is sent
  (`paper_sim` rows). `BOT_MODE=live`: `EXECUTOR_ADDR_HYPEREVM` / `EXECUTOR_ADDR` is required; sends go through the
  signer.

## Competition, last 7 days (to 2026-11-21 03:45Z, blocks 51,220,568-51,825,368)

Source: every log of the router (`scratch/r3c67/setscan.py hyperevm 0x3de2ba37... 604800 50000`) and
`scratch/trial-vtoken-arb-hyperevm/competition.py` (`competition.json`).

| address in topic2 of the router event | redeems | mints | what |
|---|---|---|---|
| `0x615340bc41c5bda250ee8103553b4953df3b4fc6` (EOA `0x61c5064704a579a4c1a5978c988afa50953b9f87`) | 130 | 72 | atomic taker, `arb(address,uint256,uint256)`, pays its gain to `0xf911e2bc...` |
| `0xb9a031e36af14f3da590fafe0504940362bd386a` | 0 | 25 | mints; the one sampled (0xf2041e77..., EOA 0xf6121c20) paid nothing to a taker |
| `0xe13ad79d54a5848cc68cea0ca64e0b28960c2443` (registry) | 0 | 11 | one mint per vToken (first mint) |
| `0xb6cfbb13`, `0x2d78928e`, `0xbd081f1b`, `0x6108624b`, `0x002b2964` | 7 | 4 | 1-3 each, not read |

- Takes per token (all callers): vANSEM 123, vJASPER 67, vFLOOD 13, vSMARTEST 13, the rest 1-5 each.
- The taker's last 26 takes: gain 0.010-0.161 USDC (median 0.026), 815k-946k gas, gas price = base fee
  (0.10-1.16 gwei in 24 of 26; 4.6 and 5.3 gwei twice, paying more gas than it gained), tx index 0-13 (median 5).
  Priority-fee level: none.
- Blocks to take: not measurable from history (the NAV is read from HyperCore, which is not archived). Observed live
  in this session: a vANSEM redeem gap of 0.132 USDC at 03:53:36Z was still open 2.5 minutes later at 0.058 USDC
  (03:56:08Z), far above the 0.010 USDC smallest gain the taker took; vANSEM takes are a median 723 blocks (12 min)
  apart, minimum 6.
- Pools are tiny: vJASPER 144 USDC, vANSEM 45 USDC, the others about 5 USDC a side (`tokens.json`), so the class is
  small: 11.97 USDC of gain in 7 days for the taker (`attempts:3106`), about 1.7 USD a day gross, for which it paid
  0.1675 HYPE (about 10 USD) of gas.

## Read cost

Live and paper: 3,200 polls x 26 CU (`eth_call`) = 83,200 CU/day, plus about 88 CU per evaluated gap (`eth_gasPrice`,
slot0, `eth_estimateGas`, the exact-bytes `eth_call`) and 95-600 CU per send (receipt polls + one `eth_getLogs`).
Hard cap 98,000 CU/day in code (`CU_CAP`), then the bot sleeps to 00:00 UTC. At 1M CU = 0.53 USD: 0.045-0.052 USD a
day. No feed filter (the NAV has no event).

## Limits

- The router, registry and incumbent taker are unverified: selectors come from traces
  (`scratch/r3c67/trace-vansem.json`, `trace-vansem-mint.json`). A router upgrade shows as `loop_error` or
  `simulate_revert` rows.
- Fork proof: redeem side only as a real fork transaction (`proof.py`, needs the fork-only HyperCore replay fixture);
  the mint side is proven by equal probe gains on fork and live.
- 15 tokens are hard-coded in `bot.py` (`TOKENS`); new vTokens (vCALMPEAK was first minted in block 51,820,765) need a new entry
  (`scratch/trial-vtoken-arb-hyperevm/tokens.py` lists pool and vault).
- After 7 days live or when the 20 USD is spent: write sends, wins and net as an `attempts` row and set the lead
  `measured` or `blocked_infra`.
