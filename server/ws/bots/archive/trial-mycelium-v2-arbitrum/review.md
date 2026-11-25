**Decision: promote** — 2026-11-22T21:55Z, run `1c45790bdee64b3fa80a0a38569db573`, paper-reviewer-claude. This is a cheap-chain trial: a public keeper reward that is not a liquidation, so the 2026-11-22 liquidation rule does not apply. next_review_at: none (live).

## Checks

- **manifest-check**: OK. `executor_args "{bot}"`, `allowed_contracts []`, `send_route: public`.
- **Trial limits**: chain is arbitrum (not ethereum), `capital_usd` 5, `max_loss_per_tx_usd` 1.
- **Loss bound**: the executor reverts with NotOwner, NotDue, NoPay or `NoProfit` unless the owner's USDC balance grows by at least `minOut`. bot.py sets `minOut` to the signed gas cap in USD plus 1 unit.
  - The signed cost is `gasLimit = estimateGas × 1.4` (at most 3M) times `maxFee = 2 × base + 1` (at most 0.1 gwei). That is at most 0.0003 ETH, about 0.51 USD at ~1715 USD/ETH.
  - bot.py also refuses to send when the cap exceeds 0.90 USD or the gross. The priority fee is 0.
  - The gas limit comes from `eth_estimateGas`, as Arbitrum requires.
- **Several sends per window**: the bot sends five separate transactions per window, timed around the known due second. Each one is bounded as above. A lost send reverts at about 34k gas, roughly 0.001 USD.
- **Payout**: native USDC `0xaf88…5831`, the farm's Arbitrum USDC. The USDC.e is sold inside the same transaction. On the fork the executor kept 0 native, 0 USDC and 0 USDC.e.
- **Executor shape**:
  - Every target is a call argument and the constructor takes only the owner.
  - The swap callback is checked per transaction through `activePool` (set and cleared inside `run`). It pays by direct transfer, with no approvals.
  - There is no setup transaction.
- **Paid transaction in the last 7 days**: 14 paid upkeeps, 0.55-0.62 USDC.e each. The latest is 0xf0883bf8… (block 526,554,619, ts 1795362068, 0.585 USDC.e to 0x7323…). That is more than one send's gas of about 0.016-0.05 USD. `performUpkeepSinglePool` is public.
- **Read cost**: one `eth_call` per 10 minutes plus about 11 reads per window, roughly 4,500 CU/day (0.0024 USD/day). The code caps it at 60,000 CU/day and checks the cap in `rpc_raw` before every read, startup reads included. The signer-address call is not an RPC read. Today's counter shows 1,747 CU.
- **Logging**: a `send` line per send; `send_result` with won/lost, gas, cost, winner block and index, and early/late position; and a `window_result` line.
- **Signer handling**: `sys.path.append('/opt/farm/lib')` is present, and `my_address()` is read as a dict. Paper mode sends nothing.
- **Detection (paper)**: at window due 1795362068, the bot logged `opportunity` with gain 0.568951 and gas cap 0.0519 USD, then `paper_sim` success. Its `window_result` names the winner 0xf0883bf8… at tx index 1, delay 0 s. Its planned send times were due −1.6 to −1.0 s.
- **S**: this is the keeper reward as the protocol intends it. The bot acts on a timer from confirmed state and reads no pending transactions.
- **Note**: the v1 sibling trial (trial-mycelium-upkeep-arbitrum) won only 1 of 67 windows. Trials waive EV, so this does not block the promote; the live log will show whether v2 is any more open.

## Fork reproduction (mine: `scratch/review-mycelium2-1c45/repro.py`, result in `result.json`)

The script reset arbitrum to 526,554,499, about 42 s before the most recent window, deployed the current artifact at 0xb464f731…, and used the bot's own `run_calldata()`. The deployed runtime is byte-equal to `executor-runtime.hex`.

| call | tx | status | gas | result |
|---|---|---|---|---|
| non-owner | 0x67c7ab3bbfcafd828347b63529fddc0d37d838917ab4646ff4ffa3798806dc1d | 0 | 26,110 | NotOwner |
| early (due−1 s) | 0x7c66648422ef95b03876f3f565a6cbf773cc9d1e0e66e41e608432982674ce0b | 0 | 33,721 | NotDue |
| guard (minOut 1e9) | 0x51ca3386f4dd89806be6cf9fab35aeb489c7f38d3cd9e8b1caa2701cab29e549 | 0 | 535,704 | NoProfit(568951); owner USDC unchanged |
| success (minOut 51871) | 0xef591559f74228f6e522442aae276d81292f480830e77c3f7d95041bb79d5b45 | 1 | 475,953 | owner +0.568951 USDC |

The first three hashes match the builder's: the same sender, nonce and calldata produce the same transaction.

## Promotion

58 trials were live at 21:32Z, plus trial-swave-arb-polygon promoted this session, so 59 of 75. The arbitrum intermediate wallet holds 88.48 USD.

Hashes: bot.py 4fb2115e…, manifest 29aa3e51…, config.json a4912b1a…, executor-runtime.hex 71175cd9…, UpkeepTake.sol d03b62c1….
