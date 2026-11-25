# moonwell-whale2-base

Core whale-class route of the stopped moonwell-whale-base (Moonwell core liquidation,
poll-catchable subset), resubmitted under a new ID per human decision
`decisions/human/2026-11-11-moonwell-stopped.md` with its two conditions below. Code, executor
(10-arg artifact), runtime and README history copied from `bots/archive/moonwell-maero-base/`
(whose final review attempts:872 demoted only the mAERO extension as a same-block race; the core
route, the executor and the >=2048-block poll windows were accepted); COLL_ROUTES[M_AERO] is back
to watch-only in this resubmission. Runtime re-taken from the fork instance, see manifest
resubmission_note.

## Poll-catchable census of the core class (resubmission run b7d2f0a3, 2026-11-11)

Decision condition 1 for the core whale route, measured on the last 14 ledger days
(`moonwell_core.liquidate_borrow[_ext]`, blocks 55512916-56090651, 50 events; whale cut at repay
>= 10 USD with every borrow market's underlying pinned via `name()` + Llama prices - MAMO
0.0051 / ADA 0.178 USD; `getAccountLiquidity` third-word shortfall probes at end-of-block
historical tags, script `scratch/mw-rerun-probe.py`, output `scratch/mw-rerun-window.json`):

- **2 whale captures were liquidatable >= 65536 blocks (>18 h at the ~1 s Base block rate; the
  probe floor) BEFORE their capture block** — their eligibility crossed on a price/interest
  update many blocks outside the capture block, so a poll bot with any cadence under 18 h
  catches them: block 55717319 (repay 52.06 USDC, gross ~= 5.8 USD at the ~11 pct penalty) and
  block 55648813 (repay 160.04 USDC, gross ~= 17.8 USD). Gross EV of the poll-catchable whale
  class ~= 2 captures x 23.6 USD / 14 d ~= **1.7 USD/day at full capture** before gas
  (executor gasUsed ~1.6M at the 0.05-0.2 gwei Base floor ~= 0.2-0.6 USD/send) and before the
  incumbent share (top liquidators took most events).
- 1 capture (55635577, mcbBTC collateral, 13.9 USD repay) also sat liquidatable >=65536 blocks
  on the liquidity lens, but its redeemable mcbBTC cash arrived only mid-capture-block — the
  cash-starved class (attempt 633) that the executor cannot atomically redeem.
- The remaining whale-scale events of the 14 d window are sub-10-USD after the corrected
  underlying pricing (MAMO repay 14.18 raw = 0.07 USD; ADA 51.57 raw = 9.2 USD).
- The archived 20-day window bracket (`scratch/mw-whale/window-bracket.json`, section below)
  measured 12/26 whale captures liquidatable at C-1 and 9/26 at C-16 — the same poll-catchable
  class; the two new captures above extend it with >=65536-block windows.

**Correction (run 2eba5673, 2026-11-11, attempt 924):** the census probe
`scratch/mw-rerun-probe.py` misread the sign word of `getAccountLiquidity` - its
`ctl_shortfall`/`window_blocks` read the **liquidity** word (the second word of the
`(err, liquidity, shortfall)` return, not the third), so `window_blocks 65536` there
means *liquidity > 0 (HEALTHY)* at the floor tag and `window_blocks 0` means
*liquidity == 0 at every ladder tag (liquidatable >= 65536 blocks)* - the
classification is inverted (wiki `pitfalls/moonwell-getaccountliquidity-decode.md`).
Re-measured with the correct lens (11 historical-tag reads,
`scratch/mw-xrp2/lastliq.json`) + the fork control at reset 55648812
(`scratch/mw-xrp2/proofX.json`): both whale captures 55717319/55648813 sat HEALTHY
across the whole probed range (55648813: liquidity +213.84..+848.06 USD at tags
B-16384..B-1; at the fork C-1 `[err 0, liquidity 213.84e18, shortfall 0]`) and
crossed liquidatable INSIDE the capture block = the same-block price-cross class
(the settled mcbXRP class, attempt 630; wiki `pitfalls/fork-reset-liquidatability-flip.md`).
The mcbXRP 55648813 re-enable candidate is therefore NOT fork-executable at any reset -
the route stays WATCH-ONLY and no success fork proof exists (the mcbXRP market cash
657,235 XRP at C-1 was not the blocker; holder debt 48,058.84 USDC; the executor's
eligibility guard on a healthy holder reverted NOT_LIQUIDATABLE, fork tx
0x582cc7069da1b500ad5af22254e29838ea7a57bd43aeca37f6afe11a7cc52ef5). The only truly
poll-catchable capture of this 14-day window, 55572125 (liquidity == 0 at every tag
of the 65536-block ladder, `scratch/mw-xrp2/lastliq-55572125.json`),
borrows mADA (repay 51.57 ADA ~= 9.2 USD) with collateral on the legacy-USDC-wrap
market 0xdc7810b47e = a watch-only borrow market for the executor, and its ~0.6 USD
expected profit at the measured 6.57 % margin is under the bot's 1 USD send floor
anyway. **The 1.7 USD/day whale EV claim of the new census is withdrawn**; the
archived 20-day window bracket (measured with correctly-labelled words,
fork-controlled green by `scratch/mw-maero/sweep30.json`) stays the
decision-condition-1 evidence.

## Decision condition 1 — poll-catchable captures (separate block from the price update) and the profit estimate

Measured 2026-11-10 (run a4f35ecf, scratch/maero-window/probe.py + probe.json; 26 whale-scale
moonwell_core ledger captures, blocks 54911221-55717319, repay >= 100 USD scale; the protocol's
own lens getAccountLiquidity (error, liquidity, shortfall) 1e18-USD probed at the end-of-block
historical tag C-1):

- **12 of 26 captures were liquidatable at C-1** (shortfall > 0, end of the block BEFORE their
  winner) = captured in a block separate from the trigger price-update block; shortfall at C-1
  between 0.0007 and 114.7 USD. Of these, **9 were liquidatable at C-16 as well** (>= 16 blocks
  of persistence = >= 1 window at the bot's 15 s cadence at the measured ~1 s Base block rate).
- 14 of 26 were healthy at C-1 (crossed mid-block of the capture = same-block race): all three
  mcbXRP whale captures (holder 0x544784a5, repay 2133.06/10955.96/15852.31 USDC), the mAERO
  whale capture 55297682 (winner tx 0xf0579b9d, repay 323.81 USDC, seize 26499.88 mAERO; C-1
  liquidity +18.94 USD healthy), and the 55297682 storm captures.
- mAERO collateral specifically: 2 of the 6 mAERO-collateral captures in the probe set were
  poll-catchable (55381952 liquidatable >= 16 blocks before its winner, 55297693 liquidatable at
  C-1). The only known mAERO WHALE capture was same-block — the window evidence supports the
  class, not the whale.
- The archived manifest's window bracket (scratch/mw-whale/window-bracket.json) additionally
  measured the supported mUSDC/mWETH-collateral whale captures as liquidatable >= 2048-16384
  blocks (>= 4095-32767 s wall) before their winners.
- Profit estimate at those captures: the fork-measured winner margin is 6.57 % of repay after
  slippage (+3.916356 USDC on repay 59.62, fork tx 0x3cdb6b0f...); whale-class cadence ~1.4/day
  (ledger moonwell_core, repay >= ~20 USD events). Larger captures scale linearly at the same
  margin: repay 2133/10956/15852 USDC -> ~140/720/1040 USD gross. Whale-scale poll-catchable
  events are sparse (12 in 20 days, mostly mid-scale repay); the whale mAERO/mcbXRP captures
  measured so far were same-block.

## Decision condition 2 — Alchemy consumption estimate per day, live

The same-shape live bot measured ~10M CU/day over its 11-10 uptime 00:39-18:03Z (16.4 h,
~10M/day as reported in the decision). Steady-state reads ~9/min (12,960/day; manifest
rpc_reads_per_min 9) dominated at startup by getLogs backfill bursts (40 pages per 15 s cycle for
~23 cycles). At the 15 s cadence (CYCLE_MS 15000) the estimate is ~10M CU/day; a 60 s cadence
cuts it to ~2.5M CU/day; the 180 s cadence (CYCLE_MS 180000, review 872998e4 item 3, run
9aedc8e1) puts the linear estimate at ~0.83M CU/day - below the 1M CU/day threshold of decision
2026-11-11-moonwell-stopped, so no human rationale is owed at promote. It stays below the
measured windows above (>= 2048 blocks (~34 min) for the supported-collateral class - 180 s
polling is 11x inside it; the poll-catchable mAERO subset measured >= 16-24 blocks and every
measured large-repay capture became eligible inside its own block - see next section).

## Poll-catchability of the mAERO route — recalculation with the third lens word (run 9aedc8e1)

`comptroller.getAccountLiquidity(holder)` returns `(error, liquidity, shortfall)` in 1e18-USD:
the MIDDLE word is liquidity (a healthy account has liquidity > 0, shortfall 0) - an earlier
manifest label read capture 55697123's middle word 1.818657 as its shortfall. Recalculated with
the THIRD word via relay-archive lens reads at C-1 for the 8 ledger captures whose repay makes a
>1 USD bonus plausible (10% of repay; scratch/mw-maero/mine_probe.py): ALL read shortfall(C-1)
= 0 with liquidity(C-1) > 0 (0/8 liquidatable-at-C-1) - every capture became eligible inside its
capture block (window 0-1 blocks, the lead-72 same-block race), so the poll-catchable capture
count with a >1 USD net is 0 of 8 measured; the fork replays the route at a +6d
advanced head (the fork now mines tx blocks at parent_ts+1s, so a plain reset never leaves a
borrow in default) and sweep27.py proves the full route there (success 0.136257 USDC paid to
OWNER in-tx, NO_PROFIT guard, NOT_LIQUIDATABLE eligibility).

## Fix round 4 (run 555959dc sweep29 + run 52994a7f sweep30) — the P6 cbETH extension and the poll-catchable capture

The artifact gained the PancakeV3 cbETH/WETH pool 0x257fcbae4ac6b26a02e4fc5e1a11e4174b5ce395
as the 10th constructor immutable (P6) for a mcbETH sell route; scratch/mw-maero/sweep30.py
reproves the current artifact on the shared fork (fresh 10-arg deploy with isPoolAllowed P5 and
P6 with no owner send: mAERO success 0.136263 USDC to OWNER in-tx + NO_PROFIT guard + the bot's
exact-calldata NOT_LIQUIDATABLE eligibility at capture 55697123 at a +6d advanced head).
The only capture measured liquidatable >= a poll window before its winner is the mcbETH capture
53283757 (holder 0x3ac21455, window >= 16383 blocks / >= 32767 s, scratch/mw-whale/window-bracket.json):
at the C-1 reset 53283756 with the +6d head its lens shortfall is 24.57 USD, but the mcbETH
market cash at the same head is 154,486,718 raw cbETH (18-dec = 0.00015 cbETH ~ 0.0002 USD)
and the bot-exact-calldata legs revert NO_REDEEM (fork tx 0xdbb7654635a2e49570a888620b34912103f21a9070aafd5f5eb2325620ea96d2)
— the cash-starved redeem class of mEURC/mcbBTC (attempts 630/633). So no measured capture is
today both poll-catchable AND executor-executable: mAERO 0/8 liquidatable at C-1 (section
above), mcbETH cash-starved at its one poll-catchable capture. The mcbETH/P6 bot route stays
watch-only (the bot logs the 0x3bf93770 collateral as opportunity_watch_only); re-enable needs
a natural mcbETH capture with market cash >= the seize quota at C-1.

## Bot next steps (before any promotion round)

Status 2026-11-10 (earner run 3ec1ed2c): steps 2-3 (paper side) are DONE - bot.js gained the
AERO/M_AERO/POOL_AERO_CBBTC constants and the enabled COLL_ROUTES[M_AERO] entry, the paper
runtime executor-runtime.hex was re-taken by eth_getCode of the fork instance 0x8f7a45eb.. after a
constructor-executing fork deploy from 0x1111..1111 at generation 467 (OWNER immutable = the sim
sender, see the manifest resubmission_note), IMMUTABLE_CHECKS were re-pinned against it
(P2/P1 words moved 7412/7480 -> 7593/7661 in the 13:11Z source build) and the heartbeat now
reports runtime_ok true. The leg1 pool was whitelisted on that same fork instance by an owner
setPoolAllowed send (fork tx 0x96fbc4983523f9e7632dc0c090f1878d19019e467e33632bfc63ae40e9881e8c,
isPoolAllowed=true verified); a later base fork RESET wipes that flag together with the executor
deployment - re-take the runtime and re-whitelist after a reset, or the first mAERO sim reverts
SELL_POOL. Step 3's live-side setPoolAllowed send on the fresh gate deployment is still open for
the promote round; step 4 (success fork proof at the first natural C-1-liquidatable mAERO
capture) stays open.

1. Reviewer reruns the archived whale fork proofs (executor core path unchanged; the manifest's
   fork_evidence scripts are in scratch/mw-whale/).
2. Enable the mAERO route in bot.js (the copied bot.js is the pre-mAERO archived version): add
   constants AERO = 0x940181a94a35a4569e4529a3cdfb74e38fd98631 (mAERO underlying() measured at
   relay latest 2026-11-10), M_AERO = 0x73902f619ceb9b31fd8efecf435cbdf89e369ba6,
   POOL_AERO_CBBTC = 0xdfe5f275020def30993f042174fc2d335678b626 (token0=AERO, token1=cbBTC
   measured at latest 2026-11-10) and the COLL_ROUTES[M_AERO] entry
   { underlying: AERO, sell: [{ pool: POOL_AERO_CBBTC, token0: AERO, token1: CBBTC,
   zeroForOne: true }, { pool: POOL_CBBTC_USDC, token0: USDC, token1: CBBTC, zeroForOne: false }],
   sellPool2: POOL_CBBTC_USDC }.
3. Live mode: one owner setPoolAllowed(POOL_AERO_CBBTC, true) send to the fresh gate-deployed
   executor before the first mAERO swap (selector 0x1bfa59c3; check isPoolAllowed 0xd1e71c94
   first). leg1 pool is not a constructor pool; no redeploy needed.
4. A success fork proof at the first natural mAERO capture that is liquidatable at its C-1
   4. A success fork proof at the first natural mAERO capture that is liquidatable at its C-1
      (aero4 closed only the mid-block whale capture as fork-unexecutable).
      MEASURED 2026-11-10T21:2x-21:5xZ (run 3ca91d39, scripts scratch/mw-maero/proof20.py +
      proof21.py + proof21-partial.json): BOTH measured poll-catchable mAERO-collateral
      captures are fork-unexecutable for the CURRENT executor, for two distinct reasons:
      - capture 55297693 (holder 0x2f2e1fbd, liquidatable at its C-1, sf 0.0217 USD) is an
        mAERO-BORROW capture: its emitting market IS the mAERO market (borrowA ==
        collateralA = 0x73902f61..., repay 0.5628 AERO 18-dec), which the executor cannot
        repay (BORROW_MKTS = mUSDC/mWETH only). proof20 measured borrowBalanceCurrent(mWETH)
        = 0 for this holder at the C-1 reset - the borrow is not a WETH borrow at all.
      - capture 55381952 (holder 0x638848d4, mWETH borrow, liquidatable >= 16 blocks, C-1 sf
        0.000739 USD re-measured on the fork at every window tag C-1..C-24) is DUST for the
        executor's repay path: `repay = shortfall / 2 / 1e12` truncates this shortfall to
        ZERO 6-dec USDC units, so the executor reverts NOT_LIQUIDATABLE at its own
        `require(repay > 0)` at the C-1 reset (proof21 eth_call legs, all three flash sizes).
        The mAERO market cash 845,669 AERO and the leg1 pool 725,503 AERO + 2.77 cbBTC are
        deep enough - cash is not the blocker.
      The success proof therefore awaits a natural mAERO capture with a USDC-or-WETH borrow
      AND a shortfall large enough to survive the 6-dec truncation (>= 2e12 wei-scale = 2
      USD) - and to clear the bot's 1 USD send floor at the measured 6.57 % margin,
      >= ~30 USD shortfall at C-1. The proof harness (reset -> deploy from 0x1111..1111
      nonce 0 -> setPoolAllowed leg1 -> probe -> liquidate + controls -> runtime check) is
      scratch/mw-maero/proof21.py and reruns in minutes.
      Paper-side status after this run: base fork reset to relay head-3 = 55785234 with the
      executor redeployed at 0x8f7a45eb.. (deploy tx
      0xd88d923126547c61fd6a11f3889d1b736becc47e68f6bcb6b4d2dd5930b3f007, same CREATE from
      0x1111..1111 nonce 0) and leg1 whitelisted (setPoolAllowed tx
      0xfd29e1b9e0d8b9ae95ffe2bf1bc52c9edb0e6093056553d09111e180fa4a66cc); the bot's
      backfill seed finished (cursor == head at 21:48Z, 31 seed_scan cycles) and the
      heartbeat reports runtime_ok true with zero restarts.

## Fix round 2026-11-10 (earner run 65d02323, review a50ef674 items 1-4)

Status: the four review blockers are implemented and proved; the success fork leg
awaits one natural capture (see step 4 below, unchanged).

1. P5 constructor whitelist (review item 1, CLOSED): MoonwellWhale.sol gained a
   9th constructor immutable P5 = 0xdfe5f275020def30993f042174fc2d335678b626 and
   isPoolAllowed now accepts it. FRESH gate deployment needs NO owner
   setPoolAllowed send - step 3 (live-side send) is SUPERSEDED. Fork proof
   (script scratch/mw-maero/proof22.py, output scratch/mw-maero/proof22.json):
   fresh deploy at reset 55697122 (C-1 of the new mUSDC-borrow mAERO-collateral
   capture 55697123, holder 0x48768c348525b888e53232bc2d020eba94741255, C-1
   shortfall 1.818657 USD) -> isPoolAllowed(P5) == true with no owner send
   (deploy tx 0x401b670edb995052e6958f84ff1e227f25b60d2f3b6e796798770163ef109f0a);
   an unknown pool stays disallowed.
2. Profit payout to the bot wallet (review item 2, CLOSED): liquidate() now
   transfers the measured profit delta to OWNER (the bot wallet) INSIDE the
   successful liquidation tx (IERC20(USDC).transfer(OWNER, profit) after the
   NO_PROFIT require), so the watchdog/gate sweep counts it; profit no longer
   stays retained in the executor (MoonwellWhale.sol:245-259 of the old
   artifact). The NO_PROFIT guard keeps its revert-before-state semantics
   (guard tx reverts with zero USDC delta on the wallet).
3. mAERO success proof (review item 3, PARTIAL - harness green, success leg
   waits): proof22.py proves the fresh-deploy whitelist, the eligibility
   control (zero mUSDC borrow holder 0x638848d4 reverts NOT_LIQUIDATABLE, tx
   0xc54f483d20938688dc1d65e93d30e61ac5088a768dabb6807a62c0dc887ea1d2 at the
   proven WADO capture) and the payout-ready executor. The full-route success
   legs at both captures now revert LIQUIDATE_REJECTED from the mToken
   delegate: the halfBorrow repay meets an UNRESOLVED delegate-side reject
   measured at the proven WADO capture 53265094 on EVERY repay size from 60e6
   to full principal INCLUDING exactly half of borrowBalanceCurrent
   (scratch/mw-maero/sweep22.py, this run; the same mystery the aero session
   recorded at capture 55297681). proof10's 11-05 green run flashed 60.000000
   USD - below half of the principal 164823.51 at today's state. NEXT: read
   MErc20Delegate.liquidateBorrow between its liquidateBorrowAllowed frame and
   the repay/seize frames for the exact reject condition, then rerun proof22
   (success + payout legs then assert; today's proof22.json records them
   honestly reverted).
4. CU/day (review items 4 and 872998e4 item 3, CLOSED): CYCLE_MS cut 15 s ->
   60 s -> 180 s (run 9aedc8e1) (measured ~10M CU/day -> ~2.5M -> linear
   estimate ~0.83M CU/day, now BELOW the 1M threshold of decision
   2026-11-11-moonwell-stopped - no human rationale owed at promote);
   MAX_REPAY_WEI raised 300 -> 400
   USD (the mToken band needs repay ~= HALF the principal; at 300 a mUSDC-borrow
   capture with principal > 600 USD capped repay below half - capture 55697123
   principal 746.201674). Window fit: supported-collateral whale captures
   measured liquidatable >= 2048 blocks before the winner (README window
   bracket) - >= 34 min at ~1 s blocks, so a 180 s poll is 11x inside that
   window with the same >= 2-window evidence; only the mAERO-route subset
   measured >= 16
   blocks and needs >= ~180 blocks of window at 180 s polling (the awaited
   success capture is by construction the multi-window default class).
Runtime: executor-runtime.hex re-taken by eth_getCode of the fork instance
0x8f7a45eb.. deployed FROM 0x1111111111111111111111111111111111111111 at relay
head-3 55795650 after this 9-arg build (deploy tx
0xf5bfb218fb44b2f485a5b1646830fc8edbe3a2c6a57ced2d71feacb66c4b7b37); bot.js
IMMUTABLE_CHECKS re-pinned against it (P4 374, P3 442, USDC 510, P0 578, P5 646,
OWNER 747, COMP 977, MORPHO 1043, P2 7846, P1 7914 - proof22.json imm_offsets).
Manifest executor_args gained the 9th word (P5).
