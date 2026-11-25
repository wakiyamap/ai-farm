#!/usr/bin/env node
// cv3-buy-watcher-ethereum — Compound v3 residual-collateral sniper on Ethereum.
// Mechanism (measured 2026-11-04, attempts 63/76): after ANYONE absorbs an
// underwater comet account, the borrower's collateral sits in the comet's
// reserves (AbsorbCollateral) and anyone may then buyCollateral() it at the
// comet's discounted oracle quote and sell it on an Uniswap v3 pool. The farm
// executor Cv3Sniper.sol (fork-proven at ethereum block 26302052, attempt 76)
// does buy + swap + revert-unless-balance-increases in ONE transaction, so
// worst case = gas.
// Detection: poll AbsorbCollateral on the two live comets every few seconds;
// on an absorb of a watched asset with a measured pool: read reserves, size a
// partial buy with the comet's own linear quoteCollateral, estimate proceeds
// from the pool's slot0 price, then simulate the executor's buy() by eth_call.
// Paper mode SIMULATES ONLY (eth_call, no keys, no sends); live mode verifies
// the deployed executor (code + OWNER() == signer wallet) and sends the same
// bytes through the signer socket. Self-contained: node built-ins only.
'use strict';
const fs = require('fs');
const path = require('path');
const net = require('net');

const RELAY = process.env.RPC_RELAY_URL || 'http://127.0.0.1:8545';
const LANE = process.env.RPC_LANE || 'paper';
const CHAIN = 'ethereum';
const MODE = process.env.BOT_MODE || 'paper';
const DIR = __dirname;

// --- measured constants (ledger + relay + fork, attempts 63/76) ---
const COMETS = {
  '0xc3d688b66703497daa19211eedff47f25384cdc3': { base: '0xa0b86991c6218b36c1d19d4a2e9eb0ce3606eb48', name: 'cUSDCv3' }, // USDC
  '0x3afdc9bca9213a35503b077a6072f3d0d5ab0840': { base: '0xdac17f958d2ee523a2206206994597c13d831ec7', name: 'cUSDTv3' }, // USDT (canonical, measured via cUSDTv3.baseToken() relay read 2026-11-04)
  // cWETHv3 (base = WETH, measured: the 26342224 absorb tx 0x3f7109f2 paid
  // 110.020324384802098030 WETH to this comet and received USDT back): the
  // ACTIVE comet - the only fresh natural absorb of the 30d window is here.
  '0xa17581a9e3356d9a858b789d68b4d866e593ae94': { base: '0xc02aaa39b223fe8d0a0e5c4f27ead9083c756cc2', name: 'cWETHv3' },
};
const WETH = '0xc02aaa39b223fe8d0a0e5c4f27ead9083c756cc2';
const USDC = '0xa0b86991c6218b36c1d19d4a2e9eb0ce3606eb48';
const USDT = '0xdac17f958d2ee523a2206206994597c13d831ec7';
const AB_TOPIC0 = '0x9850ab1af75177e4a9201c65a2cf7976d5d28e40ef63494b44366f86b2f9412e'; // AbsorbCollateral
// watched collateral -> executable UniV3 pool for {asset, USDC base} (factory
// getPool measured 2026-11-04 via 0x1f98431c8ad98523631ae4a59f267346ea31f984;
// fee-tier 500 pools, WETH/USDC one is the attempt-76 fork-proven pool).
// Assets/pairs without a measured pool stay watch-only (no executable route).
// Assets whose 500bps UniV3 pool holds NO base-side (USDC) liquidity are kept
// watch-only: measured 2026-11-04 at block 26302063, the LINK/USDC 500bps pool
// held 0.83 USDC and the UNI/USDC 500bps pool 0.06 USDC — a collateral SELL
// into them cannot pay out base, and their slot0 price is a stale last-trade
// artifact (the fork executor buys reverted mid-swap on tick-walking gas).
// Executable measured routes: WETH/USDC (token1=collateral orientation) and
// WBTC/USDC (token0=collateral orientation), both fork-proven within the
// signed 450000 gas cap (fork_evidence in manifest).
const POOL_MAP = {
  '0xc02aaa39b223fe8d0a0e5c4f27ead9083c756cc2': { '0xa0b86991c6218b36c1d19d4a2e9eb0ce3606eb48': '0x88e6a0c2ddd26feeb64f039a2c41296fcb3f5640' }, // WETH/USDC
  '0x2260fac5e5542a773aa44fbcfedf7c193bc2c599': { '0xa0b86991c6218b36c1d19d4a2e9eb0ce3606eb48': '0x9a772018fbd77fcd2d25657e5c547baff3fd7d16' }, // WBTC/USDC
  // USDT collateral -> WETH base (cWETHv3): UniV3 USDT/WETH 0.05% pool,
  // measured active 2026-11-05 (eth_getLogs USDT Transfer, last 2000 blocks:
  // 102 transfers FROM the pool, 178 TO it; the absorb tx itself swapped
  // 120,064.58 USDT for 49.84 WETH through it at block 26342224).
  '0xdac17f958d2ee523a2206206994597c13d831ec7': { '0xc02aaa39b223fe8d0a0e5c4f27ead9083c756cc2': '0x4e68ccd3e89f51c3074ca5072bbac773960dfa36' },
};
const SEL = {
  baseToken: '0xc55dae63', // comet.baseToken()
  reserves: '0x9ff567f8', // comet.getCollateralReserves(address)
  quote: '0x7ac88ed1', // comet.quoteCollateral(address,uint256)
  token0: '0x0dfe1681', // pool.token0()
  token1: '0xd21220a7', // pool.token1()
  slot0: '0x3850c7bd', // pool.slot0() -> sqrtPriceX96, tick, ...
  buy: '0xc1d7afaa', // executor buy(comet,collateral,pool,payBase,minCollOut,minProfit,wrapPool,wrapLimitLow,wrapLimitHigh)
  execOwner: '0x117803e3', // executor OWNER() getter
  balanceOf: '0x70a08231', // base.balanceOf(address) — executor funding check
};
const TRANSFER_TOPIC0 = '0xddf252ad1be2c89b69c2b068fc378daa952ba7f163c4a11628f55a4df523b3ef'; // ERC20 Transfer
// executor (Cv3Sniper.sol, readable source scratch/cv3-eth/contracts/src/):
// live = EXECUTOR_ADDR (the gate deploys the artifact at promotion, OWNER =
// the bot wallet, funded with 360 base by sweep at promotion); when unset,
// live fails CLOSED on eth_getCode. Paper mode: executor-runtime.hex is the
// DEPLOYED fork runtime with the paper owner 0xc0ffee...01 baked into the
// OWNER immutable; the bot eth_calls it at a per-base funded placeholder —
// a live-chain address holding >= BUY_CAP of the comet base, discovered from
// recent Transfer logs and verified fail-closed at startup — so a paper sim
// spends payBase <= 360 from a REAL base balance: no balance override.
const FORK_OWNER = '0xc0ffee0000000000000000000000000000000001';
const EXECUTOR_ADDR = /^0x[0-9a-f]{40}$/.test((process.env.EXECUTOR_ADDR || '').toLowerCase())
  ? process.env.EXECUTOR_ADDR.toLowerCase() : ''; // gate-deployed executor
const EXEC_PLACEHOLDER = '0x19437fd8cca145f99f9d922276de7a0ac50fbab6'; // deterministic fallback
const EXEC = EXECUTOR_ADDR || EXEC_PLACEHOLDER; // logged identity; per-base paper placeholders below
const EXEC_BY_BASE = {}; // paper: base -> funded placeholder discovered at startup
let RUNTIME_CODE = '';
try {
  RUNTIME_CODE = fs.readFileSync(path.join(DIR, 'executor-runtime.hex'), 'utf8').trim();
} catch (e) { RUNTIME_CODE = ''; }
const RUNTIME_OK = /^0x[0-9a-fA-F]{200,}$/.test(RUNTIME_CODE || '') &&
  RUNTIME_CODE.toLowerCase().includes(FORK_OWNER.slice(2).toLowerCase());

// sizing / loss bound (L): partial buys capped at ~360 USD of the comet BASE (matches principal_usdc 360)
// per base token  (360e6 USDC/USDT wei; 1.49e17 WETH wei at the ~2405 USD/ETH
// measured 2026-11-05, i.e. <= 361 USD at any price below ~2416); the on-chain
// guard reverts unless the executor's base balance ends >= start + minProfit
// higher, where minProfit INCLUDES THE FULL GAS BUDGET (fee budget in the same
// base-token units as the profit), so principal loss is impossible and the
// after-gas net cannot be below 80% of the expected gross-minus-gas margin:
// measured executor gasUsed 273216 (success); we cap gasLimit at 450k.
// Fee includability (measured 2026-11-05, run 23f0395f): the bot derives
// maxFeePerGas from the LIVE base fee each cycle: maxFee = basefee + basefee/8
// + tip (tip = maxPriorityFeePerGas estimate, floor 1000000 wei = 0.001 gwei), capped at
// MAX_GAS_PRICE_WEI. A maxFeePerGas BELOW the block base fee is never
// included, so the send fails CLOSED when basefee + margin >= the cap
// (live_skip fee_not_includable); measured live base fee 0.039794236 gwei at
// relay head (eth_baseFee, block 26344843) puts the derived fee near 1.05
// gwei -> worst case 450000 x 1.05 gwei = 0.00047 ETH ~ 1.1 USD at the fresh
// pool price. The absolute cap 17.5 gwei (450000 x 17.5 gwei = 0.007875 ETH)
// stays inside the 20 USD L bound only while the fresh ETH price is below
// ~2540 USD; above that the fresh worstCaseUsd check refuses the send (the
// historical base fees 4.6-16.1 gwei measured at blocks 26301784-26302063
// were all ABOVE the old fixed 1.5 gwei cap - the reason for this repair).
// Per-base buy caps and decimals: the cap is ~360 USD expressed in the comet
// base token (the caps are in base WEI: 360 USD of 6-decimal USDC/USDT, or
// 1.49e17 WETH-wei = 0.149 ETH ~ 358 USD at the ~2405 USD/ETH price measured
// from the USDT/WETH pool leg 120064.58 USDT per 49.84 WETH at 26342224;
// <= 360 USD for any ETH price below ~2416). MIN_BUY is ~1 USD of base.
const BUY_CAP_BY_BASE = {
  '0xa0b86991c6218b36c1d19d4a2e9eb0ce3606eb48': 360000000n, // USDC
  '0xdac17f958d2ee523a2206206994597c13d831ec7': 360000000n, // USDT
  '0xc02aaa39b223fe8d0a0e5c4f27ead9083c756cc2': 149000000000000000n, // WETH
};
const MIN_BUY_BY_BASE = {
  '0xa0b86991c6218b36c1d19d4a2e9eb0ce3606eb48': 1000000n, // 1.00 USDC
  '0xdac17f958d2ee523a2206206994597c13d831ec7': 1000000n, // 1.00 USDT
  '0xc02aaa39b223fe8d0a0e5c4f27ead9083c756cc2': 400000000000000n, // ~0.4-1 USD of WETH
};
const DEC_BY_BASE = {
  '0xa0b86991c6218b36c1d19d4a2e9eb0ce3606eb48': 6,
  '0xdac17f958d2ee523a2206206994597c13d831ec7': 6,
  '0xc02aaa39b223fe8d0a0e5c4f27ead9083c756cc2': 18,
};
const GAS_LIMIT = 640000n; // run d237253f proofs: measured route 496576 gas at generous cap, but
// signed caps of 525000/580000 REVERT (deep frames starve under the 61/64 rule); 640000 succeeds.
const MAX_GAS_PRICE_WEI = 12500000000n; // maxFeePerGas cap: 640000*12.5gwei = 19.25 USD worst case (< 20 USD, L)
const MAX_LOSS_PER_TX_USD = 20;
const POOL_FEE_DISCOUNT_NUM = 199n, POOL_FEE_DISCOUNT_DEN = 200n; // 0.995 = 0.05% fee + slippage headroom, integer-safe
const MIN_PROFIT_BPS = 8000n; // on-chain minProfit = gas budget + 80% of the gross-minus-gas margin
const TWO192 = 2n ** 192n; // sqrtPriceX96^2 scaling (integer-safe price math)

const POLL_MS = 3000;
const STATE_FILE = path.join(DIR, 'state', 'state.json');
const LOG_FILE = path.join(DIR, 'logs', 'bot.jsonl');
const HEARTBEAT_CYCLES = 20;

const pad = (a) => a.replace('0x', '').padStart(64, '0');
const hex = (n) => '0x' + BigInt(n).toString(16);
function enc(fn, args) {
  let d = fn;
  for (const a of args) d += pad(a.replace ? a.replace('0x', '').padStart(64, '0') : a.toString(16).padStart(64, '0'));
  return d;
}
function word(r, i) { return '0x' + r.slice(2 + i * 64, 2 + (i + 1) * 64); }
function u(w) { return BigInt(w); }
// eth_call results for address return types are 32-byte left-padded words;
// compare only the trailing 20 bytes against a 0x+40-char lowercase address.
function addr(w) { return '0x' + String(w).slice(-40).toLowerCase(); }

function log(o) { try { fs.appendFileSync(LOG_FILE, JSON.stringify(o) + '\n'); } catch (e) {} }

let reqId = 0;
async function rpc(method, params) {
  const r = await fetch(`${RELAY}/${CHAIN}?lane=${LANE}`, {
    method: 'POST', headers: { 'content-type': 'application/json' },
    body: JSON.stringify({ jsonrpc: '2.0', id: ++reqId, method, params }),
  });
  const j = await r.json();
  if (j.error) throw new Error((j.error.message || JSON.stringify(j.error)).slice(0, 160));
  return j.result;
}

async function call(to, data, override, from) {
  const tx = { from: from || ('0x' + FORK_OWNER.slice(2)), to, data };
  return override ? rpc('eth_call', [tx, 'latest', override])
    : rpc('eth_call', [tx, 'latest']);
}

function loadState() {
  try { return JSON.parse(fs.readFileSync(STATE_FILE, 'utf8')); } catch (e) { return null; }
}
function saveState(s) { try { fs.mkdirSync(path.dirname(STATE_FILE), { recursive: true }); fs.writeFileSync(STATE_FILE, JSON.stringify(s)); } catch (e) {} }

// --- live signer (Unix socket, one JSON line per request) ---
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

async function main() {
  log({ ts: new Date().toISOString(), type: 'start', mode: MODE, lane: LANE, exec: EXEC, executor_addr: EXECUTOR_ADDR || null, runtime_ok: RUNTIME_OK });
  if (!RUNTIME_OK) { log({ ts: new Date().toISOString(), type: 'fatal', reason: 'executor-runtime.hex missing/invalid (fail closed, no empty-code eth_call)' }); return; }

  // pool token order (one read per pool, once): map {asset, base} -> pool
  // (token0/token1 words reduced to 20-byte addresses before any compare)
  const poolMeta = {}; // pool -> {t0, t1}
  for (const pools of Object.values(POOL_MAP))
    for (const p of Object.values(pools))
      if (!poolMeta[p]) {
        try { poolMeta[p] = { t0: addr(await call(p, SEL.token0)), t1: addr(await call(p, SEL.token1)) }; }
        catch (e) { log({ ts: new Date().toISOString(), type: 'error', where: 'pool_meta', pool: p, error: String(e.message) }); }
      }

  // paper executor placeholder funding (once per comet base): find a live-chain
  // address holding >= BUY_CAP of the base from recent Transfer logs and verify
  // its balance fail-closed, so the paper eth_call spends payBase <= the cap from a
  // REAL base balance (no balance override). For the flash route (base != USDC)
  // the candidate must ALSO hold >= 400e6 USDC: the paper sim's flash leg repays
  // the borrowed base side from the placeholder's own USDC principal (no override).
  // No candidate => the deterministic placeholder with its real balance (usually 0): every sim then
  // reverts on funding, logged, never a false success.
  async function pickFunded(base) {
    const usdcSide = base.toLowerCase() !== USDC.toLowerCase(); // flash route needs USDC principal
    for (const back of [4, 40]) { // widen once
      let logs = [];
      try {
        const head = Number(await rpc('eth_blockNumber', []));
        logs = await rpc('eth_getLogs', [{ address: base, topics: [TRANSFER_TOPIC0], fromBlock: '0x' + Math.max(0, head - back).toString(16), toBlock: '0x' + head.toString(16) }]);
      } catch (e) { log({ ts: new Date().toISOString(), type: 'error', where: 'funding_scan', base, error: String(e.message) }); break; }
      for (const l of logs.slice(-24).reverse()) {
        const from = addr(l.topics[1]);
        if (from === EXECUTOR_ADDR) continue;
        try {
          const bal = u(await call(base, enc(SEL.balanceOf, [from])));
          if (bal < BUY_CAP_BY_BASE[base]) continue;
          if (usdcSide) { // fail closed: the placeholder must fund the flash repayment too
            const usdcBal = u(await call(USDC, enc(SEL.balanceOf, [from])));
            if (usdcBal < 400000000n) continue;
          }
          log({ ts: new Date().toISOString(), type: 'funding', base, addr: from, balance: Number(bal), usdc: usdcSide ? 'checked >= 400e6' : undefined }); return from;
        } catch (e) { /* candidate unreadable */ }
      }
    }
    log({ ts: new Date().toISOString(), type: 'funding_unresolved', base, note: 'placeholder keeps its real balance; sims revert on funding, fail closed' });
    return EXEC_PLACEHOLDER;
  }
  if (MODE !== 'live')
    for (const base of [...new Set(Object.values(COMETS).map((c) => c.base))])
      EXEC_BY_BASE[base.toLowerCase()] = (await pickFunded(base)).toLowerCase();

  let st = loadState();
  let lastBlock = st && Number.isFinite(st.lastBlock) ? st.lastBlock : null;
  const stats = { cycles: 0, absorbs: 0, watch_only: 0, reserves_gone: 0, opportunities: 0, sims_ok: 0, sims_rev: 0, errors: 0 };
  if (lastBlock == null) {
    // seed 3 blocks back so the first cycle scans recent history; state.json
    // persists lastBlock from then on (a re-start never replays all history)
    try { lastBlock = Math.max(0, Number(await rpc('eth_blockNumber', [])) - 3); } catch (e) { lastBlock = 0; }
  }
  let ethUsd = 0, ethUsdAt = 0, gasPriceWei = 0, gasPriceAt = 0, baseFeeWei = 0;

  while (true) {
    const t0 = Date.now();
    try {
      const latest = Number(await rpc('eth_blockNumber', []));
      if (lastBlock == null) lastBlock = Math.max(0, latest - 3);
      if (latest > lastBlock) {
        // The relay's getLogs upstream can lag our head reading: a range past
        // its head is a transient "block range extends beyond current head
        // block" error (64 such errors in the 20:32-23:50 supervised run).
        // Retry once against the relay's own head, scanning only up to it.
        // scannedTo is committed ONLY after a successful getLogs (a range that
        // never scanned keeps the cursor: cursor 100 + head 110 + error + retry
        // head 100 keeps 100; the next cycle re-scans 101..head; proven by
        // scratch/cv3-eth/cursor-check.js).
        let scannedTo = 0, logs = [];
        const scanRange = (to) => rpc('eth_getLogs', [{
          address: Object.keys(COMETS), topics: [AB_TOPIC0],
          fromBlock: '0x' + (lastBlock + 1).toString(16), toBlock: '0x' + to.toString(16),
        }]);
        try { logs = await scanRange(latest); scannedTo = latest; }
        catch (e) {
          if (!/extends beyond current head/i.test(String(e.message))) throw e;
          const h2 = Number(await rpc('eth_blockNumber', []));
          // The retry can hit the SAME transient race (head moved again
          // between our two readings): swallow it as a relay_lag record with
          // the cursor preserved (scannedTo stays lastBlock; the next cycle,
          // 3 s later, re-scans the same range). It is not a cycle error -
          // detection latency is unchanged (review 2acf28ed counted these
          // double-race lines as "transient beyond-head errors").
          try {
            if (h2 >= lastBlock + 1) { logs = await scanRange(h2); scannedTo = h2; }
            else { scannedTo = lastBlock; log({ ts: new Date().toISOString(), type: 'relay_lag', head: h2, lastBlock }); }
          } catch (e2) {
            if (!/extends beyond current head/i.test(String(e2.message))) throw e2;
            scannedTo = lastBlock;
            log({ ts: new Date().toISOString(), type: 'relay_lag', head: h2, lastBlock, note: 'retry raced too; cursor preserved, next cycle re-scans' });
          }
        }
        stats.absorbs += logs.length;
        for (const l of logs) {
          const cometKey = l.address.toLowerCase();
          const comet = COMETS[cometKey];
          if (!comet) continue;
          // AbsorbCollateral(address indexed absorber, address indexed borrower,
          // address indexed collateralType, uint256 collateralAbsorbed, uint256
          // borrowAbsorbed): topics[1]=absorber, topics[2]=borrower, topics[3]=asset
          // (measured on tx 0x16c8a985... at block 26331463: absorber 0x1f2f10d1,
          // borrower 0x52e6675f, asset WBTC 0x2260fac5...).
          const asset = addr(l.topics[3]); // collateral type (the absorbed asset)
          const base = comet.base;
          const blk = parseInt(l.blockNumber, 16);
          const rec = {
            ts: new Date().toISOString(), type: 'absorb', comet: cometKey, comet_name: comet.name,
            asset, base, blk, tx: l.transactionHash,
            absorbedWei: l.data.slice(2, 66) === '0'.repeat(64) ? 0 : Number(BigInt('0x' + l.data.slice(2, 66))), // collateralAbsorbed (collateral wei, informational)
          };
          const pool = POOL_MAP[asset] && POOL_MAP[asset][base];
          log({ ...rec, type: 'absorb' }); // machine-readable detection record
          if (!pool) { stats.watch_only++; log({ ...rec, type: 'opportunity', watch_only: true, reason: 'no measured UniV3 pool for {asset, base}' }); continue; }
          // Measured detection-to-inclusion window (review 3c9b5d18 requirement):
          // read the absorb block's own timestamp once per event; poll_delay_s is
          // OUR polling latency from event inclusion to detection. The reserves
          // check and the simulation in trade() add alive_at_s / gone_after_s,
          // which measure how long the residual stayed available (or when it was
          // taken) — the natural window that must exceed poll+sim+~1 block inclusion.
          let blkTs = 0;
          try { const bo = await rpc('eth_getBlockByNumber', ['0x' + blk.toString(16), false]); if (bo && bo.timestamp) blkTs = Number(bo.timestamp); } catch (e) { blkTs = 0; }
          const pollDelayS = blkTs > 0 ? Math.max(0, Math.round(Date.now() / 1000 - blkTs)) : 0;
          stats.opportunities++;
          log({ ...rec, type: 'opportunity', pool, blk_ts: blkTs, poll_delay_s: pollDelayS });
          await trade(cometKey, asset, base, pool, blk, blkTs, pollDelayS);
        }
        lastBlock = scannedTo;
        saveState({ lastBlock });
      }
      stats.cycles++;
      if (stats.cycles % HEARTBEAT_CYCLES === 0)
        log({ ts: new Date().toISOString(), type: 'heartbeat', lastBlock, ...stats });
    } catch (e) {
      stats.errors++;
      log({ ts: new Date().toISOString(), type: 'error', where: 'cycle', error: String(e.message).slice(0, 200) });
    }
    const dt = Date.now() - t0;
    await new Promise((r) => setTimeout(r, Math.max(200, POLL_MS - dt)));
  }

  // per-event execution: reserves -> quote-sized buy -> pool proceeds estimate
  // -> executor eth_call simulation (paper) or signer send (live).
  async function trade(cometKey, asset, base, pool, blk, blkTs, pollDelayS) {
    try {
      const meta = poolMeta[pool];
      if (!meta) return;
      const aliveS = (t) => blkTs > 0 ? Math.max(0, Math.round(t / 1000 - blkTs)) : 0; // seconds the residual has been ours-to-take since its absorb block
      const reservesW = u(await call(cometKey, enc(SEL.reserves, [asset]))); // comet reserves of asset
      if (reservesW === 0n) { stats.reserves_gone++; log({ ts: new Date().toISOString(), type: 'reserves_gone', asset, blk, gone_after_s: aliveS(Date.now()), note: 'taken before detection (window upper bound = gone_after_s)' }); return; }
      const quoteCap = u(await call(cometKey, enc(SEL.quote, [asset, BUY_CAP_BY_BASE[base].toString(16)]))); // collateral for ~360 USD of base
      let payBase = BUY_CAP_BY_BASE[base];
      let collOut = quoteCap;
      if (quoteCap > reservesW) { // reserves-limited partial buy (quote is linear)
        payBase = (BUY_CAP_BY_BASE[base] * ((reservesW * 985n) / 1000n)) / quoteCap; // 1.5% reserves margin
        if (payBase < MIN_BUY_BY_BASE[base]) { log({ ts: new Date().toISOString(), type: 'tiny_reserves', asset, payBase: Number(payBase) }); return; }
        collOut = u(await call(cometKey, enc(SEL.quote, [asset, payBase.toString(16)])));
      }
      // pool spot price from slot0 sqrtPriceX96, integer-safe:
      // raw = token1wei per token0wei = sqrtPriceX96^2 / 2^192.
      const s0 = await call(pool, SEL.slot0);
      const sqrtW = u(word(s0, 0));
      const sqrt2 = sqrtW * sqrtW;
      // proceeds of selling collOut of `asset` for `base` on this pool, with
      // the 0.995 fee/slippage factor applied exactly in BigInt (no mixed
      // BigInt/Number arithmetic): token1 = base side -> multiply by price,
      // token1 = asset side -> divide by price.
      const baseIsT1 = (meta.t1 === base && meta.t0 === asset);
      const assetIsT1 = (meta.t1 === asset && meta.t0 === base);
      if (!assetIsT1 && !baseIsT1) { log({ ts: new Date().toISOString(), type: 'watch_only', asset, pool, reason: 'pool token order unexpected' }); return; }
      const proceedsWei = baseIsT1
        ? (collOut * sqrt2 * POOL_FEE_DISCOUNT_NUM) / (TWO192 * POOL_FEE_DISCOUNT_DEN)
        : (collOut * TWO192 * POOL_FEE_DISCOUNT_NUM) / (sqrt2 * POOL_FEE_DISCOUNT_DEN);
      // fresh ETH price from the WETH/USDC pool (also the USDT proxy price):
      // USDC units per WETH = 1e12 / raw of that pool; refresh at most 1/min
      if (Date.now() - ethUsdAt > 60000) {
        const wPool = POOL_MAP[WETH][USDC];
        const ws = await call(wPool, SEL.slot0);
        const wsq = Number(BigInt(word(ws, 0)));
        ethUsd = 1e12 / ((wsq / 2 ** 96) ** 2);
        ethUsdAt = Date.now();
      }
      if (Date.now() - gasPriceAt > 60000) {
        try { gasPriceWei = Number(await rpc('eth_maxPriorityFeePerGas', [])) || 2000000000; } catch (e) { gasPriceWei = 2000000000; }
        // live base fee: maxFeePerGas below it is never included, so every send
        // must price ABOVE it (fee includability, measured 2026-11-05). The
        // relay rejects eth_baseFee, so we read the base fee from the latest
        // block header (eth_getBlockByNumber is relay-allowed):
        try { const hb = await rpc('eth_getBlockByNumber', ['latest', false]); baseFeeWei = hb && hb.baseFeePerGas ? Number(hb.baseFeePerGas) : 0; } catch (e) { baseFeeWei = 0; }
        gasPriceAt = Date.now();
      }
      let maxFee = 0n; // derived from the live base fee: basefee + 12.5% headroom + tip
      {
        const bf = BigInt(baseFeeWei);
        const tip = BigInt(Math.max(gasPriceWei, 1000000)); // tip floor 1000000 wei = 0.001 gwei
        if (baseFeeWei > 0) {
          const cand = bf + (bf >> 3n) + tip;
          maxFee = cand < MAX_GAS_PRICE_WEI ? cand : MAX_GAS_PRICE_WEI;
          if (maxFee <= bf) maxFee = 0n; // cap reached at/below base fee: not includable
        }
      }
      if (maxFee === 0n) { // base fee unreadable or not includable under the cap: fail closed, never a stale-fee send
        log({ ts: new Date().toISOString(), type: 'live_skip', asset, baseFeeGwei: Number(baseFeeWei) / 1e9, sim_result: `live base fee ${(Number(baseFeeWei) / 1e9).toFixed(4)} gwei not includable under fee cap (fail closed)` });
        return;
      }
      const dec = DEC_BY_BASE[base] || 6; // base-token units of the gas budget
      // gas budget in BASE-TOKEN units: an 18-dec base (WETH) is priced in raw
      // wei (gasLimit x maxFee IS the wei cost); a 6-dec base converts wei ->
      // ETH -> USD -> USDC units (1e6). Multiplying by 10**dec for WETH over-
      // stated the fee 2428x (review 6b61bdcb: 53796398644799990 vs 22156671600000 wei).
      const gasCostBaseWei = dec === 18 ? GAS_LIMIT * maxFee
        : BigInt(Math.floor(Number(GAS_LIMIT) * Number(maxFee) / 1e18 * ethUsd * 1e6));
      const worstCaseUsd = Number(GAS_LIMIT * maxFee) / 1e18 * ethUsd;
      const gross = proceedsWei > payBase ? proceedsWei - payBase : 0n; // gross base gain before gas
      const expected = Number(gross);
      // Enforced after-fee minimum: the on-chain minProfit INCLUDES the full
      // gas budget in base-token units, plus 80% of the margin above it, so a
      // successful tx is profitable after fees (margin 0.8*(gross-gas) >= 0).
      const minProfit = gross > gasCostBaseWei
        ? gasCostBaseWei + ((gross - gasCostBaseWei) * MIN_PROFIT_BPS) / 10000n
        : 0n;
      if (expected <= Number(gasCostBaseWei) || proceedsWei <= payBase) {
        log({ ts: new Date().toISOString(), type: 'no_edge', asset, pool, payBase: Number(payBase), expected, gasCostBaseWei: Number(gasCostBaseWei), note: 'discount below gas estimate' });
        return;
      }
      // flash principal: when base != USDC the executor flash-borrows payBase
      // base through the base->USDC UniV3 pool (PRINCIPAL=USDC) inside the tx;
      // price limits are OUR fresh ±5% read of that pool (executor clamps the
      // strict-interior endpoints; a >=5% intra-tx move reverts all).
      const wrapPool = (base.toLowerCase() !== USDC.toLowerCase() && POOL_MAP[base] && POOL_MAP[base][USDC]) || pool;
      let wrapLow = 0n, wrapHigh = 0n;
      if (wrapPool !== pool) {
        const wsq2 = await call(wrapPool, SEL.slot0);
        const sq2 = BigInt(word(wsq2, 0));
        // Strict-interior uint160 limits in EXACT BigInt (no Number(): a
        // sqrtPriceX96 near 1.6e33 exceeds Number.MAX_SAFE_INTEGER and the
        // old decimal-string encoding made enc() read the decimal digits as
        // hexadecimal words — review 9fe6b863 blocker 3). The executor clamps
        // the endpoints (MIN_SQRT_RATIO+1 / MAX_SQRT_RATIO-1).
        const lo = (sq2 * 95n) / 100n;
        wrapLow = lo < 4295128741n ? 4295128741n : lo; // strict floor above MIN_SQRT_RATIO
        const hi = (sq2 * 105n) / 100n;
        wrapHigh = hi > 1461446703485210103287273052203988822378723970341n ? 1461446703485210103287273052203988822378723970341n : hi;
      }
      const data = enc(SEL.buy, [
        cometKey.replace('0x', ''), asset.replace('0x', ''), pool.replace('0x', ''),
        payBase.toString(16), '0', minProfit.toString(16),
        wrapPool.replace('0x', ''), wrapLow, wrapHigh,
      ]);
      // executor identity: live = the gate-deployed EXECUTOR_ADDR (fail closed
      // without it); paper = the per-base funded placeholder discovered at
      // startup (real base balance >= 360, no balance override).
      const execAddr = MODE === 'live' ? EXECUTOR_ADDR
        : (EXEC_BY_BASE[base.toLowerCase()] || EXEC_PLACEHOLDER);
      const sim = { ts: new Date().toISOString(), type: 'simulate', asset, pool, comet: cometKey,
        exec: execAddr,
        payBase: Number(payBase), collOut: Number(collOut), proceedsEst: Number(proceedsWei),
        expectedProfit: expected, gasCostEst: Number(gasCostBaseWei), minProfit: Number(minProfit),
        worstCaseGasUsd: Number(worstCaseUsd.toFixed(3)), maxFee: Number(maxFee), baseFeeGwei: Number(baseFeeWei) / 1e9, ethUsd: Number(ethUsd.toFixed(2)), data,
        // measured window fields (review 3c9b5d18): poll_delay_s = event block ->
        // detection; alive_at_s = residual still available this long after its
        // absorb block at simulation time; est_incl_s adds the ~1 block (~12 s)
        // expected inclusion. Capture is feasible iff est_incl_s < the window a
        // reserve is measured to last (reserves_gone.gone_after_s events).
        blk, poll_delay_s: pollDelayS, alive_at_s: aliveS(Date.now()), est_incl_s: aliveS(Date.now()) + 12 };
      if (worstCaseUsd > MAX_LOSS_PER_TX_USD) {
        log({ ...sim, type: 'live_skip', sim_result: `worst-case gas bound ${worstCaseUsd.toFixed(2)} USD > ${MAX_LOSS_PER_TX_USD} (fail closed)` });
        return;
      }
      let simOk = false, simNote = '';
      try {
        if (MODE === 'live') {
          // live: verify deployed executor code + owner + funding before any call/send
          const wallet = await signerCall({ op: 'address' });
          const code = await rpc('eth_getCode', [execAddr, 'latest']);
          const me = wallet.ok ? addr(String(wallet.address)) : '';
          if (!wallet.ok || !me || !execAddr || code === '0x' || code === '0x00') {
            log({ ...sim, sim_result: 'live executor/signer not ready (fail closed)' }); return;
          }
          const ownerWord = await call(execAddr, SEL.execOwner, undefined, me); // deployed OWNER()
          if (addr(ownerWord) !== me) {
            log({ ...sim, sim_result: 'deployed OWNER != signer wallet (fail closed)' }); return;
          }
          // funding gate: 6-dec bases (principal == base) need base balance >=
          // payBase; the flash route (base = WETH) holds PRINCIPAL in USDC and
          // flash-borrows the base, so it needs USDC >= payBase's USDC value.
          if (base.toLowerCase() === USDC.toLowerCase()) {
            const execBal = u(await call(base, enc(SEL.balanceOf, [execAddr]))); // gate funding
            if (execBal < payBase) {
              log({ ...sim, sim_result: `executor base funding ${Number(execBal)} < payBase ${Number(payBase)} (fail closed)` }); return;
            }
          } else {
            const usdcNeed = BigInt(Math.floor(Number(payBase) / 1e18 * ethUsd * 1e6 * 1.0005));
            const execUsdc = u(await call(USDC, enc(SEL.balanceOf, [execAddr]))); // gate funds USDC
            if (execUsdc < usdcNeed) {
              log({ ...sim, sim_result: `executor USDC principal funding ${Number(execUsdc)} < need ${Number(usdcNeed)} (fail closed)` }); return;
            }
          }
          await call(execAddr, data, undefined, me); // no override: exact live bytes from our wallet
        } else {
          await call(execAddr, data, { [execAddr]: { code: RUNTIME_CODE } });
        }
        simOk = true; simNote = 'sim_ok';
      } catch (e) {
        simNote = 'sim_revert: ' + String(e.message).slice(0, 120);
      }
      if (simOk) { stats.sims_ok++; } else { stats.sims_rev++; }
      const out = { ...sim, sim_result: simNote };
      if (simOk && MODE === 'live') {
        const r = await signerCall({ op: 'send', chain: CHAIN, to: execAddr, data, value: '0x0',
          gas: '0x' + GAS_LIMIT.toString(16), maxFeePerGas: '0x' + maxFee.toString(16),
          maxPriorityFeePerGas: '0x' + (maxFee - BigInt(baseFeeWei)).toString(16) });
        out.send = r.ok ? 'sent ' + (r.txHash || r.tx || '').slice(0, 20) : 'rejected: ' + String(r.error || r.reason || '?').slice(0, 120);
      }
      log(out);
    } catch (e) {
      stats.errors++;
      log({ ts: new Date().toISOString(), type: 'error', where: 'trade', asset, error: String(e.message).slice(0, 200) });
    }
  }
}

main().catch((e) => { log({ ts: new Date().toISOString(), type: 'fatal', error: String(e.message) }); process.exit(1); });
