trial bot (decision 2026-11-17-cheap-chain-trials): trial-mayan-redeem-arbitrum, delivering Mayan CCTP bridge messages from Base and Ethereum on Arbitrum for the redeem fee.

## What it does

A user who bridges USDC with Mayan's CCTP route calls `MayanCircle.bridgeWithFee(tokenIn, amountIn, redeemFee, gasDrop, destAddr, destDomain, payloadType, customPayload)` on the source chain (`0x875d6d37ec55c8cf220b9e5080717549d8aa8eca`, same address and verified source on every chain). That burns the USDC through Circle's CCTP v1 and publishes a Wormhole message holding the hash of the bridge parameters. On the destination anyone may call `redeemWithFee(cctpMsg, cctpSigs, encodedVm, params)` (no caller check for payload type 1; `MayanCircle.sol:386`): it verifies the VAA, receives the CCTP mint, credits `redeemFee` to `msg.sender` in the FeeManager (`0x6b4d38ed0a555d4516ae81c6c8d9b19f4365b523` on arbitrum, `withdrawFee` pays at once) and sends the rest to the user.

Messages from Base and Ethereum need CCTP standard finality: the source transaction is public 15-20 minutes before Circle attests it. The bot:

1. every 300 s reads `LogMessagePublished` with sender = MayanCircle on the Wormhole core of Base (`0xbebdb6c8ddc678ffa9f8748f85c815c556dd8ac6`) and Ethereum (`0x98f3c9e6e3face36baad05fe09d375ef1464288b`) (both = `MayanCircle.wormhole()` there);
2. keeps the ones whose `MessageSent` CCTP message is bound for arbitrum (domain 3, mint recipient MayanCircle), finds the `bridgeWithFee` arguments in the source transaction's input (Mayan's forwarder nests the call; cross-checked against the burn token and amount of the CCTP message) and skips payload type 2, a gas drop, or a fee under 0.02 USDC;
3. from 780 s (Base) / 720 s (Ethereum) after the source block polls every 3 s: Circle iris `GET /v1/messages/<domain>/<source tx>` for the attestation and Wormholescan `GET /api/v1/vaas/<chain>/<emitter>/<sequence>` for the VAA (both keyless);
4. when both exist, simulates the executor call, and sends it if the fee in USD is above the signed gas cap. `MayanRedeemTake.run` delivers the message, withdraws the credited fee and reverts unless the bot wallet's USDC grew by the whole fee.

Paper mode logs `paper_sim` in place of the send, then looks up who delivered the message and how many seconds after the bot was ready (`paper_outcome.seconds_winner_after_ready`): that number is the trial's question.

Not covered: messages from Sui, Solana, Polygon and Avalanche (delivered 3-18 s after the source block; the farm has no reader for the first two), the Swift `refundOrder` path (caller's share is below gas, attempts:3732), `fulfillOrder` (driver-gated).

## Competition, blocks 524,153,466 (2026-11-14 12:32Z) to 526,489,166 (2026-11-22 10:20Z)

`scratch/trial-mayan-redeem-arbitrum/probe.py 7 400`, `summ.py` (FeeDeposited on the FeeManager, every calldata decoded; `probe.json`): 132 redeems paid 48.73 USDC on arbitrum.

| source (Wormhole chain) | redeems | USDC | median fee | seconds from source block to redeem (min / median / max) | takers |
|---|---|---|---|---|---|
| Sui (21) | 36 | 28.11 | 0.109 | 3 / 5 / 8 | 0x2cad2c5f, 0x04d9634d |
| Solana (1) | 6 | 13.38 | 2.47 | 16 / 17 / 18 | 0x2cad2c5f |
| **Base (30)** | 78 | 5.09 | 0.065 | 999 / 1,224 / 1,854 (one outlier 212,241) | 0x2cad2c5f 74, 0x04d9634d 3, 0xee1a58ea 1 |
| **Ethereum (2)** | 7 | 1.84 | 0.058 | 886 / 971 / 1,155 | 0x2cad2c5f 7 |
| Polygon (5), Avalanche (6), Unichain (44) | 5 | 0.31 | 0.065 | 5-9 (Unichain 1,481) | 0x2cad2c5f, 0x04d9634d |

The bot aims at the two bold rows: 85 messages, 6.93 USDC (0.88 USD/day), all with fee above gas.

- Addresses: `0x2cad2c5f23c9a6137fd7642b45314b033aaafc14` (relayer contract, sender EOA `0x640edda4584cd45c7da77bfefd226335706e1f94`) 81 of 85; `0x04d9634df20aa66b23f114d37c45fa6c6ab76d56` 3; `0xee1a58eafe1977a3d2ae59e2897bb815054f6d58` 1 (a message nobody had delivered for 2.5 days, `0x83e07ba2...`).
- Blocks to take: the message becomes takeable when Circle's attestation and the VAA exist, which no chain records; the on-chain bound is the delay from the source block above (Base 999-1,854 s, Ethereum 886-1,155 s). How many seconds the incumbent needs after the attestation is public is what this trial measures.
- Priority fee level: none. Effective gas price 0.020-0.0284 gwei (median 0.0280) on all 85; winners at tx index 1-4 in 78 of 85 (arbitrum orders first come first served). The bot adds a fixed 0.001 gwei.
- One attempt's gas: median 386,910 gas = 0.018 USD for a delivered message; a lost race reverts `Nonce already used` after about 272,000 gas (about 0.013 USD at 0.028 gwei, ETH 1,700 USD).
- Paid entries in the last 7 days whose gross exceeds one attempt's gas: all 85, e.g. `0x1a208d033652d93ea5126535ecf17d1f13a48fa62e6367ce3eff6ca58df944ce` (0.101166 USDC), `0x29d3e9b2e439f77d4e77ebd1a531887d090913c010f42ccb96b58c5f58e2c617` (0.424 USDC), `0x25b176164b388fec1811e52417ea929a587efa913f4530bc95fcca64dd40a945` (1.125 USDC).

## Fork proof

`python3 scratch/trial-mayan-redeem-arbitrum/proof.py` (one arbitrum fork lease; `proof-result.json`). Reset 525,423,855, the parent of the incumbent's redeem `0x1a208d03...` (block 525,423,856, Base message seq 85598); the incumbent's own message, attestation and VAA go through a fresh owner's fresh executor (fork deployment `0xb464f7314d55ec6a9a0cf6f7f6df17af8ed5b352`):

- non-owner `run` reverts NotOwner: `0xd64384adeb9bced5939f0bc7a73359bdb687d7237953b7f6b236209f9eabc690`
- guard, minProfit = fee + 1: reverts `NoProfit(101166)`: `0x345ffef526ff26b528818ce50faaee9b7b36843255a170c35c9e66ae04d5c1df`, 475,116 gas, owner USDC delta 0
- success: `0x89b1acae4f8eade750697b329c490af06387250615e75d4d2553b54b82f2b68b`, fork block 525,423,859, 426,937 gas, owner +0.101166 USDC; executor holds 0 USDC, 0 native, 0 fee-manager credit afterwards
- repeat reverts `Nonce already used`: `0xd28de3d0ee87cdd6fb7d52e849884313253e4a7649baf7cfdb5588a25dd428a7`, 271,837 gas

`selftest.py` (`selftest.json`) runs the bot's own functions on that message: encoder equals `cast calldata`; the source-input decode equals the incumbent's params; the iris and Wormholescan fetches return the incumbent's exact attestation and VAA; the simulated call at 525,423,855 with the code override returns 101166; at latest it logs `lost_before_send`. `wintest.py`: the winner lookup finds the latest redeem's transaction.

## Loss guard

- Executor: owner-only, `minProfit` = the whole fee, reverts `NoProfit` otherwise; a lost attempt costs gas only.
- Per send: gas limit = estimate x 1.20 (max 1.5m), maxFeePerGas = base fee x 1.30 + 0.001 gwei (max 0.5 gwei); refused when the cap is 0.90 USD or more at 4,000 USD/ETH, or when the fee is not above the cap at the pool price. Typical cap 0.02-0.03 USD.
- `capital_usd` 3, all native gas on arbitrum; profit arrives as USDC in the bot wallet.

## Read cost

Relay: 288 scans a day x 2 chains x (eth_blockNumber 10 + eth_getLogs 75) = 48,960 CU; about 150 source receipts x 20 = 3,000 CU; about 12 arbitrum-bound messages x about 400 CU = 4,800 CU: about 57,000 CU/day = 0.03 USD/day at 1M CU = 0.53 USD. Code cap 95,000 CU/day; every read, the first included, is inside the loop's handler that sleeps to 00:00 UTC on the cap. No feed filter (the Wormhole core is a busy emitter and the wait is 15 minutes anyway).

Outside the relay: Circle iris and Wormholescan, keyless public HTTPS, one GET each per 3 s per due message for up to 30 minutes, then one per 5 minutes; about 9,000 GETs a day in total. The first log rows show `http_check` (both APIs reachable from the bot user or not).

## Logs (`logs/bot.jsonl`)

`start` (executor), `http_check`, `scan`, `opportunity` (a message bound for arbitrum), `source_skip`, `ready` (both attestations seen, seconds after the source block), `paper_sim` / `send` + `send_result` (won or lost, gas used, winner block and tx, blocks after the winner), `paper_outcome` (winner and seconds after ready), `lost_before_send` (already delivered when the bot became ready), `opportunity_skip`, `simulate_revert`, `http_error`, `read_budget`, `loop_error`.
