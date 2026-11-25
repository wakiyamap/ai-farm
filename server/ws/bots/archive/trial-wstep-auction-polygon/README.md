trial: wstEP FBX-for-EP curve auction against the SushiSwap EP / FBX pair on Polygon (decision 2026-11-17-cheap-chain-trials)

## What it does

- WrappedStakedEP (wstEP) `0xe3df997cad0476954196fdfe94a9bc090365cad9` is an ownerless, verified ERC-4626 vault that
  stakes EP `0x60ed6acef3a96f8cdaf0c0d207bbafa66e751af2` and sells the FBX `0xd125443f38a69d776177c2b9c041f462936f8218`
  that staking pays. `takeAuction(amountEP, minFbxOut)` is open to anyone and pays
  `fbxPool * amountEP / (amountEP + 9 EP)`; no price is read from anywhere, accrual raises the rate.
- EP trades on the SushiSwap V2 pair EP / FBX `0x41d9de53ebf26f766229e42aa02904eb2495e397` (113.7 EP / 19,962 FBX,
  0.3 pct). When the book's marginal rate `fbxPool / 9` is above the pair's price plus fee, one transaction through
  the executor: flash swap EP out of the pair, `takeAuction`, repay the pair in FBX, sell the FBX left on Uniswap V2
  USDT / FBX `0x1000bb85...` and QuickSwap V2 WPOL / USDT `0x604229c9...`, unwrap, pay the wallet in POL.
- The executor reverts unless the wallet is paid at least `minProfit`; the bot sets `minProfit` = that send's gas cap.
  No principal: the pair's flash swap funds it.

## Competition, last 7 days (scratch/r8e72/hist.py, hist.json)

Every log of the vault in polygon blocks 97,436,831-97,756,831 (320,000 blocks to 2026-11-22 09:45Z; the first take
in the window is 2026-11-16 22:58:16Z, block 97,442,951):

| taker | takes | size | when | gas | tx index |
|---|---|---|---|---|---|
| EOA 0x304fa7d9, direct call | 23 of 23 | 0.5 EP for 87.5-88.1 FBX | every 19,800 or 21,600 s; 11-22: 00:28:14Z, 06:28:14Z | 0.090-0.094 POL (about 410 gwei) | 0-89, median 4 |

- The incumbent is a timer with EP inventory: fixed size, `minFbxOut` about 0.4 pct under its quote, and it pays about
  the pair's price (175.0-176.1 FBX per EP against 172.7-179.5 on the pair with fee), so it earns nothing per take.
- Blocks to take: not a race so far. The book crosses the pair's price about 1 h after each incumbent take and stays
  takeable for the 4.5-5 h until the next one. At the parent block of each of the 23 takes the best flash-funded size
  was worth 0.38-1.96 FBX before pool impact (median 0.9 FBX = 0.22 USD); the fork run at the parent of the last one
  paid 3.66 POL (0.27 USD).
- Priority fees: the incumbent pays the going rate (about 40 gwei over base); this bot bids 40-60 gwei.
- Once this bot takes, the incumbent's fixed 0.5 EP take leaves the book lower, so later cycles peak near 1.0-1.4 POL.
  Aim: 2-4 takes a day, 0.2-0.5 USD a day. This trial is about the win rate and the incumbent's reaction.

## Trigger and read cost

- Timer, every 120 s: ONE `eth_call` of the executor's `probe()` (18 sizes, 0.02-0.89 EP). Nothing to wait for on
  the feed: accrual is the clock (about 15 FBX an hour), so no feed filter is used.
- Sends when the best size pays at least 1.0 POL (`MIN_GROSS_WEI`) and more than 1.3 x gasLimit x maxFeePerGas.
- Live Alchemy CU/day: 720 looks x 26 CU = 18,720 CU, plus 3 reads (66 CU) per opportunity look and 20-75 CU per
  send: about 22,000 CU/day = 0.012 USD/day at 1M CU = 0.53 USD. The bot stops reading at 95,000 CU/day and sleeps
  to 00:00 UTC.

## Limits in the code (bot.py)

- send only when gross >= 1.0 POL and gross > 1.3 x gasLimit x maxFeePerGas; `minProfit` = that cap, so a win always
  nets more than gas;
- maxFeePerGas <= 1500 gwei, gas limit <= 1,200,000 (a take uses about 0.44M, a guard revert up to 0.55M), cap
  < 0.95 USD at a POL price of 0.5 USD (POL was 0.075 USD on 2026-11-22; a send's cap was 0.31 POL = 0.024 USD);
- every relay read is inside the loop's handler for the CU cap.

## Files

- `bot.py`, `run.sh`, `executor-runtime.hex` (paper code override = `eth_getCode` of the fork deployment);
- executor source `scratch/trial-wstep-auction-polygon/contracts/src/CurveAuctionArb.sol`;
- proof `scratch/trial-wstep-auction-polygon/proof.py` (parent of a real take), `selftest.py`, `state.py`.
- Logs: `logs/bot.jsonl`: `start`, `building`, `opportunity`, `paper_sim`, `simulate_revert`, `opportunity_skip`,
  `send_result` (won / lost, gas_used, winner_block), `heartbeat`.

## When to stop

- After 7 days live or when the 5 USD is spent: one `attempts` row (sends, wins, net) and the lead set to `measured`
  or back to `blocked_infra`.
- Earlier if only `building` lines appear for 2 days, or the Sushi pair loses its liquidity.
