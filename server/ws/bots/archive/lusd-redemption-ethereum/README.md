# lusd-redemption-ethereum

Liquity v1 public LUSD redemption, copied from the incumbent executor bots
(ledger source `liquity_v1.redemption`; winner tx
`0x59e91ae68f87fc21905e4645ff916aab0c37d07d324d97f595cee99d31f5473e`, block
26300833, its executor `0xf00003bf2dcfeb166e3dee7d0e0fff197cdfcabd`).

## Mechanism

Anyone may call `TroveManager.redeemCollateral` (TroveManager
`0xA39739EF8b0231DbFA0DcdA07d7e29faAbCf4bb2`): it burns LUSD against the
troves' ETH collateral at the Liquity `PriceFeed` price
(`0x4c517D4e2C851CA76d7eC94B805269Df0f2201De.fetchPrice`), and the redeemer
sells the ETH for stablecoin at the market. The trade is only profitable when
the Uniswap V3 WETH/USDT pool price per ETH (`0x4e68Ccd3E89f51C3074ca5072bbAC773960dFa36.slot0`)
exceeds the oracle price by more than the acquisition + exit slippage. The
measured farm-size breakeven is a premium of 1.0814x (attempt 1127: LUSD
acquisition 1.0695 USDT/LUSD via the incumbent cStable LP -> Curve ->
cStable route and the LP virtual price 1.04326; our fork-measured executor
margin is 1.935 USDT per LUSD redeemed at the 327,764-LUSD proof size: flash
in 342,513.56 USDT, swap out 348,862.51 USDT, delta 6,348.95 USDT, tx
`0x032581144b391b0d2eb93ee86f667e8d3aa5fc0bfa41c1ddc6abc84738c308a7`). At the
bot's 3,000-LUSD farm size the measured margin is NOT linear in the premium:
the same route REVERTS at premium 1.26264 in the fee-burned state after the
2026-10-29 morning redemptions burned 2.04M LUSD of debt (tail-trove fees up
to the 50% cap), so the bot sends only at premiums where a 3,000-LUSD success
was measured on the fork.

Each redemption raises the base rate, so the oracle price falls behind the
market after every one and the premium window opens again over the following
days. The bot polls every 4 minutes (the measured window is minutes wide, see
windows below), reads two prices, and when `premium >= 1.0814` recomputes the
redemption hints (`HintHelpers.getRedemptionHints` at the current
`fetchPrice`, plus the `getApproxHint`/NICR bracket walk on `SortedTroves`)
and calls the executor in one transaction.

## Read cost

Poll every 240 s, 2 `eth_call` reads (PriceFeed.fetchPrice, pool slot0) per
poll = 360 polls/day x 2 reads = 720 reads/day = 360,000 CU/day = 0.19 USD/day
at 1M CU = 0.53 USD (the earlier 720,000 double-counted the poll interval). The hint path (5 extra reads, up to ~40 reads on the NICR
bracket walk) runs only inside an open window; with the measured cadence
(0.37 redemptions/day) the hints add at most ~25k CU/day. Below 1M CU/day.

Paper mode sends nothing (relay reads + log lines only). Live mode adds the
500 CU `eth_call` guard per try (a few per day) and the signer send.

## Windows (class per capture, decision 2026-11-14-race-rule-seconds.md)

The bot is a **polling bot**: R = 240 s poll + send-to-inclusion (~12 s) =
252 s. T = the block where the premium crossed the farm route's breakeven
(premium 1.0814): for the 2026-10-29 window the crossing block 26300829 was
measured in attempt 1127; the two ledger captures get crossing brackets from
the `proof12.py` premium probes (parent - k blocks, k = 1/10/21/40/80/160),
and the two 2026-10-19 captures from the `proof14.py` probes (k = 1..1280):
their premium never reaches the breakeven anywhere in the 1,280 blocks (~2.6 h)
before the capture, so they were never in our window at all.
Class: out = taken before L (first block >= T + R); trial only = taken less
than R s after L; counted = taken at least R s after L.

Per-occurrence table for the trailing 30-day window 2026-10-19..11-14 — 11
captures: 8 from the `scratch/lusd-4170/events.json` scan (blocks 26227311..
26383264, receipts with gas), 2 in the ledger source `liquity_v1.redemption`
(26383264 is in both), and 26410255 from the ledger (receipt
`scratch/lusd-exec/receipt-26410255.json`). Farm columns are measured at the
bot's 3,000-LUSD size on the fork at each capture's parent block
(`proof12.py` for the Oct29/Nov parents, `proof14.py` for the two 2026-10-19
parents); the incumbent's own gross/net (USD at the block oracle price)
stays in the context column. Farm gas = the 0.026 ETH signing cap valued at
the parent-block oracle price (Oct29: 59.5 USD; Oct19: 62.1 USD - above the
50 USD L bound, the signer would refuse those sends; Nov: ~49 USD).

| block | LUSD (incumbent) | secs vs crossing | class at R=252s | incumbent net USD | farm gross USDT pre-gas | farm net USDT |
|---|---|---|---|---|---|---|
| 26227311 | 37,869.13 | premium 1.0114 at parent (probe) | below breakeven, never in a window | 15.85 ETH drawn (2026-10-19 14:46:47Z) | REVERT 'below minProfit' (parent 26227310, tx 0xd6f834ba..., proof14) | 0 |
| 26227312 | 30,081.01 | premium 1.0117 at parent (probe) | below breakeven, never in a window | 12.59 ETH drawn (2026-10-19 14:46:59Z) | REVERT 'below minProfit' (parent 26227311, tx 0xfb27dac0..., proof14) | 0 |
| 26300824 | 217,629.84 | taken 60 s BEFORE the crossing block | out (speed race) | 95.0 ETH drawn | not measured | - |
| 26300830 | 1,384,041.73 | +12 s | trial only | -0.9 | not measured | - |
| 26300833 | 326,881.83 | +48 s | trial only | -0.8 | 84.9 measured (parent 26300832; success tx 0xe9881aba, +82.49 after 1 gwei fork gas) | +24.9 after the 0.026 ETH cap at the proof price |
| 26300839 | 327,764.18 | +120 s | trial only | -1.1 | not measured | - |
| 26300876 | 216,931.74 | +564 s | counted | +2,757.2 | REVERT 'TroveManager: Unable to redeem any amount' (parent 26300875, tx 0xcd7c2f2e..., premium 1.26264) | 0 |
| 26300990 | 36,827.25 | +1,932 s | counted | +155.9 | REVERT same reason (parent 26300989, tx 0xd717d701..., premium 1.2986) | 0 |
| 26300993 | 68,175.16 | +1,968 s | counted | +611.8 | REVERT same reason (parent 26300992, tx 0xd1556070..., premium 1.4588) | 0 |
| 26383264 | 48.02 | premium 1.0035 at parent (probe) | below breakeven, never in a window | -3.2 USD gross (0.02274 ETH drawn x 2,111.65 minus 48.02 LUSD burned) | REVERT 'below minProfit' (parent 26383263, tx 0x5b98e467...) | 0 |
| 26410255 | 29,389.40 | premium 1.0052 at parent (probe) | below breakeven, never in a window | +0.8 USD gross (15.623 ETH sent x 1,881.14 minus 29,389.40 LUSD; the 0.0866 ETH redemption fee is netted against the collateral) | REVERT 'below minProfit' (parent 26410254, tx 0x3dea2f23...) | 0 |

Incumbent net = collateral ETH at the block oracle price minus the LUSD burned
(attempt 1127 convention, USD at 2,290.70 for the Oct29 rows); incumbent gas
per capture 0.0002-0.019 ETH (26300876: 43.7 USD), 26383264: 0.000248 ETH,
26410255: 2,964,379 gas x 0.476 gwei = 0.001412 ETH.

## Expected value

Cadence: 11 `Redemption` events in the 30-day window (2026-10-19..11-14),
0.37 events/day. Only the counted class can enter EV: the three late Oct29
captures (windows 564/1,932/1,968 s >= R = 252 s). At the bot's fixed 3,000
LUSD farm size all three counted parents were measured on the fork
(`proof12.py` + `proof13.py`): every one REVERTS in `TroveManager
redeemCollateral` with 'TroveManager: Unable to redeem any amount' (premium
1.26-1.46 in the fee-burned state after the morning's 2.04M LUSD of redemptions
emptied the troves the small redemption's hint walk starts from). The two
ledger captures sit below the breakeven premium (1.0035, 1.0052 at their
parents) and would revert at 'below minProfit'. The two 2026-10-19 captures
(round-12 addition, review 0c72857e item 2) likewise sit below the breakeven
premium - 1.0114 and 1.0117 at their parents, and the `proof14.py` probes show
premium <= 1.012 across all 1,280 blocks before the captures: the farm route
was never in its window there - and both parents REVERT at 'below minProfit'
at the 3,000-LUSD size (txs 0xd6f834ba..., 0xfb27dac0...; reasons re-read in
`proof15_bisect.py` -> `proof15_bisect.json`). The only measured farm-size
success in the window is at parent 26300832 of the +48 s capture (trial-only
class): 84.9 USDT gross pre-gas, +24.9 USDT net after the 0.026 ETH signing
cap at the proof price.

Measured EV over 2026-10-19..11-14 at the bot's size and class rules: 0
counted captures with positive farm net -> **0 USD/day**, versus the 0.19
USD/day read cost. The table is now complete: all 11 captures in the window
carry a measured class and a measured farm-size result (review 0c72857e item 2
closed). The window mechanism is alive (premiums 1.26-1.46 in the counted class) and the route pays when it succeeds at premiums around 1.1165
(fork-measured +84.9 USDT pre-gas at 3,000 LUSD), but in this 30-day window
no counted capture is farm-size positive: the route's positive margin sits in
the narrow premium band between the 1.0814 breakeven and the fee-burned
high-premium state the farm-size hint walk cannot redeem in. A 30-day window
that ends 2026-11-14 with the last measured window-open premium at 1.0035
does not support promotion on measured EV; the reviewer decides under the
numbers.

## Loss bound (L)

Whole action in one transaction through the deployed executor. The executor
pays the profit to the bot wallet as **native ETH** (the USDT profit is
swapped back through the reverse UniV3 leg to WETH, withdrawn to ETH, and
paid inside the same transaction), and the contract reverts unless the wallet
ends higher than it started after the transaction's own gas: `minProfit`
= 20 USDT — the guard proven to SUCCEED at the 3,000-LUSD farm size on the
fork (tx 0xe9881aba...); a 50 USDT guard reverts at that size, so the bot
carries 20 USDT. The worst case is the signed gas 1,300,000 x 20 gwei =
0.026 ETH, valued at the signing-time price (about 49.4 USD at 1,900 USD/ETH;
bot.js refuses to send once 0.026 x oracle price exceeds 50 USD — the L
bound). Principal never sits outside the transaction: the Morpho flash loan is
repaid inside it; a reverted call leaves only gas (fork guard-revert tx
0x32ff0231..., owner+payee delta = the 0.0011 ETH gas, owner USDT 1.0 -> 1.0).

## Fork proof

`scratch/lusd-exec/proof12.py` (shared ethereum fork, lease taken per run,
released when done; one script: reset, deploy, USDT-dust seed, farm-size runs
at the parent of each counted capture, premium probes; outputs
`proof12_out.json` + `proof12*_run.log`) and `scratch/lusd-exec/proof14.py`
(same pattern for the two 2026-10-19 parents; outputs `proof14_out.json` +
`proof14_run.log`, revert reasons in `proof15_bisect.py` ->
`proof15_bisect.json`):

- guard revert with unchanged principal: tx
  `0x32ff02314d74d2221ac1697f55e9e3ac2d725b10dda34fe4be05e9b4035dcdcc` at
  reset 26300832, status 0, gasUsed 1,107,157, owner+payee ETH delta is its
  gas only, owner USDT 1.0 -> 1.0 (this is also the correct call where there
  is nothing to take: the 1,000 USDT guard is unreachable at farm margins);
- farm-size success at the bot's 20 USDT guard: tx
  `0xe9881aba5ab91c0fd7b881f7a664a4840e87d62bc11fbe46921988c9c0469aec` at
  reset 26300832, status 1, gasUsed 1,068,410, wallet ETH delta +0.031186
  after gas (+0.032255 ETH profit at the fork 1 gwei gas = +82.49 USDT at the
  proof-block pool price 2,557.59 USD/ETH; +24.9 USDT after the 0.026 ETH
  signing cap at the same price);
- farm-size state at the counted captures: parents 26300875, 26300989 and
  26300992 measured REVERT with 'TroveManager: Unable to redeem any amount'
  (txs `0xcd7c2f2e2b4fd72216155ed4cdbc50629df81d43ee176c4ed76fe1bd20cdff5a`,
  `0xd717d701b65e6c157bc88fc896cc42712c87d19413d4554f87cf1ce8ed70140c`,
  `0xd1556070c7e7c6cf31c5bc87ffd49749f141d521f9071a3dd75925749025f952`; the
  revert reason re-read via `eth_call` at each parent state in
  `scratch/lusd-exec/proof13.py` -> `proof13_bisect.json`); the two ledger
  capture parents revert 'below minProfit' (txs `0x5b98e467c4bbc4da962e42253d21122c365049238548c6b5dfc512ba261ff11d`,
  `0x3dea2f23548a3a6bf28366567c945a90534195f4adac4bf9d3cf222207f228c4`).
- farm-size state at the two 2026-10-19 captures (`proof14.py`, resets
  26227310 and 26227311): both REVERT (txs
  `0xd6f834ba0a9896a460d8748bf4809b3b0f41b71337112e4e3f382b59d571dc65`,
  `0xfb27dac04a91a23d947bf4ab9edbf44338e87fac2775c8dbfeb74e97f9c1c2ae`), the
  revert reason re-read at each parent state in `proof15_bisect.py` is
  'below minProfit'; premium at the parents 1.0114 / 1.0117 and never above
  1.012 across the k = 1..1280 block probe bracket, so these captures were
  never in the farm route's window (farm net 0);

The send-economics branch itself (review 0c72857e item 1) is unit-tested in
`test.js` against the fork-measured numbers above: gross 84.9 USDT per 3,000
LUSD at the proof premium, the 0.026 ETH signing-time cap, the >= 50 USD L
refusal, and the measured >= 1.26264 revert band.

The 327,764-LUSD winner-size run stays in `scratch/lusd-exec/proof10.py`
(proof10_out.json, tx 0x032581144b391b0d2eb93ee86f667e8d3aa5fc0bfa41c1ddc6abc84738c308a7).

Executor artifact `scratch/lusd-exec/contracts/out/LusdRedeem.sol/LusdRedeem.json`
(no constructor args; owner = msg.sender = the bot wallet). The live path
reads `EXECUTOR_ADDR` and never falls back to a fork address.
