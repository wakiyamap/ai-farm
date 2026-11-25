---
type: method
chains: [base, arbitrum, ethereum, bsc, polygon, avalanche, optimism, hyperevm, elysium]
protocols: [any]
author: earner/qwen3.8-flash-next
updated: 2026-11-15
---
# One-shot leftovers: take a takeable leftover once, even if it never recurs (decision 2026-11-14-oneshot-leftovers-idle-pull-oracle, item 1)

**Conclusion first:** a position (or any anyone-can-take state) that has stayed takeable for **10 minutes or more** and is **still takeable at head** is taken once, by a dedicated one-shot bot, even if the same shape never happens again. The "1 USD/day floor" and the "EV above CU cost" rule (decision 2026-11-12-morpho-stop-researcher-runs item 6) do **not** apply to it; it is judged by one net figure instead. Source: the decision file (Japanese; it wins if this page disagrees). The lines 10 min / 10 USD / 48 h / 2 bots are the human's rough lines.

Trigger case: attempts 1210 (Base Morpho, wbCOIN, collateral 1,504 USD, nominal profit 57 USD, untaken >= 1.8 h) was recorded as "one-shot under the floor" only. Under this rule it is re-checked at head and, if it qualifies, sent through the flow below; if already taken, one `attempts` row and done.

## Conditions (all must hold, else no bot)

1. **Fork proof at head**: on the fork reset at (near) head, farm's executor takes it and the **bot wallet balance rises** (success tx), and a no-profit call **reverts** (guard tx). Both hashes go into `fork_evidence`.
2. **Net >= 10 USD**: net = wallet increase - (executor deploy gas + execution gas + sweep gas), all at the current base fee.
3. **Real exit**: collateral is valued by what an actual pool pays for it on the fork, never the oracle price. Collateral with no exit (USR / RLP on Base, attempts 1210) is out.
4. **Why it is still there, in one line.** Where fast takers operate, a leftover usually has a reason: check collateral transfer restrictions / pause / blacklist, a stale or frozen oracle, liquidation permissions (role, whitelist). If the reason stays "unknown", do not submit. Example: lead 174 (ethereum Morpho ynETHx/msETH market, attempts 1215): a direct `Morpho.liquidate` with textbook params and `accrueInterest` both revert (panic 0x11) at the reset tag, so nobody can take it; that is the reason, and it is not a takeable leftover until a liquidate succeeds on the fork. A protocol bug that makes funds claimable is never a one-shot: security finding to `inbox/human/`.
5. **Minimum capital**: only what is needed (gas only if principal comes from a flash loan or callback). Per-bot 400 USD, L = 50 USD and every other limit unchanged.
6. **Separate id** `oneshot-<target>-<chain>`; the README starts with the word "One-shot" (単発).

## Flow

1. **earner**: proves it on the fork and places it in paper **in the same session** that found it. It does not wait in paper for an opportunity.
2. **paper-reviewer**: reviews it first in the next run. Fork reproduction + the conditions above suffice to `promote` (no detection history, no CU-vs-EV test, no per-occurrence 30-day table). If the chain's intermediate wallet lacks funds, write the needed amount to `inbox/human/`.
3. **bot**: after one capture, or once the target is gone, sends nothing more and idles.
4. **earner or paper-reviewer**: when it is captured or gone, write `inbox/meta/` (bot id, tx hash or evidence it is gone). **meta** forwards to `inbox/human/`; the human runs `gate stop`.
5. Not captured **48 h after promotion**: same route, recommend the stop.

At most **2 one-shot bots live** at a time, separate from the 2 next-block trial bots.

## Leftover measurement from now on

Crash post-mortem step 1-3 (`methods/crash-postmortem.md`) and every later leftover measurement check each leftover against the conditions above, instead of ending with "under the floor, recorded only".

## Scan mechanics (cheap path, measured 2026-11-15 run 9151eaf0)

The cheap leftover scan is: Morpho blue-api (https://blue-api.morpho.org/graphql) full pagination of `marketPositions` with `healthFactor_lte: 1.0` per chain (100/page, `skip`), then protocol-basis probes only for the few farm-size candidates, then a real-pool exit check (coins.llama.fi price + confidence, pool balance). Schema note: the API now exposes `marketPositions` / `MarketPositionFilters` / `market.marketId`; the older `positions` / `PositionWhere` / `uniqueKey` shape used by attempts 1210 is gone (fields introspectable via `__type`). On the base Morpho deployment 0xBBBBBbbBBb9cC5e90e3b3Af64bdAF62C37EEFFCb: `marketParams(bytes32)` reverts, use `idToMarketParams` 0x2c3c9157; `market(bytes32)` 0x5c60e39a returns the 6-word Market struct; debt = roundup(borrowShares x totalBorrowAssets / totalBorrowShares), maxDebt = collateral x oracle.price x lltv / 1e54; takeable-window ladder via fixed block tags at -3000/-18000/-432000 (base 0.2 s blocks). 2026-11-15 result: base 171 + ethereum 500 HF<=1 positions, every debt>=50 USD position except two is deep bad debt or no-exit collateral; the only farm-size takeable (KTA/USDC, gap 18.7 USDC, 24 h+) loses 431 USD at the real exit because the oracle price sits 57 pct above spot - exactly condition 3's purpose (attempts 1330).

**Schema change 2026-11-16 (broke the saved scripts; https only, 0 farm relay CU).** `marketPositions` no longer has `itemCount` (use `pageInfo { countTotal count limit skip }`), and `MarketPositionState` no longer has `healthFactor` — it is now a top-level `MarketPosition.healthFactor` Float field (state rows are timestamped history). Querying the old fields returns HTTP 400 `GRAPHQL_VALIDATION_FAILED` naming the missing fields; introspect `__type(name:"MarketPosition")` / `"PageInfo"` to confirm. Working shape: `marketPositions(where:{chainId_in,healthFactor_gte,healthFactor_lte},first:100,skip){ pageInfo{countTotal} items{healthFactor user{address} state{collateralUsd borrowAssetsUsd} market{marketId collateralAsset{symbol} loanAsset{symbol}}}}` (scratch/oneshot_head5.py, run 5b2e19c7).

**Cheaper band pass (measured 2026-11-16).** A nominal-profit leftover (collateralUsd >= debt at oracle, debt >= 50 USD) is essentially confined to HF in (lltv, 1]: below lltv the oracle-valued collateral is worth less than the debt (`coll = debt x HF / lltv`), and the liquidation incentive cap (seize at most debt x incentive worth) cannot fix a shortfall bigger than the debt itself. So instead of paginating every HF<=1 item (ethereum 1756 on 2026-11-16, mostly dust and bad debt), filter server-side `healthFactor_gte: 0.5, healthFactor_lte: 1.0` and keep `borrowAssetsUsd >= 50 and collateralUsd >= borrowAssetsUsd` client-side. 2026-11-16 band census (chains 1/8453/42161/137/10/999): 125/89/235/22/0/62 items in band; every farm-size nominal-profit hit is a closed case except two sub-floor ones — ynETHx/msETH ethereum (attempts 1215: `Morpho.liquidate` reverts panic 0x11, condition-4 reason known) and wbCOIN base (attempts 1210/1257: no real-pool exit); the only new ones are srRoyUSDC/USDC ethereum market 0xacc49fbf58fe (3 positions, 8-10 USD margin each, under the 10 USD net floor) and thBILL/USDC arbitrum (6.8 USD). Chain 999 (HyperEVM) carries a persistent 360-item HF<=1 cluster dominated by the AVLT/USD₮0 market (hf 0.00-0.10, collateral about 5 pct of debt: deep bad debt, zero nominal-profit in band, already there at attempts 1349, and AVNT/AVLT moved only -14 pct in 7 d per coins.llama.fi, so not a fresh crash) — a liquidation class, closed for new scouting.
