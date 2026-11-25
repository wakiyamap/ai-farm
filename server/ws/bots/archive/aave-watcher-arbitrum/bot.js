#!/usr/bin/env node
// aave-watcher-arbitrum v3 — Aave v3 liquidation watcher on the farm's Arbitrum One pool.
// v3 rewiring: live sends ONE transaction to the bot-deployed AaveLiquidator
// executor (owner-only, Balancer 0-fee flash; NO_PROFIT end-balance guard),
// never directly to the Pool. Same-asset pairs and cross-asset pairs on a
// MEASURED positive swap route (WETH -> native USDC, fee tier 500) execute;
// every other cross-asset pair stays watch-only. Paper sims eth_call the
// EXACT live bytes with the constructor-linked runtime code
// (executor-runtime.hex) as a state override.
// Strategy copied from aave-watcher-base (v3) to the one farm chain with no bot;
// this file is self-contained (no imports from other bots, node built-ins only).
// Measured basis (2026-11-03, run 533599fb, ledger + relay research lane):
//   - pool 0x794a61358d6845594f94dc1db02a252b5b4814ad emits every aave_v3
//     liquidation event the ledger holds for arbitrum (78 events / 6.92 days);
//   - real liquidation tx 0xd8d2f4d82fce52124a7c1508a317e15c35f4cd12d5d9128107816b7ac8b09120
//     burned gasUsed 398890 x effectiveGasPrice 22361249 wei = 8.92e-6 ETH
//     (~0.026 USD); constants below cap the worst case ~40x above that;
//   - probe 08:29Z: 220 debtors among 400 most-recent pool users, zero
//     underwater, min HF 1.0023170765589917.
'use strict';
const fs = require('fs');
const path = require('path');
const net = require('net');

const RELAY = process.env.RPC_RELAY_URL || 'http://127.0.0.1:8545';
const LANE = process.env.RPC_LANE || 'paper';
const CHAIN = 'arbitrum';
const DIR = __dirname;
const MODE = process.env.BOT_MODE || 'paper';

// --- measured constants (2026-11-03, this session: scratch/probe_arb.js + relay calls) ---
const POOL = '0x794a61358d6845594f94dc1db02a252b5b4814ad'; // emits LiquidationCall 0xe413a321...
const MULTICALL = '0xca11bde05977b3631167028862be2a173976ca11'; // Multicall3
const PROV_FALLBACK = '0xa97684ead0e402dc232d5a977953df7ecbab3cdb'; // pool.ADDRESSES_PROVIDER()
const ORACLE_FALLBACK = '0xb56c2f0b653b2e0b10c9b928c8580ac5df02c7c7'; // provider.getPriceOracle()
const WETH = '0x82af49447d8a07e3bd95bd0d56f35241523fbab1'; // native-gas-token price proxy
const SEL = {
  getUserAccountData: '0xbf92857c', // (address) -> words: coll,debt,avail,lt,ltv,hf (hf = word 5)
  getReservesList: '0xd1946dbc', // () -> [offset, len, addresses...]  (measured: 20 reserves)
  getUserConfiguration: '0x4417a583', // (address) -> uint256, bit(2i)=borrowing bit(2i+1)=collateral
  getConfiguration: '0xc44b11f7', // (asset) -> uint256: ltv 0-15, lt 16-31, bonus 32-47 bps
  getReserveData: '0x35ea6a75', // (asset) -> struct: word8 aToken, word9 stableDebt, word10 varDebt
  getAssetPrice: '0xb3596f07', // (asset) -> uint256, 8-dec USD
  liquidationCall: '0x00a718a9', // (collateral,debt,user,debtToCover,bool receiveAToken) - same ABI as base pool
  balanceOf: '0x70a08231',
  allowance: '0xdd62ed3e',
  decimals: '0x313ce567',
  approve: '0x095ea7b3',
  tryAggregate: '0xbce38bd7', // (bool,(address,bytes)[])
  addProv: '0x0542975c', // pool.ADDRESSES_PROVIDER()
  getPriceOracle: '0xfca513a8', // provider.getPriceOracle()
};
const LIQ_EVENT_TOPIC0 = '0xe413a321e8681d831f4dbccbca790d2952b56f977908e45be37335533e005286';
const KNOWN_LIQUIDATORS = [ // real arbitrum liquidators measured in the ledger; simulation senders
  '0xb77a6cbb724870c569a2c9f948bd26fcab87c5a2',
  '0x5ac9bc14376bf2727c6211960cf3cec1e2f295bd',
  '0x9355ec6d797b6c8b73de9b52fffdb3bfa6d05fdb',
  '0x0dc76a8cdc8194e2ed4810e729cea63d4b864104',
  '0xd12810b19b596347a3afac206d3ca65d08594b3f',
];
// replay target: the newest real liquidation in the ledger at build time
// (block 520544718, 2026-11-03T08:02:27Z). Same-pair USDC/USDC, so the
// economics close exactly: cover 1452431 -> seized 1517789 = 4.5% bonus
// (1452431 x 1.045 = 1517790, matches within rounding).
const REPLAY = {
  tx: '0xd8d2f4d82fce52124a7c1508a317e15c35f4cd12d5d9128107816b7ac8b09120',
  block: 520544718,
  user: '0xec2d786d52d88844ef4905860e93913ed4484b7d',
  collateralAsset: '0xff970a61a04b1ca14834a43f5de4533ebddb5cc8', // USDC (bridged, 6 dec)
  debtAsset: '0xff970a61a04b1ca14834a43f5de4533ebddb5cc8',
  realDebtToCover: '1452431', // event field, measured
  realSeized: '1517789', // event field, measured
};
// discovery-replay victims measured from the ledger (aave_v3.liquidation events,
// fields verbatim): the two 2026-11-04 cross-asset LINK-collateral victims
// (dormant >62h — attempt 78) and the 2026-10-30 batch (blocks 519547371 to
// 519585307). --replay-all runs the SEED_BLOCKS discovery window for each.
const REPLAYS = [
  { tx: '0xd8d2f4d82fce52124a7c1508a317e15c35f4cd12d5d9128107816b7ac8b09120', block: 520544718, user: '0xec2d786d52d88844ef4905860e93913ed4484b7d', debtAsset: '0xff970a61a04b1ca14834a43f5de4533ebddb5cc8', cover: '1452431' },
  { tx: '0x04ae2b3b3788d3350b7efb7babac3da7a1b98aacf5cf82ff0cec9933ce806889', block: 521054999, user: '0x096f66aad22a55b00b6121dc8ab7bd7cf7bdf94d', debtAsset: '0xaf88d065e77c8cc2239327c5edb3a432268e5831', cover: '50553024' },
  { tx: '0xf2fa4f837d32d1c88d0b6bd6895aaa26c7f36a484249cc39d1915a03acd455b7', block: 521055451, user: '0xad2fb838f8d2b84ec5eaadf2abcb2b890f7edbdf', debtAsset: '0xfd086bc7cd5c481dcc9c85ebe478a1c0b69fcbb9', cover: '30473786' },
  { tx: '0x03fd7c3375c3d799fe8855021de68a9837aa3dada43a448e560440fc4f32249a', block: 519547371, user: '0x102bf626645ce3e9854d538ac5ea343b7c93a41c', debtAsset: '0xaf88d065e77c8cc2239327c5edb3a432268e5831', cover: '2' },
  { tx: '0x64b0f99dfa9ede36b26d2208a4ee5f35041e7ae77bde4db80dc29785d04ebbed', block: 519547480, user: '0x6a04a8f552666af8c5c47e4463850e62446c6196', debtAsset: '0x912ce59144191c1204e64559fe8253a0e49e6548', cover: '291598335190' },
  { tx: '0xab86c5bd4ad1b4b4b2f65fe4e3c70626a652979705d9d498f4ebf9442fef3e86', block: 519548774, user: '0x0d763abd501f3b8f923ecfd75747657e69ec302a', debtAsset: '0xaf88d065e77c8cc2239327c5edb3a432268e5831', cover: '2' },
  { tx: '0xf084280529a57ab21b96271b668f145cabf76ce0b69560aba9d5144d4a7a8fab', block: 519585307, user: '0xc6f9e59bc01bc630f1c2f6197028ab26ff1f155f', debtAsset: '0xff970a61a04b1ca14834a43f5de4533ebddb5cc8', cover: '900880' },
];

// --- executor path (live sends go HERE, never directly to the Pool) ---
// One transaction through the bot-deployed AaveLiquidator (forge artifact
// scratch/aave-executor-arbitrum/contracts/out/AaveLiquidator.sol/AaveLiquidator.json,
// constructor args [POOL, VAULT]): Balancer V2 flashLoan(debt, cover, 0 fee) ->
// pool.liquidationCall (SAME-ASSET only: collateral == debt, the measured
// dominant arbitrum pair class; no swap route exists to trust on arbitrum) ->
// the vault pulls the flash back by transfer -> the executor REVERTS unless
// its debt-asset balance ended strictly higher (>= balBefore + minProfit).
// Worst case per tx = gas only; the flash covers 100% of the principal, so
// the bot's own float is never at risk. OWNER-ONLY: liquidate() must be
// called by the deployer (the gate deploys through the bot's wallet at
// promotion; liveLiquidate verifies owner() == our wallet before sending).
const VAULT = '0xba12222222228d8ba445958a75a0704d566bf2c8'; // Balancer V2 Vault, 0-fee flash (the measured real liquidator's flash source)
const EXEC = process.env.EXECUTOR_ADDR || '0x14115b5fdab3afcd72cf03785041c720100edb0e'; // deterministic CREATE address, fork_evidence
const SEL_EXEC_LIQUIDATE = '0x2c250cfd'; // liquidate(user,collateral,debt,cover,minProfit,router,fee) - router/fee unused (no swap)
const SEL_EXEC_OWNER = '0x8da5cb5b'; // owner() - must equal our wallet before any send
const RUNTIME_FILE = path.join(DIR, 'executor-runtime.hex'); // constructor-linked runtime bytecode (immutables baked) for paper sims
let RUNTIME_CODE = '';
try { RUNTIME_CODE = fs.readFileSync(RUNTIME_FILE, 'utf8').trim(); } catch (e) { /* sims fall back to plain eth_call */ }
// owner baked into the runtime hex (the fork deployer); paper sims call from it
const EXEC_OWNER = '0xc0ffee0000000000000000000000000000000001';

// --- loss guard parameters (live) ---
// Arbitrum gas is ETH-denominated; the L1 data component is already inside the
// charged gas units of the Arbitrum gas model (measured effectiveGasPrice
// 0.0224 gwei), so a flat L1 headroom constant is kept on top for conservatism.
const MAX_GAS_PRICE_WEI = 500000000n; // 0.5 gwei cap on maxFeePerGas (22x measured 0.0224)
const MAX_GAS_LIMIT = 1200000n; // 3x the executor tx measured on the fork: successful liquidation gasUsed 364561, guard revert 390057
const L1_DATA_FEE_WEI = 100000000000000n; // flat 0.0001 ETH headroom on top
const MAX_COVER_USD = 250; // principal at risk per liquidation (capital 400)
// v3 strategy change (run 038378453c734c8a8845a4d753e152c0, review b44cbd98
// "change/narrow the strategy"): the measured same-asset class on arbitrum is
// dust (7d ledger: all 6 same-asset liquidations have debtToCover < 1.6 USD,
// gross 5% bonus < 0.5 USD floor), while cross-asset is 44/50 of 7d events and
// carries every measured >0.5 USD gross bonus (e.g. 0x64d30e55 ~14.3,
// 0x527dbfe2 ~128). v3 executes the ONE measured swap route: WETH -> USDC(native)
// on the UniV3 SwapRouter at fee tier 500, exactly the route of winning tx
// 0x527dbfe2b63015375abefd6d7bfb490ab844280a1491ca10ba43cd7a427ce5c3.
const SWAP_ROUTER = '0x68b3465833fb72a70ecdf485e0e4c7bd8665fc45'; // UniV3 SwapRouter (measured: code present on arbitrum)
const SWAP_ROUTES = {
  '0x82af49447d8a07e3bd95bd0d56f35241523fbab1': { // WETH
    '0xaf88d065e77c8cc2239327c5edb3a432268e5831': 500, // native USDC, fee tier 0.05% (measured route of tx 0x527dbfe2)
  },
};
const MAX_LOSS_PER_TX_USD = 20; // hard L bound: sends are rejected above this
const MIN_PROFIT_USD = 0.5; // arbitrum gas is ~30x cheaper than base: dust is takeable
const SLIPPAGE_BUFFER_BPS = 100n; // 1% price-move buffer subtracted from bonus
const HF_TRIGGER = 1.0;
const CLOSE_FACTOR_HF_THRESHOLD = 0.95; // official LiquidationLogic.sol:68
const CYCLE_MS = 8000;
const REFRESH_MS = 5 * 60 * 1000;
// Coverage fix 2026-11-04 (attempt 78): both 2026-11-04 liquidation victims had
// NO Borrow/Withdraw/Repay in the 600000 blocks (~62h) before their liquidation,
// so the old ~2.5h window made dormant interest-bleed debtors (the majority class,
// cf. attempts 57/58) structurally undiscoverable. 200000 blocks ~ 25h at the
// measured 2.2 blocks/s; getLogs cost stays bounded (pool emits only ~4 events
// per 500 blocks measured 2026-11-04, ~1600 logs per refresh at REFRESH_MS).
const LOG_BLOCKS = 200000;
const SIM_COOLDOWN_MS = 10 * 60 * 1000;
// Cap raised with the window: a full sweep of 20000 candidates at 200/cycle and
// 8s/cycle takes ~13min, still far below the dormant-position liquidatability
// window (measured >62h on the 2026-11-04 victims), so polling cadence stays adequate.
const MAX_CANDIDATES = 20000; // activity universe; scan is round-robin 200/cycle
const SCAN_CHUNK = 200;
// Startup seed (lead 12, 2026-11-04): the ~25h event window structurally misses
// dormant interest-bleed debtors — both 2026-11-04 liquidation victims had NO
// Borrow/Withdraw/Repay in the 600000 blocks (~62h) before liquidation (attempt
// 78), and the interest-bleed class is the majority (attempts 57/58). A one-off
// deeper window at startup discovers them before their first scan. Block rate is
// measured variable 2.2-5.2 b/s on 2026-11-04 (0x1f107fe8 at ts 1793795800 vs
// 178605 blocks in 34540 s), so 3e6 blocks covers ~7-15 days depending on
// traffic; pool logs emit ~4 events per 500 blocks (measured), so the seed is
// ~16 chunked getLogs of SEED_CHUNK blocks, ~1500 events each — one-off cost.
const SEED_BLOCKS = parseInt(process.env.SEED_BLOCKS || '3000000', 10); // env override for deep-seed probes
const SEED_CHUNK_BLOCKS = 190000;
const SEED_VERSION = 2; // saved-state marker: reseed once when absent/stale

const LOGS = path.join(DIR, 'logs');
const STATE = path.join(DIR, 'state');
fs.mkdirSync(LOGS, { recursive: true });
fs.mkdirSync(STATE, { recursive: true });
const LOG = path.join(LOGS, 'bot.jsonl');
const STATE_FILE = path.join(STATE, 'candidates.json');

function log(obj) { fs.appendFileSync(LOG, JSON.stringify(obj) + '\n'); }
function pad(a) { return a.toLowerCase().replace(/^0x/, '').padStart(64, '0'); }

let rpcId = 0;
async function rpc(method, params) {
  const res = await fetch(`${RELAY}/${CHAIN}?lane=${LANE}`, {
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
  // BigInt on purpose: the caller multiplies it into BigInt amounts
  // (a Number here threw "Cannot mix BigInt and other types" before any sim)
  return (u(c, 0) >> 32n) & 0xffffn; // bps, 10000 = no bonus
}

// worst-case gas loss in USD (loss guard, live). The EOA sends exactly ONE
// transaction (the executor call; every approval happens inside the executor
// tx), so the wei cap is MAX_GAS_LIMIT x MAX_GAS_PRICE_WEI plus the flat L1
// headroom. Valued at the FULL fresh oracle WETH price (no discount); the
// price is re-read at startup and its age is fail-closed in liveLiquidate.
let ETH_USD = 0;
let ETH_USD_AT = 0;
const ETH_USD_STALE_MS = 15 * 60 * 1000;
function worstCaseGasLossUsd() {
  const wei = Number(MAX_GAS_LIMIT * MAX_GAS_PRICE_WEI + L1_DATA_FEE_WEI) / 1e18;
  return wei * ETH_USD;
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
    // seed completeness (review 99cc9216 blocker 1): the seed counts as
    // complete ONLY when every chunk range succeeded — the exact still-
    // missing chunk ranges are persisted here and retried at the next
    // startup; a partial seed never marks itself done (a live-window
    // refresh is no substitute for the missing older debtors)
    seed: { ver: SEED_VERSION, missing: (state.seedMissing || []).map((r) => [r[0], r[1]]) },
  }));
}

// chunked pool-log fetch (the relay serves ~200k-block getLogs fine, measured
// by the 200000-block live refresh; deeper windows are fetched chunk by chunk).
// Relay getLogs is transiently flaky on deep windows (measured 2026-11-04:
// "log query timed out" / "alchemy: HTTP 400" on the research lane) — retry,
// then split the chunk in half on a size/timeout error, down to 1000 blocks
// (relay-log-scan pattern); a chunk that still fails is FAIL CLOSED: the
// window is recorded as partial, never silently trusted.
async function getLogsChunk(from, to, depth) {
  const attempts = depth > 3 ? 1 : 3;
  let lastErr = null;
  for (let i = 0; i < attempts; i++) {
    try {
      const logs = await rpc('eth_getLogs', [{
        fromBlock: '0x' + from.toString(16), toBlock: '0x' + to.toString(16), address: POOL,
      }]);
      return logs;
    } catch (e) { lastErr = e; await new Promise((r) => setTimeout(r, 400 * (i + 1))); }
  }
  if (to - from <= 1000) throw lastErr;
  const mid = from + Math.floor((to - from) / 2);
  return (await getLogsChunk(from, mid, depth + 1))
    .concat(await getLogsChunk(mid + 1, to, depth + 1));
}
function seedRanges(from, to) {
  const ranges = [];
  for (let w = from; w <= to; w += SEED_CHUNK_BLOCKS)
    ranges.push([w, Math.min(w + SEED_CHUNK_BLOCKS - 1, to)]);
  return ranges;
}
// fetch exact chunk ranges; a chunk that still fails after retry/split is
// recorded in state.seedMissing (FAIL CLOSED — its range is retried at the
// next startup, review 99cc9216 blocker 1: the old poolLogs swallowed failed
// chunks and startup persisted seed=complete anyway, so the next start skipped
// the deep seed with empty candidates)
async function fetchLogsRanges(state, ranges) {
  const out = [];
  const missing = [];
  for (const [w, chunkTo] of ranges) {
    try {
      out.push(...await getLogsChunk(w, chunkTo, 0));
    } catch (e) {
      missing.push([w, chunkTo]); // failed window recorded, never trusted whole
      log({ ts: new Date().toISOString(), type: 'seed_chunk_failed', from: w, to: chunkTo,
        msg: String(e.message || e).slice(0, 160) });
    }
  }
  state.seedMissing = missing;
  return out;
}

// one-off startup seed (or its retry with the persisted missing ranges):
// discover debtors whose last pool event is older than the live ~25h window
// (dormant interest-bleed class) from a deep chunked window
async function seedCandidates(state, ranges) {
  const logs = await fetchLogsRanges(state, ranges); // pre-capture: up to parent of latest
  const ex = extractCandidates(logs, state);
  log({ ts: new Date().toISOString(), type: 'seed', ranges: ranges.length,
    chunk_failed: state.seedMissing.length, logs: logs.length,
    added: ex.added, unknown_events: ex.unknown, universe: state.candidates.size });
}

// candidate extraction from pool logs by NAMED event schemas; shared by the
// live refresher and the historical replay so both run the SAME pipeline.
// Every topic0 below was verified to equal cast keccak(signature) of the
// deployed pool interface, and each user location was verified on real logs:
//   - LiquidationCall on the measured liquidation tx 0xd8d2f4d8... (topics =
//     [t0, collateralAsset, debtAsset, user]; liquidator is data word 2),
//   - Borrow on a live borrow (canonical v3 layout: user is data word 0,
//     onBehalfOf is topics[2]; reserve topics[1], referralCode topics[3]),
//   - Withdraw/Repay/ReserveUsedAsCollateral*/SwapBorrowRateMode samples from
//     a live 2000-block window.
// Unknown topic0s (BalanceUpdate-class noise) are SKIPPED and counted — the
// old heuristic treated every address-shaped data word as a candidate, which
// mis-read uint256 amounts as addresses.
const EVENT_SCHEMAS = {
  // LiquidationCall(address indexed collateralAsset, address indexed debtAsset,
  //   address indexed user, uint256 debtToCover, uint256 liquidatedCollateralAmount,
  //   address liquidator, bool receiveAToken)
  [LIQ_EVENT_TOPIC0]: { name: 'LiquidationCall', userTopics: [3] },
  '0xb3d084820fb1a9decffb176436bd02558d15fac9b0ddfed8c465bc7359d7dce0':
    { name: 'Borrow', userTopics: [2], userDataWords: [0] },
  '0x3115d1449a7b732c986cba18244e897a450f61e1bb8d589cd2e69e6c8924f9f7':
    { name: 'Withdraw', userTopics: [2, 3] },
  '0xa534c8dbe71f871f9f3530e97a74601fea17b426cae02e1c5aee42c96c784051':
    { name: 'Repay', userTopics: [2, 3] },
  '0x00058a56ea94653cdf4f152d227ace22d4c00ad99e2a43f58cb7d9e3feb295f2':
    { name: 'ReserveUsedAsCollateralEnabled', userTopics: [2] },
  '0x44c58d81365b66dd4b1a7f36c25aa97b8c71c361ee4937adc1a00000227db5dd':
    { name: 'ReserveUsedAsCollateralDisabled', userTopics: [2] },
  '0x7962b394d85a534033ba2efcf43cd36de57b7ebeb3de0ca4428965d9b3ddc481':
    { name: 'SwapBorrowRateMode', userTopics: [2] },
};

function extractCandidates(logs, state) {
  let added = 0, unknown = 0;
  for (const lg of logs) {
    const t0 = (lg.topics || [])[0];
    const schema = EVENT_SCHEMAS[t0];
    if (!schema) { if (t0) unknown++; continue; }
    const topics = lg.topics || [];
    const d = (lg.data || '0x').slice(2);
    const users = [];
    for (const i of schema.userTopics || []) if (topics[i]) users.push(addrOf(BigInt(topics[i])));
    for (const i of schema.userDataWords || []) {
      const w = d.slice(i * 64, i * 64 + 64);
      if (w.length === 64) users.push(addrOf(BigInt('0x' + w)));
    }
    for (const a of users) {
      if (a === '0x0000000000000000000000000000000000000000') continue;
      if (!state.candidates.has(a)) {
        state.candidates.set(a, { since: Date.now(), via: schema.name });
        added++;
      }
    }
  }
  return { added, unknown };
}

// candidate cap eviction (review 99cc9216 blocker 2 fixed: the old sort kept
// the LOW scores — its capacity harness evicted a confirmed near-boundary
// debtor behind 20000 never-scanned candidates). Kept longest first:
// confirmed DEBTORS, lowest last-seen HF kept longest (dormant interest-
// bleed debtors are the keep-forever class), then never-scanned candidates
// (unproven), then confirmed non-debtors — evicted FIRST; within a class,
// fewer scans and newer since evict first (recent-activity candidates are
// cheaply rediscovered by fresh pool events)
function trimCandidates(state) {
  if (state.candidates.size <= MAX_CANDIDATES) return 0;
  const score = (c) => c.scans === undefined ? 0.5
    : c.last_debt === 1 ? 1.0 + Math.max(0, 1.1 - (c.last_hf === undefined ? 1.1 : c.last_hf))
    : 0.25;
  const keep = [...state.candidates.entries()]
    .sort((a, b) => score(b[1]) - score(a[1]) // higher score kept longest
      || (b[1].scans || 0) - (a[1].scans || 0) // fewer scans evicted first
      || a[1].since - b[1].since)              // newer since evicted first
    .slice(0, MAX_CANDIDATES);
  const evicted = state.candidates.size - MAX_CANDIDATES;
  state.candidates = new Map(keep);
  return evicted;
}

// candidate discovery from recent pool logs
async function refreshCandidates(state) {
  const bn = await blockNumber();
  const from = '0x' + Math.max(0, bn - LOG_BLOCKS).toString(16);
  const logs = await rpc('eth_getLogs', [{ fromBlock: from, toBlock: 'latest', address: POOL }]);
  const ex = extractCandidates(logs, state);
  if (ex.added) log({ ts: new Date().toISOString(), type: 'candidates_added', added: ex.added,
    unknown_events: ex.unknown, total: state.candidates.size });
  trimCandidates(state); // candidate cap eviction (see trimCandidates above)
}

// replay of a known historical liquidation through the SAME discovery AND
// detection pipeline: discovery from the deep (SEED_BLOCKS, chunked) pool-log
// window ending at the parent block — identical to the startup seed — then HF
// at the parent block and the full economic simulation.
async function replayTarget(t) {
  const state = { candidates: new Map(), cursor: 0, lastSim: {} };
  // discovery is strictly PRE-capture: the window ends at the parent block,
  // so the victim's own LiquidationCall (emitted in t.block) can never
  // add the victim to the universe — the same constraint the live refresher
  // has (its window always ends at a block before the next HF poll)
  const from = Math.max(0, t.block - SEED_BLOCKS);
  const logs = await fetchLogsRanges(state, seedRanges(from, t.block - 1));
  const ex = extractCandidates(logs, state);
  const discovered = state.candidates.has(t.user);
  log({ ts: new Date().toISOString(), type: 'replay_discovery', tx: t.tx, block: t.block,
    logs: logs.length, candidates_added: ex.added, unknown_events: ex.unknown,
    universe: state.candidates.size, victim_discovered: discovered });
  if (!discovered) { log({ ts: new Date().toISOString(), type: 'replay_miss', user: t.user }); return; }
  const parent = '0x' + (t.block - 1).toString(16);
  let hf = null;
  try {
    const ad = await call(POOL, SEL.getUserAccountData + pad(t.user), parent);
    hf = Number(u(ad, 5)) / 1e18;
  } catch (e) {
    // historical state depth (paper lane serves ~8k blocks): detection fails
    // CLOSED — discovery is the measured flag, HF is best-effort at old blocks
    log({ ts: new Date().toISOString(), type: 'replay_detection_error', user: t.user,
      msg: String(e.message || e).slice(0, 160) });
  }
  if (hf !== null) {
    log({ ts: new Date().toISOString(), type: 'replay_detection', block: t.block - 1, hf, underwater: hf < 1 });
    if (hf < 1) await simulateLiquidation(t.user, parent, hf);
  }
}
async function replayPipeline() { await replayTarget(REPLAY); }
async function replayAll() {
  for (const t of REPLAYS) { try { await replayTarget(t); } catch (e) {
    log({ ts: new Date().toISOString(), type: 'replay_error', tx: t.tx, msg: String(e.message || e).slice(0, 200) }); } }
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
    // scan tracking feeds the cap eviction: debtors (esp. low last-seen HF)
    // are the keep-forever class, confirmed non-debtors evict first
    const c = state.candidates.get(slice[i]);
    if (c) { c.scans = (c.scans || 0) + 1; c.last_scan = Date.now(); }
    if (!r.success || r.returnData.length < 2 + 6 * 64) continue;
    const debt = u(r.returnData, 1);
    if (debt === 0n) { if (c) c.last_debt = 0; continue; }
    const hf = Number(u(r.returnData, 5)) / 1e18;
    if (!isFinite(hf)) continue;
    if (c) { c.last_debt = 1; c.last_hf = hf; }
    debtors++;
    if (hf < minHf) { minHf = hf; minHfUser = slice[i]; }
    if (hf < HF_TRIGGER) {
      const c = state.candidates.get(slice[i]) || {};
      log({ ts: now, type: 'opportunity', user: slice[i], hf, debt_raw: debt.toString() });
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
        // converted with the 10^decC / 10^decD decimal factor
        const seizedUnits = cover * priceD * bonus * (10n ** BigInt(decC)) /
          (priceC * 10000n * (10n ** BigInt(decD)));
        const seizedUsd = Number(seizedUnits * priceC / 10n ** BigInt(decC)) / 1e8;
        const gasUsd = worstCaseGasLossUsd();
        const profit = coverUsd * (Number(bonus) - 10000 - Number(SLIPPAGE_BUFFER_BPS)) / 10000 - gasUsd;
        rec.pairs.push({
          collateral: cAsset, debt: dAsset, bonus_bps: Number(bonus),
          total_debt_units: totalDebt.toString(), cover_units: cover.toString(),
          cover_usd: coverUsd, seized_units: seizedUnits.toString(), seized_usd: seizedUsd,
          profit_usd_est: profit, gas_usd_bound: gasUsd,
          profitable: profit >= MIN_PROFIT_USD && seizedUnits <= aBal,
        });
        if (profit >= MIN_PROFIT_USD && seizedUnits <= aBal) {
          const feeTierRaw = (cAsset.toLowerCase() === dAsset.toLowerCase()) ? 0
            : (SWAP_ROUTES[cAsset.toLowerCase()] && SWAP_ROUTES[cAsset.toLowerCase()][dAsset.toLowerCase()]);
          // executed ONLY on a measured POSITIVE fee tier (review 9328b6b6
          // blocker 4): the old `undefined !== 0` test let every unsupported
          // cross pair (WETH/USDC.e, LINK/USDC, ...) into the execution
          // branch with fee||0; such pairs must stay watch-only.
          const feeTier = (typeof feeTierRaw === 'number' && feeTierRaw > 0) ? feeTierRaw : 0;
          if (feeTier !== 0) {
            // cross-asset pair on a measured swap route: simulate the same
            // executor bytes, router/fee now meaningful
            let simOk = null, simRevert = null;
            const minProfit = BigInt(Math.round(MIN_PROFIT_USD * 1e8)) * 10n ** BigInt(decD) / priceD;
            const data = encExecutorCall(user, cAsset, dAsset, cover, minProfit, SWAP_ROUTER, feeTier);
            rec.pairs[rec.pairs.length - 1].executor_calldata = data;
            rec.pairs[rec.pairs.length - 1].min_profit = minProfit.toString();
            rec.pairs[rec.pairs.length - 1].swap_route = 'measured UniV3 fee ' + feeTier;
            if (!RUNTIME_CODE) {
              rec.pairs[rec.pairs.length - 1].sim_ok = false;
              rec.pairs[rec.pairs.length - 1].sim_revert = 'executor runtime missing (fail closed)';
            } else {
              const override = { [EXEC]: { code: RUNTIME_CODE } };
              simOk = null; simRevert = null;
              try {
                const r = await rpc('eth_call', [{ from: EXEC_OWNER, to: EXEC, data }, block || 'latest', override]);
                simOk = true;
                rec.pairs[rec.pairs.length - 1].sim_return = (r === '0x' ? '0x' : r.slice(0, 70));
              } catch (e) { simOk = false; simRevert = String(e.message).slice(0, 160); }
              rec.pairs[rec.pairs.length - 1].sim_ok = simOk;
              rec.pairs[rec.pairs.length - 1].sim_revert = simRevert;
              if (MODE === 'live' && simOk) await liveLiquidate({ debtAsset: dAsset, cAsset, user, cover, coverUsd, data });
            }
            rec.pairs[rec.pairs.length - 1].sim_result = simOk === true ? 'cross-asset sim of executor bytes ok' : 'cross-asset sim reverted';
          } else if (cAsset.toLowerCase() !== dAsset.toLowerCase()) {
            // no measured positive swap route for this cross pair: stays
            // watch-only in BOTH modes, no send (fail closed)
            rec.pairs[rec.pairs.length - 1].sim_result = 'watch_only: cross-asset pair without measured swap route';
            log({ ts: new Date().toISOString(), type: 'opportunity_watch_only', user, collateral: cAsset, debt: dAsset, reason: 'cross-asset pair without measured swap route' });
          } else {
            // minProfit = MIN_PROFIT_USD worth of the debt asset (the executor
            // reverts below it); router/fee args exist for call-shape
            // compatibility and are unused (no swap happens)
            const minProfit = BigInt(Math.round(MIN_PROFIT_USD * 1e8)) * 10n ** BigInt(decD) / priceD;
            const data = encExecutorCall(user, cAsset, dAsset, cover, minProfit);
            rec.pairs[rec.pairs.length - 1].executor_calldata = data;
            rec.pairs[rec.pairs.length - 1].min_profit = minProfit.toString();
            // fail CLOSED on missing runtime: a plain eth_call to an
            // empty-code destination returns success, which proves nothing
            if (!RUNTIME_CODE) {
              rec.pairs[rec.pairs.length - 1].sim_ok = false;
              rec.pairs[rec.pairs.length - 1].sim_revert = 'executor runtime missing (fail closed)';
            } else {
              // sim of the EXACT live bytes; the executor is unfunded-by-design
              // (the flash covers the cover), so the eth_call needs no funding —
              // only a code override because the gate deploys it at promotion;
              // from = EXEC_OWNER, the owner baked into the runtime code
              const override = { [EXEC]: { code: RUNTIME_CODE } };
              let simOk = null, simRevert = null;
              try {
                const r = await rpc('eth_call', [{ from: EXEC_OWNER, to: EXEC, data }, block || 'latest', override]);
                simOk = true;
                rec.pairs[rec.pairs.length - 1].sim_return = (r === '0x' ? '0x' : r.slice(0, 70));
              } catch (e) { simOk = false; simRevert = String(e.message).slice(0, 160); }
              rec.pairs[rec.pairs.length - 1].sim_ok = simOk;
              rec.pairs[rec.pairs.length - 1].sim_revert = simRevert;
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
// AaveLiquidator.liquidate(user, collateral, debt, cover, minProfit, router, fee):
// atomic flash + same-asset repayment + seizure + flash pull-back + end-balance
// guard (reverts NO_PROFIT unless the executor's debt-asset balance ends
// strictly higher). router/fee are call-shape compatibility args, unused.
function encExecutorCall(user, cAsset, debtAsset, cover, minProfit, router, fee) {
  return SEL_EXEC_LIQUIDATE + pad(user) + pad(cAsset) + pad(debtAsset) +
    pad('0x' + cover.toString(16)) + pad('0x' + minProfit.toString(16)) +
    pad(router || '0x0000000000000000000000000000000000000000') + pad('0x' + ((fee || 0).toString(16)));
}

function minBn(a, b) { return a < b ? a : b; }

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

// live execution path: the whole flash, repayment, seizure and flash pull-back
// runs in ONE transaction through the bot-deployed AaveLiquidator executor,
// which reverts unless its debt-asset balance ends higher (contract
// liquidate(), the NO_PROFIT guard). Loss guard (named mechanism, in code):
//  (a) principal: the executor's require(balAfter >= balBefore + minProfit + 1)
//      on-chain guard — any shortfall rolls the whole tx back, worst case gas;
//      the flash covers 100% of the cover, so our own float is never spent;
//  (b) gas: signer send carries gas = MAX_GAS_LIMIT and maxFeePerGas =
//      MAX_GAS_PRICE_WEI, and liveLiquidate refuses to send when
//      worstCaseGasLossUsd() (executor tx at the FULL fresh ETH price + flat L1
//      headroom) > MAX_LOSS_PER_TX_USD, so a reverted tx burns <= 20 USD
//      (fork-measured executor liquidation gasUsed 364561, guard revert
//      390057 — both under half the 1.2M limit);
//  (c) cover <= MAX_COVER_USD re-checked; native valuation staleness fails
//      closed (> 15 min => no send);
//  (d) executor owner() must equal our wallet (owner-only executor) and the
//      pre-send eth_call of the EXACT live bytes must succeed.
// Signer rejections are final (no retry loop).
async function liveLiquidate(p) {
  const { debtAsset, cAsset, user, cover, coverUsd, data } = p;
  const skip = (reason) => log({ ts: new Date().toISOString(), type: 'live_skip', user, reason });
  // enforced $20 bound: gas worst case (all fees included, full fresh price)
  const gasUsd = worstCaseGasLossUsd();
  if (gasUsd > MAX_LOSS_PER_TX_USD) { skip(`gas bound ${gasUsd.toFixed(2)} USD > ${MAX_LOSS_PER_TX_USD}`); return; }
  // enforced principal bound: cover in USD re-checked against the cap
  if (coverUsd > MAX_COVER_USD) { skip(`cover ${coverUsd.toFixed(2)} USD > ${MAX_COVER_USD}`); return; }
  // native valuation staleness fails closed (no send on a stale gas bound)
  if (Date.now() - ETH_USD_AT > ETH_USD_STALE_MS) { skip('native ETH valuation stale > 15 min'); return; }
  // enforced freshness/stability: skip if either side's oracle price moved >2% in 1 block
  if (!(await priceStable(debtAsset, cAsset))) { skip('oracle price moved >2% between parent and latest'); return; }
  const wallet = await signerCall({ op: 'address' });
  if (!wallet.ok) { skip('no signer address'); return; }
  const me = '0x' + String(wallet.address).slice(-40);
  // owner-only executor: our wallet must be the deployer-of-record, else the
  // tx would revert ONLY_OWNER — fail closed instead of burning gas. An empty
  // return also means EXEC has no runtime code on-chain (gate deploy pending):
  // fail closed, never send.
  let ownerRaw;
  try { ownerRaw = await call(EXEC, SEL_EXEC_OWNER); } catch (e) { skip('executor owner() read failed: ' + String(e.message).slice(0, 100)); return; }
  if (ownerRaw === '0x' || ownerRaw.length < 66) { skip('executor has no runtime code on-chain (owner() empty) — fail closed'); return; }
  const owner = '0x' + ownerRaw.slice(-40);
  if (owner.toLowerCase() !== me.toLowerCase()) { skip(`executor owner ${owner} != our wallet ${me}`); return; }
  // pre-send simulation of the EXACT live bytes from OUR wallet must succeed
  let sim;
  try { sim = await call(EXEC, data, 'latest', me); } catch (e) { skip('pre-send sim revert: ' + String(e.message).slice(0, 120)); return; }
  if (sim !== '0x') { skip('pre-send sim returned data: ' + sim.slice(0, 70)); return; }
  const r = await sendLive(EXEC, data, MAX_GAS_LIMIT, MAX_GAS_PRICE_WEI);
  log({ ts: new Date().toISOString(), type: 'live_send', to: EXEC, user, cover: cover.toString(),
    cover_usd: coverUsd, worst_case_gas_usd: gasUsd, sim_from: me, calldata: data, reply: r });
}

// live send through the signer socket; returns parsed reply
function sendLive(to, data, gas, maxFeePerGas) {
  return signerCall({ op: 'send', chain: CHAIN, to, data, value: '0x0',
    gas: '0x' + gas.toString(16), maxFeePerGas: '0x' + maxFeePerGas.toString(16),
    maxPriorityFeePerGas: '0x' + (maxFeePerGas / 10n).toString(16) });
}

async function selftest() {
  log({ ts: new Date().toISOString(), type: 'selftest_start' });
  const { oracle } = await resolveOracle();
  ORACLE = oracle; // module global used by assetPrice()
  ETH_USD = Number(u(await call(oracle, SEL.getAssetPrice + pad(WETH)), 0)) / 1e8;
  ETH_USD_AT = Date.now();
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

// pure (no-RPC) check of the live trim/retention path and seedRanges chunk
// coverage — review 99cc9216 blocker 2 asked for retention demonstrated AT the
// cap (replayTarget only tested uncapped extractCandidates) — plus the
// seed-completeness saveState/loadState roundtrip. Run: node bot.js --pure-check
async function pureCheck() {
  const now = Date.now();
  const addr = (n) => '0x' + n.toString(16).padStart(40, '0');
  const DEEP = addr(0xd001), BOUND = addr(0xd002), NONDEBT = addr(0xd003);
  const cand = new Map();
  cand.set(BOUND, { since: now, via: 'Borrow', scans: 5, last_debt: 1, last_hf: 1.001 });
  cand.set(DEEP, { since: now, via: 'Borrow', scans: 5, last_debt: 1, last_hf: 0.55 });
  cand.set(NONDEBT, { since: now, via: 'Borrow', scans: 5, last_debt: 0 });
  for (let i = 0; i < 20000; i++) cand.set(addr(0x10000 + i), { since: now, via: 'Borrow' });
  const overflow = cand.size - MAX_CANDIDATES; // 3 over the cap
  const st = { candidates: cand };
  const removed = trimCandidates(st); // replaces st.candidates with the kept set
  const kept = st.candidates;
  const okTrim = removed === overflow && kept.size === MAX_CANDIDATES
    && kept.has(BOUND) && kept.has(DEEP) && !kept.has(NONDEBT)
    && [...kept.values()].some((c) => c.scans === undefined);
  const rs = seedRanges(1000000, 1599999);
  const covered = rs.reduce((s, r) => s + (r[1] - r[0] + 1), 0);
  const okRanges = rs.length === 4 && covered === 600000 && rs[0][0] === 1000000
    && rs[rs.length - 1][1] === 1599999
    && rs.every((r, i) => r[1] - r[0] + 1 <= SEED_CHUNK_BLOCKS && (i === 0 || r[0] === rs[i - 1][1] + 1));
  const had = fs.existsSync(STATE_FILE);
  const backup = had ? fs.readFileSync(STATE_FILE, 'utf8') : null;
  let okSeed = false;
  try {
    saveState({ candidates: cand, cursor: 7, seedMissing: [[1000000, 1189999]] });
    const r = loadState();
    okSeed = !!r && r.cursor === 7 && !!r.seed && r.seed.ver === SEED_VERSION
      && r.seed.missing.length === 1 && r.seed.missing[0][0] === 1000000
      && r.seed.missing[0][1] === 1189999 && r.candidates.length === MAX_CANDIDATES;
  } finally {
    if (had) fs.writeFileSync(STATE_FILE, backup); else fs.unlinkSync(STATE_FILE);
  }
  const ok = okTrim && okRanges && okSeed;
  log({ ts: new Date().toISOString(), type: 'pure_check', ok, trim_removed: removed,
    kept_confirmed_debtors: kept.has(BOUND) && kept.has(DEEP),
    nondebtor_evicted: !kept.has(NONDEBT), ranges_covered_blocks: covered,
    seed_roundtrip: okSeed });
  console.log(JSON.stringify({ ok, okTrim, okRanges, okSeed }));
  process.exitCode = ok ? 0 : 1;
}

async function main() {
  log({ ts: new Date().toISOString(), type: 'start', relay: RELAY, lane: LANE, mode: MODE, pool: POOL });
  if (process.argv.includes('--selftest')) return selftest();
  if (process.argv.includes('--pure-check')) return pureCheck();
  if (process.argv.includes('--replay')) return replayPipeline();
  if (process.argv.includes('--replay-all')) return replayAll();
  const { prov, oracle } = await resolveOracle();
  ORACLE = oracle; // module global used by assetPrice()
  ETH_USD = Number(u(await call(oracle, SEL.getAssetPrice + pad(WETH)), 0)) / 1e8;
  ETH_USD_AT = Date.now();
  const reserves = await getReserves();
  // runtime sanity: the constructor-linked runtime must carry the POOL and
  // VAULT immutables (hex, no 0x prefix); a missing address means the runtime
  // hex does not belong to this executor build — sims then fail closed
  const rtHas = (a) => RUNTIME_CODE.toLowerCase().includes(a.toLowerCase().slice(2));
  const runtimeImmutablesOk = RUNTIME_CODE ? (rtHas(POOL) && rtHas(VAULT)) : false;
  log({ ts: new Date().toISOString(), type: 'config', provider: prov, oracle, eth_usd: ETH_USD,
    reserves_count: reserves.length, gas_loss_bound_usd: worstCaseGasLossUsd(),
    executor: EXEC, executor_runtime_len: RUNTIME_CODE.length, executor_owner_sim_from: EXEC_OWNER,
    runtime_immutables_ok: runtimeImmutablesOk });
  const saved = loadState();
  const state = {
    candidates: new Map(saved ? saved.candidates : []),
    cursor: saved ? saved.cursor || 0 : 0,
    lastSim: {},
    seedMissing: [],
  };
  // one-off deep seed on first start (or whenever the snapshot predates the
  // seed version): the ~25h live window alone never discovers dormant
  // interest-bleed debtors, so the universe starts from SEED_BLOCKS.
  // Review 99cc9216 blocker 1: the snapshot carries the seed version plus
  // its EXACT still-missing chunk ranges — a partial seed KEEPS the
  // candidates discovered so far and only the missing ranges are retried;
  // the seed is complete only once every range succeeded
  let ranges = null;
  if (!saved) ranges = 'new';
  else if (saved.seed && saved.seed.ver === SEED_VERSION && Array.isArray(saved.seed.missing)) {
    if (saved.seed.missing.length) ranges = saved.seed.missing.map((r) => [r[0], r[1]]);
  } else ranges = 'new'; // snapshot predates this seed format: reseed once
  if (ranges) {
    if (ranges === 'new') {
      const bn = await blockNumber();
      ranges = seedRanges(Math.max(0, bn - SEED_BLOCKS), bn - 1); // pre-capture: up to parent of latest
    }
    await seedCandidates(state, ranges);
  }
  await refreshCandidates(state);
  let lastRefresh = Date.now(), lastSave = Date.now();
  setInterval(async () => {
    try {
      // refresh the conservative native valuation every 5 min: live sends are
      // rejected above ETH_USD_STALE_MS (15 min), so a FAILED refresh keeps
      // the old value but does NOT renew its timestamp — staleness fails
      // closed and no send happens on a stale gas bound
      if (Date.now() - ETH_USD_AT > 5 * 60 * 1000) {
        try {
          const p = Number(u(await call(ORACLE, SEL.getAssetPrice + pad(WETH)), 0)) / 1e8;
          if (p > 0) { ETH_USD = p; ETH_USD_AT = Date.now(); }
        } catch (e) {
          log({ ts: new Date().toISOString(), type: 'eth_usd_refresh_error', msg: String(e).slice(0, 140) });
        }
      }
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
