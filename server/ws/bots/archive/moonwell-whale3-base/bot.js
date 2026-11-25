#!/usr/bin/env node
// moonwell-whale-base — Moonwell core-market (Compound v2 mToken) whale-liquidation
// watcher on Base. Discovery: LiquidateBorrow events on the two core loan markets
// (mUSDC, mWETH) mark repeat-default borrowers (whale class, poll window >=32 blocks
// measured, scratch/mw-window-batch.json). Probe: comptroller.getAccountLiquidity
// (shortfall>0 => liquidatable). Execution: the MoonwellWhale executor does the WHOLE
// path in one transaction: Morpho flashLoan(USDC) -> mToken.liquidateBorrow ->
// redeem seized mToken -> 0-2 direct V3-pool swaps -> revert unless its USDC balance
// ends >= start + minProfit + 1 (NO_PROFIT). Paper mode: simulates the exact executor
// calldata via eth_call with the fork-deployed runtime as code override. Live mode:
// sends the same bytes through the signer. Self-contained: node built-ins only.
// Constants measured on the shared fork (scratch/mw-whale/proof10.py, green run) and
// the relay (scratch/mw-coll-underly.json), 2026-11-05.
'use strict';
const fs = require('fs');
const path = require('path');

const RELAY = process.env.RPC_RELAY_URL || 'http://127.0.0.1:8545';
const LANE = process.env.RPC_LANE || 'paper';
const BOT_MODE = process.env.BOT_MODE || 'paper';
const CHAIN = 'base';
const DIR = __dirname;

// --- measured constants (fork proof10 + relay probes) ---
const COMP = '0xfbb21d0380bee3312b33c4353c8936a0f13ef26c';   // moonwell core comptroller (getAccountLiquidity)
const MORPHO = '0xbbbbbbbbbb9cc5e90e3b3af64bdaf62c37eeffcb'; // Morpho Blue (0-fee flashLoan)
const USDC = '0x833589fcd6edb6e08f4c7c32d4f71b54bda02913';
const WETH = '0x4200000000000000000000000000000000000006';
const WADO = '0x0B3e328455C4059EEB9E3f84b5543F74e24e7e1b';
const M_USDC = '0xedc817a28e8b93b03976fbd4a3ddbc9f7d176c22'; // core USDC loan market (underlying USDC)
const M_WETH = '0x628ff693426583d9a7fb391e54366292f509d457'; // core WETH loan market (underlying WETH, 18-dec borrow)
const M_WADO = '0xde8df9d942d78ede3ca06e60712582f79cfffc64'; // WADO collateral market
const POOL_WETH_USDC = '0x4a7af46bc8abc00048c6c7920a1488daf568366c'; // PancakeV3 WETH/USDC (winner route leg 2)
const POOL_WADO_WETH = '0x792f465e0434fb1028ea3bfeb05240cb839c4e04'; // PancakeV3 WADO/WETH fee100 (winner route leg 1)
const CBBTC = '0xcbb7c0000ab88b473b1f5afd9ef808440eed33bf'; // cbBTC underlying (pinned via asset transfers to the mcbBTC market, lead 72; mcbBTC underlying() agrees at fork reset 54167202)
const M_CBBTC = '0xf877acafa28c19b96727966690b2f44d35ad5976'; // mcbBTC collateral market
const POOL_CBBTC_USDC = '0x784e539f15ca2d19449a6311c5dab6cf37d8f1ba'; // PancakeV3 cbBTC/USDC fee100 (measured at fork reset 54167202: token0=USDC, liquidity 7.17e12, pool balances 843,825 USDC + 40.9 cbBTC - deep for a 300 USD leg)
const EURC = '0x60a3e35Cc302BFA44cB288bc5A4f316FDb1aDb42'; // EURC underlying (mEURC underlying() read at fork reset 54158850, 2026-11-09 run f04b98e0)
const M_EURC = '0xb682c840b5f4fc58b20769e691a6fa1305a501a2'; // mEURC collateral market (lead 72 whale collateral)
const POOL_EURC_WETH = '0x4dbdcb087992404ea9b14fa83cc695b02797f39a'; // PancakeV3 EURC/WETH fee100 (a ClonesERc196Proxy; measured at fork resets: token0=WETH token1=EURC, pool balances 130,842-315,496 EURC + 165-210 WETH at 53948855-53517745 - deep for a whale leg)
const XRP = '0xcb585250f852c6c6bf90434ab21a00f02833a4af'; // XRP underlying, 6-dec (the mcbXRP redeem pays this token - pinned from the incumbent trace of capture tx 0xa59906ec, ledger source moonwell_core.liquidate_borrow)
const M_CBXRPL = '0xb4fb8fed5b3aaa8434f0b19b1b623d977e07e86d'; // mcbXRP collateral market (lead 72 whale collateral: captures 54911221 repay 2133.06, 54922327 repay 10955.96, 55160602 repay 15852.31 USDC - same borrower 0x544784a5)
const POOL_XRP_WETH = '0xb90fe999be6869af0afc557dccfbe169ea3403d6'; // XRP/WETH pool = constructor P4 (interface pinned from the incumbent trace tx 0xa59906ec: swap 0x128acb08, zeroForOne=false, positive amountSpecified = exact input, pool pays WETH to recipient, callback uniswapV3SwapCallback 0xfa461e33 = this executor's; proxy -> impl 0xc770898522d2a9c8da7a10d63989b6b58305b665; measured XRP balance at the pool 46,608.69 XRP at fork resets 55029530/55160601 - deep for a 300 USD leg; the OTHER XRP pool 0x170b6bfc071426aab7c81ae12383219facbb6b6a uses a callback this executor does not implement - unused)
const MULTICALL = '0xca11bde05977b3631167028862be2a173976ca11';
const AAVE_ORACLE = '0x2cc0fc26ed4563a5ce5e8bdcfe1a2878676ae156'; // fresh WETH/USD for the live gas bound (measured by aave-watcher-base)
const LIQ_TOPIC = '0x298637f684da70674f26509b10f07ec2fbc77a335ab1e7d6215a4b2484d8bb52'; // LiquidateBorrow(address,address,uint256,address,uint256) non-indexed
const SEL_LIQ = '0x5ec88c79';        // getAccountLiquidity(address) -> (error, liquidity, shortfall) 1e18-USD
const SEL_TRYAGG = '0xbce38bd7';     // Multicall3.tryAggregate(bool,(address,bytes)[])
const SEL_GET_ASSET_PRICE = '0xb3596f07'; // Aave getAssetPrice(address) -> uint256 8-dec USD
const SEL_SWAP = '0x128acb08';       // PancakeV3 pool.swap(address,bool,int256,uint160,bytes); positive amountSpecified = EXACT INPUT (PancakeV3)
const SEL_BB = '0x17bfdfbc';         // mToken borrowBalanceCurrent(address) -> 18-dec borrow principal (the flash sizing input on WETH borrows)
const SEL_EXEC_OWNER = '0x117803e3'; // OWNER() — the executor's public immutable getter (MoonwellWhale.sol exposes OWNER(), NOT owner(): owner() 0x8da5cb5b reverted with empty data, review c4297fae; OWNER() = cast keccak("OWNER()"), verified on a fork-deployed executor run 3b13c4a6). Live path requires OWNER() == our wallet.

// sqrtPriceLimitX96 values: 0x1000276a4 is the measured winner's value for the
// decreasing legs (MIN_SQRT_RATIO+1 is rejected by this pool's SPL check - measured
// fork revert); increasing legs (USDC->WETH) use MAX_SQRT_RATIO-1.
const LIMIT_DOWN = '0x1000276a4';
const LIMIT_UP = '0xfffd8963efd1fc6a506488495d951d5263988d25'; // PancakeV3 MAX_SQRT_RATIO-1 for the increasing legs (proven by the promoted morpho-watcher-base executor on this P1 pool; measured 2026-11-09: 2**160-2 is above the pool's MAX_SQRT_RATIO and reverts BORROW_SWAP_FAILED on the fork)

// Collateral market -> sale route (measured underlyings, scratch/mw-coll-underly.json).
// sell = list of {pool, token0, token1, zeroForOne} legs; zeroForOne=true is token0->token1
// (decreasing sqrtPrice); the pool pays the output to the recipient (executor) and calls
// the swap callback for the input side. null route = watch-only (opportunity logged, no sim).
const COLL_ROUTES = {
  [M_WETH.toLowerCase()]: { underlying: WETH, sell: [{ pool: POOL_WETH_USDC, token0: WETH, token1: USDC, zeroForOne: true }], sellPool2: null },
  [M_WADO.toLowerCase()]: { underlying: WADO, sell: [{ pool: POOL_WADO_WETH, token0: WADO, token1: WETH, zeroForOne: true }, { pool: POOL_WETH_USDC, token0: WETH, token1: USDC, zeroForOne: true }], sellPool2: POOL_WETH_USDC },
  [M_USDC.toLowerCase()]: { underlying: USDC, sell: [], sellPool2: null }, // redeemed asset is USDC: no sale
  [M_EURC.toLowerCase()]: null, // WATCH-ONLY 2026-11-09 run f04b98e0 (lead 72 mEURC route extension, measured): the whale window is poll-catchable (borrower 0xbf65b647 liquidatable >=60 blocks before its captures 53462692/53464103/53517746, mWETH borrows repay 0.0823/0.0083 WETH; 0xfe6e5a14 at 54158851 repay 0.000856 WETH) but the mEURC market cash at capture-1 is the blocker - measured at fork resets: 0 EURC at 53462691, 0.014 EURC at 53517745, 1.86 EURC at 54158850 (scratch/mw-whale/proof15.py): cash-starved same-block class like mcbBTC/mcbXRPL (attempts 630/633); the only pre-block cashed capture supports ~1.7 USD repay, under MIN_SEND_PROFIT_USD. Executor extension P3 (redeem mEURC -> EURC/WETH on P3 -> WETH/USDC on P1, 7-arg constructor) deployed 0x8f7a45eb.. at reset 54158851-1: sf>0, borrow swap + P3 pool leg calls execute, the executor reverts NO_REDEEM - redeem paid 0 EURC with 1.86 EURC market cash (open question for the next session, script + json in scratch/mw-whale/). Re-enable needs a natural mEURC capture with cash >= seize at capture-1 plus a success fork proof there. Leg direction when enabled: token1 EURC -> token0 WETH, zeroForOne=false, LIMIT_UP, sellPool = constructor P3, then the proven P1 leg.
  [M_CBXRPL.toLowerCase()]: null, // WATCH-ONLY 2026-11-09 run d11f8a2c (lead 72 mcbXRP route extension, measured): the executor gained the P4 XRP/WETH collateral-side leg (redeem mcbXRP -> sell XRP->WETH on P4 zeroForOne=false LIMIT_UP -> WETH->USDC on P1, pinned from the incumbent trace of capture tx 0xa59906ec: swap 0x128acb08 positive exact input, callback 0xfa461e33; mcbXRP market cash 689,945 XRP at the deep reset >= any whale seize - cash is NOT the blocker). The blocker is the window: holder 0x544784a5 (three mcbXRP captures 54911221/54922327/55160602, repay 2133/10956/15852 USDC) measured getAccountLiquidity shortfall == 0 at every fork reset this session probed end-of-block: 55160601 (capture-1, liquidity +177.58 USD), 55029530 (capture-131072) and 54791255 (older capture - 131072) - scratch/mw-whale/proof16.py. Same-block price-cross class (mcbBTC/mcbXRPL/mEURC, attempts 630/633; decisions/human/2026-11-06-no-latency-race.md): the incumbent won inside the capture block. Re-enable needs a natural mcbXRP capture liquidatable >= 2 poll windows before its winner; then a success fork proof at that reset-1. Leg direction when enabled: token1 XRP -> token0 WETH, zeroForOne=false, LIMIT_UP, sellPool = constructor P4, then the proven P1 leg WETH->USDC.
  [M_CBBTC.toLowerCase()]: { underlying: CBBTC, sell: [{ pool: POOL_CBBTC_USDC, token0: USDC, token1: CBBTC, zeroForOne: false }], sellPool2: null }, // ENABLED 2026-11-13 run ecde30a1 for the 0x7b63 whale (windows 3.3-6.5 h measured by attempts:1074; seize 0.00003-0.001 cbBTC; leg token1 cbBTC -> token0 USDC zeroForOne=false LIMIT_UP on constructor P2; the mcbBTC market CASH lens (getCash 92 raw8 at the deep reset 56482155) is UNPROVEN at the measured windows - the executor reverts NO_REDEEM and the paper sim logs it; no send without cash

};
// Borrow-market side: the executor's maxRepay argument is ALWAYS the Morpho
// flash cap in USDC 6-dec units (the executor computes repay = shortfall/2 in
// USDC units, caps it at maxRepay, and flashes that USDC for EITHER borrow
// underlying). For a mUSDC borrow the flash repays directly and the mToken
// caps the real repay at half the borrow balance (300 USDC cap = capital 400).
// For a mWETH borrow the executor swaps the WHOLE flash USDC -> WETH on the
// borrow pool and caps the WETH repay at borrowBalanceCurrent/16 (the measured
// seize-value cap; LIQUIDATE_SEIZE_TOO_MUCH above it), so the bot must size
// the flash near the repay value: excess swap output stays as unconverted
// WETH inventory that cannot repay Morpho (measured 2026-11-06: a shortfall/2
// flash stranded ~294 of 300 USD and reverted). Sizing proof: fork flash
// 5.60 USD on debt/16 value 5.29 USD (proof11, +0.042771 USDC).
// borrowBalanceCurrent gives the bot the debt to size from.
const BORROW_MKTS = {
  [M_USDC.toLowerCase()]: { underlying: USDC, borrowPool: null, dec: 6 },
  [M_WETH.toLowerCase()]: { underlying: WETH, borrowPool: POOL_WETH_USDC, dec: 18 },
};

// LiquidateBorrow emitting markets = the 2 core loan markets + the 15 markets
// that emitted LiquidateBorrow in the 14-day protocol-wide scan (attempt 235,
// ledger source moonwell_core.liquidate_borrow_ext). The drought ended
// 2026-11-06: blocks 53786333 (06:47Z), 53799551 and 53799599 (07:31Z) came
// after the 9-day drought; the old 2-market watchlist captured them (all
// three emitted on mUSDC/mWETH), but the last >=100 USD whale of the drought
// window (block 53507231, 122.3 USD) emitted on unwatched mWSTETH — the
// drought session recorded the 2-market watchlist as insufficient. Candidates
// from non-executor debt markets are watch-only: the executor repays only
// USDC/WETH borrow (BORROW_MKTS gate in simulate).
const EXT_MARKETS = [
  '0x703843c3379b52f9ff486c9f5892218d2a065cc8',
  '0x3bf93770f2d4a794c3d9ebefbaebae2a8f09a5e5',
  '0x73b06d8d18de422e269645eace15400de7462417',
  '0x627fe393bc6edda28e99ae648fd6ff362514304b',
  '0x73902f619ceb9b31fd8efecf435cbdf89e369ba6',
  '0xb8051464c8c92209c92f3a4cd9c73746c4c3cfb3',
  '0xf877acafa28c19b96727966690b2f44d35ad5976',
  '0xb682c840b5f4fc58b20769e691a6fa1305a501a2',
  '0xfc41b49d064ac646015b459c522820db9472f4b5',
  '0xdc7810b47eaab250de623f0ee07764afa5f71ed1',
  '0xb6419c6c2e60c4025d6d06ee4f913ce89425a357',
  '0x9a858ebff1beb0d3495bb0e2897c1528ed84a218',
  '0x10ff57877b79e9bd949b3815220ec87b9fc5d2ee',
  '0xde8df9d942d78ede3ca06e60712582f79cfffc64',
  '0x2f90bb22eb3979f5ffad31ea6c3f0792ca66da32',
];
const EMIT_MARKETS = [M_USDC, M_WETH]; // lean scan 2026-11-13 run ecde30a1: the covered whale population borrows these two markets (EXT_MARKETS list kept for reference; scanning 17 markets at 15 s was the ~10M CU/day burn that stopped moonwell-whale-base)
const CAND_CAP = 400;               // candidates kept (oldest pruned)
const CAND_TTL_MS = 12 * 3600 * 1000; // healthy candidate retention: 12 h wall clock since its last LiquidateBorrow event (whale-class holders re-default ~1/day; wall clock is the stable unit because the Base block rate changed mid-window)
const CYCLE_MS = 600000;            // lean 10-min poll (decision 2026-11-13 retriage windows of attempts:1074 are 3.3-6.5 h; the archived 15 s cadence burned ~10M CU/day)
const LOG_REFRESH_MS = 30000;
const LOG_BLOCKS = 120000;          // candidate discovery window (~2.8 days)
const LOG_PAGE_BLOCKS = 2000;       // getLogs page; halved on relay max-results errors
const CURSOR_LOOKBACK = 8;          // blocks re-scanned on resume
// Fresh-start candidate seeding (attempt 644: the 2026-11-08T21:5xZ WADO whale
// captures were MISSED because both borrowers were first-time defaults ~150k
// blocks before the head - outside the head-LOG_BLOCKS discovery window - while
// getAccountLiquidity showed the shortfall stable >=211 blocks before capture).
// A cursor==0 start (live promotion, fresh paper state) backfills candidates
// from the ledger source floor instead of only the last LOG_BLOCKS: past
// captured whale borrowers re-default and are then trackable. Seed filter
// (measured attempt 647): only executor-route borrow markets (mUSDC/mWETH)
// with a whale-class repay >= 10 USD-class at the last event - of the 242
// historical borrowers only 23 qualify; the dust tail cannot clear the bot's
// 1 USD send floor, and watch-only borrow markets would be seeded probe noise.
const SEED_FLOOR = 56596000;        // lean seed backfill floor (2026-11-13 run ecde30a1: ~118 pages from head; the archived floor 53247461 meant a ~1800-page backfill at the new cadence)
const SEED_WHALES = [ // measured mUSDC-borrow whales (ledger moonwell_core.liquidate_borrow, blocks 56505061-56789577, run ecde30a1)
  { holder: '0x7b6300131a4f4002545ff420ba5100d4a8779223', borrowMkt: M_USDC, collMkt: M_CBBTC, lastBlock: 56727680, repay: 26.63 },
  { holder: '0x57a3e7377b103f3e33c7cd0572881051c8bf9b55', borrowMkt: M_USDC, collMkt: M_USDC, lastBlock: 56789577, repay: 2225.9 },
  { holder: '0x9ab538c106c9ac3398c91c0bf72ded19791a5028', borrowMkt: M_USDC, collMkt: M_WETH, lastBlock: 56754499, repay: 882.4 },
  { holder: '0xb1145c99bea1323d80f43dd9bb74ee31433f10a2', borrowMkt: M_USDC, collMkt: M_WETH, lastBlock: 56757950, repay: 2705.7 },
];
const SEED_MIN_REPAY_USD = 10;      // whale-class seed filter, same units as repay_usd_last
const CHUNK = 250;                  // inner calls per multicall probe
const MAX_REPAY_WEI = 300000000n;   // flash-cap ceiling 300 USDC 6-dec units (capital 400); per-candidate sizing in simulate() caps it lower for WETH borrows
const MIN_PROFIT_WEI = 1000000n;    // executor minProfit argument = 1 USDC (fork proof floor)
const FLASH_MARGIN = 106n;          // x/100: size the WETH-borrow flash at 1.06x the debt/16 repay value (proof11 sizing 5.60 vs 5.29 USD = 1.0586x; a shortfall/2 flash strands the swap excess as unconverted WETH)
const MARGIN_EST = 0.06;            // fallback-only profit heuristic (sim revert); the success evidence is the executor's returned balance delta, not this ratio
const MIN_SEND_PROFIT_USD = 1;      // skip live sends below this measured profit
const MAX_GAS_LIMIT = 2200000n;     // measured executor success gasUsed 1642259 + headroom (guard NO_PROFIT path 1908994)
const MAX_FEE_CAP_WEI = 2000000000n; // 2 gwei maxFeePerGas cap (the old constant 25000000 was 0.025 gwei despite the 25 gwei comment). 2.2M gas x 2 gwei = 0.0044 ETH ~ 9.8 USD at ETH/USD 2233: fits the 18 USD Base wallet's EIP-1559 upfront check (balance >= gasLimit x maxFeePerGas) and carries 385x headroom over the measured Base baseFee 0.0052 gwei (feeHistory 8-block, relay research lane, 2026-11-06).
const LIVE_BALANCE_CAP_USD = 18;    // gate Base gas-float funding cap: on Base the enforceable worst case is the bot's native wallet (accepted policy); the signer refuses to sign while the balance is above it and the check below enforces it bot-side too
const ETH_USD_STALE_MS = 15 * 60 * 1000;

// --- executor (gate deploys the artifact at promotion; owner = bot wallet) ---
const EXEC = process.env.EXECUTOR_ADDR || '0xb464f7314d55ec6a9a0cf6f7f6df17af8ed5b352'; // fork-deployed MoonwellWhale of record (10-arg ctor, deployed at reset 56776412 run ecde30a1; live path reads EXECUTOR_ADDR/state/executor.json)
const RUNTIME_FILE = path.join(DIR, 'executor-runtime.hex');
const EXEC_OWNER = '0xfffffffffffffffffffffffffffffffffffffffe'; // owner baked into the forked runtime (the farm fork deploy deployer of record, measured from OWNER() at the 56776412 reset deploy run ecde30a1); paper sims call from it
const SEL_EXEC_LIQUIDATE = '0x3230da5d'; // liquidate(address,address,address,address,address,uint256,uint256,address,bytes,address,bytes,address,bytes)
// Fail-closed runtime validation: the paper sim must exercise the REAL deployed
// runtime (constructor-immutables patched). These are the byte offsets of the
// PUSH32 immutable words in the bundled forked runtime (measured 2026-11-05 by
// diffing the forge template against the fork eth_getCode); every value must be
// present at its offset or sims are disabled.
const IMMUTABLE_CHECKS = [
  [385, 'b90fe999be6869af0afc557dccfbe169ea3403d6'],  // P4 (offsets re-measured 2026-11-13 run ecde30a1 against the 10-arg fork-instance runtime of scratch/moonwell-whale3-base/contracts)
  [521, '4dbdcb087992404ea9b14fa83cc695b02797f39a'],  // P3 (offsets re-measured 2026-11-13 run ecde30a1 against the 10-arg fork-instance runtime of scratch/moonwell-whale3-base/contracts)
  [589, '833589fcd6edb6e08f4c7c32d4f71b54bda02913'],  // USDC (offsets re-measured 2026-11-13 run ecde30a1 against the 10-arg fork-instance runtime of scratch/moonwell-whale3-base/contracts)
  [657, '792f465e0434fb1028ea3bfeb05240cb839c4e04'],  // P0 (offsets re-measured 2026-11-13 run ecde30a1 against the 10-arg fork-instance runtime of scratch/moonwell-whale3-base/contracts)
  [826, 'fffffffffffffffffffffffffffffffffffffffe'],  // OWNER (offsets re-measured 2026-11-13 run ecde30a1 against the 10-arg fork-instance runtime of scratch/moonwell-whale3-base/contracts)
  [1054, 'fbb21d0380bee3312b33c4353c8936a0f13ef26c'],  // COMP (offsets re-measured 2026-11-13 run ecde30a1 against the 10-arg fork-instance runtime of scratch/moonwell-whale3-base/contracts)
  [1122, 'bbbbbbbbbb9cc5e90e3b3af64bdaf62c37eeffcb'],  // MORPHO (offsets re-measured 2026-11-13 run ecde30a1 against the 10-arg fork-instance runtime of scratch/moonwell-whale3-base/contracts)
  [725, 'dfe5f275020def30993f042174fc2d335678b626'],  // P5 (offsets re-measured 2026-11-13 run ecde30a1 against the 10-arg fork-instance runtime of scratch/moonwell-whale3-base/contracts)
  [453, '257fcbae4ac6b26a02e4fc5e1a11e4174b5ce395'],  // P6 (offsets re-measured 2026-11-13 run ecde30a1 against the 10-arg fork-instance runtime of scratch/moonwell-whale3-base/contracts)
  [7937, '784e539f15ca2d19449a6311c5dab6cf37d8f1ba'],  // P2 (offsets re-measured 2026-11-13 run ecde30a1 against the 10-arg fork-instance runtime of scratch/moonwell-whale3-base/contracts)
  [8005, '4a7af46bc8abc00048c6c7920a1488daf568366c'],  // P1 (offsets re-measured 2026-11-13 run ecde30a1 against the 10-arg fork-instance runtime of scratch/moonwell-whale3-base/contracts)
];
let RUNTIME_CODE = '';
let RUNTIME_OK = false;
try {
  RUNTIME_CODE = fs.readFileSync(RUNTIME_FILE, 'utf8').trim();
  RUNTIME_OK = IMMUTABLE_CHECKS.every(([o, a]) =>
    RUNTIME_CODE.slice(2 + 2 * o, 4 + 2 * o).toLowerCase() === '7f' &&
    RUNTIME_CODE.slice(4 + 2 * o, 68 + 2 * o).toLowerCase() === '0'.repeat(24) + a);
} catch (e) { /* sims disabled below */ }

let ETH_USD = 0, ETH_USD_AT = 0;
// Fix (review 2939f16e, 2026-11-09): this cycle's fresh-valuation flag, set in
// cycle() from refreshEthUsd()'s success and cleared at cycle start. The live send
// consults it: while confirmed gas receipts are still pending and THIS cycle has
// no fresh valuation, no send proceeds (the old up-to-15-minute price cache let
// sends continue while pending unvalued gas grew — the $30 stop threshold could
// then stay understated forever).
let PRICE_FRESH_THIS_CYCLE = false;
// Includable-fee cache for the net-gas send gate (review 71396b4d: a simulated
// profit >= 1 USD gross must also be positive AFTER expected gas before a live
// send; the signed worst-case cap stays log-only).
let FEE_WEI = 0n, FEE_WEI_AT = 0;
const FEE_STALE_MS = 60 * 1000;

const LOGS = process.env.BOT_LOGS_DIR || path.join(DIR, 'logs'); // BOT_LOGS_DIR: offline stop-tests keep their lines out of the paper audit trail
const STATE = process.env.BOT_STATE_DIR || path.join(DIR, 'state'); // BOT_STATE_DIR: offline stop-tests point state/ at scratch/
fs.mkdirSync(LOGS, { recursive: true });
fs.mkdirSync(STATE, { recursive: true });
const LOG = path.join(LOGS, 'bot.jsonl');
const STATE_FILE = path.join(STATE, 'state.json');
function log(obj) { fs.appendFileSync(LOG, JSON.stringify(obj) + '\n'); }

let rpcId = 0;
async function rpc(method, params, retry = 0) {
  const res = await fetch(`${RELAY}/${CHAIN}?lane=${LANE}`, {
    method: 'POST', headers: { 'content-type': 'application/json' },
    body: JSON.stringify({ jsonrpc: '2.0', id: ++rpcId, method, params }),
  }).then(r => r.json()).catch(e => { throw e; });
  if (res.error) {
    const msg = JSON.stringify(res.error).slice(0, 200);
    if (/rate|limit|quota|429|overloaded|-32005|busy/i.test(msg) && retry < 4) {
      await new Promise(r => setTimeout(r, 1200 * (retry + 1)));
      return rpc(method, params, retry + 1);
    }
    throw new Error(msg);
  }
  return res.result;
}
async function rpcRaw(method, params, retry = 0) {
  const res = await fetch(`${RELAY}/${CHAIN}?lane=${LANE}`, {
    method: 'POST', headers: { 'content-type': 'application/json' },
    body: JSON.stringify({ jsonrpc: '2.0', id: ++rpcId, method, params }),
  }).then(r => r.json()).catch(e => { throw e; });
  if (res.error) {
    const msg = JSON.stringify(res.error).slice(0, 200);
    // A rate/quota error is not the executor reverting: retry like rpc(), so a
    // sim revert string stays honest.
    if (/rate|limit|quota|429|overloaded|-32005|busy/i.test(msg) && retry < 4) {
      await new Promise(r => setTimeout(r, 1200 * (retry + 1)));
      return rpcRaw(method, params, retry + 1);
    }
  }
  return res; // the full response: keeps error AND gasUsed (the executable gas estimate)
}
const addr = a => a.toLowerCase().replace(/^0x/, '').padStart(64, '0');
const hex = x => '0x' + BigInt(x).toString(16);

// --- LiquidateBorrow event decoding (5 non-indexed words) ---
// The event DATA field starts right after 0x (no 4-byte selector like a tx
// input): word i lives at data.slice(2 + 64*i). (Reviewer ground truth block
// 53550622: borrower 0xa55ab0d1..., market 0x628ff693..., repay 66958.)
function decodeLB(data) {
  const w = [];
  for (let i = 0; i < 5; i++) w.push(data.slice(2 + 64 * i, 66 + 64 * i));
  return {
    liquidator: '0x' + w[0].slice(24),
    borrower: '0x' + w[1].slice(24),
    repayAmount: BigInt('0x' + w[2]),
    mTokenCollateral: '0x' + w[3].slice(24),
    seizeTokens: BigInt('0x' + w[4]),
  };
}

// --- swap calldata (fork-proven layout, proof10 swap_data) ---
function pad(a) { return a.replace(/^0x/, '').toLowerCase().padStart(64, '0'); }
function swapData(exec, zeroForOne, limit, token0, token1) {
  // swap(address recipient, bool zeroForOne, int256 amountSpecified, uint160 sqrtPriceLimitX96, bytes data)
  // data tail = abi.encode(token0, token1); the amountSpecified slot (bytes
  // [36:68)+4 ... the int256 word) is OVERWRITTEN by the executor with the
  // amount it measured, so pre-sizing cannot over-spend the operation.
  return '0x' + SEL_SWAP.slice(2) + pad(exec) + (zeroForOne ? '1'.padStart(64, '0') : '0'.repeat(64)) +
    '0'.repeat(64) + limit.slice(2).padStart(64, '0') +
    (160).toString(16).padStart(64, '0') + (64).toString(16).padStart(64, '0') +
    pad(token0) + pad(token1);
}
function liquidateCalldata(c, route, maxRepay) {
  // liquidate(address account, address holder, address borrowMkt, address collateralMkt,
  //   address underlying, uint256 maxRepay, uint256 minProfit, address borrowPool,
  //   bytes borrowSwapData, address sellPool1, bytes sellSwapData1, address sellPool2,
  //   bytes sellSwapData2): 13 head words (dynamic args carry offsets), then the
  //   three (length,data) tails in order. The fork proof DATA carries exactly the
  //   offsets 0x1a0/0x1c0/0x300 of that run (scratch/mw-whale/proof10.py).
  const legs = route.sell;
  const s1 = legs.length > 0 ? swapData(EXEC, legs[0].zeroForOne, legs[0].zeroForOne ? LIMIT_DOWN : LIMIT_UP, legs[0].token0, legs[0].token1) : '0x';
  const s2 = legs.length > 1 ? swapData(EXEC, legs[1].zeroForOne, legs[1].zeroForOne ? LIMIT_DOWN : LIMIT_UP, legs[1].token0, legs[1].token1) : '0x';
  // Borrow-underlying != USDC: the executor converts the flashed USDC to it on
  // the borrow pool (USDC->WETH = token1->token0, zeroForOne=false, increasing
  // sqrtPrice side). The borrow leg was never wired into the calldata before
  // (c.borrowSwap/c.borrowPool undefined => zero pool + empty data => the
  // executor reverts BORROW_POOL on every mWETH-borrow candidate).
  const bm = BORROW_MKTS[c.borrowMkt] || {};
  const bsd = bm.borrowPool ? swapData(EXEC, false, LIMIT_UP, bm.underlying, USDC) : '0x';
  const zero = '0x0000000000000000000000000000000000000000';
  const tail = (h) => { // (length,data padded to 32)
    const len = h === '0x' ? 0 : (h.length - 2) / 2;
    const pad = len % 32 ? '0'.repeat((32 - len % 32) * 2) : '';
    return len.toString(16).padStart(64, '0') + h.slice(2) + pad;
  };
  const t1 = tail(bsd), t2 = tail(s1), t3 = tail(s2);
  const headSize = 13 * 32;
  const off1 = headSize;
  const off2 = off1 + t1.length / 2;
  const off3 = off2 + t2.length / 2;
  const w = (s) => BigInt(s).toString(16).padStart(64, '0');
  const head = [c.holder, c.holder, c.borrowMkt, c.collMkt, route.underlying]
    .map(pad).join('') + w(maxRepay) + w(MIN_PROFIT_WEI) + pad(bm.borrowPool || zero) +
    w(off1) + pad(legs.length > 0 ? legs[0].pool : zero) + w(off2) +
    pad(legs.length > 1 ? legs[1].pool : zero) + w(off3);
  return '0x' + SEL_EXEC_LIQUIDATE.slice(2) + head + t1 + t2 + t3;
}

// --- state ---
const state = { cursor: 0, candidates: {}, probes: 0, cycles: 0, liveLoss: { usd: 0, pending: [] } };
// Fix (review 2026-11-09 run 13c85970, checklist items 8/9): a LIVE start must honour
// state/STOPPED.json (the durable stop marker: its existence stops the bot even if the
// persisted total was lost) and must NOT silently reset the cumulative loss to zero when
// state.json is missing or unreadable — startup fails closed until the next successful write.
// Fix (review 2026-11-09 run 7ba9c267, checklist item 9): failing closed until the first
// cycle persist() is NOT enough — that write succeeds, clears the flag and sends resume
// with a SILENTLY ZEROED loss total (the prior pending hashes and realized loss were in
// the damaged file, STOPPED.json was never written because the stop was never crossed).
// The halt must be kept until the prior loss history is RECOVERED, or made durable by a
// stop marker. Recovery source: the bot's own append-only log.
// Fix (review 2026-11-09 run c0654dd1, checklist item 9): the old SECOND-TO-LAST-heartbeat
// cutoff assumed a receipt settles within ~2 cycles of its send; it does not. A failed
// receipt read, a failed valuation or an unaccounted fee leg keeps a hash pending through
// MANY heartbeats (the send gate holds every send meanwhile — checklist item 2), so a
// receipt older than two heartbeats can still be uncounted. Recovery now keeps ALL
// accepted send hashes whose settlement is NOT durably recorded: liveLossSettle logs a
// {type:'live_loss_settled', hash, live_loss_usd} event the moment it counts a receipt,
// and every hash covered by such an event (or by a later heartbeat total) is inside the
// total. Unsettled hashes stay pending: their gas lands again once the receipt is re-read
// — over-, never under-count. The recovered total is the LAST total durably recorded: a
// heartbeat (written at the end of the cycle, after settlement) or a settlement event (a
// crash between settlement and the heartbeat leaves no heartbeat carrying that charge; the
// event itself carries the new total). A log with live sends but NO total recorded
// anywhere, an unreadable log, or no log file at all after a real run: history not
// restorable — keep the halt and make it durable (raise the total, set stopLogged, write
// the STOPPED.json marker; sends stay blocked across restarts). No log file / empty log:
// no prior live run to lose, a zero total is the truth.
function recoverLossFromLogs() {
  let raw;
  try { raw = fs.readFileSync(LOG, 'utf8'); } catch (e) { return { fresh: true }; } // no log file: no prior live run
  if (!raw || !raw.trim()) return { fresh: true }; // empty log: no prior run
  const lines = raw.split('\n');
  const sends = [];
  const settled = new Set();
  let lastUsd = null; // append order: the LAST durably recorded total wins (heartbeat or settlement event)
  for (const ln of lines) {
    if (!ln || (ln.indexOf('"type":"live_send"') < 0 && ln.indexOf('"type":"heartbeat"') < 0 && ln.indexOf('"type":"live_loss_settled"') < 0)) continue;
    let o = null; try { o = JSON.parse(ln); } catch (e) { continue; }
    if (!o || typeof o !== 'object' || typeof o.ts !== 'string') continue;
    if (o.type === 'heartbeat' && typeof o.live_loss_usd === 'number' && Number.isFinite(o.live_loss_usd)) {
      lastUsd = o.live_loss_usd;
    } else if (o.type === 'live_loss_settled' && typeof o.live_loss_usd === 'number' && Number.isFinite(o.live_loss_usd) && typeof o.hash === 'string' && /^0x[0-9a-fA-F]{10,}$/.test(o.hash)) {
      lastUsd = o.live_loss_usd; settled.add(o.hash); // settlement logged with its new total: this hash is durably counted
    } else if (o.type === 'live_send' && o.ok && typeof o.hash === 'string' && /^0x[0-9a-fA-F]{10,}$/.test(o.hash)) {
      sends.push(o.hash);
    }
  }
  if (lastUsd === null) return sends.length ? null : { fresh: true }; // sends logged with NO total recorded anywhere: not restorable
  const pending = []; const seen = new Set();
  for (const h of sends) if (!settled.has(h) && !seen.has(h)) { seen.add(h); pending.push(h); } // retain ALL accepted hashes whose settlement is not durably recorded (review c0654dd1)
  return { usd: lastUsd, pending };
}
function writeStartupStopMarker(reason) {
  try {
    const p = path.join(STATE, 'STOPPED.json');
    fs.writeFileSync(p + '.tmp', JSON.stringify({ reason, live_loss_usd: state.liveLoss.usd, at: new Date().toISOString() }) + '\n');
    fs.renameSync(p + '.tmp', p);
    return true;
  } catch (e) { return false; }
}
function loadState() {
  let loaded = false, stoppedPresent = false;
  try { stoppedPresent = BOT_MODE === 'live' && fs.existsSync(path.join(STATE, 'STOPPED.json')); } catch (e) { }
  try { Object.assign(state, JSON.parse(fs.readFileSync(STATE_FILE, 'utf8'))); loaded = true; } catch (e) { } // a truncated/unreadable file stays loaded=false
  if (!state.liveLoss) state.liveLoss = { usd: 0, pending: [] }; // pre-existing state.json has no key
  if (BOT_MODE === 'live' && !loaded) stateWriteFailed = true; // review 13c85970 blocker 4: fail closed at live startup on a missing/malformed state file
  // review 7ba9c267, checklist item 9: recover the prior loss history from the durable log,
  // or write a durable stop marker — the send gate never rearms on a silently zeroed total.
  if (BOT_MODE === 'live' && !loaded && !stoppedPresent) {
    const rec = recoverLossFromLogs();
    if (rec && rec.fresh) {
      // no prior live run: the zero total is the history
    } else if (rec) {
      state.liveLoss.usd = rec.usd; state.liveLoss.pending = rec.pending.slice();
      log({ ts: new Date().toISOString(), type: 'state_recovered', live_loss_usd: rec.usd, pending_hashes: rec.pending.length, source: 'logs/bot.jsonl heartbeats + live_send hashes' });
    } else {
      state.liveLoss.pending = [];
      state.liveLoss.stopLogged = true;
      writeStartupStopMarker('live state file missing or unreadable at startup and the loss history is not restorable from the logs: fail-closed durable stop marker written at startup, sending blocked');
      if (state.liveLoss.usd < LIVE_LOSS_STOP_USD) state.liveLoss.usd = LIVE_LOSS_STOP_USD;
      log({ ts: new Date().toISOString(), type: 'state_unrecoverable', live_loss_usd: state.liveLoss.usd, note: 'STOPPED.json marker written at startup; sends stay blocked across restarts' });
    }
  }
  if (stoppedPresent) { state.liveLoss.stopLogged = true; if (state.liveLoss.usd < LIVE_LOSS_STOP_USD) state.liveLoss.usd = LIVE_LOSS_STOP_USD; }
}
function saveState() { try { const tmp = STATE_FILE + '.tmp'; fs.writeFileSync(tmp, JSON.stringify(state)); fs.renameSync(tmp, STATE_FILE); return true; } catch (e) { return false; } } // review 13c85970 blocker 4: atomic write (temp + rename)
// Fix (review 2026-11-09 run 233973f5 parity): the §5 loss state (accepted send
// hash, settled gas, stopLogged) is persisted after EVERY change and BEFORE another
// send, not only at the cycle end (a cycle that throws after a send never reached
// the old save). While the last write failed, live sends are refused (fail closed);
// the next successful write clears the flag.
let stateWriteFailed = false;
function persist() { const ok = saveState(); stateWriteFailed = !ok; return ok; }

// --- cumulative live-loss stop (decisions/human/2026-11-09-promote-criteria.md §5) ---
// Realized loss = gas actually paid (gasUsed x effectiveGasPrice from the confirmed receipt,
// valued at the bot's fresh Base-ETH/USD) plus any realized principal loss; the executor
// reverts unless its USDC balance ends higher, so a failed send costs gas only. Settles
// confirmed live sends each cycle; at LIVE_LOSS_STOP_USD cumulative loss the bot stops
// sending and writes the reason to state/STOPPED.json.
const LIVE_LOSS_STOP_USD = 30;
// STATED upper bound per inclusion-fee component the receipt omits. Justified against
// OUR OWN signed gas cap, not an observation fit: every Base inclusion fee is charged
// over the gas our transaction consumed (gasUsed <= MAX_GAS_LIMIT = 2,200,000). The
// largest l1Fee measured for this route is 3.58e-8 ETH at 5,074,916 gasUsed (7.05e-15
// ETH per gas; capture tx 0xf0579b9d... block 55297682); scaled to our cap that is
// 1.55e-8 ETH, so 1e-6 ETH per omitted component carries ~65x headroom on the cap
// (measured again this session, 2026-11-09, relay research lane: relay Base receipt of
// capture tx 0x77259097... block 53550622 reports l1Fee 0x7cb1b809f = 3.36e-9 ETH at
// gasUsed 0xefbb9 = 981,993, and reports NO operatorFee/l2FeesIn11Eth — the provider
// omits those components, so their bound is the accounting rule).
const INCL_FEE_BOUND_ETH = 1e-6;
async function liveLossSettle(freshOk, fetchReceipt) {
  const keep = [];
  const getReceipt = fetchReceipt || ((h) => rpc('eth_getTransactionReceipt', [h])); // offline tests inject a receipt stub (checklist item 10)
  for (const h of state.liveLoss.pending) {
    let r = null;
    try { r = await getReceipt(h); } catch (e) {}
    if (!r) { keep.push(h); continue; } // receipt not visible yet
    // Fix (review 2026-11-09 run 7cbf8b95): settle ONLY on a valuation refreshed
    // in THIS cycle — cycle() passes refreshEthUsd()'s success flag. A failed
    // refresh leaves the prior ETH_USD in place; valuing a receipt with that
    // stale price would remove it from pending and lock the charge at the old
    // price forever (understating the $30 stop if ETH/USD rose). While the
    // refresh failed (including a live restart before any positive valuation,
    // ETH_USD = 0), keep confirmed receipts pending; they are counted exactly
    // once, when a cycle's refresh succeeds, and persist() in cycle() saves
    // the charge before the next send.
    if (!freshOk) { keep.push(h); continue; }
    // Fix (review 13c85970 blocker 2): the L1 data fee and the operator fee are charged
    // at INCLUSION and are bounded by NO signed field of our transaction (L is enforced
    // on Base by the 18 USD native wallet cap, not by fee fields). The reviewer rejected
    // settling on a PARTIALLY accounted fee total ("retain the receipt until the full
    // charged amount is known or establish a bound"). Two rules now, no partial zeroing:
    // (a) the receipt must report its L1 fee leg (l1Fee — measured: the relay's Base
    //     receipts DO report l1Fee; its absence means the provider is not accounting the
    //     inclusion fee at all) — without it the receipt stays pending;
    // (b) each further component the provider omits (operatorFee, l2FeesIn11Eth) is
    //     counted at the STATED cap INCL_FEE_BOUND_ETH above — never at zero, never at a
    //     1e-6 fit of the moment but a documented bound justified against our gas cap.
    // Fix (review 13c85970 blocker 2, gas legs): missing or malformed gasUsed /
    // effectiveGasPrice must keep the receipt pending — the old gasUsed || '0x0'
    // defaulted a missing field to zero and DROPPED the receipt, undercounting its gas.
    const gu = r.gasUsed, ep = r.effectiveGasPrice;
    if (typeof gu !== 'string' || !/^0x[0-9a-fA-F]*$/.test(gu) || typeof ep !== 'string' || !/^0x[0-9a-fA-F]*$/.test(ep)) { keep.push(h); continue; } // wei product kept exact, then float ETH
    const l1 = r.l1Fee;
    if (typeof l1 !== 'string' || !/^0x[0-9a-fA-F]*$/.test(l1)) { keep.push(h); continue; } // no L1 fee leg accounted yet: stay pending, sends blocked until accounted
    const gasEth = Number(BigInt(gu) * BigInt(ep)) / 1e18;
    let l1Eth = Number(BigInt(l1)) / 1e18;
    for (const f of ['operatorFee', 'l2FeesIn11Eth']) {
      const v = r[f];
      if (typeof v === 'string' && /^0x[0-9a-fA-F]*$/.test(v)) l1Eth += Number(BigInt(v)) / 1e18; // provider reported this component: count it exactly
      else if (typeof v === 'number' && Number.isFinite(v)) l1Eth += v / 1e18; // decimal wei variant
      else l1Eth += INCL_FEE_BOUND_ETH; // provider omitted this component: count the stated cap (over-, never under-count)
    }
    state.liveLoss.usd += (gasEth + l1Eth) * ETH_USD;
    // Fix (review 2026-11-09 run c0654dd1, checklist item 9): durable proof that this hash is
    // now inside the total — startup recovery keeps every accepted send hash UNLESS a
    // live_loss_settled event (or a later heartbeat) covers it, regardless of how many
    // heartbeats the pending receipt spanned.
    log({ ts: new Date().toISOString(), type: 'live_loss_settled', hash: h, live_loss_usd: state.liveLoss.usd });
  }
  state.liveLoss.pending = keep;
}
// Fix (review 13c85970 blocker 5): return the write result and write atomically — the
// caller sets stopLogged ONLY once the reason is durable; a failed write is retried.
function liveLossStopWrite() {
  try {
    const p = path.join(STATE, 'STOPPED.json');
    fs.writeFileSync(p + '.tmp',
      JSON.stringify({ reason: `cumulative live loss ${state.liveLoss.usd.toFixed(2)} USD reached ${LIVE_LOSS_STOP_USD} USD: stop sending`, live_loss_usd: state.liveLoss.usd, at: new Date().toISOString() }) + '\n');
    fs.renameSync(p + '.tmp', p);
    return true;
  } catch (e) { return false; }
}
// Fix (review 2026-11-09, attempt 677 parity): persist the §5 stop reason AS SOON AS
// settlement reaches the threshold — the send-time check in the live branch only
// fires when another qualifying candidate appears, so without this the reason is
// never written while the threshold sits crossed with no new opportunities.
// Called from cycle() right after liveLossSettle; writes STOPPED.json exactly once
// (the persisted stopLogged flag also guards the send-time branch below).
function liveLossStopCheck() {
  if (BOT_MODE === 'live' && state.liveLoss.usd >= LIVE_LOSS_STOP_USD && !state.liveLoss.stopLogged) {
    if (liveLossStopWrite()) state.liveLoss.stopLogged = true; // review 13c85970 blocker 5: set the flag ONLY when the reason is durable; a failed write is retried by this cycle-level check
    persist(); // review 233973f5 parity: STOPPED.json and the state total must stay consistent — persist the flag with the reason
    log({ ts: new Date().toISOString(), type: 'send_stop', live_loss_usd: state.liveLoss.usd, max_usd: LIVE_LOSS_STOP_USD, reason: 'settlement reached the stop threshold without a new opportunity: STOPPED.json persisted, sending stopped' });
  }
}

async function ethBlock() { return Number(await rpc('eth_blockNumber', [])); }

async function refreshEthUsd() {
  try {
    const r = await rpc('eth_call', [{ to: AAVE_ORACLE, data: SEL_GET_ASSET_PRICE + pad(WETH) }, 'latest']);
    ETH_USD = Number(BigInt(r)) / 1e8;
    ETH_USD_AT = Date.now();
    return true; // review 7cbf8b95: the settlement needs to know the price was refreshed in THIS cycle
  } catch (e) { /* stale check fails closed at send time */ }
  return false;
}
// Cached includable fee for the net gate: latest 8-block feeHistory baseFee tail
// + p90 priority reward (0.001 gwei floor). Used only to price the EXPECTED gas
// cost of a send; the signed cap MAX_FEE_CAP_WEI bounds the worst case.
async function refreshFee() {
  try {
    const r = await rpc('eth_feeHistory', ['0x8', 'latest', [50, 90]]);
    const bfs = r && r.baseFeePerGas, rws = r && r.reward;
    if (!bfs || !bfs.length || !rws || !rws.length) return;
    const bf = BigInt(bfs[bfs.length - 1]);
    const last = rws[rws.length - 1];
    let tip = 1000000n;
    if (last) { const t = BigInt((last[1] !== null && last[1] !== undefined ? last[1] : (last[0] || 0)) || 0); if (t > tip) tip = t; }
    if (bf >= 0n) { FEE_WEI = bf + tip; FEE_WEI_AT = Date.now(); }
  } catch (e) { /* stale fee: net gate falls back to the signed cap (fail closed) */ }
}

async function scanLogs(head) {
  // Seeding/catch-up mode: the cursor has not reached the live discovery
  // window. A cursor==0 start scans from SEED_FLOOR (one-time backfill,
  // ~40 pages x 2000 blocks per cycle: ~(head - SEED_FLOOR)/80000 cycles to
  // catch up); a lagged cursor resumes from its own cursor as before. In
  // catch-up mode the seed filter below trims past dust/watch-only captures.
  const seeding = state.cursor < Math.max(1, head - LOG_BLOCKS);
  let from = state.cursor === 0 ? Math.min(SEED_FLOOR, head) : state.cursor - CURSOR_LOOKBACK;
  if (from > head) return;
  let pages = 0;
  while (from <= head && pages < 40) {
    const to = Math.min(head, from + LOG_PAGE_BLOCKS - 1);
    let logs;
    try {
      logs = await rpc('eth_getLogs', [{ fromBlock: '0x' + from.toString(16), toBlock: '0x' + to.toString(16), address: EMIT_MARKETS, topics: [LIQ_TOPIC] }]);
    } catch (e) {
      if (/limit|too large|range|429/i.test(String(e).slice(0, 200)) && LOG_PAGE_BLOCKS > 125) {
        // shrink the page and retry this range
        rpc.pageBlocks = Math.floor(LOG_PAGE_BLOCKS / 2);
        continue;
      }
      throw e;
    }
    const pageBlocks = rpc.pageBlocks || LOG_PAGE_BLOCKS;
    for (const l of logs || []) {
      const ev = decodeLB(l.data);
      const key = ev.borrower.toLowerCase();
      const isNew = !state.candidates[key];
      const c = state.candidates[key] || { holder: key, probes: 0, added: to };
      c.borrowMkt = l.address.toLowerCase();
      c.collMkt = ev.mTokenCollateral.toLowerCase();
      c.repay_usd_last = Number(ev.repayAmount) / (10 ** ((BORROW_MKTS[c.borrowMkt] || {}).dec || 6)); // underlying units (the reviewed bug: 18-dec mWETH amounts divided by 1e6)
      c.lastBlock = to;
      c.seenAt = Date.now(); // wall clock of the LAST LiquidateBorrow sighting (TTL unit: the Base block rate changed mid-window, so blocks are not a stable retention unit)
      c.probes = 0; // event seen: fresh default state, keep the candidate
      if (isNew && seeding && (!BORROW_MKTS[c.borrowMkt] || c.repay_usd_last < SEED_MIN_REPAY_USD)) {
        // seed filter (attempt 647): past dust or watch-only-borrow captures
        // are probe noise on the seed pass; live discovery (cursor > 0) still
        // adds every borrower as before.
        continue;
      }
      state.candidates[c.holder] = c;
      if (isNew) state.added_total = (state.added_total || 0) + 1;
    }
    state.cursor = to;
    from = to + 1;
    pages++;
    rpc.pageBlocks = LOG_PAGE_BLOCKS;
  }
  if (seeding) log({ ts: new Date().toISOString(), type: 'seed_scan', floor: SEED_FLOOR, min_repay_usd: SEED_MIN_REPAY_USD, cursor: state.cursor, head, pages, candidates: Object.keys(state.candidates).length });
  // candidate cap: prune the least-recently-seen when over CAND_CAP
  const keys = Object.keys(state.candidates);
  if (keys.length > CAND_CAP) {
    keys.sort((a, b) => state.candidates[a].lastBlock - state.candidates[b].lastBlock);
    for (let i = 0; keys.length > CAND_CAP && i < keys.length; i++) delete state.candidates[keys[i]];
  }
}

// Simplest robust probe: one getAccountLiquidity eth_call per holder
// (whale candidate counts stay small under CAND_CAP; every probe is a plain
// read, chunked to bound one cycle's RPC burst).
async function probeAll() {
  const holders = Object.keys(state.candidates).slice(0, CAND_CAP);
  const out = {};
  for (let i = 0; i < holders.length; i += CHUNK) {
    const batch = holders.slice(i, i + CHUNK);
    for (const h of batch) {
      try {
        const r = await rpc('eth_call', [{ to: COMP, data: SEL_LIQ + pad(h) }, 'latest']);
        out[h] = [BigInt('0x' + r.slice(2, 66)), BigInt('0x' + r.slice(66, 130)), BigInt('0x' + r.slice(130, 194))];
      } catch (e) { out[h] = null; }
    }
    if (batch.length !== CHUNK) break;
  }
  return out;
}

async function simulate(c, shortfall) {
  const skip = reason => log({ ts: new Date().toISOString(), type: 'live_skip', holder: c.holder, reason: String(reason).slice(0, 160) });
  if (!BORROW_MKTS[c.borrowMkt]) { log({ ts: new Date().toISOString(), type: 'opportunity_watch_only', holder: c.holder, borrow: c.borrowMkt, reason: 'borrow market underlying is not USDC/WETH: executor cannot repay it' }); return; }
  const route = COLL_ROUTES[c.collMkt];
  if (!route) { log({ ts: new Date().toISOString(), type: 'opportunity_watch_only', holder: c.holder, coll: c.collMkt, reason: 'no measured collateral sale route' }); return; }
  if (!RUNTIME_OK) { log({ ts: new Date().toISOString(), type: 'opportunity_watch_only', holder: c.holder, coll: c.collMkt, reason: 'executor runtime missing or immutables unpatched (fail closed)' }); return; }
  const bm = BORROW_MKTS[c.borrowMkt] || {};
  // Flash cap sizing (USDC 6-dec units, the executor's maxRepay argument):
  // a USDC borrow repays in the flashed asset itself (the mToken caps the
  // repay at half the balance), so the 300 USDC ceiling stands. A WETH
  // borrow swaps the WHOLE flash to WETH and the mToken REVERTS the repay
  // above the seize value cap (the executor caps it at
  // borrowBalanceCurrent/16), so the flash must sit near the repay value:
  // flash = 1.06 x value(borrowBalance/16) (fork-proven sizing: flash
  // 5.60 USD against the 5.29 USD debt/16 value, +0.042771 USDC net; a
  // shortfall/2 flash stranded the swap excess and reverted).
  let maxRepay = MAX_REPAY_WEI;
  if (bm.borrowPool) {
    if (!ETH_USD) { log({ ts: new Date().toISOString(), type: 'live_skip', holder: c.holder, reason: 'no fresh ETH/USD for the flash sizing' }); return; }
    let bb;
    try { bb = BigInt(await rpc('eth_call', [{ to: c.borrowMkt, data: SEL_BB + pad(c.holder) }, 'latest'])); }
    catch (e) { log({ ts: new Date().toISOString(), type: 'live_skip', holder: c.holder, reason: 'borrowBalanceCurrent read failed: ' + String(e.message || e).slice(0, 120) }); return; }
    const price8 = BigInt(Math.round(ETH_USD * 1e8)); // 8-dec WETH/USD
    maxRepay = (bb * price8 * FLASH_MARGIN) / (16n * 100n * 100000000000000000000n); // 18-dec debt x 8-dec price x 1.06 /16 -> 6-dec USDC (1e26/1e20)
    if (maxRepay > MAX_REPAY_WEI) maxRepay = MAX_REPAY_WEI;
  }
  const repayUsd = Number(shortfall / 2n / 1000000000000000000n); // 1e18-USD -> dollars (reviewed unit bug: /1e12 gave microdollars labeled as dollars)
  // Dust gate: the executor's profit must clear its 1 USDC minProfit plus gas
  // (~0.05-0.4 USD at the measured Base fees). The conservative profit
  // heuristic repay x MARGIN_EST - 0.5 (MARGIN_EST = the measured 6.57
  // percent realized margin, 0.5 USD gas allowance) is below
  // MIN_SEND_PROFIT_USD once the repay estimate falls under ~25 USD;
  // re-simulating such a candidate every 15 s is RPC noise (measured
  // 2026-11-07: candidate 0xa55ab0 with an 0.067 USDC event repay and
  // shortfall ~0 ran sims labeled est_profit_usd -0.5 for hours).
  if (repayUsd * MARGIN_EST - 0.5 < MIN_SEND_PROFIT_USD) {
    log({ ts: new Date().toISOString(), type: 'simulate_skip_dust', holder: c.holder,
      repay_est_usd: repayUsd, shortfall_usd: Number(shortfall / 1000000000000000000n) });
    return;
  }
  const data = liquidateCalldata(c, route, maxRepay);
  let simFrom = EXEC_OWNER;
  if (BOT_MODE === 'live') {
    let me;
    try { me = await signer({ op: 'address' }); } catch (e) { skip('no signer address'); return; }
    if (!me || !me.address) { skip('no signer address'); return; }
    me = '0x' + String(me.address).slice(-40);
    const code = await rpc('eth_getCode', [EXEC, 'latest']).catch(() => null);
    if (!code || code === '0x') { skip('executor has no deployed code (gate has not deployed)'); return; }
    let owner;
    try { owner = '0x' + (await rpc('eth_call', [{ to: EXEC, data: SEL_EXEC_OWNER }, 'latest'])).slice(-40); } catch (e) { skip('OWNER() read failed'); return; }
    if (owner.toLowerCase() !== me.toLowerCase()) { skip(`executor owner ${owner} != our wallet ${me}`); return; }
    if (!ETH_USD || Date.now() - ETH_USD_AT > ETH_USD_STALE_MS) { skip('native valuation missing or stale'); return; }
    let balWei;
    try { balWei = BigInt(await rpc('eth_getBalance', [me, 'latest'])); } catch (e) { skip('wallet balance read failed'); return; }
    const capWei = BigInt(Math.floor(LIVE_BALANCE_CAP_USD / ETH_USD * 1e15)) * 1000n;
    if (balWei > capWei) { skip(`wallet balance ${(Number(balWei) / 1e18).toFixed(6)} ETH exceeds the ${LIVE_BALANCE_CAP_USD} USD gas-float funding cap at ETH/USD ${ETH_USD.toFixed(1)}`); return; }
    simFrom = me;
  }
  const callParams = [{ from: simFrom, to: EXEC, data }, 'latest'];
  if (BOT_MODE !== 'live') callParams.push({ [EXEC]: { code: RUNTIME_CODE } });
  // The executor RETURNS its measured USDC balance delta (liquidate()'s loss
  // bound): the eth_call return value IS the exact simulated profit, so the
  // bot's economics follow the simulated executor balance delta, not a
  // repay-ratio heuristic (the heuristic remains only as a fallback label on
  // reverted sims).
  if (Date.now() - FEE_WEI_AT > FEE_STALE_MS) await refreshFee();
  // rpcRaw keeps the eth_call RESPONSE OBJECT: its gasUsed is the executable gas
  // estimate for this exact calldata. Send gate per review 71396b4d: estimated
  // executable gas x includable fee comes off the simulated profit, and a live
  // send requires positive NET profit, not just the 1 USD gross floor.
  const raw = await rpcRaw('eth_call', callParams);
  const sim = raw && !raw.error
    ? { ok: true, ret: typeof raw.result === 'string' && raw.result.length >= 66 ? BigInt('0x' + raw.result.slice(-64)) : null }
    : { ok: false, revert: raw && raw.error ? JSON.stringify(raw.error).slice(0, 200) : 'rpc raw error' };
  let gasUsedEst = null;
  try { if (raw && raw.gasUsed !== undefined && raw.gasUsed !== null) gasUsedEst = Number(BigInt(raw.gasUsed)); }
  catch (e) { gasUsedEst = null; }
  const profitWei = sim.ok ? sim.ret : null;
  const estProfit = profitWei !== null ? Number(profitWei) / 1e6 : repayUsd * MARGIN_EST - 0.5;
  const gasCapUsd = Number(MAX_GAS_LIMIT * MAX_FEE_CAP_WEI) / 1e18 * (ETH_USD || 3000);
  // Expected gas cost of this exact calldata: eth_call gasUsed (fallback: the
  // signed gas limit) x cached includable fee, never above the signed fee cap.
  const feeNetWei = (FEE_WEI > MAX_FEE_CAP_WEI || Date.now() - FEE_WEI_AT > 5 * 60 * 1000) ? MAX_FEE_CAP_WEI : FEE_WEI;
  const gasUsd = profitWei !== null
    ? Number((gasUsedEst !== null ? BigInt(gasUsedEst) : MAX_GAS_LIMIT) * feeNetWei) / 1e18 * (ETH_USD || 3000)
    : null;
  const netProfitUsd = gasUsd !== null ? estProfit - gasUsd : null;
  const gatePassNet = sim.ok && profitWei !== null && estProfit >= MIN_SEND_PROFIT_USD
    && netProfitUsd !== null && netProfitUsd > 0;
  log({
    ts: new Date().toISOString(), type: 'simulate', holder: c.holder,
    borrowMkt: c.borrowMkt, collMkt: c.collMkt, underlying: route.underlying,
    shortfall_usd: Number(shortfall / 1000000000000000000n), repay_est_usd: repayUsd,
    flash_cap_usd: Number(maxRepay) / 1e6,
    est_profit_usd: Math.round(estProfit * 100) / 100,
    measured: profitWei !== null,
    min_profit_usd: Number(MIN_PROFIT_WEI) / 1e6,
    gas_cap_usd: Math.round(gasCapUsd * 100) / 100, sim_from: simFrom, sim_ok: sim.ok,
    sim_revert: sim.revert || null, to: EXEC, calldata: data,
    gas_used_estimate: gasUsedEst, fee_includable_gwei: Number(feeNetWei) / 1e9,
    gas_usd_estimate: gasUsd !== null ? Math.round(gasUsd * 1e6) / 1e6 : null,
    net_profit_usd: netProfitUsd !== null ? Math.round(netProfitUsd * 1e6) / 1e6 : null,
    gate_pass_net: gatePassNet,
  });
  if (!sim.ok && sim.revert && sim.revert.includes('LIQUIDATE_SEIZE_TOO_MUCH')) {
    // The protocol's own bad-debt signal: seizeTokens = liquidationCloseFactor
    // x accountBorrows is FIXED (independent of our repay size), and
    // liquidateBorrow reverts whenever seize x exchangeRate exceeds the
    // borrower's assets. Such a candidate cannot be liquidated on this path
    // at any repay size, so re-simulating it every 15 s forever is RPC noise:
    // drop it (measured 2026-11-07: the two retained core-market candidates
    // 0xa55ab0 and 0x21df358f reverted LIQUIDATE_SEIZE_TOO_MUCH on every
    // 15 s sim for hours - bots/paper/moonwell-whale-base/logs/bot.jsonl).
    // The next LiquidateBorrow event for the holder re-adds a fresh
    // candidate (scanLogs resets candidates on every seen event).
    log({ ts: new Date().toISOString(), type: 'candidate_drop_bad_debt', holder: c.holder, borrowMkt: c.borrowMkt, collMkt: c.collMkt, revert_reason: 'LIQUIDATE_SEIZE_TOO_MUCH' });
    delete state.candidates[c.holder];
  }
  if (BOT_MODE === 'live' && gatePassNet) {
    if (stateWriteFailed) { log({ ts: new Date().toISOString(), type: 'live_skip', holder: c.holder, reason: 'state persistence failed — fail closed, no send until the next successful state write (review 233973f5 parity)' }); return; }
    if (state.liveLoss.usd >= LIVE_LOSS_STOP_USD) { // §5 cumulative-loss stop: stop sending, reason in state/STOPPED.json
      if (!state.liveLoss.stopLogged) { if (liveLossStopWrite()) state.liveLoss.stopLogged = true; persist(); } // review 233973f5 parity: persist the flag with the reason; review 13c85970 blocker 5: flag only after a durable STOPPED.json write
      log({ ts: new Date().toISOString(), type: 'send_stop', holder: c.holder, live_loss_usd: state.liveLoss.usd, max_usd: LIVE_LOSS_STOP_USD });
      return;
    }
    // Fix (review 2939f16e, then review 13c85970 blocker 1): block a send while ANY
    // confirmed gas receipt is pending — not only when the price is not freshly
    // valued. The old condition let a fresh price permit another send while a failed
    // receipt read had left its receipt pending, so unvalued gas kept growing past a
    // pending send (checklist item 2). Settlement runs earlier in the same cycle
    // (cycle() settles before probeAll/simulate), so receipts confirmed in a previous
    // cycle clear this gate before this cycle can send; a send's own hash stays
    // pending (and blocks further sends) until the next cycle's settlement accounts it.
    if (state.liveLoss.pending.length > 0) { log({ ts: new Date().toISOString(), type: 'live_skip', holder: c.holder, reason: 'confirmed gas receipts pending — fail closed, no send until settlement accounts them (every signer send is blocked, review 13c85970)' }); return; }
    // Live send policy (Base accepted policy): the enforceable worst case is the
    // bot's native gas wallet (gate funds it at most 18 USD; the signer refuses
    // while above, checked above bot-side too), the executor reverts unless its
    // USDC balance ends higher, and the signer caps the signed fee field. A
    // rejection is final - log it, never retry in a loop.
    const s = await signer({
      op: 'send', chain: CHAIN, to: EXEC, data, value: '0x0',
      gasLimit: '0x' + MAX_GAS_LIMIT.toString(16), maxFeePerGas: '0x' + MAX_FEE_CAP_WEI.toString(16),
    });
    // Fix (review 2026-11-09 run c0654dd1): log the hash the signer ACTUALLY returned — the
    // live path below accepts s.hash || s.txHash; with only hash logged, a txHash-only
    // acceptance was invisible to the startup loss recovery.
    log({ ts: new Date().toISOString(), type: 'live_send', holder: c.holder, ok: !!s.ok, hash: s.hash || s.txHash || null, error: s.error ? String(s.error).slice(0, 160) : null });
    const txh = s && s.ok && (s.hash || s.txHash);
    if (txh) { state.liveLoss.pending.push(txh); persist(); } // settle its realized gas once the receipt is visible; review 233973f5 parity: persist the accepted hash BEFORE another send
  }
}
function signer(req) {
  const net = require('net');
  return new Promise((resolve) => {
    const sock = net.connect(process.env.SIGNER_SOCK);
    let buf = '';
    sock.on('data', d => buf += d);
    sock.on('end', () => { try { resolve(JSON.parse(buf)); } catch (e) { resolve({ ok: false, error: 'signer parse' }); } });
    sock.on('error', e => resolve({ ok: false, error: String(e) }));
    sock.write(JSON.stringify(req) + '\n');
  });
}

async function cycle() {
  const t0 = Date.now();
  const head = await ethBlock();
  const priceFresh = await refreshEthUsd(); // review 7cbf8b95: settlement requires a valuation refreshed in THIS cycle
  PRICE_FRESH_THIS_CYCLE = priceFresh && ETH_USD > 0; // review 2939f16e: publish this cycle's fresh-valuation result to the live send gate before settlement and before any candidate can send
  await liveLossSettle(priceFresh && ETH_USD > 0); // settle confirmed live sends' realized gas into the cumulative loss (§5); stale price -> receipts stay pending
  liveLossStopCheck(); // persist the §5 stop reason as soon as settlement crosses the threshold (no new candidate required)
  persist(); // review 233973f5 parity: settlement changed liveLoss.usd/pending — persist it before this cycle can send
  try { await scanLogs(head); } catch (e) { log({ ts: new Date().toISOString(), type: 'scan_error', error: String(e).slice(0, 200) }); }
  const probes = await probeAll();
  const underwater = [];
  let scanned = Object.keys(state.candidates).length;
  for (const h of Object.keys(state.candidates)) {
    const c = state.candidates[h];
    const w = probes[h];
    state.probes++;
    if (!w) { c.probes = (c.probes || 0) + 1; continue; }
    const [error, liquidity, shortfall] = w;
    if (error > 0n) { c.probes = (c.probes || 0) + 1; continue; } // LIQ_READ fail: keep, retry next cycle
    if (shortfall > 0n) {
      underwater.push(h);
      if (c.underwater !== true) {
        c.underwater = true;
        log({ ts: new Date().toISOString(), type: 'opportunity', holder: h, borrowMkt: c.borrowMkt, collMkt: c.collMkt, repay_usd_last_event: c.repay_usd_last, shortfall_usd: Number(shortfall / 1000000000000000000n), head });
      }
      await simulate(c, shortfall);
    } else {
      if (c.underwater === true) {
        log({ ts: new Date().toISOString(), type: 'underwater_closed', holder: h, head, note: 'was liquidatable, now healthy/gone - window measured' });
        c.underwater = false;
      }
      c.probes = (c.probes || 0) + 1;
      // healthy: keep the candidate until CAND_TTL_MS after its last LiquidateBorrow
      // event (repeat-default whale holders re-default; wall clock, NOT blocks: the
      // Base block rate changed mid-window, 4 probes ~= 60 s dropped all candidates
      // within one minute).
      if (Date.now() - (c.seenAt || 0) > CAND_TTL_MS) delete state.candidates[h];
    }
  }
  state.cycles++;
  log({ ts: new Date().toISOString(), type: 'heartbeat', head, scanned: Object.keys(state.candidates).length, added_total: state.added_total || 0, underwater_now: underwater.length, eth_usd: ETH_USD, cycle_ms: Date.now() - t0, executor: EXEC, runtime_ok: RUNTIME_OK, cursor: state.cursor, live_loss_usd: state.liveLoss.usd, live_loss_stop_usd: LIVE_LOSS_STOP_USD });
  persist(); // review 233973f5 parity: the cycle-end write re-clears the fail-closed flag on success
}

async function main() {
  loadState();
  // lean seed (run ecde30a1): the measured whale population from the ledger,
  // so the 10-min bot probes them from cycle 1 without a long event backfill.
  if (state.cursor === 0) {
    for (const s of SEED_WHALES) {
      const key = s.holder.toLowerCase();
      if (!state.candidates[key]) state.candidates[key] = { holder: key, borrowMkt: s.borrowMkt.toLowerCase(), collMkt: s.collMkt.toLowerCase(), repay_usd_last: s.repay, lastBlock: s.lastBlock, seenAt: Date.now(), probes: 0, added: s.lastBlock };
    }
  }
  await cycle().catch(e => log({ ts: new Date().toISOString(), type: 'cycle_error', error: String(e).slice(0, 300) }));
  let busy = false;
  setInterval(async () => {
    if (busy) return;
    busy = true;
    try { await cycle(); } catch (e) { log({ ts: new Date().toISOString(), type: 'cycle_error', error: String(e).slice(0, 300) }); }
    busy = false;
  }, CYCLE_MS);
}
main().catch(e => { console.error(e); process.exit(1); });
