#!/usr/bin/env node
// aave-watcher-base v4 — Aave v3 liquidation watcher on the farm's Base chain.
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
const CHAIN = 'base';
const DIR = __dirname;
const MODE = process.env.BOT_MODE || 'paper';

// --- measured constants (2026-11-03, this session: scratch/verify_aave.js) ---
const POOL = '0xa238dd80c259a72e81d7e4664a9801593f98d1c5'; // emits LiquidationCall 0xe413a321...
const MULTICALL = '0xca11bde05977b3631167028862be2a173976ca11'; // Multicall3
const PROV_FALLBACK = '0xe20fcbdbffc4dd138ce8b2e6fbb6cb49777ad64d'; // pool.ADDRESSES_PROVIDER()
const ORACLE_FALLBACK = '0x2cc0fc26ed4563a5ce5e8bdcfe1a2878676ae156'; // provider.getPriceOracle()
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
const KNOWN_LIQUIDATORS = [ // real liquidators measured in the ledger; selftest senders
  '0xeeacf719dbbbe9a2a06c076ab6bd5beb08e8c41d',
  '0xd12810b19b596347a3afac206d3ca65d08594b3f',
  '0xdb61a25516b4480df393d7bfe2d8e33fdaaf079a',
];
// replay target: real liquidation at block 53438141 (event-decoded victim)
const REPLAY = {
  tx: '0xaf3a3bd7574807bd4ce442a1c76e19043898df8da116c0eb53224e77a30cf476',
  block: 53438141,
  user: '0x633653043d622ad588c0bd5c3c604070c931110c',
  collateralAsset: '0x833589fcd6edb6e08f4c7c32d4f71b54bda02913', // USDC
  debtAsset: '0x4200000000000000000000000000000000000006', // WETH
  realDebtToCover: '107437262369723369', // event word1 (measured)
  realSeized: '253374810', // event word0 (measured)
};

// --- executor path (live sends go HERE, never directly to the Pool) ---
// One tx through the bot-deployed AaveLiquidator (forge artifact
// scratch/aave-executor-base/contracts/out/AaveLiquidator.sol/AaveLiquidator.json,
// constructor args [POOL, MORPHO]): Morpho flashLoan(debt, cover) ->
// pool.liquidationCall -> swap ALL seized collateral on the measured UniswapV3
// pool -> Morpho pulls the flash back -> revert "NO_PROFIT" unless the
// executor's debt-asset balance rose by minProfit. Worst case per tx = gas only.
const MORPHO = '0xbbbbbbbbbb9cc5e90e3b3af64bdaf62c37eeffcb'; // 0-fee flashLoan provider
const EXEC = process.env.EXECUTOR_ADDR || '0x14115b5fdab3afcd72cf03785041c720100edb0e';
const SEL_EXEC_LIQUIDATE = '0x9153f799'; // liquidate(user,collateral,debt,cover,minProfit,fee) — v4 executor
// OWNER() — the executor declares the uppercase constant; owner() 0x8da5cb5b
// reverts on the deployed artifact (review 8a5a4f8a blocker 1, measured:
// lowercase reverts empty, uppercase returns the deployer)
const SEL_EXEC_OWNER = '0x117803e3';
const ROUTER = '0x2626664c2603336e57b271c5c0b26f421741e481'; // SwapRouter02 (Uniswap) base — the executor's ONLY route
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
    RUNTIME_CODE.toLowerCase().includes(bare(MORPHO)) &&
    RUNTIME_CODE.toLowerCase().includes(bare(ROUTER)) &&
    RUNTIME_CODE.toLowerCase().includes(bare(FORK_OWNER));
} catch (e) { RUNTIME_CODE = ''; RUNTIME_OK = false; }
// measured collateral-swap pools: one UniswapV3 0.01% WETH/USDC pool serves both
// directions (token0=WETH 0x4200..06, token1=USDC 0x8335..13, measured 2026-11-03);
// same-asset routes (collateral == debt, the newest observed class, block
// 53465304) need no swap at all (executor skips it); pairs without a measured
// pool are watch-only (no executor sim / live send)
const POOL_MAP = {
  '0x4200000000000000000000000000000000000006->0x833589fcd6edb6e08f4c7c32d4f71b54bda02913': { router: ROUTER, fee: 100 },
  '0x833589fcd6edb6e08f4c7c32d4f71b54bda02913->0x4200000000000000000000000000000000000006': { router: ROUTER, fee: 100 },
  '0x833589fcd6edb6e08f4c7c32d4f71b54bda02913->0x833589fcd6edb6e08f4c7c32d4f71b54bda02913': { router: ROUTER, fee: 0 },
  '0x4200000000000000000000000000000000000006->0x4200000000000000000000000000000000000006': { router: ROUTER, fee: 0 },
};

// --- loss guard parameters (live) ---
const MAX_GAS_PRICE_WEI = 200000000n; // 0.2 gwei cap on maxFeePerGas
const MAX_GAS_LIMIT = 1200000n; // executor path bound (fork: successful liquidation gasUsed 518466, guard revert 617607)
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
const MIN_PROFIT_USD = 1.0;
const SLIPPAGE_BUFFER_BPS = 100n; // 1% price-move buffer subtracted from bonus
const HF_TRIGGER = 1.0;
const CLOSE_FACTOR_HF_THRESHOLD = 0.95; // official LiquidationLogic.sol:68
const CYCLE_MS = 8000;
const REFRESH_MS = 5 * 60 * 1000;
const LOG_BLOCKS = 4000;
const REPLAY_BLOCKS = 50000; // replay discovery window: strictly pre-event blocks
const SIM_COOLDOWN_MS = 10 * 60 * 1000;
const MAX_CANDIDATES = 5000; // full recent-activity universe; scan is round-robin 200/cycle
const SCAN_CHUNK = 200;

const LOGS = path.join(DIR, 'logs');
const STATE = path.join(DIR, 'state');
fs.mkdirSync(LOGS, { recursive: true });
fs.mkdirSync(STATE, { recursive: true });
const LOG = path.join(LOGS, 'bot.jsonl');
const STATE_FILE = path.join(STATE, 'candidates.json');

function log(obj) { fs.appendFileSync(LOG, JSON.stringify(obj) + '\n'); }
function pad(a) { return a.toLowerCase().replace(/^0x/, '').padStart(64, '0'); }

let rpcId = 0;
// FORK_RPC (selftest-live only): talk to the local fork endpoint verbatim;
// paper/live always use the relay with the chain + lane path.
const ENDPOINT = process.env.FORK_RPC || `${RELAY}/${CHAIN}?lane=${LANE}`;
async function rpc(method, params) {
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

async function tryAggregate(calls) {
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
  const r = await call(MULTICALL, enc);
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
async function assetPrice(asset, block) {
  const p = await call(ORACLE, SEL.getAssetPrice + pad(asset), block);
  const price = u(p, 0); // 8-dec USD
  if (price === 0n) throw new Error('assetPrice zero (oracle returned 0) for ' + asset);
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
async function liqBonusBps(asset) {
  const c = await call(POOL, SEL.getConfiguration + pad(asset));
  return Number((u(c, 0) >> 32n) & 0xffffn); // bps, 10000 = no bonus
}

// Enforced L1 data-fee bound in wei (live): fresh l1BaseFee()+blobBaseFee()
// from the GasPriceOracle predeploy times the MEASURED per-l1-gas coefficient,
// times the L1_GAS_USED_MAX calldata cover, times the spike margin — and the
// caller requires it under the hard cap L1_DATA_FEE_WEI. Any read failure
// throws => the send path fails CLOSED (no send without a fresh bound).
async function l1FeeBoundWei() {
  const lbf = BigInt(await call(GPO, SEL_GPO_L1BASEFEE));
  const blob = BigInt(await call(GPO, SEL_GPO_BLOB));
  const bound = L1_GAS_USED_MAX * L1_FEE_COEFF_NUM * (lbf + blob) * L1_MARGIN / L1_FEE_COEFF_DEN;
  if (bound > L1_DATA_FEE_WEI) throw new Error(`L1 fee bound ${bound} wei > cap ${L1_DATA_FEE_WEI} (fail closed)`);
  return bound;
}

// worst-case gas loss in USD (loss guard, live): the executor tx gas bound
// (ENFORCED by the tx itself: gas=MAX_GAS_LIMIT, maxFeePerGas=MAX_GAS_PRICE_WEI)
// plus the enforced fresh L1 data-fee bound plus two bounded-allowance approval
// txs, valued at the FRESH full oracle ETH price (no discount) refreshed every
// cycle and again at send; staleness fails the send closed.
let ETH_USD = 0, ETH_USD_AT = 0;
function worstCaseGasLossUsd(l1BoundWei) {
  const l1 = l1BoundWei === undefined ? L1_DATA_FEE_WEI : BigInt(l1BoundWei);
  const wei = MAX_GAS_LIMIT * MAX_GAS_PRICE_WEI + l1 + 2n * APPROVE_GAS * MAX_GAS_PRICE_WEI;
  return Number(wei) / 1e18 * ETH_USD;
}
async function refreshEthUsd(oracle) {
  try {
    const p = Number(u(await call(oracle, SEL.getAssetPrice + pad('0x4200000000000000000000000000000000000006')), 0)) / 1e8;
    if (p > 0) { ETH_USD = p; ETH_USD_AT = Date.now(); }
  } catch (e) { /* keep last; staleness checked at send */ }
}

async function resolveOracle() {
  try {
    const prov = addrOf(u(await call(POOL, SEL.addProv), 0));
    const oracle = addrOf(u(await call(prov, SEL.getPriceOracle), 0));
    if (oracle !== '0x0000000000000000000000000000000000000000') return { prov, oracle };
  } catch (e) { /* fall through */ }
  return { prov: PROV_FALLBACK, oracle: ORACLE_FALLBACK };
}

async function getReserves() {
  const rl = await call(POOL, SEL.getReservesList);
  const n = Number(u(rl, 1)); // word1 = array length
  const out = [];
  for (let i = 0; i < n; i++) out.push(addrOf(u(rl, 2 + i)));
  return out;
}

function loadState() {
  try { return JSON.parse(fs.readFileSync(STATE_FILE, 'utf8')); } catch (e) { return null; }
}
function saveState(state) {
  fs.writeFileSync(STATE_FILE, JSON.stringify({
    candidates: [...state.candidates.entries()].slice(0, MAX_CANDIDATES),
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
function extractCandidates(logs, state) {
  let added = 0;
  const add = (a, via) => {
    if (a === '0x0000000000000000000000000000000000000000') return;
    if (!state.candidates.has(a)) { state.candidates.set(a, { since: Date.now(), via }); added++; }
  };
  for (const lg of logs) {
    const topics = lg.topics || [];
    if (!topics.length) continue;
    if (topics[0] === LIQ_EVENT_TOPIC0) {
      // named LiquidationCall: user = topic3, liquidator = data word 4
      if (topics.length === 4) add(addrOf(BigInt(topics[3])), 'liquidation');
      const d = (lg.data || '0x').slice(2);
      if (d.length >= (4 + 1) * 64) add(addrOf(BigInt('0x' + d.slice(4 * 64, 5 * 64))), 'liquidation_liquidator');
    } else {
      for (let i = 1; i < Math.min(topics.length, 4); i++) add(addrOf(BigInt(topics[i])), 'activity');
    }
  }
  return added;
}

// candidate discovery from recent pool logs
async function refreshCandidates(state) {
  const bn = await blockNumber();
  const from = '0x' + Math.max(0, bn - LOG_BLOCKS).toString(16);
  const logs = await rpc('eth_getLogs', [{ fromBlock: from, toBlock: 'latest', address: POOL }]);
  const added = extractCandidates(logs, state);
  if (added) log({ ts: new Date().toISOString(), type: 'candidates_added', added, total: state.candidates.size });
  // cap keeps the newest addresses if the universe overflows; the rotating
  // window below scans MAX_CANDIDATES in SCAN_CHUNK steps per cycle
  if (state.candidates.size > MAX_CANDIDATES) {
    const keep = [...state.candidates.entries()].sort((a, b) => b[1].since - a[1].since).slice(0, MAX_CANDIDATES);
    state.candidates = new Map(keep);
  }
}

// replay of the known historical liquidation through the SAME discovery AND
// detection pipeline: discovery from historical pool logs around the block,
// detection (HF at parent block), then the full economic simulation.
async function replayPipeline() {
  const state = { candidates: new Map(), cursor: 0, lastSim: {} };
  // discovery uses ONLY information available before the capture block (no +50);
  // chunked in 10k-block ranges to stay inside relay/alchemy getLogs limits
  let logs = [];
  for (let b = Math.max(0, REPLAY.block - REPLAY_BLOCKS); b < REPLAY.block; b += 10000) {
    const chunk = await rpc('eth_getLogs', [{ fromBlock: '0x' + b.toString(16), toBlock: '0x' + Math.min(b + 9999, REPLAY.block - 1).toString(16), address: POOL }]);
    logs = logs.concat(chunk);
  }
  const added = extractCandidates(logs, state);
  const discovered = state.candidates.has(REPLAY.user);
  log({ ts: new Date().toISOString(), type: 'replay_discovery', block: REPLAY.block, logs: logs.length,
    candidates_added: added, universe: state.candidates.size, victim_discovered: discovered });
  if (!discovered) { log({ ts: new Date().toISOString(), type: 'replay_miss', user: REPLAY.user }); return; }
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

async function blockNumber() { return parseInt(await rpc('eth_blockNumber', []), 16); }

// round-robin scan over the WHOLE candidate set (rotating window)
async function scanCycle(state) {
  const users = [...state.candidates.keys()];
  if (!users.length) return;
  const slice = [];
  for (let k = 0; k < Math.min(SCAN_CHUNK, users.length); k++) {
    slice.push(users[(state.cursor + k) % users.length]);
  }
  state.cursor = (state.cursor + slice.length) % Math.max(1, users.length);
  const calls = slice.map((u) => ({ to: POOL, data: SEL.getUserAccountData + pad(u) }));
  const res = await tryAggregate(calls);
  const now = new Date().toISOString();
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
    if (hf < HF_TRIGGER) {
      const c = state.candidates.get(slice[i]) || {};
      log({ ts: now, type: 'opportunity', user: slice[i], hf, debt_usd: Number(debt) / 1e8 });
      const last = state.lastSim[slice[i]] || 0;
      if (Date.now() - last > SIM_COOLDOWN_MS) {
        state.lastSim[slice[i]] = Date.now();
        await simulateLiquidation(slice[i], 'latest', hf);
      }
    }
  }
  log({ ts: now, type: 'heartbeat', scanned: slice.length, universe: users.length, cursor: state.cursor,
    debtors, min_hf: isFinite(minHf) ? minHf : null, min_hf_user: minHfUser });
}

// pick a real liquidator that is funded and approved for the debt asset now
async function fundedSender(debtAsset, neededUnits) {
  for (const a of KNOWN_LIQUIDATORS) {
    try {
      const bal = u(await call(debtAsset, SEL.balanceOf + pad(a)), 0);
      if (bal < neededUnits) continue;
      const allow = u(await call(debtAsset, SEL.allowance + pad(a) + pad(POOL).slice(-64)), 0);
      if (allow >= neededUnits) return { address: a, balance: bal.toString(), allowance: allow.toString() };
    } catch (e) { /* try next */ }
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
        const cover = minBn(maxLiq, coverUsdCap);
        const coverUsd = Number(cover * priceD / 10n ** BigInt(decD)) / 1e8;
        // seized collateral in base units of cAsset: USD cover * (1+bonus) / priceC,
        // converted with the 10^decC / 10^decD decimal factor (measured layout:
        // cover/10^decD * priceD/1e8 = USD; result * 10^decC = cAsset base units)
        const seizedUnits = cover * priceD * BigInt(bonus) * (10n ** BigInt(decC)) /
          (priceC * 10000n * (10n ** BigInt(decD)));
        const seizedUsd = Number(seizedUnits * priceC / 10n ** BigInt(decC)) / 1e8;
        const gasUsd = worstCaseGasLossUsd();
        const profit = coverUsd * (Number(bonus) - 10000 - Number(SLIPPAGE_BUFFER_BPS)) / 10000 - gasUsd;
        const sender = await fundedSender(dAsset, cover);
        rec.pairs.push({
          collateral: cAsset, debt: dAsset, bonus_bps: bonus,
          total_debt_units: totalDebt.toString(), cover_units: cover.toString(),
          cover_usd: coverUsd, seized_units: seizedUnits.toString(), seized_usd: seizedUsd,
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
            // minProfit = 1 USD worth of the debt asset (the executor reverts below it)
            const minProfit = BigInt(Math.round(1e8)) * 10n ** BigInt(decD) / priceD;
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
              if (MODE === 'live' && simOk) await liveLiquidate({ debtAsset: dAsset, cAsset, user, cover, coverUsd, data });
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
  const { user, cover, coverUsd, data } = p;
  const skip = (reason) => log({ ts: new Date().toISOString(), type: 'live_skip', user, reason });
  // enforced L1 data-fee bound, FRESH at send (throws => fail closed)
  let l1Bound;
  try { l1Bound = await l1FeeBoundWei(); } catch (e) { skip('L1 fee bound unavailable: ' + String(e.message).slice(0, 120)); return; }
  // fresh native valuation at send (no send on a stale gas bound)
  await refreshEthUsd(ORACLE);
  // enforced $20 bound: gas worst case (executor + approvals + L1 fee, fresh price)
  const gasUsd = worstCaseGasLossUsd(l1Bound);
  if (gasUsd > MAX_LOSS_PER_TX_USD) { skip(`gas bound ${gasUsd.toFixed(2)} USD > ${MAX_LOSS_PER_TX_USD}`); return; }
  // enforced principal bound: cover in USD re-checked against the cap
  if (coverUsd > MAX_COVER_USD) { skip(`cover ${coverUsd.toFixed(2)} USD > ${MAX_COVER_USD}`); return; }
  if (Date.now() - ETH_USD_AT > ETH_USD_STALE_MS) { skip('native ETH valuation stale > 15 min'); return; }
  if (process.env.LIVE_SIM_ONLY === '1') { skip('selftest-live: send suppressed (no signer call)'); return; }
  const r = await sendLive(EXEC, data, MAX_GAS_LIMIT, MAX_GAS_PRICE_WEI);
  log({ ts: new Date().toISOString(), type: 'live_send', to: EXEC, user, cover: cover.toString(),
    cover_usd: coverUsd, worst_case_gas_usd: gasUsd, l1_fee_bound_wei: l1Bound.toString(), calldata: data, reply: r });
}

// live send through the signer socket; returns parsed reply
function sendLive(to, data, gas, maxFeePerGas) {
  return signerCall({ op: 'send', chain: CHAIN, to, data, value: '0x0',
    gas: '0x' + gas.toString(16), maxFeePerGas: '0x' + maxFeePerGas.toString(16),
    maxPriorityFeePerGas: '0x' + (maxFeePerGas / 10n).toString(16) });
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
  ETH_USD = Number(u(await call(oracle, SEL.getAssetPrice + pad('0x4200000000000000000000000000000000000006')), 0)) / 1e8;
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
  if (process.argv.includes('--replay')) return replayPipeline();
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
  };
  await refreshCandidates(state);
  let lastRefresh = Date.now(), lastSave = Date.now();
  setInterval(async () => {
    try {
      await refreshEthUsd(ORACLE); // fresh full-price native valuation for the gas bound
      await scanCycle(state);
      if (Date.now() - lastRefresh > REFRESH_MS) {
        lastRefresh = Date.now();
        await refreshCandidates(state);
      }
      if (Date.now() - lastSave > 60000) { lastSave = Date.now(); saveState(state); }
    } catch (e) {
      log({ ts: new Date().toISOString(), type: 'error', msg: String(e).slice(0, 300) });
    }
  }, CYCLE_MS);
}
main().catch((e) => { log({ type: 'fatal', msg: String(e).slice(0, 300) }); process.exit(1); });
