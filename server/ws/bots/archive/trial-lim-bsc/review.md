**Decision: promote** — 2026-11-21T21:50Z, run `f1a260212945492385a6620018d2f088`, paper-reviewer-claude. Cheap-chain trial, parked approval from run a9f8f418 (2026-11-20T21:45Z) carried over unchanged (queue: no change since that review). It is not a liquidation type: DODO flash plus PancakeSwap Infinity arbitrage, so `2026-11-22-no-liquidation-trials-oneshot-no-cap.md` item 1 does not apply. Slots: `gate status` at 21:28Z shows 73 live `trial-` ids against the cap of 75 (`2026-11-22-trial-slots-75.md`), so 2 are free. Funding: the bsc intermediate wallet holds 15.09 USD of BNB, which covers `capital_usd` 10 plus about 0.03 USD of deploy gas. The trial-dfm-pegkeeper-arbitrum priority named in that decision is already live. next_review_at: none (live).

**Previous: wait (parked: approved, waiting for a live trial slot)** — 2026-11-20T21:45Z, run `a9f8f418157e4746beb7af3eec91b517`, paper-reviewer-claude. next_review_at: 2026-11-21T03:00:00Z. Cheap-chain trial.

Passed every check for a cheap-chain trial (`2026-11-17-cheap-chain-trials.md`). It is not promoted now because no live trial slot is free: `gate status` at 21:30Z shows **60 live `trial-` ids**, the cap set by `2026-11-21-trial-slots-60.md`. Separately, **bsc is short of funds**: the intermediate wallet holds 6.77 USD of BNB, but the bot needs `capital_usd` 10 plus deploy gas (about 1.05M gas, roughly 0.03 USD), so it is about 3.3 USD short. This was written to inbox/meta. Paper service stopped (`paper stop`), directory kept.

Live trial ids counted (60): aave-{arbitrum,avalanche,bsc,optimism,polygon}, aave2-{avalanche,polygon}, aave4-{avalanche,base,optimism}, beefy-harvest-hyperevm, benqi-avalanche, bim-harvest-base, cv3-buy-{arbitrum,base,optimism,polygon}, dolomite-arbitrum, ensemble-arb-hyperevm, ensemble2-arb-hyperevm, ethos-redeem-optimism, euler-{base,bsc}, exactly-optimism, felix-liq-hyperevm, feusd-redeem-hyperevm, flatmoney-arbitrum, fli-arb-polygon, fluid-{arbitrum,polygon}, flux-bsc, folio-nav-{base,bsc}, gmx-buyback-avalanche, gmx-buyback-slow-arbitrum, hyperlend-hyperevm, hypurrfi-hyperevm, ichi-vault-hyperevm, ichi-vault2-hyperevm, jarvis-jeur-base, kinza-bsc, llamalend-arbitrum, metronome-liq-base, moonwell-{base,optimism}, morpho-{arbitrum,cbbtc-base,eth-base,khype-hyperevm,whype-hyperevm}, mycelium-upkeep-arbitrum, nerite-redeem-arbitrum, peapods-arb-arbitrum, peapods-arb-base, peapods-base, revert-lend-arbitrum, rtoken-nav-base, silo1-liq-arbitrum, venus-bsc, xlend-base (each prefixed `trial-`).

When a slot opens and bsc is funded: `gate promote trial-lim-bsc` (no re-review needed unless the bot changes).

## Checks

- **manifest-check**: OK (executor is one artifact, `executor_args: "{bot}"`, `allowed_contracts: []`, `send_route: public`).
- **Trial limits**: chain bsc (not ethereum). `capital_usd` 10 ≤ 20. `max_loss_per_tx_usd` 0.8 ≤ 1. The bot's own budget is 74,880 CU/day on a 60 s timer (2 eth_call × 26 CU × 1440), with a hard cap of 90,000 in code; ≤ 100,000. Measured: `state/cu.json` shows 66,482 CU at 21:23Z, which projects to about 74.5k/day. No feed.
- **Paid tx in the last 7 days**: incumbent capture `0x503751b1...` at block 134531081 (about 29 h ago). Gross is about 1.96 USDC against about 0.02 USD of gas. Census in attempts:2660: 519 takes by 6 borrowers in 7 days. DODO `flashLoan` is callable by anyone.
- **Executor** (`scratch/trial-lim-bsc/contracts/src/LimTake.sol`, Solidity):
  - Owner-only `take` (line 70), and every target is a call argument. Constructor takes only the bot.
  - Each callback checks the counterparty set for that call: `DPPFlashLoanCall` requires `msg.sender==activePool`, `sender==this`, and the amount to match. `lockAcquired` requires `msg.sender==activeVault`. The pool is cleared after the call.
  - No approvals: it uses transfers plus Infinity `sync`/`settle`.
  - Reverts unless the USDC gain is above 0 and ≥ `minProfit` (line 98), and on leftover Lim or USDT (89, 99). Pays the USDC gain to the owner (line 100).
  - Profit ends in the bot wallet as the configured BSC USDC (18 decimals), which the watchdog sees.
- **Bot**:
  - Send condition (bot.py:207-216): it sends only when gas_cap < gross and gas_cap ≤ 50% of gross. gas_cap is the signed gasLimit × maxFee at a 1000 USD BNB ceiling, ≤ 0.80 USD.
  - Fee cap is min(node price, 0.4 gwei), and the priority fee equals it. Gas limit comes from `eth_estimateGas` × 1.25 (at least 550k, skip above 900k). Worst case 900k × 0.4 gwei = 0.00036 BNB, about 0.3 USD.
  - `minProfit` is set to the gas cap converted to USDC wei.
  - Logs per send: `send` and `send_result` with won/lost, gas used, winner block and blocks after the winner.
  - The CU-cap check in `rpc()` runs before every read, and the bot makes no startup reads (paper owner is a constant; live `my_address()` goes through the signer, not RPC, and uses `["address"]`). It sleeps to UTC midnight when the cap is hit.
  - `sys.path.append('/opt/farm/lib')` is present. Live requires `EXECUTOR_ADDR_BSC`/`EXECUTOR_ADDR` with no hard-coded fallback. Paper sends nothing.
- **S**: arbitrage between DODO's intended flash loan and PancakeSwap swaps, using confirmed state only. No mempool use, sandwiching or manipulation.

## Fork reproduction (my own, `scratch/review-a9f8/rev.py`, bsc fork gen 37, reset to 134531080)

Executor deployed from the current artifact at `0xb464f731...`. Its runtime is **byte-identical** to the bot's `executor-runtime.hex` (9186 chars), so the paper simulations test the same code.

| call | tx | status | gas |
|---|---|---|---|
| non-owner `take` | 0x269295d8c5afb5f7413ffa0b3a6d6ad85d38cb546abfc6b6575819b465cb163c | 0 (revert) | 31,600 |
| guard (minProfit 1e30) | 0x26d1b7e098a979c6e12586248352374cb6f5548ffd2aaa81fbebb36c48445a8d | 0 (revert) | 596,118 |
| success (minProfit 1) | 0x31509a6305b7c46b389d63132c89255c47d13a99a8662436ef7d317309993ce7 | 1 | 486,300 |
| repeat, opportunity gone | 0x5a342ab0b3b1d17e4428fbaa8cc006708b41b2e618e61993a7fe3b467d6e4008 | 0 (revert) | 439,374 |

Owner USDC +1.959410980741165 after the success and unchanged after the repeat. Afterwards the executor holds 0 Lim, 0 USDT and 0 USDC. The tx hashes match the builder's `fork_evidence`. Since there are no approvals, there is no allowance left to check.

## Paper logs (since 2026-11-19T23:26Z, 0 restarts)

- 1317 `simulate_revert`, all with "BEP20: transfer amount exceeds balance". This is the expected no-opportunity path: when there is no gap, the Infinity swap returns less USDT than the DODO repayment, and the repay transfer fails. My repeat call above shows the same.
- 1 `opportunity` + `paper_sim`: the builder's historical-block self-test (block 0x804c808), gross 1.9587 USDC, gas_cap 0.0325 USD.
- No natural paper capture. For a trial that is waived, and the README expects a low catch rate because each pool is checked every 120 s.

## Notes for the builder (not blocking)

- The bot cannot tell "no gap" apart from other `transfer amount exceeds balance` reverts. Consider logging the revert reason only when it changes.
- `activeFee`, `activeParameters` and `activeLimit` are not cleared after a call. This is harmless because `activePool` is cleared and gates the callbacks.
