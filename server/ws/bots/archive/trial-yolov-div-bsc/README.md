trial: YoloVerse dividend trigger caller reward on BSC (2,400 YOLOV once every 28,800 blocks, about 3.6 hours; the due block is known in advance).

## What pays

The YoloVerse helper contract's `triggerDivRewards()` (no arguments, no caller check) calls
`YOLOV.sendDivRewardsToNft()` (the token mints the dividend of its NFT holders) and the token mints a fixed
2,400 YOLOV "gas refund" to the helper, which burns 96, sends 48 to a project wallet and 2,256 to `msg.sender`.
It can run once every 28,800 blocks: `YOLOV.getNextDivBlock()` = `lastDivRewBlock()` + 28,800, the call passes from
block `next + 1` and reverts `Not time yet !` before that and again right after a take.

The executor (`DivTrigger.run`) does, in one transaction: `triggerDivRewards()` -> transfer the YOLOV received to
the PancakeSwap V2 YOLOV / WBNB pair (the token keeps 6 pct on a sale; the executor swaps what the pair actually
received) -> WBNB out -> unwrap -> BNB to the bot wallet; it reverts unless the BNB paid out is at least `minProfit`.
Gross per take: 0.000951805 BNB = 0.529 USD (BNB 555.57 USD, coins.llama.fi 2026-11-22 19:55 UTC). No principal.

## Last 7 days of competition (blocks 133,798,526-135,137,407, 2026-11-15 20:20 to 2026-11-22 19:45 UTC by block timestamp)

47 takes, one every 28,801 blocks (12,965 s). 42 landed in the due block itself, 4 one block later (the first of the
47 has no predecessor in the window). Every take is a first-block take, so this is a latency race: a trial only.

| taker (tx.to) | takes | gas price | tx index | note |
|---|---|---|---|---|
| 0x4d33a2b8ee4b2bc1083284d978c0a762e7b6cf0a (EOA 0x93cbe460) | 24 | 0.05 gwei | 1-66, median 11 | the project's own keeper: it also makes all 1,114 small "loyalty" calls; a plain public transaction timed on the block |
| 0xf38c67a72476b23e60700dc0bbad07d7be02ea14 (rotating sender keys) | 19 | 0.055 gwei | 1 in 13 of 19 (2, 5, 6, 8, 9, 85) | pays about 43 pct of the gross to the builder address 0x4848489f inside the transaction (0x636a959c29d39f37958ee01e9fd51cee58e7238bfdb7b58152e0249e60a561ee: 0.000952 BNB from the pair, sender net 0.000498 BNB) |
| 0x9f634fb8a6b5b2208d2e158dae93a67d588e70cb (EOA 0x1ce6fb87) | 4 | 0.0501 gwei | 1, 1, 1, 8 | |

Blocks to take: 0 (42 of 46), 1 (4 of 46). Priority-fee level: 0.05-0.056 gwei signed (BSC's floor); one of the
three bids through a builder payment instead. Sources: `scratch/rfe02/yolo_census.py` (every `GasSpent` log of the
helper), `scratch/trial-yolov-div-bsc/stats.py`, `competition.json`.

What the bot aims at: the 28 of 47 takes that went to plain public transactions at 0.05 gwei. It signs a gas price
of up to 25 pct of the simulated gross (about 0.355 gwei, 7 times the public incumbents) and sends so that the
transaction lands in the due block. Whether a public transaction lands in the intended 0.45 s block from the farm's
signer is what the trial measures; a send that lands early or late reverts at `Not time yet !` for 48,151 gas.

## Timing

The due block is known 3.6 hours ahead. The bot sleeps towards it without reading, polls `eth_blockNumber` every
0.25 s for the last 40 blocks (18 s), simulates the exact transaction 12 blocks before the send point with
`eth_call`'s block override (`number` = due block; the relay passes it on bsc: `scratch/rfe02/yolo_ovr.py`) and sends
at `head >= due - LEAD` without any further read. A second send follows as soon as the head has moved (at most 2 per
window). `LEAD` starts at 5 blocks (2.25 s: the signer alone took 1.25 s on its first timed send, wiki
`methods/timer-first-block-send.md`) and is corrected after each window from the first send's landing block (early:
one less; late: more by the blocks it was late, at most 3), kept in `state/lead.json` between 1 and 12. Each send
logs the signer's latency (`sent.signer_s`). If the reward is already due and untaken when the bot looks, it sends
at once.

## Addresses (BSC)

- Helper `0x97f9388f389e1bb3019935b7939eee50163d9624`: unverified; `YOLOV_ADDRESS()` = the token, `getPair()` = the pair; emits `GasSpent`. Found in the traces of the incumbent's takes.
- YOLOV `0xd084c5a4a621914ed2992310024d2438dfde5bfd`: `symbol()` YOLOV, `getNextDivBlock()`, `lastDivRewBlock()`, `getPairAddress()` = the pair, `WBNB_ADDRESS()` = WBNB, `owner()` = 0.
- Pair `0x526a03728156aea4af6051e47d52e99a818bc087`: PancakeSwap V2 WBNB / YOLOV (the incumbents sell through the PancakeSwap V2 router `0x10ed43c7...`), about 33.5 WBNB deep.
- WBNB `0xbb4cdb9cbd36b01bd1cbaebf2de08d9173bc095c`.

## Read cost

Per window (6.7 a day): about 6 schedule reads (36 CU each), at most about 100 head polls of 10 CU, one simulation
(26 CU), one winner lookup (26 + 75 CU) and, live, receipt polls (at most 50 x 20 CU): about 2,300 CU live, 1,300
paper. Per day about 15,000 CU = 0.008 USD at 1M CU = 0.53 USD; the bot stops reading at 60,000 CU a day. No feed
filter (the trigger is a block number known in advance).

## Loss bound

Per send: gas limit 900,000 x the signed gas price (at most 0.8 gwei, normally about 0.355 gwei) = at most
0.00072 BNB = 0.86 USD at the bot's conservative 1,200 USD per BNB (0.40 USD at 555 USD), normally 0.00032 BNB.
What a lost send really costs: 48,151 gas = 0.000017 BNB = 0.01 USD. A won send costs 669,733 gas = 0.00024 BNB of
the 0.00095 BNB gross. `minProfit` = the larger of the gas cap and half the simulated gross, so a transaction that
does not pay for its own worst-case gas reverts. At most 2 sends per window, 6.7 windows a day: at most about
0.13 USD a day when every send loses.

## Fork proof

`scratch/trial-yolov-div-bsc/proof.py` (one BSC lease; reset to 135,131,935 = the parent of the incumbent's take
0x636a959c...): success `0x8f9bc2283e2c4eb6f94591e0ce974efb2e55d6e6a2efcb57862d0026e5cfca9e` (fork block 135,131,939, 669,733 gas): owner BNB
+0.000884832 net of gas, gross 0.000951805 (the incumbent's own amount to the wei), executor left with 0 BNB / WBNB /
YOLOV. Guard (minProfit 1e24) `0x8a9f2f21583605ddffe95e661c43b82027cf66ca309d161d3a0e9ce809c96ac9`: revert `NoProfit(951805330073073)`, gas only. Repeat right after
the take `0xba57edae8de02df0493b18b29d183d1e86ec187fedfaafda2971add383569730`: revert `TriggerFailed("Not time yet !")`, 48,151 gas. Non-owner
`0x11ff89ba896f1754f60d4be3d5de0e9ff61956d8ad747ea64853a3481b571fb9`: `NotOwner`. Paper path: `selftest.py` (the bot's own `eth_call` with the code
and block overrides: 0.000951805 / 0.000951913 / 0.000952022 BNB at the due block of the last three takes, 0 one
block earlier, 0 after the take).

## Logs (`logs/bot.jsonl`)

`start` (executor=...), `wait`, `check` (nothing to take), `opportunity` (gross, bid, cap), `opportunity_skip`,
`paper_sim` + `paper_outcome` (paper: who took it, tx index, blocks after the due block), `send_result` (live, one
per send: won / lost, `lost_why` early / late / outbid_same_block, gas used, landing block, winner block, index and
caller), `signer_reject`, `read_budget`, `loop_error`.

## After the trial

Write sends, wins and net as an `attempts` row; lead: win rate and net per day, or `blocked_infra` with how many
blocks early / late the sends landed and the tx index of the winners.
