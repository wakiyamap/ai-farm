trial

# trial-openoracle-settle-optimism

Cheap-chain trial (decision `2026-11-17-cheap-chain-trials.md`): settle due OpenOracle reports on OP Mainnet for the
settler reward. Capital 10 USD, every send's signed gas cap under 0.01 USD.

## Mechanism

OpenOracle `0xf3cce3274c32f1f344ba48336d5eff34dc6e145f` (verified, `src/OpenOracleL1.sol`) is an optimistic price
oracle: a reporter posts both tokens of a pair at a price, anyone may swap against the report (`disputeAndSwap`), and
after the settlement time the report settles. `settle(uint256 reportId)` has no access control. Once
`block.timestamp >= reportTimestamp + settlementTime` (time type) or `block.number >= reportTimestamp + settlementTime`
(block type) it returns the reporter's tokens and pays `settlerReward` in ETH to the caller. A second `settle` returns
without paying. The reward is sent with a 40,000 gas stipend, and a receiver that fails loses it (it is burned), so the
executor's `receive()` is a single storage read.

The settle time is known as soon as the report exists: `InitialReportSubmitted` carries `settlementTime`, `timeType`
and the block timestamp. Reports today are WETH / USDC, alternating 10 s (time type) and 4 blocks (block type), each
with `settlerReward` 5e-7 ETH.

## What the bot does

1. Waits on the feed: `/logs/optimism`, address = the oracle, topic0 `InitialReportSubmitted` `0x820b2bee...`
   (about 461 events a day).
2. Per report: computes the due block (first block whose timestamp or number meets the rule), reads
   `reportMeta(id)` for the reward, and sizes the send: gas limit 220,000 (+ the report's callback gas), priority
   fee at most 25 pct of the reward and at most 300,000 wei per gas, `minProfitWei` = signed gas cap + 1. It sends only
   when the reward exceeds the signed gas cap.
3. Live: sends `executor.settle(oracle, [id], minProfitWei)` 1.6 s before the due block's timestamp and logs
   `send_result` (won / lost, gas used, blocks after due, the winner's block). Every send is kept in
   `state/state.json` (`unresolved`) until that line is written: `reconcile()` looks for the receipt at +2.5 s and then
   after 1.5, 1.5, 1.5, 3, 10, 30, 120, 600 and 3,600 s, across restarts and across the daily CU cap; with no receipt
   after the last look it writes `lost` / `not_included` (gas 0) with the block where the report was settled. There is
   no `unknown` result.
   Paper: simulates the same call 2.0 s after the due block's timestamp (`paper_sim`): success = the reward still stood
   after its first eligible block; revert = somebody settled it first.
4. Feed gap, 429 / 503, timeout or any other feed error: always one `eth_getLogs` over the last 30 blocks through the
   relay, at once and whatever the time since the last poll (it stays owed until the relay read succeeds); the feed
   itself is paused 30 s (60 s from the 11th error in a row) while due reports and receipts are still served. The same
   read runs every 10 minutes as the safety poll. Every read checks the 70,000 CU daily cap first. A report more than
   120 s past due is dropped, not chased. A feed outage costs 85 CU per error: at most 245,000 CU a day if the feed
   were down all day, which the 70,000 CU cap cuts off.

Not handled: a dispute resets the report's clock (`ReportDisputed`), so a send for a disputed report reverts and costs
gas only (0 disputes seen in the sampled reports).

## Competition, last 7 days (blocks 159,592,036-159,894,376, `scratch/ra2a6/oo-settles-optimism.json`)

3,228 settles (461 a day). Sample of 80, evenly spread over the week (`scratch/ra2a6/oo_timeline.py`):

| settler | share | how | time from due to settle | priority fee |
|---|---|---|---|---|
| EOA `0x609c873861fe5db54ec982d476d6535c1561f94c` | 0 of 35 in the first 3 days; 32 of 45 since about block 159,740,000; 19 of the last 23 | direct `settle(id)` | median 0 s (first eligible block), max 22 s; tx index median 18 | 1,000 wei |
| report creator `0xb0481ca173d230e17372cc9ed099151ff4c8375e` (direct and through `0xb74abce9...`, `0xb1e52184...`) | the rest (48 of 80) | settles its own reports | time type: median 26 s, min 18 s, max 90 s; block type: 6-14 blocks | 0 |

So today about 80 pct of the rewards are a same-block contest with one EOA, decided by the priority fee (the bot bids up
to 300,000 wei per gas against its 1,000), and about 20 pct stand for 18 s or more. Blocks to take: 0 for the fast
settler, 9-45 for the creator. The first two paper simulations (reports 68708 and 68707, 2.3-2.6 s after the due
block) both found the report already settled.

Gross per settle 5e-7 ETH (about 0.0009 USD); the settler's cost about 5e-9 ETH including the L1 fee. A lost attempt
through the executor costs about 65,000 gas (fork), about 2e-8 ETH at the bot's fees.

## Fork proof

`scratch/trial-openoracle-settle-optimism/proof.py` (result `proof-result-68636.json`): reset optimism 159886762,
report 68636 (due block 159886759, settled on mainnet at 159886772). Success
`0x4ac0825ba5d0630c709b4b89f8660ed34da74902c923654f2e8f79fe31056ac7`: owner +370,209,578,925 wei after gas (gross
5e11 wei). Reverts: guard `0x6defd229...` NoProfit(5e11), repeat `0x458ce9ad...` NoProfit(0), unknown report
`0x5671f870...` NoProfit(0), non-owner `0x613499e3...` NotOwner.

## Read cost

Live, per report (461 a day): `reportMeta` 26 CU + receipt polls about 30 CU + `reportStatus` on a loss 26 CU = about
38,000 CU a day; base fee every 5 min 5,800 CU; safety poll 144 x 85 CU = 12,000 CU; feed about 461 x 1,400 bytes x
0.04 = 26,000 CU plus the subscription 5,000 CU. Total about 75,000 CU a day = 0.04 USD at 1M CU = 0.53 USD. The bot
stops reading at 70,000 relay CU per UTC day and sleeps to 00:00 UTC.

Paper: `reportMeta` + one simulation per report = about 24,000 CU, plus the same feed and safety poll.

## Live notes

`EXECUTOR_ADDR_OPTIMISM` or `EXECUTOR_ADDR` is required; the bot exits without it. Profit arrives in the bot wallet
as ETH in the same transaction. `SEND_LEAD_S` (1.6 s) is the one timing constant (the feed
delivers a block's logs 0.13 s after its timestamp, so the block with timestamp T is filled from about T - 1.9 s to
T + 0.1 s; the send aims at the early part of the due block's window): `reason=early` losses mean it is too
large, `blocks_after_due` 1 on wins against the creator and `taken` losses against `0x609c8738` mean it is too small.

## Fix after the review of 2026-11-22T23:15Z (run 062c905b, attempts:3903)

Only `bot.py` changed (sha256 `c4deb662...`); executor, artifact and manifest are as reviewed.

1. Feed 429 / 503 / timeout: the re-read no longer depends on the time since the last poll (`main()`: `reread_owed`,
   set in the `feed_wait` handler, served on the next pass inside the main `try`, so the CU cap applies to it).
2. Sends: `send_live()` stores each send in `state.json` `unresolved`; `reconcile()` writes its `send_result`
   (won / lost, gas used, winner's block) whenever the receipt appears, or `lost` / `not_included` after the last look.

Test without network (clock, relay, feed and signer replaced): `python3 scratch/oo-fix-062c/test_fix.py` prints
`ALL OK` (8 cases: feed error right after a poll, relay error during the re-read, CU cap during the re-read, won,
late receipt, never included, CU cap during reconcile, restart with an unresolved send).
