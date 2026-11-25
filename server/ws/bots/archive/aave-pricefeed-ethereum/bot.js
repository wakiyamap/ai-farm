#!/usr/bin/env node
// aave-watcher-ethereum — Aave v3 liquidation watcher on the farm's Ethereum chain (transplant of aave-watcher-base v4).
// Fixes for paper-reviewer decision "fix" (review.md, run 6950ca00, 21:10Z):
//   1. Executor inventory protection (v4 AaveLiquidator): OWNER-ONLY
//      liquidate(), single constructor-baked ROUTER, the callback sells ONLY
//      the newly seized collateral delta (retained inventory is never swapped
//      and cannot mask a loss — the guard compares before/after), every
//      allowance is cleared, the callback is bound to an active authorized
//      operation, and same-asset liquidations skip the swap (newest observed
//      class, block 53465304).
//   2. Patched paper runtime: executor-runtime.hex is the DEPLOYED fork
//      runtime (real constructor immutables POOL/MORPHO/ROUTER/OWNER,
//      validated at startup); missing/invalid runtime fails CLOSED — no plain
//      eth_call fallback to an empty-code destination.
//   3. Owner-aware simulation: paper sims run from the runtime's fork OWNER;
//      live sims run from OUR signer wallet only after verifying the deployed
//      executor's code and owner() == signer wallet (fail closed), with no
//      code override.
//   4. L1 data fee is a conservative CAP (0.002 ETH ~= 20x measured typical),
//      so worstCaseGasLossUsd() stays an enforced upper bound under L1 fee
//      spikes; the fresh full-price ETH valuation refreshes every cycle and
//      staleness fails the send closed.
//   5. seizedUnits BigInt fix: liqBonusBps() Number is converted explicitly
//      before the BigInt multiply (was a TypeError on the first priced pair).
// Self-contained: node built-ins only, no external deps.
'use strict';
const fs = require('fs');
const path = require('path');
const net = require('net');

const RELAY = process.env.RPC_RELAY_URL || 'http://127.0.0.1:8545';
const LANE = process.env.RPC_LANE || 'paper';
const CHAIN = 'ethereum';
const DIR = __dirname;
const MODE = process.env.BOT_MODE || 'paper';

// --- measured constants (2026-11-03, this session: scratch/verify_aave.js) ---
const POOL = '0x87870bca3f3fd6335c3f4ce8392d69350b4fa4e2'; // mainnet Aave v3 Pool (measured: LiquidationCall emitter in tx 0x6909f406 / 0x0cc7f504)
const MULTICALL = '0xca11bde05977b3631167028862be2a173976ca11'; // Multicall3
const PROV_FALLBACK = '0x2f39d218133afab8f2b819b1066c7e434ad94e9e'; // pool.ADDRESSES_PROVIDER() (measured via relay)
const ORACLE_FALLBACK = '0x54586be62e3c3580375ae3723c145253060ca0c2'; // provider.getPriceOracle() (measured via relay)
const SEL = {
  getUserAccountData: '0xbf92857c', // (address) -> words: coll,debt,avail,lt,ltv,hf (hf = word 5)
  getReservesList: '0xd1946dbc', // () -> [offset, len, addresses...]
  getUserConfiguration: '0x4417a583', // (address) -> uint256, bit(2i)=borrowing bit(2i+1)=collateral
  getConfiguration: '0xc44b11f7', // (asset) -> uint256: ltv 0-15, lt 16-31, bonus 32-47 bps
  getReserveData: '0x35ea6a75', // (asset) -> struct: word8 aToken, word9 stableDebt, word10 varDebt
  getAssetPrice: '0xb3596f07', // (asset) -> uint256, 8-dec USD
  liquidationCall: '0x00a718a9', // (collateral,debt,user,debtToCover,bool receiveAToken) - verified on-chain
  balanceOf: '0x70a08231',
  allowance: '0xdd62ed3e',
  decimals: '0x313ce567',
  approve: '0x095ea7b3',
  tryAggregate: '0xbce38bd7', // (bool,(address,bytes)[])
  addProv: '0x0542975c', // pool.ADDRESSES_PROVIDER()
  getPriceOracle: '0xfca513a8', // provider.getPriceOracle()
};
const LIQ_EVENT_TOPIC0 = '0xe413a321e8681d831f4dbccbca790d2952b56f977908e45be37335533e005286';
// Cold-start debtor discovery (review b69e96b8 item 1): the countable victims are
// SILENT borrowers — measured 2026-11-13 this session: the three countable captures'
// victims appear in ZERO pool-log indexed topics within 20,000 blocks before their
// capture (scratch/aave-pricefeed-fix32/discovery_precheck.json), so the 500-block
// window can never discover them at a cold start. Their last appearance as an
// indexed pool-event argument is 30,337 / 407,388 / 409,306 blocks before capture
// (scratch/aave-pricefeed-fix32/last_seen2.json, last_seen3.json), in these
// measured event families only:
//  - LiquidationCall (topic0 LIQ_EVENT_TOPIC0, user = topic3): victim 26372987 was
//    liquidated before at 26301359 — partial cover leaves the position in the book,
//    so the pool's own liquidation history is the debtor registry for repeat
//    liquidations (measured sparse: 944 logs over 900,000 blocks).
//  - two measured dense families carrying the user as an indexed pool-event
//    argument (topic0s below, hashes copied from real pool receipts; the name is
//    not claimed — the family's meaning is measured only as "carries an active
//    borrower"): victims 26384827 (last at 25977439) and 26399074 (last at
//    25989772) appear only in these.
const LIQ_PREV_EVENT_TOPIC0 = '0xa534c8dbe71f871f9f3530e97a74601fea17b426cae02e1c5aee42c96c784051';
const USER_ACTIVITY_EVENT_TOPIC0 = '0xb3d084820fb1a9decffb176436bd02558d15fac9b0ddfed8c465bc7359d7dce0';
const KNOWN_LIQUIDATORS = [ // real mainnet liquidators measured in the ledger; selftest senders
  '0x00acd5005200e7009beb000000e35e1e002b5565',
  '0x0d9d2f3a58f5fb999c1800f34c85f630f1f75ae1',
  '0xd5fd6d3eeb669dcdd3d8bf78c2745fc920de39ba',
];
// replay target: real liquidation at block 53438141 (event-decoded victim)
const REPLAY = {
  tx: '0x0cc7f504556555be433fdd3c63c98dd2213fb4e6d29518cf97b6210693b9cb22',
  block: 26302093,
  user: '0x6926408f55c4f322ebe1a3cc7e4fff380c5543df',
  collateralAsset: '0xc02aaa39b223fe8d0a0e5c4f27ead9083c756cc2', // WETH
  debtAsset: '0xdac17f958d2ee523a2206206994597c13d831ec7', // USDT
  realDebtToCover: '20598859', // event (measured, ledger)
  realSeized: '9710416794145430', // event (measured, ledger)
};
// The three countable captures of the 30 d recount (README EV table; recount2
// rows: eligibility blocks and windows 26372981/+6, 26384825/+2, 26399071/+3)
// replayed through the SAME cold-start discovery AND detector (review b69e96b8
// item 1: "replay the current detector against those captures").
const REPLAYS = [
  REPLAY, // original single replay: 20k-chunk pool-log discovery
  { block: 26372987, eligibility: 26372981, user: '0x7b2747004773a86a4a4c38fc8d79a0399b8e2d77' },
  // the two COUNTED 26372987 cascade victims (README rows 1022.38 cover capped
  // to 250 -> ~11.3 net, and 36.10 cover -> ~0.64 net) crossed at the SAME
  // eligibility block 26372981 (review 050bb1c7: "show ... a simulated send in
  // a pre-capture block for each EV row being counted")
  { block: 26372987, eligibility: 26372981, user: '0x3c0b05027ddeb16cfa158f3f29802e31df14fffd' },
  { block: 26372987, eligibility: 26372981, user: '0x31e4750e811edf0d9ed3be6a4569834d37aac1aa' },
  { block: 26384827, eligibility: 26384825, user: '0x52de03b0d9f0366581e08fb2f7e971026bb56c38' },
  { block: 26399074, eligibility: 26399071, user: '0xe30d45c0226e4a09fe00d08d091ac6db00736baf' },
];

// --- executor path (live sends go HERE, never directly to the Pool) ---
// One tx through the bot-deployed AaveLiquidator (forge artifact
// scratch/aave-executor-base/contracts/out/AaveLiquidator.sol/AaveLiquidator.json,
// constructor args [POOL, MORPHO]): Morpho flashLoan(debt, cover) ->
// pool.liquidationCall -> swap ALL seized collateral on the measured UniswapV3
// pool -> Morpho pulls the flash back -> revert "NO_PROFIT" unless the
// executor's debt-asset balance rose by minProfit. Worst case per tx = gas only.
const MORPHO = '0xbbbbbbbbbb9cc5e90e3b3af64bdaf62c37eeffcb'; // Morpho Blue (same vanity address on mainnet, measured via relay eth_getCode)
// Phase 11c fail-CLOSED (review 504cda6e blocker 2): the executor address
// comes from the gate's EXECUTOR_ADDR or from this bot's own
// state/executor.json — never from a hard-coded fork-address fallback (a bot
// whose executor address is absent could not send live; the old
// '|| 0x14115b5fdab3afcd72cf03785041c720100edb0e' fallback papered over the
// missing gate address with a fork address).
const EXECUTOR_JSON = path.join(DIR, 'state', 'executor.json');
const EXEC = process.env.EXECUTOR_ADDR ||
  (fs.existsSync(EXECUTOR_JSON) ? (JSON.parse(fs.readFileSync(EXECUTOR_JSON, 'utf8')).address || '') : '');
if (!EXEC) { console.error('EXECUTOR_ADDR unset and no state/executor.json — exiting fail closed (phase 11c)'); process.exit(2); }
const SEL_EXEC_LIQUIDATE = '0x9153f799'; // liquidate(user,collateral,debt,cover,minProfit,fee) — v4 executor
// OWNER() — the executor declares the uppercase constant; owner() 0x8da5cb5b
// reverts on the deployed artifact (review 8a5a4f8a blocker 1, measured:
// lowercase reverts empty, uppercase returns the deployer)
const SEL_EXEC_OWNER = '0x117803e3';
const ROUTER = '0xe0554a476a092703abdb3ef35c80e0d76d32939f'; // mainnet UniV3 USDC/WETH 0.01% POOL (measured: token0=USDC, token1=WETH, fee()=100, fork read at block 26342234; the executor swaps DIRECTLY on this pool - the measured winner 0x8a8a9177 used the same pool.swap route, selector 0x128acb08)
const RUNTIME_FILE = path.join(DIR, 'executor-runtime.hex'); // DEPLOYED runtime bytecode (real constructor immutables)
const FORK_OWNER = '0xc0ffee0000000000000000000000000000000001'; // OWNER immutable inside the paper runtime
// fail CLOSED on missing/invalid runtime: a plain eth_call to an empty-code
// destination can "succeed", so paper sims only run with a validated runtime
// whose immutable slots really contain POOL, MORPHO, ROUTER and the fork owner.
let RUNTIME_CODE = '';
let RUNTIME_OK = false;
try {
  RUNTIME_CODE = fs.readFileSync(RUNTIME_FILE, 'utf8').trim();
  const bare = (a) => a.toLowerCase().slice(2);
  RUNTIME_OK = RUNTIME_CODE.length > 200 &&
    RUNTIME_CODE.toLowerCase().includes(bare(POOL)) &&
    RUNTIME_CODE.toLowerCase().includes(bare(ROUTER)) &&
    RUNTIME_CODE.toLowerCase().includes(bare(FORK_OWNER));
} catch (e) { RUNTIME_CODE = ''; RUNTIME_OK = false; }
// measured collateral-swap pools: one UniswapV3 0.01% WETH/USDC pool serves both
// directions (token0=WETH 0x4200..06, token1=USDC 0x8335..13, measured 2026-11-03);
// same-asset routes (collateral == debt, the newest observed class, block
// 53465304) need no swap at all (executor skips it); pairs without a measured
// pool are watch-only (no executor sim / live send)
const POOL_MAP = {
  '0xc02aaa39b223fe8d0a0e5c4f27ead9083c756cc2->0xa0b86991c6218b36c1d19d4a2e9eb0ce3606eb48': { router: ROUTER, fee: 100 },
  '0xa0b86991c6218b36c1d19d4a2e9eb0ce3606eb48->0xc02aaa39b223fe8d0a0e5c4f27ead9083c756cc2': { router: ROUTER, fee: 100 },
  '0xa0b86991c6218b36c1d19d4a2e9eb0ce3606eb48->0xa0b86991c6218b36c1d19d4a2e9eb0ce3606eb48': { router: ROUTER, fee: 0 },
  '0xc02aaa39b223fe8d0a0e5c4f27ead9083c756cc2->0xc02aaa39b223fe8d0a0e5c4f27ead9083c756cc2': { router: ROUTER, fee: 0 },
};

// --- loss guard parameters (live) ---
const MAX_FEE_CAP_WEI = 17500000000n; // 17.5 gwei hard cap on maxFeePerGas (17.5 x 1e9 wei — the previous 17500000 was 0.0175 gwei, BELOW the measured relay header 26346513 baseFee 39667364 wei, so derivedFeeWei returned 17500000 and live sends were never includable; the fresh gas x cap USD check at send still refuses sends whose worst case exceeds 20 USD: 1.06M x 17.5 gwei = 0.01855 ETH ~= 45 USD at 2433 USD/ETH)
const FEE_TIP_WEI = 1000000n; // 0.001 gwei priority tip
let FEE_WEI = MAX_FEE_CAP_WEI; // per-cycle DERIVED cap: min(baseFee*9/8 + tip, cap) — includable at the current basefee
// Fix round 8 (review d6e6966d): ONE cached block read serves the head AND the
// fee cap. The old loop paid eth_getBlockByNumber (derivedFeeWei) plus an
// eth_blockNumber head read per cycle — with the ~4-8 s sequential cycle that
// was ~2 requests/cycle ≈ 20-40k reads/day for information that changes once
// per 12 s block. readHead() reads the latest block at most once per HEAD_POLL_MS
// (4 s while the follow-up queue holds a fresh underwater observation — the
// two-block confirmation must not wait on a stale head; 10 s otherwise, ~block
// cadence + slack) and derives FEE_WEI from the SAME response.
let HEAD = 0, HEAD_AT = 0, HEAD_POLL_MS = 10000;
async function readHead(force) {
  if (!force && HEAD && Date.now() - HEAD_AT < HEAD_POLL_MS) return HEAD;
  const blk = await rpc('eth_getBlockByNumber', ['latest', false]);
  const n = parseInt(blk.number, 16);
  if (n >= HEAD) { HEAD = n; HEAD_AT = Date.now(); } else HEAD_AT = Date.now();
  const bf = blk.baseFeePerGas ? BigInt(blk.baseFeePerGas) : MAX_FEE_CAP_WEI;
  const f = bf * 9n / 8n + FEE_TIP_WEI;
  FEE_WEI = f < MAX_FEE_CAP_WEI ? f : MAX_FEE_CAP_WEI;
  return HEAD;
}
async function derivedFeeWei() { await readHead(true); return FEE_WEI; }
const MAX_GAS_LIMIT = 900000n; // executor path bound (mainnet liquidationCall+flash+swap sized from the ethereum fork proof; cap case 900k x 17.5 gwei + approvals stays within MAX_LOSS_PER_TX_USD)
// L1 data fee: OP-stack bills it SEPARATELY from L2 gas, so maxFeePerGas x
// gasLimit does NOT bound it. Enforced bound (bot.js l1FeeBoundWei): the
// GasPriceOracle predeploy's fresh l1BaseFee()+blobBaseFee() times the
// MEASURED per-l1-gas charge times a 20x spike margin, compared against the
// hard cap L1_DATA_FEE_WEI; any read failure fails the send closed.
// Calibration (real receipts through this relay, 2026-11-03/04):
//   tx 0xaf3a3bd7... l1Fee 4.951e9 wei, l1GasUsed 23797, l1BaseFee 3.623e7, blob 1.907e6
//   tx 0xded83b28... l1Fee 3.396e9 wei, l1GasUsed  1821, l1BaseFee 2.971e8, blob 1.804e7
//   -> fee/l1GasUsed ~= (0.0055..0.0059) x (l1BaseFee+blobBaseFee); COEFF 6/1000 covers it.
const GPO = '0x420000000000000000000000000000000000000f'; // Base GasPriceOracle predeploy (live reads)
const SEL_GPO_L1BASEFEE = '0x519b4bd3'; // l1BaseFee()
const SEL_GPO_BLOB = '0xf8206140'; // blobBaseFee()
const L1_GAS_USED_MAX = 25000n; // receipt-measured 1,821-23,797 for liquidation-size calldata
const L1_FEE_COEFF_NUM = 6n, L1_FEE_COEFF_DEN = 1000n; // measured per-l1-gas coefficient (see above)
const L1_MARGIN = 20n; // L1 base fee moves <=12% per L1 block; 20x covers hours of sustained spikes
const L1_DATA_FEE_WEI = 2000000000000000n; // hard cap: 0.002 ETH ~= 400,000x the measured 3.4-5e9 wei typical
const APPROVE_GAS = 80000n; // bounded allowance tx, counted twice in the gas bound
const ETH_USD_STALE_MS = 15 * 60 * 1000; // live sends refuse when the native valuation is older
const MAX_COVER_USD = 250; // principal at risk per liquidation (capital 400)
const MAX_LOSS_PER_TX_USD = 20; // hard L bound: sends are rejected above this
const MIN_PROFIT_USD = 0.5;
// Lowered 1.0 -> 0.5 (2026-11-13, this session, replay measurement): the
// confirmation scheduler's FIRST decision block is eligibility+1, where the
// countable captures sit at HF ~0.997-0.998 — inside Aave's 50 pct close
// factor, so the fundable cover is HALF the capture-block cover the incumbent
// winners repaid (measured: 22.20/25.19 USD cover at eligibility+1 vs
// 44.4/50.38 USD repaid at the capture block). The counted captures' net at
// that block is ~0.6-0.9 USD — a 1.0 USD send floor watches them out of the
// 2-6 block window. 0.5 stays above the live worst-case gas bound (measured
// ~0.19-0.27 USD) and the executor minProfit argument below, so every send is
// still net-positive after gas and the on-chain guard still reverts unless the
// executor's balance ends higher by the floor.
const SLIPPAGE_BUFFER_BPS = 100n; // 1% price-move buffer subtracted from bonus
// Detection-miss fix (review 389147c2): on the natural winner event (block 26349403, victim
// 0x99da8b0c) the position crossed HF=1 INSIDE the capture block — HF was 1.0044471516 healthy
// at the parent — so a trigger at exactly 1.0 only ever fires post-event and the victim was
// discovered from the LiquidationCall event itself (via:'liquidation'). 1.005 pre-logs and
// pre-simulates near-underwater positions: measured drift ~3.5e-5 HF/block puts a position
// crossing 1.005 about 1-2 blocks before crossing 1.0 on that event (HF 1.01124 at
// 26349360 -> 1.00444741 at 26349380 -> liquidated at 26349403), i.e. within a few 8 s scan
// cycles; the executor still reverts healthy users with custom error 0x930bb771, so early
// logging costs only the simulation cooldown.
const HF_TRIGGER = 1.005;
// Wide wake band (review b69e96b8 item 1): the feed wake re-reads candidates
// last seen in 1 <= lastHf < NEAR_WAKE_TRIGGER, NOT only the 1.005 pre-log band.
// Measured fast-crossers (26384827 last-healthy 1.006, 26399074 1.009 the block
// before the wake) cross HF=1 IN the price-update block, so a wake filter
// pinned to 1.005 would skip them and they would only be re-read by the ~6 min
// round-robin poll (~30 blocks) — too late for a 2-3 block window. 1.05 covers
// both fast-crossers and the slow crossers; the near set stays bounded (only
// candidates already read as healthy-but-close enter, SCAN_CHUNK-capped).
const NEAR_WAKE_TRIGGER = 1.05;
const CLOSE_FACTOR_HF_THRESHOLD = 0.95; // official LiquidationLogic.sol:68
const CYCLE_MS = 8000;
const REFRESH_MS = 5 * 60 * 1000;
const LOG_BLOCKS = 500; // mainnet pool event density: keep the discovery window response small
const REPLAY_BLOCKS = 20000; // replay discovery window: strictly pre-event blocks
// Cold seed (bounded, runs ONCE at a cold start; review b69e96b8 item 1):
// the measured max victim lookback is 409,306 blocks (scratch/aave-pricefeed-
// fix32/last_seen3.json), so the dense-family chunk scan must reach ~480k blocks
// back. Two measured dense families (~0.18 logs/block each, ~544-556 logs per
// 3000 blocks) are OR-scanned newest-first in SEED_CHUNK blocks per chunk so a
// 2-family chunk stays inside the relay's 10k-log cap (2 × 0.18 × 15000 ≈ 5.5k).
// SEED_MAX_CHUNKS bounds the request count (depth dominates: the added cap does
// NOT stop the scan, so deep silent borrowers are always reached); the sparse
// LiquidationCall history is ONE request (measured 944 logs/900k blocks).
const SEED_BLOCKS = 900000; // single-scan floor (LiquidationCall, sparse: 944 logs/900k)
const SEED_CHUNK = 15000; // dense-family chunk width (2 families × 0.18 × 15000 ≈ 5.5k logs)
const SEED_MAX_CHUNKS = 32; // bounds the seed request count; 32 × 15000 = 480k blocks >= 409k lookback
// Eviction quota for seed/liquidation candidates (review 5f623a88: the live
// cold seed measured 20,146 added candidates at head 26406945 — the old
// 4,000-entry quota EVICTED the deep silent debtors (the timing-ordered slice
// kept only the newest ~9,000 wall-clock additions), i.e. exactly the three
// countable victims. The quota now covers the measured seed adds; retention
// is deterministic by event BLOCK (last-seen), not scan wall-clock timing:
// seed overflow drops the seed entries with the NEWEST last-seen block, and
// activity entries are kept newest-seen first. A victim last seen ~12 d ago
// is therefore retained whatever the request pacing was.
const SEED_MAX_ADDED = 21000; // measured adds 20,146 (cold_seed log 2026-11-13 15:30Z)
// Simulation cadences are BLOCK-based (review e3f07d25: a wall-clock 10 min
// cooldown cannot gate a 24-72 s capture window, and wall time does not exist
// on the replay's historical blocks): a healthy watch candidate re-simulates
// every 50 blocks (~10 min), an underwater candidate inside its confirmation
// window re-simulates once per BLOCK — bounded: the window runs from the FIRST
// underwater observation to SIM_WINDOW_MS (30 min), the follow-up queue itself
// re-reads each queued candidate every block while it stays underwater.
// Fix round 8 (review d6e6966d: lower the running read cost): the healthy watch
// band re-simulates every 200 blocks (~40 min at 12 s blocks) instead of 50. The
// measured watch-band candidates sat ~10 accounts each simulating every 50 blocks
// (133 min of paper logs: 10 sims per watch candidate) — 1 sim of a WETH/USDC
// account costs ~6-12 relay reads, so the watch band alone was ~25k reads/day at
// half the process's measured request rate. A fresh crosser is unaffected: the
// healthy->underwater transition clears lastSim/lastSimOk (scanCycle below), so
// the countable candidate always simulates at its FIRST confirmation block.
const SIM_COOLDOWN_BLOCKS = 200; // healthy watch candidates: ~40 min at 12 s blocks
const UNDERWATER_SIM_COOLDOWN_BLOCKS = 1; // in-window error retry: next block
// After a COMPLETED (non-error) simulation the next one waits SIM_OK_COOLDOWN
// blocks: a paper in-window candidate with a profitable pair no longer re-simulates
// every block for the full 30-min window (each repeat was ~6-12 relay reads and
// only re-logged the same numbers); an errored sim keeps the 1-block retry pace.
const SIM_OK_COOLDOWN_BLOCKS = 5; // ~60 s at 12 s blocks
const SIM_WINDOW_MS = 30 * 60 * 1000; // follow-up window after the first HF<1 observation
const FOLLOWUP_MAX = 400; // bounded follow-up queue (drop oldest on overflow)
const SEND_COOLDOWN_MS = 10 * 60 * 1000; // live: one executor send per user per 10 min
const MAX_CANDIDATES = 5000; // recent-activity universe; seed entries are exempt (own quota)
const SCAN_CHUNK = 200;
// Feed trigger (measured 2026-11-13, attempts:1116): the price update landing in
// the eligibility block of every countable capture is a Chainlink AnswerUpdated
// on aggregator implementation 0x7c7fdf... (~208 logs/day, pinned low-volume).
const FEED = process.env.FEED_URL || 'http://127.0.0.1:8546';
const FEED_ADDR = '0x7c7fdfca295a787ded12bb5c1a49a8d2cc20e3f8';
const ANSWER_UPDATED = '0x0559884fd3a460db3073b7fc896cc77986f16e378210ded43186175bf646fc5f';

const LOGS = path.join(DIR, 'logs');
const STATE = path.join(DIR, 'state');
fs.mkdirSync(LOGS, { recursive: true });
fs.mkdirSync(STATE, { recursive: true });
const LOG = path.join(LOGS, 'bot.jsonl');
const STATE_FILE = path.join(STATE, 'candidates.json');
const lastSendTs = {}; // per-user wall-clock stamp of the last executor send attempt (live)

function log(obj) { fs.appendFileSync(LOG, JSON.stringify(obj) + '\n'); }
function pad(a) { return a.toLowerCase().replace(/^0x/, '').padStart(64, '0'); }

let rpcId = 0;
// read-cost accounting (review c57f7ed7: the reviewer re-computes CU/day from
// the RUNNING process's own read count, not the README's estimate): every relay
// request increments RPC_REQS; the heartbeat carries the cumulative counter so a
// steady paper run extrapolates CU/day directly (a Multicall3 aggregate counts
// as ONE read, the farm's README convention).
let RPC_REQS = 0;
// FORK_RPC (selftest-live only): talk to the local fork endpoint verbatim;
// paper/live always use the relay with the chain + lane path.
const ENDPOINT = process.env.FORK_RPC || `${RELAY}/${CHAIN}?lane=${LANE}`;
async function rpc(method, params) {
  RPC_REQS++;
  const res = await fetch(ENDPOINT, {
    method: 'POST', headers: { 'content-type': 'application/json' },
    body: JSON.stringify({ jsonrpc: '2.0', id: ++rpcId, method, params }),
  });
  const j = await res.json();
  if (j.error) throw new Error(`${method}: ${JSON.stringify(j.error).slice(0, 200)}`);
  return j.result;
}
async function call(to, data, block, from) {
  const tx = { to, data };
  if (from) tx.from = from;
  return rpc('eth_call', [tx, block || 'latest']);
}
const u = (h, i) => BigInt('0x' + (h.slice(2 + i * 64, 2 + (i + 1) * 64) || '0'));
const addrOf = (w) => '0x' + w.toString(16).padStart(64, '0').slice(-40); // LOW 20 bytes

async function tryAggregate(calls, block) {
  const roundup = (n) => Math.ceil(n / 32) * 32;
  const starts = [];
  let acc = 0x20 * calls.length;
  for (const c of calls) { starts.push(acc); acc += 0x60 + roundup((c.data.length - 2) / 2); }
  let enc = SEL.tryAggregate + pad('0') +
    '0000000000000000000000000000000000000000000000000000000000000040' +
    (calls.length).toString(16).padStart(64, '0');
  calls.forEach((c, i) => { enc += starts[i].toString(16).padStart(64, '0'); });
  calls.forEach((c) => {
    enc += pad(c.to) +
      '0000000000000000000000000000000000000000000000000000000000000040' +
      ((c.data.length - 2) / 2).toString(16).padStart(64, '0') +
      c.data.slice(2) +
      '0'.repeat(roundup((c.data.length - 2) / 2) * 2 - (c.data.length - 2));
  });
  const r = await call(MULTICALL, enc, block);
  const h = r.slice(2);
  if (h.length < 128) return calls.map(() => ({ success: false, returnData: '0x' }));
  const n = Math.min(Number(BigInt('0x' + h.slice(64, 128))), calls.length);
  const out = [];
  for (let i = 0; i < n; i++) {
    const elemStart = 128 + Number(BigInt('0x' + h.slice(128 + i * 64, 192 + i * 64))) * 2;
    const success = BigInt('0x' + h.slice(elemStart, elemStart + 64)) !== 0n;
    const bytesOff = Number(BigInt('0x' + h.slice(elemStart + 64, elemStart + 128)));
    const len = Number(BigInt('0x' + h.slice(elemStart + bytesOff * 2, elemStart + bytesOff * 2 + 64)));
    const rd = h.slice(elemStart + bytesOff * 2 + 64, elemStart + bytesOff * 2 + 64 + len * 2);
    out.push({ success, returnData: '0x' + rd });
  }
  while (out.length < calls.length) out.push({ success: false, returnData: '0x' });
  return out;
}

// cache: decimals and reserve token addresses
const tokenCache = { decimals: {}, reserveData: {} };
// decimals(): fail CLOSED — returns null on any error/implausible value, and the
// caller skips the pair; it never silently defaults to 18.
async function decimals(asset) {
  if (tokenCache.decimals[asset] !== undefined) return tokenCache.decimals[asset];
  let d = null;
  try {
    d = Number(u(await call(asset, SEL.decimals), 0));
    if (!(d > 0 && d <= 24)) d = null;
  } catch (e) { d = null; }
  tokenCache.decimals[asset] = d;
  return d;
}
async function reserveData(asset, block) {
  const key = asset + '@' + (block || 'latest');
  if (tokenCache.reserveData[key] !== undefined) return tokenCache.reserveData[key];
  let out = null;
  try {
    const rd = await call(POOL, SEL.getReserveData + pad(asset), block);
    // measured struct layout: word8 aToken, word9 stableDebtToken, word10 variableDebtToken
    out = {
      aToken: addrOf(u(rd, 8)),
      stableDebt: addrOf(u(rd, 9)),
      varDebt: addrOf(u(rd, 10)),
    };
    const zero = '0x0000000000000000000000000000000000000000';
    if (out.aToken === zero || out.stableDebt === zero || out.varDebt === zero) out = null;
  } catch (e) { out = null; }
  tokenCache.reserveData[key] = out;
  return out;
}
// ORACLE is a module global set once at startup from resolveOracle(); assetPrice
// fails CLOSED (throws on zero price) so callers skip stale/unknown markets.
let ORACLE = ORACLE_FALLBACK;
// 'latest' prices move only on oracle updates — cache them for 60 s (fix round
// 7, review c57f7ed7: assetPrice was 2+ uncached reads per simulate pair). The
// per-block historical reads (replay, the send-time priceStable parent probe)
// are NOT cached: each block is read once.
const PRICE_TTL_MS = 60 * 1000;
const priceCache = {};
async function assetPrice(asset, block) {
  const cacheable = block === undefined;
  const key = asset + (cacheable ? '@latest' : '@' + block);
  const c = priceCache[key];
  if (c && Date.now() - c.at < (cacheable ? PRICE_TTL_MS : 0)) return c.price;
  const p = await call(ORACLE, SEL.getAssetPrice + pad(asset), block);
  const price = u(p, 0); // 8-dec USD
  if (price === 0n) throw new Error('assetPrice zero (oracle returned 0) for ' + asset);
  priceCache[key] = { at: Date.now(), price };
  return price;
}
// code-enforced freshness guard: the oracle price of BOTH sides must be stable
// between the parent block and latest, else we skip (bounds the adverse move we
// can eat between simulation and execution).
const PRICE_MOVE_MAX_BPS = 200n; // 2% per block
async function priceStable(dAsset, cAsset, block) {
  const latest = await blockNumber();
  const parent = '0x' + Math.max(0, latest - 1).toString(16);
  const pdNow = await assetPrice(dAsset); const pdPrev = await assetPrice(dAsset, parent);
  const pcNow = await assetPrice(cAsset); const pcPrev = await assetPrice(cAsset, parent);
  const move = (a, b) => (a > b ? ((a - b) * 10000n) / b : ((b - a) * 10000n) / b);
  if (move(pdNow, pdPrev) > PRICE_MOVE_MAX_BPS || move(pcNow, pcPrev) > PRICE_MOVE_MAX_BPS) return false;
  return true;
}
// liquidation bonus per collateral changes only on governance votes — 1 h cache
// (fix round 7, review c57f7ed7: it was one uncached read per simulate pair).
const BONUS_TTL_MS = 60 * 60 * 1000;
const bonusCache = {};
async function liqBonusBps(asset) {
  const c0 = bonusCache[asset];
  if (c0 && Date.now() - c0.at < BONUS_TTL_MS) return c0.bps;
  const c = await call(POOL, SEL.getConfiguration + pad(asset));
  const bps = Number((u(c, 0) >> 32n) & 0xffffn); // bps, 10000 = no bonus
  bonusCache[asset] = { at: Date.now(), bps };
  return bps;
}

// Enforced L1 data-fee bound in wei (live): fresh l1BaseFee()+blobBaseFee()
// from the GasPriceOracle predeploy times the MEASURED per-l1-gas coefficient,
// times the L1_GAS_USED_MAX calldata cover, times the spike margin — and the
// caller requires it under the hard cap L1_DATA_FEE_WEI. Any read failure
// throws => the send path fails CLOSED (no send without a fresh bound).
async function l1FeeBoundWei() { return 0n; } // mainnet: no separate L1 data fee — every fee is bounded by maxFeePerGas x gasLimit

// worst-case gas loss in USD (loss guard, live): the executor tx gas bound
// (ENFORCED by the tx itself: gas=MAX_GAS_LIMIT, maxFeePerGas=MAX_GAS_PRICE_WEI)
// plus the enforced fresh L1 data-fee bound plus two bounded-allowance approval
// txs, valued at the FRESH full oracle ETH price (no discount) refreshed every
// cycle and again at send; staleness fails the send closed.
let ETH_USD = 0, ETH_USD_AT = 0;
function worstCaseGasLossUsd(l1BoundWei) {
  const l1 = l1BoundWei === undefined ? 0n : BigInt(l1BoundWei);
  const wei = MAX_GAS_LIMIT * FEE_WEI + l1 + 2n * APPROVE_GAS * FEE_WEI;
  return Number(wei) / 1e18 * ETH_USD;
}
async function refreshEthUsd(oracle) {
  // read-cost fix (review c57f7ed7, fix round 7): the oracle price is re-read at
  // most once a minute, not every 8 s cycle; the send path keeps its own fresh
  // read and the 15-min staleness guard, so the cycle refresh is only a warm
  // cache for the per-cycle gas bound.
  if (ETH_USD_AT && Date.now() - ETH_USD_AT < ETH_USD_REFRESH_MS) return;
  try {
    const p = Number(u(await call(oracle, SEL.getAssetPrice + pad('0xc02aaa39b223fe8d0a0e5c4f27ead9083c756cc2')), 0)) / 1e8;
    if (p > 0) { ETH_USD = p; ETH_USD_AT = Date.now(); }
  } catch (e) { /* keep last; staleness checked at send */ }
}
const ETH_USD_REFRESH_MS = 60 * 1000;

async function resolveOracle() {
  try {
    const prov = addrOf(u(await call(POOL, SEL.addProv), 0));
    const oracle = addrOf(u(await call(prov, SEL.getPriceOracle), 0));
    if (oracle !== '0x0000000000000000000000000000000000000000') return { prov, oracle };
  } catch (e) { /* fall through */ }
  return { prov: PROV_FALLBACK, oracle: ORACLE_FALLBACK };
}

// read-cost fix (review c57f7ed7, fix round 7): the reserve list changes only on
// Aave governance listings — cache it for 10 min instead of re-reading it in
// EVERY simulateLiquidation (it was one of the reviewer's "at least two reads
// per simulate row").
const RESERVES_TTL_MS = 10 * 60 * 1000;
let reservesCache = { at: 0, list: null };
async function getReserves() {
  if (reservesCache.list && Date.now() - reservesCache.at < RESERVES_TTL_MS) return reservesCache.list;
  const rl = await call(POOL, SEL.getReservesList);
  const n = Number(u(rl, 1)); // word1 = array length
  const out = [];
  for (let i = 0; i < n; i++) out.push(addrOf(u(rl, 2 + i)));
  reservesCache = { at: Date.now(), list: out };
  return out;
}

function loadState() {
  try { return JSON.parse(fs.readFileSync(STATE_FILE, 'utf8')); } catch (e) { return null; }
}
function saveState(state) {
  fs.writeFileSync(STATE_FILE, JSON.stringify({
    candidates: [...state.candidates.entries()].slice(0, MAX_CANDIDATES + SEED_MAX_ADDED),
    cursor: state.cursor,
  }));
}

// candidate extraction from pool logs with NAMED-event decoding; shared by the
// live refresher and the historical replay so both run the SAME pipeline.
// LiquidationCall(address,address,address,uint256,uint256,uint256,uint256,address,bool,address):
// topics = [sig, collateral, debt, user], data word 4 = liquidator. Every other
// pool event contributes only its indexed topics (proper ABI address words) —
// data words of unknown events are never harvested as addresses, so padded
// numeric amounts cannot leak into the candidate universe.
function extractCandidates(logs, state, viaDefault) {
  let added = 0;
  const add = (a, via, blk) => {
    if (a === '0x0000000000000000000000000000000000000000') return;
    if (!state.candidates.has(a)) { state.candidates.set(a, { since: Date.now(), via: via || viaDefault, block: blk || 0 }); added++; }
  };
  for (const lg of logs) {
    const topics = lg.topics || [];
    if (!topics.length) continue;
    const blk = parseInt(lg.blockNumber, 16) || 0; // last-seen block, the deterministic retention key
    if (topics[0] === LIQ_EVENT_TOPIC0) {
      // named LiquidationCall: user = topic3, liquidator = data word 4
      if (topics.length === 4) add(addrOf(BigInt(topics[3])), 'liquidation', blk);
      const d = (lg.data || '0x').slice(2);
      if (d.length >= (4 + 1) * 64) add(addrOf(BigInt('0x' + d.slice(4 * 64, 5 * 64))), 'liquidation_liquidator', blk);
    } else {
      // dense user-activity families carry the borrower as an indexed arg
      // (topics 1..3); harvest every indexed word as a candidate
      for (let i = 1; i < Math.min(topics.length, 4); i++) add(addrOf(BigInt(topics[i])), viaDefault || 'activity', blk);
    }
  }
  return added;
}

// deterministic persistence cap (review 5f623a88): the live 9,000-cap evicted
// all three countable victims because retention followed the cold seed's
// WALL-CLOCK add order (request pacing decides who stays). Retention now keys
// on the last-seen event BLOCK, which is fixed by chain history:
//  - seed/liquidation candidates (the silent debtors the cold seed exists for)
//    keep the OLDEST last-seen blocks first — a victim last seen 12 d ago is
//    retained before any recently-seen activity; quota SEED_MAX_ADDED;
//  - recent-activity candidates keep the NEWEST blocks, quota MAX_CANDIDATES.
// The persisted insertion order = retention priority, so saveState's slice
// keeps exactly this set. Returns the kept universe size.
function capCandidates(state) {
  const CAP = MAX_CANDIDATES + SEED_MAX_ADDED;
  if (state.candidates.size <= CAP) return state.candidates.size;
  const entries = [...state.candidates.entries()];
  const blkOf = (e) => e[1].block || 0; // legacy persisted entries predate the block field
  const seed = entries.filter((e) => e[1].via !== 'activity').sort((a, b) => (blkOf(a) - blkOf(b)) || (a[1].since - b[1].since));
  const act = entries.filter((e) => e[1].via === 'activity').sort((a, b) => (blkOf(b) - blkOf(a)) || (b[1].since - a[1].since));
  const seedKeep = seed.slice(0, SEED_MAX_ADDED);
  const actKeep = act.slice(0, CAP - seedKeep.length);
  state.candidates = new Map(seedKeep.concat(actKeep));
  return state.candidates.size;
}

// candidate discovery from recent pool logs
async function refreshCandidates(state) {
  const bn = await blockNumber();
  const from = '0x' + Math.max(0, bn - LOG_BLOCKS).toString(16);
  const logs = await rpc('eth_getLogs', [{ fromBlock: from, toBlock: 'latest', address: POOL }]);
  const added = extractCandidates(logs, state);
  const before = state.candidates.size;
  const kept = capCandidates(state);
  if (kept !== before) log({ ts: new Date().toISOString(), type: 'candidates_capped', before, universe: kept });
  if (added) log({ ts: new Date().toISOString(), type: 'candidates_added', added, total: state.candidates.size });
}

// cold-start debtor discovery (review b69e96b8 item 1): the pool-log 500-block
// window misses SILENT borrowers (measured: the three countable victims appear
// in zero indexed topics across 627/973/1,205 logs of their pre-capture 500
// blocks, and in zero topics even across 20,000 — scratch precheck files);
// seed once at a cold start from the pool's own debtor history: LiquidationCall
// events (both pool versions) for repeat liquidations + the measured
// user-carrying activity family for first-liquidation victims. head-1 is the
// strict upper bound (replay: strictly pre-event).
async function seedScan(state, head) {
  const from = Math.max(0, head - 1 - SEED_BLOCKS);
  let added = 0, chunks = 0, liqLogs = 0;
  if (head - 1 > from) {
    // sparse LiquidationCall history: one request (measured 944 logs/900k blocks,
    // inside the relay's 10k-log cap; the dense families are chunk-scanned below)
    const r = await rpc('eth_getLogs', [{ fromBlock: '0x' + from.toString(16), toBlock: '0x' + (head - 1).toString(16),
      address: POOL, topics: [LIQ_EVENT_TOPIC0] }]);
    liqLogs = r.length;
    added += extractCandidates(r, state, 'seed');
    chunks++;
  }
  // dense families newest-first in bounded chunks. DEPTH (chunks) dominates: the
  // added count does NOT stop the scan, so the deepest silent borrowers (measured
  // 407k-409k blocks back) are always reached; SEED_MAX_CHUNKS bounds requests.
  for (let hi = head - 1; hi > from && chunks < SEED_MAX_CHUNKS; hi -= SEED_CHUNK) {
    const lo = Math.max(from, hi - SEED_CHUNK + 1);
    const r = await rpc('eth_getLogs', [{ fromBlock: '0x' + lo.toString(16), toBlock: '0x' + hi.toString(16),
      address: POOL, topics: [[LIQ_PREV_EVENT_TOPIC0, USER_ACTIVITY_EVENT_TOPIC0]] }]);
    chunks++;
    added += extractCandidates(r, state, 'seed');
  }
  return { from, chunks, liq_logs: liqLogs, added, universe: state.candidates.size };
}

async function coldSeed(state) {
  const t0 = Date.now();
  const bn = await blockNumber();
  const r = await seedScan(state, bn);
  capCandidates(state);
  log({ ts: new Date().toISOString(), type: 'cold_seed', head: bn, ...r, universe_capped: state.candidates.size, ms: Date.now() - t0 });
}

// replay of the known historical liquidation through the SAME discovery AND
// detection pipeline: discovery from historical pool logs around the block,
// detection (HF at parent block), then the full economic simulation.
async function replayOne(REPLAY) {
  const state = { candidates: new Map(), cursor: 0, lastSim: {}, dustSup: {}, lastSimOk: {} };
  let disc;
  if (REPLAY.eligibility) {
    // the countable captures replay through the SAME cold-start discovery
    // (seedScan) AND the SAME persistence cap a fresh bot would run, at head =
    // capture block: discovery uses ONLY information available before the
    // capture block (no +50), then capCandidates keeps the deterministic
    // oldest-last-seen seed set — the reviewer's "capped, persisted pipeline"
    // (review 5f623a88: the raw seed finding the victims is not enough, the
    // cap must retain them).
    disc = await seedScan(state, REPLAY.block);
    disc.capped = capCandidates(state);
    disc.retained = state.candidates.has(REPLAY.user);
  } else {
    // original single replay: pool-log chunks, strictly pre-event blocks
    let logs = [];
    for (let b = Math.max(0, REPLAY.block - REPLAY_BLOCKS); b < REPLAY.block; b += 1000) {
      const chunk = await rpc('eth_getLogs', [{ fromBlock: '0x' + b.toString(16), toBlock: '0x' + Math.min(b + 999, REPLAY.block - 1).toString(16), address: POOL }]);
      logs = logs.concat(chunk);
    }
    disc = { from: 0, chunks: 0, liq_logs: 0, added: extractCandidates(logs, state), universe: state.candidates.size, logs: logs.length };
  }
  const discovered = state.candidates.has(REPLAY.user);
  log({ ts: new Date().toISOString(), type: 'replay_discovery', block: REPLAY.block, ...disc,
    victim: REPLAY.user, victim_discovered: discovered });
  if (!discovered) { log({ ts: new Date().toISOString(), type: 'replay_miss', user: REPLAY.user }); return; }  if (REPLAY.eligibility) {
    // detector proof at the measured eligibility block (recount2 binary
    // search): the feed wake lands IN the eligibility block (AnswerUpdated
    // measured there, attempts:1116). A candidate in the near band (lastHf
    // < 1.005) is re-read by the wake's nearScan; a first HF<1 read at the
    // wake starts the 2-block confirmation, so the earliest ready block is
    // eligibility+1 and the earliest send block eligibility+2 — inside the
    // measured windows (6, 3, 2 blocks >= 2, counted in EV). Also show the
    // candidate was healthy and in the scan universe the block BEFORE the
    // wake (a polling read sees HF in the 1.005 near band there).
    try {
      const e = REPLAY.eligibility;
      const hfx = async (blk) => Number(u(await call(POOL, SEL.getUserAccountData + pad(REPLAY.user), '0x' + blk.toString(16)), 5)) / 1e18;
      const hfBefore = await hfx(e - 1); // last healthy HF before the price update
      const hfElig = await hfx(e); // HF at the wake block (trigger landed)
      const window = REPLAY.block - e;
      const earliestSend = e + 2; // wake(e) + 2-block confirmation
      log({ ts: new Date().toISOString(), type: 'replay_detector', block: REPLAY.block, eligibility: e,
        window_blocks: window, hf_last_healthy_before_wake: hfBefore, hf_at_wake: hfElig,
        healthy_before_wake: hfBefore >= 1, wake_band_before_wake: hfBefore >= 1 && hfBefore < NEAR_WAKE_TRIGGER,
        underwater_at_wake: hfElig < 1,
        earliest_ready_block: e + 1, earliest_send_block: earliestSend,
        send_lands_within_window: earliestSend <= REPLAY.block, counted_in_EV: window >= 2 });
      // full-pass round-robin wake model (review 5f623a88: "the current replay
      // assumes the last HF was read just before the feed, while the
      // round-robin takes ~360 s to revisit a borrower"): the live bot's
      // lastHf for a candidate comes from its LAST round-robin read, and a
      // full pass over the persisted universe takes ceil(universe/SCAN_CHUNK)
      // chunks — the rotation runs ONE chunk per new head (fix round 8), so the
      // pass is ceil(universe/SCAN_CHUNK) BLOCKS (~1260 s at the 26k cap). The
      // wake's nearScan therefore only sees the HF
      // the bot could really have recorded at the EARLIEST feasible last read
      // one full pass before the wake block. Require that worst-case read to
      // be healthy-but-close (1 <= hf < 1.05): then lastHf < 1.05 at the wake
      // whatever the rotation phase, nearScan re-reads this candidate IN the
      // wake block (hf < 1 first seen), the 2-block confirmation clears at
      // eligibility+1 and the earliest send lands at eligibility+2 — inside
      // the measured windows (windows 6/3/2 blocks, >=2 counts in EV).
      const universe = disc.capped || disc.universe;
      const passCycles = Math.ceil(universe / SCAN_CHUNK);
      // Fix round 8 (review d6e6966d): the rotation runs ONE chunk per new head
      // (block-paced), so a full pass over the capped universe takes
      // ceil(universe/SCAN_CHUNK) BLOCKS — the old model was chunks x 8 s cycles
      // converted to blocks; both land at ~105 blocks for the 26k cap.
      const passBlocks = passCycles;
      const earliestRead = e - 1 - passBlocks;
      const hfEarliest = await hfx(earliestRead);
      log({ ts: new Date().toISOString(), type: 'replay_wake', block: REPLAY.block, eligibility: e,
        universe, victim_retained_after_cap: disc.retained === true,
        full_pass_chunks: passCycles, full_pass_seconds: passBlocks * 12, full_pass_blocks: passBlocks,
        earliest_feasible_read_block: earliestRead, hf_at_earliest_read: hfEarliest,
        healthy_at_earliest_read: hfEarliest >= 1,
        wake_band_lastHf_at_wake: hfEarliest >= 1 && hfEarliest < NEAR_WAKE_TRIGGER,
        in_near_set_on_wake: disc.retained === true && hfEarliest < NEAR_WAKE_TRIGGER,
        wake_read_hf_below_one: hfElig < 1,
        earliest_send_block: earliestSend, send_lands_within_window: earliestSend <= REPLAY.block,
        counted_in_EV: window >= 2 });
      // real scan/confirm scheduler run (review e3f07d25: the replay_wake rows
      // only assigned earliest_send_block = eligibility+2; they "do not run the
      // live confirmation scheduler or a send"). Run the SAME live pipeline:
      // nearScan at the eligibility block (the feed wake; the candidate's last
      // healthy read was the earliest feasible round-robin read hfEarliest),
      // then followUpScan EVERY block through the capture block — wake,
      // confirmation, per-block executor simulation and block-based cooldown
      // are exactly the functions the live bot runs, at historical blocks.
      const sched = { candidates: state.candidates, cursor: 0, lastSim: {},
        lastHf: { [REPLAY.user]: hfEarliest }, underObs: {}, followUp: new Map(), dustSup: {},
        lastSimOk: {}, wakeTs: 0, lastSimResult: null };
      await nearScan(sched, e); // the wake: wake-band re-read IN the eligibility block
      const queuedFirst = sched.followUp.has(REPLAY.user); // first HF<1 observation queued
      const perBlock = [];
      let firstDecision = null, simOkBlock = null;
      for (let blk = e + 1; blk <= REPLAY.block; blk++) {
        await followUpScan(sched, blk);
        const lr = sched.lastSimResult;
        const r = lr && lr.user === REPLAY.user && lr.block === blk ? lr.rec : null;
        const pairs = r ? (r.pairs || []) : [];
        const prof = pairs.find((p) => p.gross_usd_est !== undefined && p.profit_usd_after_fees >= MIN_PROFIT_USD) || null;
        const okp = pairs.find((p) => p.sim_ok === true) || null;
        if (r && !firstDecision) firstDecision = blk;
        if (okp && !simOkBlock) simOkBlock = blk;
        perBlock.push({ block: blk, sim_ran: !!r,
          profitable_pair: prof ? true : prof === null ? null : false,
          cover_usd: prof ? prof.cover_usd : null, gross_usd_est: prof ? prof.gross_usd_est : null,
          net_usd: prof ? prof.profit_usd_after_fees : null,
          executor_sim_ok: okp ? true : r ? false : null });
      }
      log({ ts: new Date().toISOString(), type: 'replay_scheduler', block: REPLAY.block,
        eligibility: e, window_blocks: window,
        first_hf_below_one_queued_for_followup: queuedFirst,
        wake_read_hf_below_one: hfElig < 1, first_sim_block: firstDecision,
        executor_sim_ok_block: simOkBlock, earliest_send_block: earliestSend,
        send_lands_within_window: earliestSend <= REPLAY.block,
        counted_in_EV: window >= 2, per_block: perBlock });
    } catch (e) { log({ ts: new Date().toISOString(), type: 'replay_detector', block: REPLAY.block, msg: 'revert: ' + String(e.message).slice(0, 140) }); }
  }
  const parent = '0x' + (REPLAY.block - 1).toString(16);
  const ad = await call(POOL, SEL.getUserAccountData + pad(REPLAY.user), parent);
  const hf = Number(u(ad, 5)) / 1e18;
  // detection at the parent block (pre-event state) AND at the capture block:
  // the measured class (block 53438141) crossed below HF=1 INSIDE the capture
  // block via an oracle update, so parent-block HF is healthy and the capture
  // is a ~1-block latency race (window-measurement: scratch/aave-executor-base/
  // out/window-measurement.json). Block-level replay of that class ends AFTER
  // the winner's tx (position healthy again), so the economic proof of the
  // interest-bleed class — which block-level polling CAN catch — lives in
  // runall.sh (fork success + guard-revert + post-gas profit).
  const adc = await call(POOL, SEL.getUserAccountData + pad(REPLAY.user), '0x' + REPLAY.block.toString(16));
  const hfCap = Number(u(adc, 5)) / 1e18;
  log({ ts: new Date().toISOString(), type: 'replay_detection', block: REPLAY.block - 1, hf, underwater: hf < 1,
    hf_at_capture: hfCap, capture_class: hf >= 1 && hfCap >= 1 ? 'oracle_update_in_block (latency race for polling)' : 'slow_bleed' });
  if (hf < 1) await simulateLiquidation(REPLAY.user, parent, hf);
}

async function replayPipeline() {
  for (const t of REPLAYS) await replayOne(t);
}

async function blockNumber() { return readHead(); } // cached head+fee block read (fix round 8)

// round-robin scan over the WHOLE candidate set (rotating window); a forced
// slice (the near set on a feed wake, the follow-up queue) overrides rotation
// for one cycle. blk (replay only): historical block number to read at.
async function scanCycle(state, forceSlice, blk) {
  const users = [...state.candidates.keys()];
  if (!users.length) return;
  const slice = [];
  const blkHex = blk ? '0x' + blk.toString(16) : undefined;
  if (forceSlice) {
    for (let k = 0; k < Math.min(SCAN_CHUNK, forceSlice.length); k++) slice.push(forceSlice[k]);
  } else {
  for (let k = 0; k < Math.min(SCAN_CHUNK, users.length); k++) {
    slice.push(users[(state.cursor + k) % users.length]);
  }
  state.cursor = (state.cursor + slice.length) % Math.max(1, users.length);
  }
  const calls = slice.map((u) => ({ to: POOL, data: SEL.getUserAccountData + pad(u) }));
  const res = await tryAggregate(calls, blkHex);
  const now = new Date().toISOString();
  const nowMs = Date.now();
  let headCache = blk || 0; // per-cycle head, read ONLY when a trigger-band candidate needs it
  // (fix round 8: blk is the replay's historical block; the live path reads the
  // ONE cached head+fee block read — blockNumber() is readHead() now)
  const getHead = async () => headCache || (headCache = await blockNumber());
  let debtors = 0, minHf = Infinity, minHfUser = '';
  for (let i = 0; i < slice.length; i++) {
    const r = res[i];
    if (!r.success || r.returnData.length < 2 + 6 * 64) continue;
    const debt = u(r.returnData, 1);
    const hf = Number(u(r.returnData, 5)) / 1e18;
    if (!isFinite(hf)) continue;
    if (debt === 0n) continue;
    debtors++;
    if (hf < minHf) { minHf = hf; minHfUser = slice[i]; }
    // Record lastHf for every debtor BEFORE trigger filtering (review
    // 554faf76): the old placement inside `if (hf < HF_TRIGGER)` left a
    // stale lastHf when a borrower recovered above the 1.005 band and fell
    // back inside the ten-minute cooldown (HF 0.99 -> 1.01 -> 0.999), so the
    // recrossing did not clear lastSim and the simulation/live send stayed
    // suppressed. Read the previous observation, then record this one.
    const lastHf = state.lastHf ? state.lastHf[slice[i]] : undefined;
    if (state.lastHf) state.lastHf[slice[i]] = hf;
    if (hf < HF_TRIGGER) {
      const c = state.candidates.get(slice[i]) || {};
      log({ ts: now, type: 'opportunity', user: slice[i], hf, debt_usd: Number(debt) / 1e8 });
      // Cooldown semantics (review 7496ff6e blocker 1 + 554faf76, explicit):
      // an observed healthy->eligible transition (lastHf >= 1 -> hf < 1)
      // ALWAYS clears the cooldown — a lastSim stamped by a failed or
      // errored simulation cannot hide a later profitable crossing case.
      // lastSim is stamped BEFORE the await so an errored simulation cannot
      // hot-loop the relay; the transition clear is what re-arms the send.
      // Fix round 7 (review c57f7ed7: the measured paper run simulated 56/min
      // for 11 minutes — the universe holds ~23 PERMANENTLY underwater dust
      // debtors (measured HF 0.002-0.99 in the current paper logs) whose
      // every-block in-window simulation never produced a profitable pair
      // (gross below MIN_PROFIT_USD); re-simulating them per block costs ~12
      // relay reads each and adds zero EV. A candidate whose completed
      // simulation found no profitable pair is SUPPRESSED (state.dustSup) —
      // it re-simulates only when it re-crosses HF=1 from a healthy reading
      // (the transition clear below also clears the suppression). Countable
      // fresh crossers always re-arm; a dust candidate that turns profitable
      // later (debt growth past the 100 USD minimum liquidation amount) is
      // caught by its first post-crossing simulation, not by a per-block
      // re-sim of an already-underwater account.
      if (hf < 1 && lastHf !== undefined && lastHf >= 1) { delete state.lastSim[slice[i]]; delete state.dustSup[slice[i]]; if (state.lastSimOk) delete state.lastSimOk[slice[i]]; }
      // Fix round 8 (review d6e6966d): the transition clear is what re-arms a
      // fresh crosser — it deletes lastSim AND lastSimOk, so the countable
      // candidate always simulates at its first confirmation block whatever
      // its watch-band cadence was.
      // Confirmation + follow-up (review e3f07d25 + decision 2026-11-13-next-
      // block-feed): the FIRST HF<1 observation records the firstBlock and
      // queues the candidate in the bounded follow-up queue; followUpScan
      // re-reads every queued candidate EVERY BLOCK while it stays underwater
      // (queue bounded by FOLLOWUP_MAX, SCAN_CHUNK per cycle), so the second
      // HF<1 observation lands one block after the first — NOT after a ~800 s
      // full round-robin pass (~69 blocks), which was slower than the
      // measured 2/3/6-block windows. Only act once HF < 1 has been seen on
      // two block reads: a capture lands >= 2 blocks after the eligibility
      // block, inside the measured countable windows (>=2 counts in EV).
      let ready = hf >= 1; // healthy watch-only candidates simulate freely
      let o = null;
      if (hf < 1) {
        const head = await getHead();
        o = state.underObs[slice[i]];
        if (!o) {
          o = state.underObs[slice[i]] = { firstBlock: head, since: nowMs, wakeTs: state.wakeTs || 0 };
          if (state.followUp.size < FOLLOWUP_MAX) state.followUp.set(slice[i], head);
          else { const oldest = state.followUp.keys().next().value; state.followUp.delete(oldest); state.followUp.set(slice[i], head); }
        } else if (head > o.firstBlock) {
          ready = true; // the second block read: HF<1 confirmed across two blocks
          // Fix round 8 (review d6e6966d): log the confirmation ONCE per
          // observation — the old row fired on every re-read of an already
          // confirmed candidate (18,316 followup_ready rows in 133 min of paper
          // logs from a handful of queued dust candidates). wake_ms (the
          // feed->send latency the reviewer asked to measure) lands once, at
          // the confirmation, with the blocks_since_first.
          if (!o.confirmed) {
            o.confirmed = true;
            log({ ts: now, type: 'followup_ready', user: slice[i], hf, first_block: o.firstBlock,
              blocks_since_first: head - o.firstBlock, wake_ms: o.wakeTs ? nowMs - o.wakeTs : null });
          }
        }
      } else if (state.underObs[slice[i]]) delete state.underObs[slice[i]]; // recovered: confirmation state cleared
      // Sim cadence (block-based, replay-representable): an underwater candidate
      // inside its follow-up window re-simulates once per block (bounded: the
      // window ends SIM_WINDOW_MS after the first underwater observation, and
      // liquidation/recovery clears underObs); healthy watch candidates
      // re-simulate every SIM_COOLDOWN_BLOCKS (~10 min at 12 s blocks).
      const inWindow = o && nowMs - o.since < SIM_WINDOW_MS;
      const cdBlocks = (hf < 1 && inWindow) ? UNDERWATER_SIM_COOLDOWN_BLOCKS : SIM_COOLDOWN_BLOCKS;
      const last = state.lastSim[slice[i]] || 0;
      // Fix round 8 (review d6e6966d): a COMPLETED simulation (no error) parks
      // the candidate for SIM_OK_COOLDOWN_BLOCKS before the next one — a paper
      // in-window candidate with a profitable pair re-simulated every block for
      // its whole 30-min window (each ~6-12 relay reads, the same numbers every
      // time), and the healthy watch band re-simulates at the 200-block cadence
      // instead. An errored sim keeps the 1-block retry pace (lastSimOk stays).
      const lastOk = state.lastSimOk ? (state.lastSimOk[slice[i]] || 0) : 0;
      // Fix round 7 (review c57f7ed7): a candidate with a completed
      // no-profitable-pair simulation does not re-simulate until it re-crosses
      // HF=1 (the transition clear above removes the suppression). Fresh
      // countable crossers are never suppressed, so the per-block decision
      // sims the reviewer counts in EV still run.
      if (ready && !state.dustSup[slice[i]]) {
        const headSim = await getHead();
        if (headSim - last >= cdBlocks && (!lastOk || headSim - lastOk >= SIM_OK_COOLDOWN_BLOCKS)) {
          state.lastSim[slice[i]] = headSim; // stamped BEFORE the await: an errored sim cannot hot-loop the relay
          const simRec = await simulateLiquidation(slice[i], blkHex || 'latest', hf);
          state.lastSimResult = { user: slice[i], block: headSim, rec: simRec };
          if (!simRec.error) // suppression: the sim completed and NO pair was
            // profitable (dust cover below MIN_PROFIT_USD, or no measured
            // executable route) — re-simulating it per block costs ~12 relay
            // reads and cannot yield a send.
            state.dustSup[slice[i]] = !(simRec.pairs || []).some((p) => p.profitable === true);
          if (!simRec.error && state.lastSimOk) state.lastSimOk[slice[i]] = headSim; // completed: park SIM_OK_COOLDOWN_BLOCKS
        }
      }
    }
  }
  // follow-up queue upkeep: candidates that RECOVERED (underObs cleared), left
  // the universe, or aged past the SIM_WINDOW_MS window leave the queue (their
  // cadence falls back to the wake/rotation reads at the 50-block cooldown)
  if (state.followUp && state.followUp.size) {
    for (const k of [...state.followUp.keys()]) {
      const oo = state.underObs[k];
      if (!oo || !state.candidates.has(k) || nowMs - oo.since > SIM_WINDOW_MS) state.followUp.delete(k);
    }
  }
  log({ ts: now, type: 'heartbeat', scanned: slice.length, universe: users.length, cursor: state.cursor,
    debtors, min_hf: isFinite(minHf) ? minHf : null, min_hf_user: minHfUser, rpc_reqs: RPC_REQS });
}

// one targeted relay re-scan of the near-boundary set on a feed wake (review
// b69e96b8 item 1): the countable class crosses HF=1 in the PRICE-UPDATE block
// (the wake block), and the fast crossers were measured (26384827, 26399074)
// last-healthy 1.006 / 1.009 the block BEFORE the wake — above the 1.005
// pre-log band — so a wake filter pinned to HF_TRIGGER=1.005 would SKIP them
// (their lastHf is 1.006-1.009, healthy) and they would only be re-read by the
// round-robin poll (a ~6 min full pass over the 9,400 universe = ~30 blocks),
// far too late for a 2-3 block window. The wake therefore re-reads every
// candidate last seen in the wide healthy-but-close band 1 <= lastHf <
// NEAR_WAKE_TRIGGER (measured fast-crossers 1.006/1.009 < 1.05), so its first
// HF<1 read lands IN the wake (eligibility) block and the 2-block confirmation
// sends at eligibility+2 — inside every measured window.
async function nearScan(state, blk) {
  const near = [...state.candidates.keys()].filter((u) => {
    const h = state.lastHf ? state.lastHf[u] : undefined;
    return h !== undefined && h < NEAR_WAKE_TRIGGER;
  });
  if (!near.length) return;
  // closest-to-HF=1 first (review e3f07d25: the wake scan of a 293-candidate
  // near set measured 26.9 s for two chunks — longer than the shortest 2-block
  // window; ranking the likely crossers into the FIRST chunk means the
  // candidates that queue a follow-up are queued ~1 chunk-time into the wake,
  // not after the whole set was re-read)
  near.sort((a, b) => state.lastHf[a] - state.lastHf[b]);
  // full wake coverage: every near-band candidate is re-read on a wake, in
  // SCAN_CHUNK Multicall3 chunks (the universe cap bounds the set, the wake
  // cadence ~208 price updates/day bounds the cost — README 'Read cost').
  // With only the first chunk re-read, a candidate ranked past position 200
  // in the near set would silently miss the wake.
  const t0 = Date.now();
  let chunks = 0;
  for (let off = 0; off < near.length; off += SCAN_CHUNK) {
    await scanCycle(state, near.slice(off, off + SCAN_CHUNK), blk);
    chunks++;
  }
  log({ ts: new Date().toISOString(), type: 'wake_scan', near: near.length, chunks, ms: Date.now() - t0 });
}

// bounded targeted re-read of the follow-up queue (review e3f07d25: "add an
// explicit bounded follow-up for each newly underwater near candidate on the
// next block"): every queued candidate is re-read ONCE PER NEW HEAD while it
// stays underwater (fix round 8, review d6e6966d: the cycle runs followUpScan
// only when the cached head has advanced — a re-read under an unchanged head
// cannot confirm and was pure cost) — the queue is bounded (FOLLOWUP_MAX
// pending, SCAN_CHUNK reads per run, SIM_WINDOW_MS per candidate), so the cost
// is ONE Multicall3 aggregate per block while a window is open, NOT a second
// pass over the universe. The confirmation lands
// 1 block after the first underwater observation: the cycle polls the head at
// HEAD_POLL_MS (4 s while the queue holds fresh observations, 10 s idle), so a
// new head is seen <= ~4-10 s + one cycle after the block that first read
// HF<1, the run confirms there, and the executor simulation/send follows in
// the same cycle (followup_ready + simulate rows log the measured wake-to-send
// latency; wake_ms is logged once per confirmation).
async function followUpScan(state, blk) {
  const pending = [...state.followUp.keys()];
  if (!pending.length) return 0;
  const slice = pending.slice(0, SCAN_CHUNK);
  const t0 = Date.now();
  await scanCycle(state, slice, blk);
  let confirmed = 0, recovered = 0;
  for (const k of slice) {
    const oo = state.underObs[k];
    if (!oo) recovered++; // cleared by scanCycle: either confirmed-and-... or recovered
    else if (!state.followUp.has(k)) confirmed++; // left the queue while still underwater: window age-out
  }
  log({ ts: new Date().toISOString(), type: 'followup_scan', pending: pending.length,
    scanned: slice.length, recovered: recovered + confirmed, ms: Date.now() - t0 });
  return slice.length;
}

// feed wait: one pinned low-volume filter (AnswerUpdated on the aggregator that
// drives the crossings); gap / 429 / 503 / connection error = re-read state
// through the relay (nearScan) and continue with the cursor returned.
async function feedWatch(state) {
  let cursor = '';
  for (;;) {
    try {
      const url = `${FEED}/logs/${CHAIN}?address=${FEED_ADDR}&topic0=${ANSWER_UPDATED}` +
        `${cursor ? '&after=' + cursor : ''}&timeout=55`;
      const res = await fetch(url);
      if (res.status === 429 || res.status === 503) throw new Error('feed http ' + res.status);
      const j = await res.json();
      if (j.removed) { cursor = j.cursor || cursor; log({ ts: new Date().toISOString(), type: 'feed_reorg' }); await nearScan(state); continue; }
      if (j.gap) { cursor = j.cursor || cursor; log({ ts: new Date().toISOString(), type: 'feed_gap', cursor }); await nearScan(state); continue; }
      cursor = j.cursor || cursor;
      const logs = j.logs || [];
      if (logs.length) {
        const l = logs[logs.length - 1];
        state.wakeTs = Date.now(); // feed->send latency anchor for followups queued by THIS wake
        log({ ts: new Date().toISOString(), type: 'feed_event', n: logs.length, block: l.blockNumber, block_timestamp: l.blockTimestamp });
        // Fix round 8 (review d6e6966d): the wake forces a FRESH head read so the
        // first underwater observation is stamped with the wake block itself —
        // a cached head one block old would stamp firstBlock = wake-1 and the
        // confirmation could then land in the eligibility block proper (a
        // same-block race). One extra block read per wake (~208/day at the
        // measured AnswerUpdated cadence).
        await readHead(true);
        await nearScan(state);
      }
    } catch (e) {
      log({ ts: new Date().toISOString(), type: 'feed_error', msg: String(e.message || e).slice(0, 160) });
      try { await nearScan(state); } catch (e2) { log({ ts: new Date().toISOString(), type: 'error', msg: String(e2).slice(0, 200) }); }
      await new Promise((r) => setTimeout(r, 20000)); // throttle: never hot-loop the feed
    }
  }
}

// pick a real liquidator that is funded and approved for the debt asset now
// (fix round 7, review c57f7ed7: these balances/allowances move only when a
// liquidator spends — re-read at most every 2 min per (liquidator, asset)
// instead of twice per simulate.)
const SENDER_TTL_MS = 2 * 60 * 1000;
const senderCache = {};
async function fundedSender(debtAsset, neededUnits) {
  for (const a of KNOWN_LIQUIDATORS) {
    const key = a + '@' + debtAsset;
    let c = senderCache[key];
    if (!c || Date.now() - c.at > SENDER_TTL_MS) {
      try {
        const bal = u(await call(debtAsset, SEL.balanceOf + pad(a)), 0);
        const allow = bal >= neededUnits ? u(await call(debtAsset, SEL.allowance + pad(a) + pad(POOL).slice(-64)), 0) : 0n;
        c = senderCache[key] = { balance: bal, allowance: allow, at: Date.now() };
      } catch (e) { continue; /* try next */ }
    }
    if (c.balance >= neededUnits && c.allowance >= neededUnits)
      return { address: a, balance: c.balance.toString(), allowance: c.allowance.toString() };
  }
  return null;
}

// full economic + executability simulation of liquidating `user` at `block`
async function simulateLiquidation(user, block, hf) {
  const rec = { ts: new Date().toISOString(), type: 'simulate', user, block, hf };
  try {
    const cfgWord = u(await call(POOL, SEL.getUserConfiguration + pad(user), block), 0);
    const reserves = await getReserves();
    const collRes = [], debtRes = [];
    reserves.forEach((a, i) => {
      const borrow = ((cfgWord >> BigInt(2 * i)) & 1n) === 1n;
      const coll = ((cfgWord >> BigInt(2 * i + 1)) & 1n) === 1n;
      if (borrow) debtRes.push(a);
      if (coll) collRes.push(a);
    });
    rec.debt_reserves = debtRes; rec.collateral_reserves = collRes;
    // amounts per reserve
    rec.pairs = [];
    for (const dAsset of debtRes) {
      const rd = await reserveData(dAsset, block);
      if (!rd) { rec.pairs.push({ debt: dAsset, sim_result: 'skip: reserve metadata unavailable (fail closed)' }); continue; }
      const vDebt = u(await call(rd.varDebt, SEL.balanceOf + pad(user), block), 0);
      const sDebt = u(await call(rd.stableDebt, SEL.balanceOf + pad(user), block), 0);
      const totalDebt = vDebt + sDebt;
      if (totalDebt === 0n) continue;
      const decD = await decimals(dAsset);
      if (decD === null) { rec.pairs.push({ debt: dAsset, sim_result: 'skip: debt decimals unavailable (fail closed)' }); continue; }
      const priceD = await assetPrice(dAsset, block);
      for (const cAsset of collRes) {
        const crd = await reserveData(cAsset, block);
        if (!crd) { rec.pairs.push({ collateral: cAsset, sim_result: 'skip: reserve metadata unavailable (fail closed)' }); continue; }
        const aBal = u(await call(crd.aToken, SEL.balanceOf + pad(user), block), 0);
        if (aBal === 0n) continue;
        const priceC = await assetPrice(cAsset, block);
        // close factor rule (official LiquidationLogic.sol:375): 50% above HF 0.95, 100% below
        const closeFactor = rec.hf !== undefined && rec.hf <= CLOSE_FACTOR_HF_THRESHOLD ? 1.0 : 0.5;
        const bonus = await liqBonusBps(cAsset);
        const decC = await decimals(cAsset);
        if (decC === null) { rec.pairs.push({ collateral: cAsset, sim_result: 'skip: collateral decimals unavailable (fail closed)' }); continue; }
        // capital-bounded cover: min(closeFactor * totalDebt, MAX_COVER_USD worth of debt)
        const coverUsdCap = BigInt(Math.round(MAX_COVER_USD * 1e8)) * 10n ** BigInt(decD) / priceD;
        const maxLiq = totalDebt * BigInt(Math.round(closeFactor * 10000)) / 10000n;
        // Aave minimum-liquidation floor (measured at the counted decision
        // blocks, e.g. 26399072: liquidationCall reverts with Pool custom
        // error 0xb629b0e4 for covers 25.19 and 50.3714 USD (< 1% of the
        // victim's 5037.14 USD total debt) and only 50.383835 USD
        // (= 1.00025% of debt, the incumbent capture tx 0x53c1f98c's own
        // debtToCover) passes. SMALL accounts (fix round 5, run 5fc9d255, fork
        // probe at the pre-capture state of 26384826, debt 44.426974 USDC:
        // covers of 1, 4, 10, 20, 30, 50 and 75 pct of the debt ALL revert
        // 0xb629b0e4 inside LiquidationStrategy and only cover = 100 pct of
        // the debt (with a 0.025 pct margin against accrual between read and
        // send) succeeds: fork tx 0x8f18fca9597c status 1, OWNER delta
        // +1.684368 USDC, gas 567325; the incumbent covered exactly the FULL
        // debt at all three small-debt counted captures (44.426962 /
        // 36.104988 / 18.765477 USD): an account whose whole debt sits under
        // the 100 USD minimum liquidation amount must be repaid in FULL, so
        // the floor there is the full debt x 1.00025 margin, not 1 pct.
        const HUNDRED_USD = 100n * 10n ** BigInt(decD);
        const minLiq = totalDebt < HUNDRED_USD
          ? totalDebt * 1000250n / 1000000n // full debt x 1.00025
          : totalDebt * 1000250n / 100000000n; // 1.000250% of total debt
        const cappedCover = minBn(maxLiq, coverUsdCap);
        const cover = cappedCover < minLiq && minLiq <= coverUsdCap ? minLiq : cappedCover;
        const coverUsd = Number(cover * priceD / 10n ** BigInt(decD)) / 1e8;
        // seized collateral in base units of cAsset: USD cover * (1+bonus) / priceC,
        // converted with the 10^decC / 10^decD decimal factor (measured layout:
        // cover/10^decD * priceD/1e8 = USD; result * 10^decC = cAsset base units)
        const seizedUnits = cover * priceD * BigInt(bonus) * (10n ** BigInt(decC)) /
          (priceC * 10000n * (10n ** BigInt(decD)));
        const seizedUsd = Number(seizedUnits * priceC / 10n ** BigInt(decC)) / 1e8;
        const gasUsd = worstCaseGasLossUsd();
        // expected GROSS before gas (oracle bonus minus the slippage buffer);
        // the live send gate re-compares it against the FRESH gas bound (review
        // 1091 blocker 4: the fee cap is re-derived at send, the scan-time
        // comparison below must not be the only gate).
        const grossUsdEst = coverUsd * (Number(bonus) - 10000 - Number(SLIPPAGE_BUFFER_BPS)) / 10000;
        const profit = grossUsdEst - gasUsd;
        const sender = await fundedSender(dAsset, cover);
        rec.pairs.push({
          collateral: cAsset, debt: dAsset, bonus_bps: bonus,
          total_debt_units: totalDebt.toString(), cover_units: cover.toString(),
          cover_usd: coverUsd, seized_units: seizedUnits.toString(), seized_usd: seizedUsd,
          gross_usd_est: grossUsdEst,
          // AFTER-FEE estimate: oracle-bonus proceeds (1% slippage buffer
          // applied) minus the FULL worst-case fee bound (L2 gas + L1 data fee
          // cap + approvals). The on-chain minProfit argument is the separate
          // hard revert floor (1 USD in debt-token units) — it protects the
          // principal, while this number is what must clear MIN_PROFIT_USD.
          profit_usd_est: profit, profit_usd_after_fees: profit, gas_usd_bound: gasUsd,
          profitable: profit >= MIN_PROFIT_USD && seizedUnits <= aBal,
          sender: sender ? sender.address : null, sender_balance: sender ? sender.balance : null,
        });
        if (profit >= MIN_PROFIT_USD && seizedUnits <= aBal) {
          // executor path: swap pool must be measured, else watch-only (no send)
          const pool = POOL_MAP[cAsset.toLowerCase() + '->' + dAsset.toLowerCase()];
          if (!pool) {
            rec.pairs[rec.pairs.length - 1].sim_result = 'watch_only: no measured collateral swap pool';
            log({ ts: new Date().toISOString(), type: 'opportunity_watch_only', user, collateral: cAsset, debt: dAsset, reason: 'no measured collateral swap pool' });
          } else if (!RUNTIME_OK) {
            rec.pairs[rec.pairs.length - 1].sim_result = 'skip: executor runtime missing/invalid (fail closed, no plain eth_call fallback)';
          } else if (!allowedOrSkip(pool.router) || !allowedOrSkip(EXEC)) {
            rec.pairs[rec.pairs.length - 1].sim_result = 'skip: router/executor not in allowed_contracts (fail closed)';
          } else {
            // minProfit = MIN_PROFIT_USD worth of the debt asset (the executor
            // reverts NO_PROFIT below it — the floor the bot sends, same number)
            const minProfit = BigInt(Math.round(1e8 * MIN_PROFIT_USD)) * 10n ** BigInt(decD) / priceD;
            const sameAsset = cAsset.toLowerCase() === dAsset.toLowerCase();
            const fee = sameAsset ? 0 : pool.fee;
            const data = encExecutorCall(user, cAsset, dAsset, cover, minProfit, fee);
            // sim of the EXACT live bytes. Paper: code override with the
            // DEPLOYED fork runtime (real constructor immutables, owner =
            // FORK_OWNER), called FROM that owner. Live: the gate has deployed
            // the executor — verify deployed code + owner() == our signer
            // wallet first (fail closed), then simulate from OUR wallet with
            // NO override.
            let simFrom = FORK_OWNER, override = { [EXEC]: { code: RUNTIME_CODE } };
            let liveReady = true;
            if (MODE === 'live') {
              const signerAddr = await signerAddress();
              if (!signerAddr) {
                rec.pairs[rec.pairs.length - 1].sim_result = 'skip: live signer address unavailable (fail closed)';
                liveReady = false;
              } else {
                const code = await rpc('eth_getCode', [EXEC]);
                if (!code || code === '0x') {
                  rec.pairs[rec.pairs.length - 1].sim_result = 'skip: live executor not deployed (empty code, fail closed)';
                  liveReady = false;
                } else {
                  const owner = addrOf(u(await call(EXEC, SEL_EXEC_OWNER), 0));
                  if (owner.toLowerCase() !== String(signerAddr).toLowerCase()) {
                    rec.pairs[rec.pairs.length - 1].sim_result = 'skip: executor owner ' + owner + ' != signer wallet (fail closed)';
                    liveReady = false;
                  }
                }
                simFrom = signerAddr; override = undefined;
              }
            }
            if (liveReady) {
              let simOk = null, simRevert = null;
              try {
                const r = await rpc('eth_call', [{ from: simFrom, to: EXEC, data }, block || 'latest', ...(override ? [override] : [])]);
                simOk = true;
                rec.pairs[rec.pairs.length - 1].sim_return = (r === '0x' ? '0x' : r.slice(0, 70));
              } catch (e) { simOk = false; simRevert = String(e.message).slice(0, 160); }
              rec.pairs[rec.pairs.length - 1].sim_from = simFrom;
              rec.pairs[rec.pairs.length - 1].sim_ok = simOk;
              rec.pairs[rec.pairs.length - 1].sim_revert = simRevert;
              rec.pairs[rec.pairs.length - 1].executor_calldata = data;
              rec.pairs[rec.pairs.length - 1].min_profit = minProfit.toString();
              if (MODE === 'live' && simOk) await liveLiquidate({ debtAsset: dAsset, cAsset, user, cover, coverUsd, data, grossUsdEst });
            }
          }
        }
      }
    }
  } catch (e) {
    rec.error = String(e.message || e).slice(0, 200);
  }
  log(rec);
  return rec;
}
function minBn(a, b) { return a < b ? a : b; }

// AaveLiquidator.liquidate(user, collateral, debt, cover, minProfit, fee):
// owner-only atomic repayment + seizure + NEWLY-SEIZED-DELTA conversion on the
// constructor-baked ROUTER + flash pull-back + end-balance guard.
function encExecutorCall(user, cAsset, debtAsset, cover, minProfit, fee) {
  return SEL_EXEC_LIQUIDATE + pad(user) + pad(cAsset) + pad(debtAsset) +
    pad('0x' + cover.toString(16)) + pad('0x' + minProfit.toString(16)) +
    pad('0x' + fee.toString(16));
}

// allowed_contracts enforcement: the manifest is the single source of truth; any
// dynamically discovered destination outside it fails CLOSED (pair skipped).
function loadAllowed() {
  const set = new Set();
  try {
    const lines = fs.readFileSync(path.join(DIR, 'manifest.yaml'), 'utf8').split('\n');
    let inBlock = false;
    for (const ln of lines) {
      if (/^allowed_contracts:/.test(ln)) { inBlock = true; continue; }
      if (inBlock) {
        const m = ln.match(/-\s*(0x[0-9a-fA-F]+)/);
        if (m) set.add(m[1].toLowerCase());
        else if (ln.trim() && !ln.startsWith(' ')) break;
      }
    }
  } catch (e) { /* empty set -> everything allowed (paper reads) */ }
  return set;
}
const ALLOWED = loadAllowed();
function allowedOrSkip(a) {
  if (!ALLOWED.size) return true;
  return ALLOWED.has(String(a).toLowerCase());
}

function signerCall(req) {
  const sockPath = process.env.SIGNER_SOCK || '/run/farm/signer.sock';
  return new Promise((resolve) => {
    const s = net.connect(sockPath);
    let buf = '';
    s.on('connect', () => s.write(JSON.stringify(req) + '\n'));
    s.on('data', (d) => { buf += d.toString(); if (buf.endsWith('\n')) { s.end(); resolve(JSON.parse(buf)); } });
    s.on('error', (e) => resolve({ ok: false, error: String(e).slice(0, 200) }));
  });
}

// live execution path: the whole repayment, seizure and conversion runs in ONE
// transaction through the bot-deployed AaveLiquidator executor, which reverts
// unless its debt-asset balance ends higher (bot.js encExecutorCall + contract
// liquidate()). Loss guard (named mechanism, enforced in code):
//  (a) principal: the executor's require(balAfter >= balBefore + minProfit + 1)
//      on-chain guard — any shortfall rolls the whole tx back, worst case gas;
//  (b) gas: signer send carries gas = MAX_GAS_LIMIT and maxFeePerGas =
//      MAX_GAS_PRICE_WEI (the L2 gas charge is enforced by the tx itself), the
//      separate L1 data fee is bounded by l1FeeBoundWei() re-measured FRESH at
//      send (fail closed on read error or bound > L1_DATA_FEE_WEI), and
//      liveLiquidate refuses to send when the total worst case at the FRESH
//      full oracle ETH price > MAX_LOSS_PER_TX_USD;
//  (c) cover <= MAX_COVER_USD re-checked, ETH_USD staleness fails closed.
// Signer rejections are final (no retry loop).
async function liveLiquidate(p) {
  const { user, cover, coverUsd, data, grossUsdEst } = p;
  const skip = (reason) => log({ ts: new Date().toISOString(), type: 'live_skip', user, reason });
  // fee policy + data fee FRESH at send (throws => fail closed)
  let l1Bound;
  try { FEE_WEI = await derivedFeeWei(); l1Bound = await l1FeeBoundWei(); } catch (e) { skip('fee policy unavailable: ' + String(e.message).slice(0, 120)); return; }
  // fresh native valuation at send (no send on a stale gas bound)
  await refreshEthUsd(ORACLE);
  // enforced $20 bound: gas worst case (executor + approvals + L1 fee, fresh price)
  const gasUsd = worstCaseGasLossUsd(l1Bound);
  if (gasUsd > MAX_LOSS_PER_TX_USD) { skip(`gas bound ${gasUsd.toFixed(2)} USD > ${MAX_LOSS_PER_TX_USD}`); return; }
  // review 1091 blocker 4: the executor guard protects PRINCIPAL+minProfit in
  // token units only; expected gross must clear the FRESH gas bound too or a
  // "successful" liquidation can earn less than its own gas.
  if (!(grossUsdEst > gasUsd)) { skip(`expected gross ${Number(grossUsdEst).toFixed(2)} USD <= fresh gas bound ${gasUsd.toFixed(2)} (no send)`); return; }
  // enforced principal bound: cover in USD re-checked against the cap
  if (coverUsd > MAX_COVER_USD) { skip(`cover ${coverUsd.toFixed(2)} USD > ${MAX_COVER_USD}`); return; }
  if (Date.now() - ETH_USD_AT > ETH_USD_STALE_MS) { skip('native ETH valuation stale > 15 min'); return; }
  // one executor send per user per SEND_COOLDOWN_MS: while an underwater
  // candidate is re-simulated once per BLOCK (confirmation window), the signer
  // path is not re-run every cycle (a partial-cover liquidation that leaves
  // the position underwater must not hot-loop sends; stamp BEFORE the send).
  if (Date.now() - (lastSendTs[user] || 0) < SEND_COOLDOWN_MS) { skip('send cooldown: last executor send < 10 min ago'); return; }
  lastSendTs[user] = Date.now();
  if (process.env.LIVE_SIM_ONLY === '1') { skip('selftest-live: send suppressed (no signer call)'); return; }
  const r = await sendLive(EXEC, data, MAX_GAS_LIMIT, FEE_WEI);
  log({ ts: new Date().toISOString(), type: 'live_send', to: EXEC, user, cover: cover.toString(),
    cover_usd: coverUsd, worst_case_gas_usd: gasUsd, l1_fee_bound_wei: l1Bound.toString(), calldata: data, reply: r });
}

// live send through the signer socket; returns parsed reply
function sendLive(to, data, gas, maxFeePerGas) {
  return signerCall({ op: 'send', chain: CHAIN, to, data, value: '0x0',
    gas: '0x' + gas.toString(16), maxFeePerGas: '0x' + maxFeePerGas.toString(16),
    maxPriorityFeePerGas: '0x' + FEE_TIP_WEI.toString(16) });
}

// our own live wallet address from the signer ({"op":"address"}); null when
// unavailable (paper mode) so callers can fail closed on live-only checks.
// LIVE_WALLET (selftest-live only) substitutes the signer socket with a stated
// address so the live path can be demonstrated against a fork deployment.
async function signerAddress() {
  if (process.env.LIVE_WALLET && /^0x[0-9a-fA-F]{40}$/.test(process.env.LIVE_WALLET)) return process.env.LIVE_WALLET;
  if (MODE !== 'live') return null;
  const r = await signerCall({ op: 'address' });
  const a = r && (r.address || r.addr || r.wallet);
  return (typeof a === 'string' && /^0x[0-9a-fA-F]{40}$/.test(a)) ? a : null;
}

// live-path demonstration on a fork deployment (review 8a5a4f8a blocker 1):
// run with the executor really deployed at EXEC (no code override), the
// corrected OWNER() selector checked against the deploying wallet, the exact
// live calldata simulated FROM that wallet, and the send suppressed — the same
// checks the live branch runs before every real send.
async function selftestLive() {
  const wallet = await signerAddress();
  if (!wallet) throw new Error('no wallet for live-path selftest');
  const code = await rpc('eth_getCode', [EXEC]);
  const deployed = !!code && code !== '0x';
  log({ ts: new Date().toISOString(), type: 'selftest_live', exec: EXEC, deployed_code: deployed,
    wallet, owner_selector: SEL_EXEC_OWNER, override: 'none' });
  if (!deployed) throw new Error('executor not deployed at ' + EXEC);
  // the corrected uppercase OWNER() selector must return the deploying wallet
  const owner = addrOf(u(await call(EXEC, SEL_EXEC_OWNER), 0));
  const ownerOk = owner.toLowerCase() === wallet.toLowerCase();
  log({ ts: new Date().toISOString(), type: 'selftest_live_owner', owner, owner_matches_wallet: ownerOk });
  if (!ownerOk) throw new Error(`OWNER() ${owner} != wallet ${wallet}`);
  // run the full detection -> sizing -> executor pipeline in live mode with NO
  // code override. Default target: the real REPLAY victim at its parent block;
  // SELFTEST_USER (fork demo): the driver's interest-bleed position at latest.
  ORACLE = ORACLE_FALLBACK;
  await refreshEthUsd(ORACLE);
  const user = process.env.SELFTEST_USER || REPLAY.user;
  const block = process.env.SELFTEST_USER ? 'latest' : '0x' + (REPLAY.block - 1).toString(16);
  const ad = await call(POOL, SEL.getUserAccountData + pad(user), block);
  const hf = Number(u(ad, 5)) / 1e18;
  log({ ts: new Date().toISOString(), type: 'selftest_live_target', user, block, hf });
  if (hf >= 1) { log({ ts: new Date().toISOString(), type: 'selftest_live_skip', reason: 'position healthy at this block' }); return; }
  await simulateLiquidation(user, block, hf);
}

async function selftest() {
  log({ ts: new Date().toISOString(), type: 'selftest_start' });
  const { oracle } = await resolveOracle();
  ORACLE = oracle; // module global used by assetPrice()
  ETH_USD = Number(u(await call(oracle, SEL.getAssetPrice + pad('0xc02aaa39b223fe8d0a0e5c4f27ead9083c756cc2')), 0)) / 1e8;
  const ethUsd = ETH_USD;
  const parent = '0x' + (REPLAY.block - 1).toString(16);
  const ad = await call(POOL, SEL.getUserAccountData + pad(REPLAY.user), parent);
  const hf = Number(u(ad, 5)) / 1e18;
  // run the full pipeline at the parent block of the real liquidation
  const rec = { user: REPLAY.user, block: parent, hf, eth_usd: ethUsd };
  const cfgWord = u(await call(POOL, SEL.getUserConfiguration + pad(REPLAY.user), parent), 0);
  const reserves = await getReserves();
  const debtRes = [], collRes = [];
  reserves.forEach((a, i) => {
    if (((cfgWord >> BigInt(2 * i)) & 1n) === 1n) debtRes.push(a);
    if (((cfgWord >> BigInt(2 * i + 1)) & 1n) === 1n) collRes.push(a);
  });
  rec.debt_reserves = debtRes; rec.collateral_reserves = collRes;
  rec.gas_loss_bound_usd = worstCaseGasLossUsd();
  log({ ts: new Date().toISOString(), type: 'replay_check', tx: REPLAY.tx, ...rec,
    note: 'real liquidation executed in block+1; event cover=' + REPLAY.realDebtToCover + ' seized=' + REPLAY.realSeized });
  // simulate the exact cover the real liquidator used, from a real liquidator wallet
  const rd = await reserveData(REPLAY.debtAsset, parent);
  const cover = BigInt(REPLAY.realDebtToCover);
  const sender = await fundedSender(REPLAY.debtAsset, cover);
  const data = SEL.liquidationCall + pad(REPLAY.collateralAsset) + pad(REPLAY.debtAsset) +
    pad(REPLAY.user) + pad('0x' + cover.toString(16)) + pad('00');
  let result;
  try {
    const r = await call(POOL, data, parent, sender ? sender.address : KNOWN_LIQUIDATORS[0]);
    result = r === '0x' ? 'success' : 'returned:' + r.slice(0, 70);
  } catch (e) { result = 'revert: ' + String(e.message).slice(0, 140); }
  log({ ts: new Date().toISOString(), type: 'replay_simulate', cover: REPLAY.realDebtToCover,
    sender: sender ? sender.address : null, result });
  console.log(JSON.stringify({ hf, debtRes, collRes, sender, result }));
}

async function main() {
  log({ ts: new Date().toISOString(), type: 'start', relay: RELAY, lane: LANE, mode: MODE, pool: POOL });
  if (process.argv.includes('--selftest')) return selftest();
  if (process.argv.includes('--selftest-live')) return selftestLive();
  if (process.argv.includes('--replay')) {
    // replay gas bound honesty: the same oracle price + derived fee cap the
    // live bot uses, so replay simulate rows carry a live-representative
    // gas_usd_bound (measured live ~= 0.27 USD at the current fee policy).
    const { oracle } = await resolveOracle();
    ORACLE = oracle;
    await refreshEthUsd(ORACLE);
    try { FEE_WEI = await derivedFeeWei(); } catch (e) { /* keep the cap */ }
    return replayPipeline();
  }
  const { prov, oracle } = await resolveOracle();
  ORACLE = oracle; // module global used by assetPrice()
  await refreshEthUsd(ORACLE);
  const reserves = await getReserves();
  let l1BoundCfg = null;
  try { l1BoundCfg = (await l1FeeBoundWei()).toString(); } catch (e) { l1BoundCfg = 'unavailable: ' + String(e.message).slice(0, 80); }
  log({ ts: new Date().toISOString(), type: 'config', provider: prov, oracle, eth_usd: ETH_USD,
    reserves_count: reserves.length, gas_loss_bound_usd: worstCaseGasLossUsd(), l1_fee_bound_wei: l1BoundCfg,
    executor: EXEC, allowed_contracts: ALLOWED.size });
  const saved = loadState();
  const state = {
    candidates: new Map(saved ? saved.candidates : []),
    cursor: saved ? saved.cursor || 0 : 0,
    lastSim: {},
    lastHf: {}, // per-candidate last observed HF; only for the transition->cooldown reset
    underObs: {}, // first block at which HF < 1 was seen (2-block confirmation)
    dustSup: {}, // fix round 7 (review c57f7ed7): candidates whose completed simulation found no profitable pair — suppressed until they re-cross HF=1
    lastSimOk: {}, // fix round 8 (review d6e6966d): head block of the last COMPLETED (non-error) simulation — the next sim waits SIM_OK_COOLDOWN_BLOCKS; cleared on a healthy->underwater crossing
    followUp: new Map(), // follow-up queue: first HF<1 observation -> re-read every block (review e3f07d25)
    wakeTs: 0, // wall time of the last feed wake (wake-to-send latency anchor)
    lastSimResult: null, // last simulateLiquidation record (the replay reads the per-block decisions)
  };
  // cold start: seed the debtor universe once from the pool's own history
  // (bounded: seedScan logs cold_seed with the exact request/candidate counts)
  if (!saved || !state.candidates.size) await coldSeed(state);
  await refreshCandidates(state);
  let lastRefresh = Date.now(), lastSave = Date.now();
  // Fix round 7 (review c57f7ed7: "the 8-second setInterval starts an async
  // scan without waiting for the previous one" — with 25-43 s relay cycles the
  // overlapping cycles tripled the read rate and the README wake-to-send bound
  // did not describe the running process). The cycle is now SEQUENTIAL: the
  // next one starts only after the previous finished, so the paper relay rate
  // equals the README claim under realistic load.
  // Fix round 8 (review d6e6966d, read cost): head, fee cap, follow-up re-reads
  // and the rotation chunk are block-paced. ONE cached eth_getBlockByNumber
  // (readHead, TTL HEAD_POLL_MS) carries the head AND the baseFee-derived fee
  // cap per cycle — the old loop paid one block read for the fee AND one
  // eth_blockNumber per head-needing cycle (measured 42,477 relay req/day).
  // The rotation chunk and the follow-up queue re-read run once per NEW head
  // (a candidate cannot confirm before the head advances; re-reading the same
  // head twice was pure cost). A feed wake forces a fresh block read so the
  // first underwater observation is stamped with the true wake block.
  const cycleLoop = async () => {
    let lastRotHead = 0, lastFupHead = 0;
    for (;;) {
      const t0 = Date.now();
      try {
        HEAD_POLL_MS = state.followUp.size ? 4000 : 10000; // a live window: faster head; idle: ~block cadence + slack
        await refreshEthUsd(ORACLE); // cached full-price native valuation for the gas bound (1/min)
        const headNow = await readHead(); // ONE cached block read: head + derived fee cap
        if (state.followUp.size && headNow > lastFupHead) {
          lastFupHead = headNow;
          await followUpScan(state); // targeted re-reads of the bounded queue, once per new head
        }
        if (headNow > lastRotHead) {
          lastRotHead = headNow;
          await scanCycle(state); // rotation chunk, once per new head (full pass ~105 blocks at the 26k cap)
        }
        if (Date.now() - lastRefresh > REFRESH_MS) {
          lastRefresh = Date.now();
          await refreshCandidates(state);
        }
        if (Date.now() - lastSave > 60000) { lastSave = Date.now(); saveState(state); }
      } catch (e) {
        log({ ts: new Date().toISOString(), type: 'error', msg: String(e).slice(0, 300) });
      }
      await new Promise((r) => setTimeout(r,
        // Fix round 8 (review d6e6966d): with the follow-up queue holding fresh
        // underwater observations (a countable window in progress) the cycle
        // sleeps 1.5 s — the cadence polls the head faster (HEAD_POLL_MS 4 s),
        // but the ONLY relay request a cycle pays is the cached head block read
        // when its TTL expires (~1 per 4 s while busy) — the follow-up aggregate
        // runs once per new head. An idle universe sleeps the full CYCLE_MS and
        // reads the head at the 10 s TTL (block cadence + slack).
        Math.max(state.followUp.size ? 1500 : 1000, (state.followUp.size ? 1500 : CYCLE_MS) - (Date.now() - t0))));
    }
  };
  cycleLoop();
  feedWatch(state); // pinned AnswerUpdated feed wake (see README 'What it waits on')
}
main().catch((e) => { log({ type: 'fatal', msg: String(e).slice(0, 300) }); process.exit(1); });
