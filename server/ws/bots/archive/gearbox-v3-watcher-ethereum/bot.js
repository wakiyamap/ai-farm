#!/usr/bin/env node
// gearbox-v3-watcher-ethereum — Gearbox Protocol V3 (CreditFacadeV3) credit-account
// liquidation watcher on the farm's Ethereum chain.
// Mechanism (measured: attempts 358-367, lead 47/48 + fork proof scratch/gearbox-v3/
// proof-flash5.py): a credit account whose health factor crosses 1 (creditManager
// isLiquidatable true) may be liquidated by anyone through the CreditFacadeV3
// multicall; the bot flashes WETH on Morpho, runs liquidateCreditAccount with the
// measured tx1 adapter calls (the account's own BPT collateral exits through the
// Balancer router into the pool wrapper and repays the pool debt from the account),
// and the protocol pays the liquidator the remaining funds (premium ~2-4% of the
// repaid debt: fork-measured 3.222826 WETH on an ~87.7 WETH debtor, tx1 layout).
// The whole action runs in ONE transaction through the bot-deployed
// GearboxFlashLiquidator5 contract, which reverts (NoProfit) unless its WETH balance
// ended at least principal + minProfit, sweeps the premium to its owner in the same
// tx, repays the flash and ends at 0 WETH — worst case per tx is the signed gas only
// (maxFeePerGas x 1500000 gas, capped 10 gwei: 0.015 ETH <= 35 USD at ETH/USD <= 2333).
// Paper mode: each poll cycle enumerates the credit accounts through the
// CreditManagerCompressor, batch-reads isLiquidatable through Multicall3
// tryAggregate (healthy accounts return 0 or revert 0x309d1501 — measured on the
// live head 26360848), logs new liquidatable transitions that hold the measured-pool
// BPT, and SIMULATES the executor with relay eth_call carrying the fork-deployed
// CONSTRUCTOR-PATCHED runtime as a code state-override (executor-runtime.hex from
// eth_getCode on the fork — never forge's deployedBytecode). Live mode: sends the
// same calldata through the signer to the gate-deployed executor.
// Self-contained: node built-ins only. All constants measured on-chain 2026-11-07.
'use strict';
const fs = require('fs');
const path = require('path');
const net = require('net');

const RELAY = process.env.RPC_RELAY_URL || 'http://127.0.0.1:8545';
const LANE = process.env.RPC_LANE || 'paper';
const BOT_MODE = process.env.BOT_MODE || 'paper';
const CHAIN = 'ethereum';
const DIR = __dirname;

// --- measured constants (lead 48; facade/CM/compressor/oracle read live at head 26360848) ---
const FACADE = '0x4da50da058ad6cc96bb63edff55b534d2a2cbe92'; // CreditFacadeV3 (WETH)
const CM_EXPECTED = '0x1293a69e4ad4a93293a06b6303104be35bdd83af'; // facade.creditManager() @26360848
const COMPRESSOR = '0x81cb9eA2d59414Ab13ec0567EFB09767Ddbe897a'; // enumerates credit accounts per CM
const MULTICALL = '0xca11bde05977b3631167028862be2a173976ca11'; // Multicall3 (reads only)
const MORPHO = '0xbbbbbbbbbb9cc5e90e3b3af64bdaf62c37eeffcb';
const WETH = '0xc02aaa39b223fe8d0a0e5c4f27ead9083c756cc2';
const ORACLE_WETH_USDC = '0x0f948cba8231db7898ef36a4212581ad7b1b4580'; // MorphoChainlinkOracle: price() = USDC per WETH at the 1e36 protocol scale (valuation only)
const BPT = '0x57c23c58b1d8c3292c15becf07c62c5c52457a42'; // measured tx1 pool token (calls[1] arg 0)
const WMOO_ADAPTER = '0xb4adb364309ec7af0ec286d706b7cb6c3c46381d'; // ERC4626Adapter registered for WMoo (tx1 calls[0] target; cm.adapterToContract control)
const ROUTER_ADAPTER = '0x0214d10f4922c8407351c509150761e0bd487989'; // BalancerV3RouterAdapter (tx1 calls[1] target)
const WRAP_ADAPTER = '0x5deb19295e463eee1457c009d3e9a3f84211868e'; // ERC4626Adapter registered for the WRAP token (tx1 calls[2] target)
const MIN_RATE_RAY = 0x02a649c112686927b4n; // tx1 measured router exit rate floor (scratch/gb-tx1-trace.json)
const PRINCIPAL = 4000000000000000000n; // 4 WETH flash (Morpho flash fee 0; Morpho WETH liquidity measured 15272.25 WETH at head 26360848)
const MIN_PROFIT_WEI = 100000000000000000n; // 0.1 WETH on-chain floor; fork-measured premium 3.22 WETH on the ~87.7 WETH debtor -> premium ~2-4% of debt: the floor covers debtors >= ~2.5-5 WETH of debt

const SEL = {
  getCreditAccounts: '0x3b007fb9', // compressor.getCreditAccounts(address,uint256,uint256)
  isLiquidatable: '0x8340e24d',    // creditManager.isLiquidatable(address,uint16)
  balanceOf: '0x70a08231',
  price: '0xa035b1fe',             // oracle.price()
  creditManager: '0xc12c21c0',     // facade.creditManager()
  underlying: '0x6f307dc3',        // facade.underlying()
  tryAggregate: '0xbce38bd7',      // Multicall3 tryAggregate(bool,(address,bytes)[]) — encoding measured on the farm relay (morpho-watcher-ethereum production)
  owner: '0x8da5cb5b',             // executor.owner()
};
// executor entry selector: keccak of flashLiquidate(address,address,address,address,
// address,address,uint256,uint256,uint256) printed by cast keccak in
// scratch/gearbox-v3/proof-flash5.py (the proof sends with it; measured, not invented)
const SEL_FLASH = '0x365846f2';

const CYCLE_MS = 120000;           // liquidation cadence measured 0.31/day with 34-10398-block poll-catchable windows (attempts 358): 20 s is plenty
const SIM_RETRY_MS = 6 * 3600e3;  // a liquidatable account whose sim reverted is retried at most MAX_SIM_TRIES times, 6 h apart (dust-premium debtors revert NoProfit deterministically)
const MAX_SIM_TRIES = 3;
const PAGE = 100;                  // compressor.getCreditAccounts page size
const MAX_PAGES = 5;               // 500 accounts headroom (21 true accounts measured at head 26360944; the 32 seen at 26360848 was the old dynamic-array decode artifact)
const AGG_CHUNK = 200;             // inner calls per tryAggregate (multicall gas ceiling)

// --- executor path (live sends go HERE, never directly to the facade) ---
const EXEC = process.env.EXECUTOR_ADDR || '0x14115b5fdab3afcd72cf03785041c720100edb0e'; // fork-deployed GearboxFlashLiquidator5 of record (proof-flash5.py); the gate deploys the real one at promotion from the bot wallet (owner = msg.sender baked at deploy, no constructor args)
const SIM_OWNER = '0xc0ffee0000000000000000000000000000000001'; // paper sim caller: the proof owner; measured NO code and NO WETH balance at mainnet head 26360848
const RUNTIME_FILE = path.join(DIR, 'executor-runtime.hex');
const RUNTIME_CODE = fs.existsSync(RUNTIME_FILE) ? fs.readFileSync(RUNTIME_FILE, 'utf8').trim() : '0x';
const RUNTIME_OK = /^0x[0-9a-fA-F]{40,}$/.test(RUNTIME_CODE);

// --- loss bounds (fork-measured gasUsed 1350704 success; the signed fields enforce the worst case) ---
const MAX_GAS_LIMIT = 1500000n;   // fork-measured 1350704 + margin
const FEE_TIP_WEI = 1000000n;     // 0.001 gwei priority
const FEE_CAP_WEI = 10000000000n; // 10 gwei cap on the DERIVED maxFeePerGas
const FEE_ALLOWANCE_WEI = 15000000000000000n; // 0.015 ETH = MAX_GAS_LIMIT x FEE_CAP_WEI: the signed-field worst case, <= 35 USD at ETH/USD <= 2333 (measured oracle 2239.78 on 2026-11-07)
const MAX_LOSS_TX_USD = 35;       // the bot's own L bound, within L=50
const FEE_EXPECTED_GAS = 1400000n; // expected-fee leg of the live minProfit floor (below the enforced cap)

const STATE_FILE = path.join(DIR, 'state', 'state.json');

let rpcId = 0;
let RPC_TOTAL = 0;
async function rpc(method, params, timeoutMs = 30000) {
  const res = await fetch(`${RELAY}/${CHAIN}?lane=${LANE}`, {
    method: 'POST',
    headers: { 'content-type': 'application/json' },
    body: JSON.stringify({ jsonrpc: '2.0', id: ++rpcId, method, params }),
    signal: AbortSignal.timeout(timeoutMs),
  });
  const j = await res.json();
  RPC_TOTAL++;
  if (j.error) throw new Error(`${method}: ${JSON.stringify(j.error).slice(0, 160)}`);
  return j.result;
}

function log(o) {
  o.ts = o.ts || new Date().toISOString();
  const line = JSON.stringify(o);
  fs.appendFileSync(path.join(DIR, 'logs', 'bot.jsonl'), line + '\n');
  console.log(line);
}
function saveState(s) { try { fs.mkdirSync(path.dirname(STATE_FILE), { recursive: true }); fs.writeFileSync(STATE_FILE, JSON.stringify(s)); return true; } catch (e) { return false; } }
function loadState() { try { return JSON.parse(fs.readFileSync(STATE_FILE, 'utf8')); } catch (e) { return null; } }
// Fix (review 2026-11-09 run 233973f5): the §5 loss state must be RESTART-SAFE. A
// signer-accepted hash and a settled gas charge were only in memory until the whole
// scan loop ended, so a restart in that interval loses an accepted transaction or its
// gas from the persisted cumulative loss. persist() writes the state after every such
// change BEFORE another send and fails closed: while the last write failed, live sends
// are refused; the next successful write (every cycle's end) clears the flag again.
let stateWriteFailed = false;
function persist(st) { const ok = saveState(st); stateWriteFailed = !ok; return ok; }

// --- cumulative live-loss stop (decisions/human/2026-11-09-promote-criteria.md §5) ---
// Realized loss = gas actually paid (gasUsed x effectiveGasPrice from the confirmed receipt,
// valued at the bot's fresh ETH/USD) plus any realized principal loss. The executor reverts
// unless its USDC/WETH balance ends higher, so a failed send costs gas only; the tracker
// settles confirmed sends each cycle and the bot stops sending at 30 USD cumulative loss,
// writing the reason to state/STOPPED.json.
const LIVE_LOSS_STOP_USD = 30;
function liveLossInit(st) { if (!st.liveLoss) st.liveLoss = { usd: 0, pending: [] }; }
async function liveLossSettle(st, rpc, ethUsd) {
  const keep = [];
  for (const h of st.liveLoss.pending) {
    let r = null;
    try { r = await rpc('eth_getTransactionReceipt', [h]); } catch (e) {}
    if (!r) { keep.push(h); continue; } // receipt not visible yet
    // Fix (review 2026-11-09, attempt 677): NO valuation yet is NOT a reason to drop
    // the confirmed receipt — on a live service restart ETH_USD initializes to 0 and the
    // first cycle settles before its oracle read, so a receipt settled now would have its
    // gas omitted from liveLoss.usd forever. Keep it pending while ethUsd <= 0 and count
    // it exactly once when a positive fresh valuation exists.
    if (ethUsd <= 0) { keep.push(h); continue; }
    const gasEth = Number(BigInt(r.gasUsed || '0x0') * BigInt(r.effectiveGasPrice || '0x0')) / 1e18; // wei product kept exact, then float ETH (Number stays exact well below 2^53 at these gas sizes)
    st.liveLoss.usd += gasEth * ethUsd;
  }
  st.liveLoss.pending = keep;
}
function liveLossStopWrite(st) {
  try { fs.mkdirSync(path.join(DIR, 'state'), { recursive: true }); fs.writeFileSync(path.join(DIR, 'state', 'STOPPED.json'),
    JSON.stringify({ reason: `cumulative live loss ${st.liveLoss.usd.toFixed(2)} USD reached ${LIVE_LOSS_STOP_USD} USD: stop sending`, live_loss_usd: st.liveLoss.usd, at: new Date().toISOString() }) + '\n'); } catch (e) {}
}
// Fix (review 2026-11-09, attempt 677): the §5 stop reason must be persisted AS SOON AS
// settlement reaches the threshold — the send-time check in the fresh-eligible-account
// branch only fires when another qualifying opportunity appears, so without this the
// reason is never written while the threshold sits crossed with no new opportunities.
// Called from scanCycle right after liveLossSettle; writes STOPPED.json exactly once
// (the persisted stopLogged flag also guards the send-time branch below).
function liveLossStopCheck(st, mode) {
  if (mode === 'live' && st.liveLoss.usd >= LIVE_LOSS_STOP_USD && !st.liveLoss.stopLogged) {
    st.liveLoss.stopLogged = true;
    liveLossStopWrite(st);
    persist(st); // review 233973f5: STOPPED.json and the state total must stay consistent — persist the flag with the reason
    log({ type: 'send_stop', live_loss_usd: st.liveLoss.usd, max_usd: LIVE_LOSS_STOP_USD, reason: 'settlement reached the stop threshold without a new opportunity: STOPPED.json persisted, sending stopped' });
    return true;
  }
  return false;
}

// --- minimal ABI encoding: static-only calls + the production-proven tryAggregate ---
function addrWord(a) { return a.toLowerCase().replace(/^0x/, '').padStart(64, '0'); }
function uintWord(n) { return BigInt(n).toString(16).padStart(64, '0'); }
function encCall(selector, args) {
  let head = selector.replace(/^0x/, '');
  for (const a of args) {
    if (a.t === 'a') head += addrWord(a.v);
    else if (a.t === 'u') head += uintWord(a.v);
    else throw new Error('encCall: unsupported arg');
  }
  return '0x' + head;
}
// tryAggregate(bool requireSuccess, (address,bytes)[] calls) — encoder copied from the
// morpho-watcher-ethereum bot (measured against the farm relay in production).
function encTryAggregate(calls) {
  const roundup = (n) => Math.ceil(n / 32) * 32;
  const starts = [];
  let acc = 0x20 * calls.length;
  for (const c of calls) { starts.push(acc); acc += 0x60 + roundup((c.data.length - 2) / 2); }
  let enc = SEL.tryAggregate + addrWord('0') + '0000000000000000000000000000000000000000000000000000000000000040' + calls.length.toString(16).padStart(64, '0');
  calls.forEach((c, i) => { enc += starts[i].toString(16).padStart(64, '0'); });
  calls.forEach((c) => {
    enc += addrWord(c.to) + '0000000000000000000000000000000000000000000000000000000000000040' +
      ((c.data.length - 2) / 2).toString(16).padStart(64, '0') + c.data.slice(2) +
      '0'.repeat(roundup((c.data.length - 2) / 2) * 2 - (c.data.length - 2));
  });
  return '0x' + enc.replace(/^0x/, '');
}
function decTryAggregate(ret) {
  const h = ret.replace(/^0x/, '');
  if (h.length < 128) return null;
  const base = 64; // skip the leading offset word to the results array
  const n = parseInt(h.slice(base, base + 64), 16);
  const out = [];
  for (let i = 0; i < n; i++) {
    const elemStart = base + 64 + parseInt(h.slice(base + 64 + i * 64, base + 128 + i * 64), 16) * 2;
    const success = BigInt('0x' + h.slice(elemStart, elemStart + 64)) !== 0n;
    const bytesOff = parseInt(h.slice(elemStart + 64, elemStart + 128), 16);
    const len = parseInt(h.slice(elemStart + bytesOff * 2, elemStart + bytesOff * 2 + 64), 16);
    const rd = h.slice(elemStart + bytesOff * 2 + 64, elemStart + bytesOff * 2 + 64 + len * 2);
    out.push({ success, returnData: '0x' + rd });
  }
  return out;
}

// --- signer (live only): one JSON line over the Unix socket ---
function signerCall(obj) {
  return new Promise((resolve) => {
    const sock = process.env.SIGNER_SOCK;
    if (!sock) return resolve({ ok: false, error: 'no SIGNER_SOCK' });
    try {
      const s = net.connect(sock);
      let buf = '';
      const done = (j) => { if (!s.destroyed) s.destroy(); resolve(j); };
      s.setTimeout(90000);
      s.on('data', (d) => {
        buf += d.toString();
        try { done(JSON.parse(buf)); } catch (e) { /* partial line */ }
      });
      s.on('timeout', () => done({ ok: false, error: 'signer timeout' }));
      s.on('error', (e) => done({ ok: false, error: String(e.message || e).slice(0, 120) }));
      s.write(JSON.stringify(obj) + '\n');
    } catch (e) { resolve({ ok: false, error: String(e.message || e).slice(0, 120) }); }
  });
}

let feePolicy = null; // { baseFeeWei, maxFeeWei } — DERIVED from the latest header each cycle (fail closed without it)
function updateFeePolicy(header) {
  if (!header || !header.baseFeePerGas) return null;
  const baseFeeWei = BigInt(header.baseFeePerGas);
  const derived = (baseFeeWei * 9n + 7n) / 8n + FEE_TIP_WEI; // basefee x 9/8 + tip
  const maxFeeWei = derived > FEE_CAP_WEI ? FEE_CAP_WEI : derived;
  feePolicy = { baseFeeWei, maxFeeWei };
  return feePolicy;
}
function feeBound() {
  if (!feePolicy) return { ok: false, why: 'no fee policy (header read failed): fail closed, nothing is sent' };
  const totalWei = feePolicy.maxFeeWei * MAX_GAS_LIMIT;
  return { ok: totalWei <= FEE_ALLOWANCE_WEI, totalWei };
}

let ETH_USD = 0, ETH_USD_AT = 0;

function encFlashCall(acct, minProfit) {
  return encCall(SEL_FLASH, [
    { t: 'a', v: FACADE }, { t: 'a', v: acct }, { t: 'a', v: BPT },
    { t: 'a', v: WMOO_ADAPTER }, { t: 'a', v: ROUTER_ADAPTER }, { t: 'a', v: WRAP_ADAPTER },
    { t: 'u', v: PRINCIPAL }, { t: 'u', v: MIN_RATE_RAY }, { t: 'u', v: minProfit },
  ]);
}

let st;
async function main() {
  // --- cold start controls (measured values above must match live state; fail closed) ---
  const cmLive = '0x' + (await rpc('eth_call', [{ to: FACADE, data: SEL.creditManager }, 'latest'])).slice(-40);
  const und = '0x' + (await rpc('eth_call', [{ to: FACADE, data: SEL.underlying }, 'latest'])).slice(-40);
  log({ type: 'startup', cm: cmLive, cm_expected: CM_EXPECTED, underlying: und, executor: EXEC, mode: BOT_MODE, runtime_ok: RUNTIME_OK });
  if (und.toLowerCase() !== WETH) { log({ type: 'fatal', why: `facade.underlying() = ${und}, expected WETH: the facade no longer matches the measured executor layout — fail closed` }); return; }
  if (!RUNTIME_OK) { log({ type: 'fatal', why: 'executor-runtime.hex missing/empty: paper sims need the fork code override — fail closed' }); return; }

  st = loadState();
  st = (st && st.schema === 1) ? st : { schema: 1, cursorBlock: null, cm: null, seen: {}, liqTotal: 0 };
  liveLossInit(st);
  st.cm = cmLive; // the compressor enumerates by CM; the measured adapters are registered on THIS CM (the sim is the filter if the CM ever changes)

  for (;;) {
    const t0 = Date.now();
    try { await scanCycle(); } catch (e) { log({ type: 'cycle_error', error: String(e.message || e).slice(0, 200) }); }
    const dt = Date.now() - t0;
    if (dt < CYCLE_MS) await new Promise(r => setTimeout(r, CYCLE_MS - dt));
  }
}

async function scanCycle() {
  const rpcStart = RPC_TOTAL;
  // 1. fresh header (review 2026-11-07 fix 4): the relay answers
  // eth_getBlockByNumber("latest") with a header up to 25 blocks stale, while an explicit
  // NUMBER read is fresh (measured 26360969 vs 26360944 by number at 05:44:35Z) — so take
  // eth_blockNumber first, then the header BY NUMBER; every read in the cycle uses the same
  // explicit tag so fee policy, enumeration and isLiquidatable see one consistent state.
  const headNum = await rpc('eth_blockNumber');
  const header = await rpc('eth_getBlockByNumber', [headNum, false]);
  const lastBlock = parseInt(header.number, 16);
  const headerLag = parseInt(headNum, 16) - lastBlock; // must be ~0: the header is read by its own number
  updateFeePolicy(header);
  // Fix (review 2026-11-09 run 811c0a9f): liveLossSettle used to run HERE at the top of
  // the cycle with the PREVIOUS cycle's ETH_USD — a failed or stale oracle read still
  // settled confirmed receipts at the old price. It now runs below, right after THIS
  // cycle's own oracle valuation, and only with a fresh positive price.

  // 2. enumerate the credit accounts from the compressor (all pages)
  const accounts = [];
  let pageOk = false;
  for (let p = 0; p < MAX_PAGES; p++) {
    const data = encCall(SEL.getCreditAccounts, [{ t: 'a', v: st.cm }, { t: 'u', v: p * PAGE }, { t: 'u', v: PAGE }]);
    const ret = await rpc('eth_call', [{ to: COMPRESSOR, data }, headNum]);
    const body = ret.slice(2);
    // ABI of getCreditAccounts (measured at block 26287069, scratch/gb-enum-verify.py):
    // a DYNAMIC array of tuples — word 0 is the array offset 0x20, word 1 the length,
    // words 2..n+1 the per-tuple pointers, and tuple k starts at word (2 + ptr_k/32)
    // with the account address as its FIRST field. (The old decode mistook word 0 for
    // the count and harvested pointer words as addresses: 32 pseudo-addresses.)
    const words = [];
    for (let i = 0; i + 64 <= body.length; i += 64) words.push(body.slice(i, i + 64));
    const n = parseInt(words[1], 16);
    for (let i = 0; i < n; i++) accounts.push('0x' + words[2 + parseInt(words[2 + i], 16) / 32].slice(-40));
    if (n < PAGE) { pageOk = true; break; }
  }
  if (!pageOk) log({ type: 'heartbeat_note', block: lastBlock, note: `compressor enumeration hit MAX_PAGES x PAGE = ${MAX_PAGES * PAGE} accounts: headroom exhausted, heartbeat accounts is a lower bound` });

  // 3. batch isLiquidatable (+ oracle price in the first batch) through tryAggregate
  const liq = new Set();
  let priceRaw = null;
  let priceFreshCycle = false; // review 811c0a9f: this cycle carries a fresh oracle valuation
  for (let i = 0; i < accounts.length; i += AGG_CHUNK) {
    const chunk = accounts.slice(i, i + AGG_CHUNK);
    const calls = chunk.map(a => ({ to: st.cm, data: encCall(SEL.isLiquidatable, [{ t: 'a', v: a }, { t: 'u', v: 10000n }]) }));
    if (i === 0) calls.push({ to: ORACLE_WETH_USDC, data: encCall(SEL.price, []) }); // native (gas) valuation slot: the measured WETH/USDC Morpho oracle price (USDC per WETH at 1e36)
    const ret = await rpc('eth_call', [{ to: MULTICALL, data: encTryAggregate(calls) }, headNum]);
    const res = decTryAggregate(ret);
    if (!res) { log({ type: 'agg_decode_error', block: lastBlock }); continue; }
    for (let k = 0; k < chunk.length; k++) {
      const r = res[k];
      if (r && r.success) {
        const v = r.returnData && r.returnData.length >= 66 ? BigInt(r.returnData) : 0n;
        if (v === 1n) liq.add(chunk[k]); // 1 = liquidatable; 0 = healthy (measured: healthy accounts return 0 or revert 0x309d1501 — the revert leaves success=false)
      }
    }
    if (res.length > chunk.length) {
      const pr = res[res.length - 1];
      if (pr && pr.success && pr.returnData.length >= 66) priceRaw = pr.returnData;
    }
  }
  if (!priceRaw) { // accounts list empty, the first-chunk decode failed, or the oracle leg reverted: one oracle-only read keeps the fail-closed settlement and live send gate reachable on such cycles too (review 2026-11-09 run 811c0a9f; +1 RPC on this rare path only)
    const oret = await rpc('eth_call', [{ to: MULTICALL, data: encTryAggregate([{ to: ORACLE_WETH_USDC, data: encCall(SEL.price, []) }]) }, headNum]);
    const ores = decTryAggregate(oret);
    const pr = ores && ores.length ? ores[ores.length - 1] : null;
    if (pr && pr.success && pr.returnData.length >= 66) priceRaw = pr.returnData;
  }
  if (priceRaw) {
    const p = BigInt(priceRaw);
    if (p > 0n) { ETH_USD = Number(p / 10n ** 24n); ETH_USD_AT = Date.now(); priceFreshCycle = true; } // USDC per WETH at the measured 1e36 oracle scale (divisor 1e24 measured by morpho-watcher-ethereum)
  }

  // Fix (review 2026-11-09 run 811c0a9f): settle confirmed live sends' realized gas with
  // THIS cycle's fresh valuation only — pass 0 when the oracle read failed or was absent
  // this cycle so liveLossSettle keeps the receipts pending (fail closed) instead of
  // pricing them with the previous cycle's stale price; a price rise during a read
  // failure can otherwise push the signed 0.015 ETH above the manifest bound while the
  // bot still sends. Stop reason persists as soon as settlement crosses the threshold.
  await liveLossSettle(st, rpc, priceFreshCycle ? ETH_USD : 0);
  liveLossStopCheck(st, BOT_MODE); // persist the §5 stop reason as soon as settlement crosses the threshold (no new opportunity required)
  persist(st); // review 233973f5: settlement changed liveLoss.usd/pending — persist it before this cycle can send

  // 4. transitions + sim retries -> BPT pre-check -> simulate
  const fresh = [];
  for (const a of liq) {
    let row = st.seen[a];
    if (!row) row = st.seen[a] = { liq: false, since: 0, sims: 0, nextAt: 0 };
    if (!row.liq) { row.liq = true; row.since = lastBlock; st.liqTotal++; } // transition edge
    if (row.sims < MAX_SIM_TRIES && (row.since === lastBlock || Date.now() >= row.nextAt)) fresh.push(a);
  }
  for (const a of Object.keys(st.seen)) { // fell back to healthy: reset the transition flag
    if (!liq.has(a) && st.seen[a].liq) { st.seen[a].liq = false; st.seen[a].sims = 0; st.seen[a].nextAt = 0; }
  }
  let simsDone = 0;
  if (fresh.length) {
    // deterministic pre-check WITHOUT an eth_call: the fixed tx1 adapter layout exits the
    // measured-pool BPT; an account holding none cannot be serviced by this executor.
    const balCalls = fresh.map(a => ({ to: BPT, data: encCall(SEL.balanceOf, [{ t: 'a', v: a }]) }));
    const ret = await rpc('eth_call', [{ to: MULTICALL, data: encTryAggregate(balCalls) }, headNum]);
    const res = decTryAggregate(ret) || [];
    for (let k = 0; k < fresh.length; k++) {
      const a = fresh[k];
      const row = st.seen[a];
      const r = res[k];
      const bal = r && r.success && r.returnData.length >= 66 ? BigInt(r.returnData) : 0n;
      if (!r || !r.success || bal === 0n) {
        row.sims++; row.nextAt = Date.now() + SIM_RETRY_MS;
        log({ type: 'opportunity_skip', account: a, liquidatable_since_block: row.since, bpt_balance: bal.toString(), reason: 'measured-pool BPT balance 0: the fixed tx1 adapter layout cannot exit this account collateral — deterministic revert, no RPC sim spent' });
        continue;
      }
      // live minProfit floor: MIN_PROFIT_WEI + the fee the send will actually pay
      let minProfitOn = MIN_PROFIT_WEI;
      if (BOT_MODE === 'live') {
        if (!feePolicy || !ETH_USD || !priceFreshCycle) { log({ type: 'live_skip', account: a, reason: 'fee policy or a fresh-cycle native valuation missing — fail closed (review 811c0a9f: no send on a stale or failed oracle read)' }); continue; }
        const expFeeUsd = Number(FEE_EXPECTED_GAS * (feePolicy.baseFeeWei + FEE_TIP_WEI)) / 1e18 * ETH_USD;
        minProfitOn = MIN_PROFIT_WEI + BigInt(Math.ceil(expFeeUsd / ETH_USD * 1e18));
      }
      const calldata = encFlashCall(a, minProfitOn);
      let simOk = false, simNote = '';
      if (BOT_MODE === 'live') {
        if (stateWriteFailed) { log({ type: 'live_skip', account: a, reason: 'state persistence failed — fail closed, no send until the next successful state write (review 233973f5)' }); continue; }
        if (st.liveLoss.usd >= LIVE_LOSS_STOP_USD) { // §5 cumulative-loss stop: stop sending, reason in state/STOPPED.json
          if (!st.liveLoss.stopLogged) { st.liveLoss.stopLogged = true; liveLossStopWrite(st); persist(st); } // review 233973f5: persist the flag with the reason
          log({ type: 'send_stop', account: a, live_loss_usd: st.liveLoss.usd, max_usd: LIVE_LOSS_STOP_USD });
          continue;
        }
        const w = await signerCall({ op: 'address' });
        if (!w.ok) { log({ type: 'live_skip', account: a, reason: 'no signer address: ' + String(w.error).slice(0, 80) }); continue; }
        const me = '0x' + String(w.address).slice(-40);
        const fb = feeBound();
        const gasUsd = fb.ok ? Number(fb.totalWei) / 1e18 * ETH_USD : Infinity;
        if (!fb.ok || gasUsd > MAX_LOSS_TX_USD) { log({ type: 'live_skip', account: a, reason: `worst-case signed-fee bound ${fb.ok ? (Number(fb.totalWei) / 1e18).toFixed(6) + ' ETH x ' + ETH_USD.toFixed(1) + ' = ' + gasUsd.toFixed(2) + ' USD over ' + MAX_LOSS_TX_USD : fb.why}` }); continue; }
        let code = null, owner = null;
        try { code = await rpc('eth_getCode', [EXEC, 'latest']); } catch (e) { code = null; }
        try { owner = '0x' + (await rpc('eth_call', [{ to: EXEC, data: SEL.owner }, 'latest'])).slice(-40); } catch (e) { owner = null; }
        if (!code || code === '0x' || owner.toLowerCase() !== me.toLowerCase()) { log({ type: 'live_skip', account: a, reason: `executor not deployed/owned: code ${(code || '').length / 2 - 2} bytes, owner ${owner} != ${me}` }); continue; }
        const sim = await rpc('eth_call', [{ from: me, to: EXEC, data: calldata }, 'latest'], 60000)
          .then(() => ({ ok: true })).catch(e => ({ ok: false, revert: String(e.message || e).slice(0, 160) }));
        simOk = sim.ok; simNote = sim.ok ? '' : sim.revert;
        simsDone++;
        log({ type: simOk ? 'simulate' : 'simulate_revert', account: a, mode: 'live', liquidatable_since_block: row.since, bpt_balance: bal.toString(), sim_ok: sim.ok, note: simNote, principal: PRINCIPAL.toString(), min_profit: minProfitOn.toString() });
        row.sims++; row.nextAt = Date.now() + SIM_RETRY_MS;
        if (sim.ok) {
          const r = await signerCall({ op: 'send', chain: CHAIN, to: EXEC, data: calldata,
            gas: '0x' + MAX_GAS_LIMIT.toString(16), maxFeePerGas: '0x' + feePolicy.maxFeeWei.toString(16),
            maxPriorityFeePerGas: '0x' + FEE_TIP_WEI.toString(16) });
          log({ type: 'send_result', account: a, result: r }); // a signer rejection is FINAL — never retried in a loop
          if (r && r.ok && r.txHash) { st.liveLoss.pending.push(r.txHash); persist(st); } // settle its realized gas once the receipt is visible; review 233973f5: persist the accepted hash BEFORE another send
        }
        continue;
      }
      // paper: eth_call with the fork code override (constructor-patched runtime), at the
      // same explicit head number as the detection reads (fix 4: one consistent fresh state)
      const sim = await rpc('eth_call', [
        { from: SIM_OWNER, to: EXEC, data: calldata }, headNum,
        { [EXEC]: { code: RUNTIME_CODE } },
      ], 60000).then(() => ({ ok: true })).catch(e => ({ ok: false, revert: String(e.message || e).slice(0, 160) }));
      simOk = sim.ok; simNote = sim.ok ? '' : sim.revert;
      simsDone++;
      row.sims++; row.nextAt = Date.now() + SIM_RETRY_MS;
      log({ type: simOk ? 'simulate' : 'simulate_revert', account: a, mode: 'paper', liquidatable_since_block: row.since,
        bpt_balance: bal.toString(), sim_ok: sim.ok, note: simNote, principal: PRINCIPAL.toString(),
        min_profit: minProfitOn.toString(), sim_from: SIM_OWNER });
    }
  }

  // 5. heartbeat + persisted cursor
  st.cursorBlock = lastBlock;
  if (saveState(st)) stateWriteFailed = false; // review 233973f5: the cycle-end write re-clears the fail-closed flag; a failed one keeps refusing sends
  const fbound = feeBound();
  const liquidatable = [...liq];
  log({ type: 'heartbeat', block: lastBlock, header_lag: headerLag, accounts: accounts.length, liquidatable: liquidatable.length,
    liquidatable_accounts: liquidatable.slice(0, 8), sims: simsDone, liq_total: st.liqTotal,
    eth_usd: ETH_USD || null, eth_usd_age_ms: ETH_USD_AT ? Date.now() - ETH_USD_AT : null, eth_usd_fresh: priceFreshCycle,
    base_fee_gwei: feePolicy ? Number(feePolicy.baseFeeWei) / 1e9 : null,
    max_fee_gwei: feePolicy ? Number(feePolicy.maxFeeWei) / 1e9 : null,
    fee_bound_ok: fbound.ok, fee_bound_eth: fbound.ok ? Number(fbound.totalWei) / 1e18 : null,
    executor: EXEC, runtime_ok: RUNTIME_OK, live_loss_usd: st.liveLoss.usd, live_loss_stop_usd: LIVE_LOSS_STOP_USD, rpc_cycle: RPC_TOTAL - rpcStart, rpc_total: RPC_TOTAL });
}

if (require.main === module) {
  main().catch(e => { log({ type: 'fatal', error: String(e.stack || e.message || e).slice(0, 300) }); process.exit(1); });
} else {
  module.exports = { encCall, encTryAggregate, decTryAggregate, encFlashCall, SEL, SEL_FLASH,
    liveLossInit, liveLossSettle, liveLossStopWrite, liveLossStopCheck, LIVE_LOSS_STOP_USD };
}
