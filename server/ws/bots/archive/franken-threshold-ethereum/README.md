# franken-threshold-ethereum

Threshold bidder for frankencoin MintingHub **Dutch challenges** on ethereum (lead 74,
decision `decisions/human/2026-11-16-franken-threshold-bid.md`). Builds on the
fork-proven executor shape of `bots/archive/franken-dutch-tail-ethereum`
(DutchFlashTail) with a `deadline` argument and a returned profit value.

## Mechanism (one line)

A challenged position's collateral is sold by `hub.bid(num, size, false)` at a Dutch
price that decays linearly from `liqPrice` at `start+phase` to 0 at `start+2*phase`
(`hub.price(num)`, hub `0xDE12B620A8a714476A97EfD14E6F7180Ca653557`); the bidder pays
ZCHF and takes the collateral — wiki `mechanisms/frankencoin-challenge-auction.md`.

## Strike rule (decision §1)

- Wake on `ChallengeStarted` (topic0 `0xc4b384b2...85f5`, `number` = data word 1);
  while a challenge is open, **once per block** simulate the full executor bid at head
  (eth_call of the pinned runtime); do not read per block while idle.
- The simulation **returns the USDC profit** (collateral sold on the real UniV3 pool −
  ZCHF offer − flash premium; gas excluded). Send when
  `net = profit − signed_gas_bound >= max(25 USD, 3 x signed_gas_bound)` — i.e. take it
  at a line **below** the incumbent `0xd694da17...` (their line: gross 630–1350 ZCHF,
  13–26 s after takeable, attempts:1383), not beside them. The 25 USD figure is the
  decision's guideline; the reviewer may adjust it (see num 10 below).
- One tx: Aave V3 USDC flashLoanSimple → USDC→USDT→ZCHF → `hub.bid()` → sell collateral
  to USDC on a per-call UniV3 exit pool → repay → revert unless profit ≥ minProfit →
  USDC profit to the wallet in the same tx. `maxOffer` = 2× the simulated offer + 1 ZCHF.
- Post-expiry bids (the num-10 form, offer floored at 0) ride the same path.

## Why private

`send_route: private` (decision 2026-11-15-private-send.md): the public mempool copies
this exact bid (the incumbent watches the same event). The entry takes a `deadline`
block (head+3, fork-proven `Deadline()` revert); after sending the bot polls the
receipt to the deadline and logs `private_not_included` if none. Never pays coinbase.

## Occurrences (30 d window 2026-10-16 .. 11-15; per decision §2 both figures are listed)

Fork-proof rule (decision): the state **one block before** each incumbent winning block
is replayed with this exact executor (lease-releasable script
`scratch/franken-threshold/proof.py`).

| num | collateral | incumbent win | block−1 fork replay | counted EV? |
|---|---|---|---|---|
| 8 | 2.0 WETH | blk 26293524, 13–26 s after takeable | **success, owner USDC +2434.36** (tx `0x6199ea89…`, gas 692,787) | **yes** — threshold crossed ~1–2 blocks after the market cross, ≥1 block before the incumbent |
| 9 | 0.1 BTC.b | blk 26311563 (T+12) | **FlashShort revert** (tx `0xe8e86bcf…`) — not yet profitable one block earlier | tie in the winner's block, NOT counted (same-block net +750 USD per attempts:1383) |
| 10 | 0.0107 WETH (60 s phase) | blk 26327481 post-expiry | **success, owner USDC +24.65** (tx `0xc468a784…`, gas 435,656) | net 24.65 < 25 floor → does not fire at 25; a floor ≤ 24 counts it 1 block ahead |

Same-block figures (regrade attempts:1383, block-boundary spot, not counted per the
decision): +1610 / +750 / +24.5 USD at T+12 for nums 8/9/10. Counted 30-day EV at the
25 floor: one occurrence (num 8 class) of ~10²–10³ USD net, gas ~0.2–0.5 USD/tx at
signing; cadence 3 challenges / 30 d in Oct–Nov 2026 (12 total 2025-04..2026-11-13).

Guard reverts proven on the fork (all three states): `Deadline` `0xc6f221aa`,
`NotOwner` `0x30cd7471`, `AboveCap` `0x4d1dd389`, `FlashShort` `0x69b5651a`,
rebid-after-success `NoChallenge` `0xf75693b6`; pre-cross states revert FlashShort /
AboveCap (offer above market = nothing to take). Executor ends with zero USDC/token/
ZCHF/USDT and zero approvals on both successes. Deploy gas 1,802,518.

## Loss bound

No principal: the flash loan is sourced and repaid inside the tx; an accepted call
reverts unless the executor's USDC ends above borrow + premium; wallet worst case =
`GAS_LIMIT 1,200,000 × maxFeePerGas` clamped ≤ **8 USD** at a fresh UniV3 USDC/WETH
price (L ≤ 50; 3× bound ≤ 24 < 25 keeps the strike rule's second condition honest).
A private send never included costs nothing. Stop line (decision §3): 3 consecutive
live failures (revert or not included) → `state/STOPPED.json`, recommend stop.

## Reads

Idle: 30 s poll × 2 reads ≈ 6k CU/day. Challenge-open (≤ ~48 h each): 12 s poll ×
(block + `challenges()` + full-bid eth_call + offer read) ≈ 250k CU per open day;
expected ≈ 0.06 USD/day, worst case ≈ 0.27 USD/day — at 0.53 USD/1M CU.

## Waiting state

Challenge 11 (the one the human asked about, started blk 26403144 2026-11-13 02:47:11Z):
**taken at blk 26410802 2026-11-14 04:22:47Z = expiry+1.59 h by generalist 0x2ff82bd2
via router 0xbc034f23** (ChallengeSucceeded `7d3a26e8`), gross ≈ breakeven-at-open class.
Head has no challenge open (26425159). Small challenges are taken slowly; the 13–26 s
competition applies to the large ones — R = 12 s stays adequate (attempts:1386/1383).
