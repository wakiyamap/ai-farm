trial: Flat Money delayed-order keeper on Arbitrum (cheap-chain trial, decision 2026-11-17-cheap-chain-trials)

# trial-flatmoney-arbitrum

Executes announced Flat Money orders (dHEDGE Flatcoin fork, WBTC collateral) and keeps the
keeper fee the order carries.

- `OrderAnnouncementModule` `0x2326bb21b769d81e134c9b305ca156f989249fe7` emits
  `OrderAnnounced(account, orderType, keeperFee)` (topic0 `0x0aaed4f1...582c`, no indexed fields).
- 5 s later (minExecutabilityAge; expires 60 s after that) anyone may call
  `OrderExecutionModule` `0x7e50ad6e467d9fafc3b4bfd003247ceaa2f17e5b`
  `executeOrder(address account, bytes[] pythUpdate)`; the vault pays `keeperFee`
  (199-262 sat WBTC, about 0.13-0.17 USD) to the caller. The call needs a Pyth WBTC/USD update
  whose publishTime is at or after the executable time.
- The bot takes that update from the farm's local Hermes proxy `http://127.0.0.1:29486`
  (decision 2026-11-18-lanes-hermes-toga; the trial key ends about 2026-12-02, then 401 and the
  bot logs `hermes:` errors and sends nothing).

One transaction through the executor `FlatOrderKeeper` (deployed by the gate, owner = bot wallet):
`executeOrder`, sell the WBTC fee on UniV3 WBTC/WETH 0.05% `0x2f5e87c9312fa29aed5c179e456625d79015299c`,
unwrap, pay the bot wallet in native ETH. It reverts `NoProfit` unless the native gain is at least
`minProfit` (= the send's gas cap), so a lost attempt costs gas only. No principal, msg.value 0.

## Competition, last 7 days (blocks 522693627-525113627, attempts:1835, scratch/trial-flatmoney/timing.json)

| | |
|---|---|
| orders announced / executed / cancelled unexecuted | 50 / 45 / 5 |
| takers | 1: EOA `0x45d83e658e2f70ba83e4e519f792f065c4a01d7d`, all 45, direct call, msg.value 0 |
| seconds from executable to taken | 2-6 (announce + 7 to 11 s, median 8) |
| blocks from executable to taken (sample 19) | median 11, range 7-22 |
| tx index of the take | 1-13, median 2 |
| priority fee | 0 in all 45 (Arbitrum orders first-come, a tip buys nothing) |
| winner's Pyth publishTime minus executable time | 0 s x18, 1 s x22, 2 s x3, 3 s x1 |
| gross per take | 199-262 sat WBTC, median 217 = 0.138 USD; 7-day sum 9,738 sat = about 6.2 USD |
| gas per take | winner 761k gas at 0.02 gwei = 0.027 USD; this executor 877k gas = about 0.032 USD |

What the trial measures: whether a send that leaves about 1-2.5 s after the executable time
(Hermes update published >= executable time arrives about 1.2 s behind the wall clock, then one
simulation round trip and the signer) lands before the incumbent's at 2-6 s. Aim: any share of the
about 6.4 takes per day. The bid: nothing beyond the base fee is useful on Arbitrum; the code caps
`maxFeePerGas x gasLimit` at 90% of the simulated gross and the tip at 20% of it.

## Flow (bot.py)

1. Long-poll the feed: `/logs/arbitrum?address=0x2326bb21...&topic0=0x0aaed4f1...` (about 7 events/day).
2. Per event: executable time = log `blockTimestamp` + 5 s. Read `eth_gasPrice` and the ETH
   reference price during the wait, sleep until the executable time.
3. Fetch the latest WBTC/USD update from Hermes until its publish time >= executable time,
   then `eth_call` + `eth_estimateGas` of `run(...)` side by side (paper: code override at the
   fork address, `executor-runtime.hex`). Retry every 0.35 s, at most 12 simulations / 20 s;
   `OrderInvalid` (0x1bed8430) = someone took it.
4. Send (live) only if `gasLimit x maxFeePerGas` < 1 USD and < the simulated gain; `minProfit` =
   that gas cap in wei. gasLimit = estimate x 1.30.
5. Log who executed the order (`OrderExecuted` on the module) with block, sender and seconds
   after the executable time: `send_result` (live: won / lost, gas used, winner's block) or
   `order_result` (paper / not sent).
6. `gap`, feed error or every 600 s: `eth_getLogs` of the last 280 blocks (70 s, every order that
   can still be live) and handle what is found.

## Read cost (live)

- Feed: 7 logs/day x about 35 CU + about 4 CU/min for the subscription = about 6,000 CU/day.
- Relay: safety poll 144/day x (eth_blockNumber 10 + eth_getLogs 75) = 12,240; per order about
  250 CU (gasPrice 10, 1-3 x (eth_call 26 + estimateGas 20), result lookup 75 + 20 + 20, receipt
  polls) x 7 = about 1,800. Hard cap in code: 60,000 relay CU/day (`CU_CAP`).
- Total about 20,000 CU/day = 0.011 USD/day at 1M CU = 0.53 USD. Hermes reads (about 10 per
  order) are not Alchemy CU.

## Fork evidence

`scratch/trial-flatmoney/proof.py` (lease, reset arbitrum 525070833, deploy, non-owner revert,
NoProfit guard, success +82,602,606,487,086 wei before gas on a 231-sat fee, OrderInvalid after;
output `proof.out`). `scratch/trial-flatmoney/selftest.py` runs this bot's own `handle()` paper path
against the same fork state and reproduces the same gain (`selftest.out`).

## Files

`bot.py`, `run.sh`, `executor-runtime.hex` (eth_getCode of the fork deployment, paper override
only), `logs/bot.jsonl`, `state/`.
