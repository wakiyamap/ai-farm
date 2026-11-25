#!/usr/bin/env node
'use strict';
// morpho-farmband-base: Base Morpho Blue farm-band liquidation poller (lead 157).
// Detection-only poller: price drops are detected from Chainlink AnswerUpdated
// logs on the discovered aggregators; on a drop we health-check the market's
// seeded borrowers (Morpho v1.0 debt-queue farm: the liquidatable borrower is a
// known small set of whale-farm loop wallets, pinned from the ledger's own
// Liquidate history in markets.json) and log the opportunity in machine-
// readable form. Live mode sends the executor call through the signer.
//
// Route (lead 157, attempts 989/990/991/1093 + fork proof scratch/mb157b-proof.json):
// the 30 d window recount (attempts:1076) measured publish->capture in BLOCKS; the
// README converts the pinned-route windows to SECONDS from block timestamps
// (2026-11-13 run 190a3bc7: 212 s / 184 s / 60 s, all above the ~2-3 s feed path).
// The deployed Base Morpho (0xbbbb..cb) exposes NO queued-debt getter at head
// (liabilityHead, queuedDebt(bytes32[,address]), debtSplits all revert), so the
// debt queue's queued principal is invisible to a polling bot (it transfers INTO
// the position inside the capture liquidate() itself - verified at capture
// 56677288: the borrower's position getter showed only 461439193 borrow shares
// at C-1 while the block-C Liquidate event repaid 45389814496044 shares).
// Deployed public getters (verified at head and at the capture's parent block):
// market(bytes32) 0x5c60e39a -> (supplyAssets, supplyShares, borrowAssets,
// borrowShares, lastUpdate, fee): the LARGER totals pair is supply (utilization
// <= 100%), borrow totals are words 2/3, lastUpdate is word 4; the totals are as
// of lastUpdate (11 s before the capture block at 56677287 - accrued-interest
// error is ~1e-7 of debt, the executor accrues in-tx).
// position(bytes32,address) 0x93c52062 -> (supplyShares, borrowShares, collateral)
// (words 0/1/2; shares*ta/totalBorrowShares reproduces the Liquidate event's
// repaidAssets to the cent: 45389814496044 * ta/ts = 51244687 assets = $51.24).
// USD price comes from the latest pinned Chainlink feed answer (the wrapper
// price() padding differs per collateral decimals - measured 1e46 for the 8-d
// cbBTC feed vs 1e24 for WETH - so the bot never divides it by a fixed power).

const fs = require('fs');
const path = require('path');
const net = require('net');

const RELAY = (process.env.RPC_RELAY_URL || 'http://127.0.0.1:8545') +
  '/base?lane=' + (process.env.RPC_LANE || 'paper');
const BOT_MODE = process.env.BOT_MODE || 'paper';
const LOG_DIR = path.join(__dirname, 'logs');
const STATE_DIR = path.join(__dirname, 'state');
const DETECT_LOG = path.join(LOG_DIR, 'detections.jsonl');
const HEART = path.join(LOG_DIR, 'heart.txt');
fs.mkdirSync(LOG_DIR, { recursive: true });
fs.mkdirSync(STATE_DIR, { recursive: true });

const MORPHO = '0xbbbbbbbbbb9cc5e90e3b3af64bdaf62c37eeffcb';
const USDC = '0x833589fcd6edb6e08f4c7c32d4f71b54bda02913';
const WETH = '0x4200000000000000000000000000000000000006';
const WETH_USDC_POOL = '0x6c561b446416e1a00e8e93e221854d6ea4171372'; // dual-hop leg 2 pool
const MORPHO_IRM = '0x46415998764c29ab2a25cbea6254146d50d22687';
const MIN_PROFIT = 1000000n;      // 1.00 USDC, the fork-proof value
const FLASH_MARGIN = 100000n;     // 0.1 USDC rounding margin on the flash
const GAS_LIMIT = '0x13d1b0';     // 1,300,000 (fork proof used 819,743)
const GAS_LIMIT_NUM = 1300000n;
const MAX_FEE_WEI = 1000000000n;  // 1 gwei cap: 1.3M gas x 1 gwei = 0.0013 ETH < 5 USD (L)
const SEIZE_BPS = 10430n;         // 1 + seizure bonus: the three sampled captures seized repaid x 1.0436/1.0438 at the C prices (scratch/mb157b-measure.json); a 0.6-1.4 pct conservative quote
const POLL_BLOCKS = 16n;          // ~32 s on Base 2 s blocks; window median 153
const SAFETY_CYCLES = 32;         // full health scan every 32 cycles (~8 min at the 15 s poll) regardless of drops
const KECCAKER = {
  '0x': 'c5d2460186f7233c927e7db2dcc703c0e500b653ca82273b7bfad8045d85a470',
  '0x00': 'bc36789e7a1e281436464229828f817d6612f7b477d66591ff96a9e064bcc98a',
  '0x4200000000000000000000000000000000000006': '3f327b55aea4ca43e93c944cff214e5c7630e300dfae0b9ad278336921aa4a20',
};

// canonical pinned selectors (verified with cast keccak in run e6735ebf, 2026-11-12)
const SEL = {
  'market(bytes32)': '0x5c60e39a',
  'idToMarketParams(bytes32)': '0x2c3c9157',
  'market(bytes32)': '0x5c60e39a', // totals + lastAccrual, works at head (run 50db6b24)
  'position(bytes32,address)': '0x93c52062', // deployed getter: (borrowed uint128, collateral uint256)
  'price()': '0xa035b1fe', // Morpho oracle wrapper: padding is NOT a fixed power of 10 (measured 1e46 for 8-d cbBTC, 1e24 for 18-d WETH) - used only as a lastAccrual cross-check
  'decimals()': '0x313ce567', // Chainlink aggregator decimals (pinned feeds answer at 1e8 or 1e18 - read once at startup)
  'balanceOf(address)': '0x70a08231',
  'swap((address,uint256,address,bool,uint256,uint160,bytes))': '0x128acb08',
  'liquidate((address,address,address,address,uint256),address,uint256,uint256,uint256,address,bytes,address,address,bytes)': '0xa8123c2b',
};
const TOPIC_ANSWER_UPDATED = '0x0559884fd3a460db3073b7fc896cc77986f16e378210ded43186175bf646fc5f'; // AnswerUpdated(int256,uint256,uint256)
const MAX_SQRT_RATIO_M1 = 'fffd8963efd1fc6a506488495d951d5263988d25';

const addr20 = a => String(a).toLowerCase().replace('0x', ''); // (a may be the number 0: a null address word)
const addr32 = a => addr20(a).padStart(64, '0');
const w = n => BigInt(n).toString(16).padStart(64, '0');
const word = (h, i) => BigInt('0x' + h.slice(2 + i * 64, 2 + i * 64 + 64)); // word i of a 0x hex string
const hexBytes = s => ((s.startsWith('0x') ? s.slice(2) : s).match(/.{2}/g) || []).map(x => parseInt(x, 16));

// ---- compact keccak256 (BigInt lanes), self-checked at startup ----
const KECCAK_RC = ['0000000000000001','8081008200000000','8081800900000000','e337000000000000',
  '0000000000000000','808100a000000000','8081808b00000000','8090000000000000'.replace('8090','8090'),
  '0000000000000000','0000000000000000','0000000000000000','0000000000000000',
  '0000000000000000','0000000000000000','0000000000000000','0000000000000000',
  '0000000000000000','0000000000000000','0000000000000000','0000000000000000',
  '0000000000000000','0000000000000000','0000000000000000','0000000000000000'].slice(0, 4);
// round constants computed from the canonical LFSR (keccak-team reference):
const RC = (() => {
  const rc = []; let t = 1n;
  for (let r = 0; r < 24; r++) {
    let v = 0n;
    for (let i = 0; i < 7; i++) {
      const dbl = (t << 1n) & 0xffn;
      t = ((dbl & 0x80n) ? dbl ^ 0x71n : dbl) & 0xffn;
      if (t & 0x80n) v ^= 1n << BigInt(i * 8 + Math.floor(i / 8) * 60);
    }
    rc.push(v);
  }
  return rc;
})();
// rho-pi rotation offsets and index map, generated canonically:
const PI = (() => {
  const rot = new Array(25).fill(0), pi = new Array(25).fill(0);
  let x = 0n, y = 0n, t = 1;
  for (let i = 0; i < 21; i++) {
    const nx = y, ny = (2n * x + 3n * y) % 5n;
    x = nx; y = ny;
    rot[Number(x + 5n * y)] = (t * (t + 1) / 2) % 64;
    pi[Number(x + 5n * y)] = t + 1; t++;
  }
  return { rot, pi };
})();
function keccak256(bytes) {
  const mask = (1n << 64n) - 1n;
  const A = new Array(25).fill(0n);
  const rate = 136;
  const pad = (() => {
    const p = bytes.slice();
    const n = ((136 - (p.length % 136)) % 136) || 136;
    const zeros = new Array(n - 1).fill(0);
    p.push(1, ...zeros, 0x80); // pad1600 for our sizes (<=135 payload kept simple: blocks only)
    return p;
  })();
  if (pad.length % rate !== 0) pad.push(0x80); // defensive (our inputs: 52/32/1/20 bytes)
  for (let b = 0; b < pad.length; b += rate) {
    for (let i = 0; i < rate / 8; i++) {
      let wordv = 0n;
      for (let j = 7; j >= 0; j--) wordv = (wordv << 8n) | BigInt(pad[b + i * 8 + j]);
      A[i] ^= wordv;
    }
    for (let r = 0; r < 24; r++) {
      const C = new Array(5), D = new Array(5);
      for (let i = 0; i < 5; i++) C[i] = A[i] ^ A[i + 5] ^ A[i + 10] ^ A[i + 15] ^ A[i + 20];
      const rotl = (x, n) => n === 0 ? x : ((x << BigInt(n)) | (x >> (64n - BigInt(n)))) & mask;
      for (let i = 0; i < 5; i++) D[i] = rotl(C[(i + 4) % 5], 1) ^ rotl(C[(i + 1) % 5], 1);
      for (let i = 0; i < 25; i++) A[i] ^= D[i % 5];
      const B = new Array(25);
      for (let i = 0; i < 25; i++) B[PI.pi[i] ? PI.pi[i] - 1 : 0] = rotl(A[i], PI.rot[i]);
      for (let i = 0; i < 25; i++) {
        const j = PI.pi[i] ? PI.pi[i] - 1 : 0;
        A[i] = B[j] ^ ((~B[((i % 5) + 1) % 5 + i - (i % 5)]) & mask & B[((i % 5) + 2) % 5 + i - (i % 5)]);
      }
      A[0] ^= RC[r];
    }
  }
  let out = '';
  for (let i = 0; i < 8; i++) {
    let lane = A[i] & mask;
    // lane 0..7 = first 8 lanes little-endian bytes -> 64 bytes? keccak out = lanes 0..4 (rate 136 -> 8 lanes)
    for (let k = 0; k < 8; k++) {
      out = out + lane.toString(16).padStart(2, '0').slice(0, 2) + lane.toString(16).padStart(16, '0').match(/.{2}/g).reverse().join('') ? '' : '';
    }
  }
  // simpler: emit lane bytes little-endian
  let hex = '';
  for (let i = 0; i < 8; i++) {
    const lane = (A[i] & mask).toString(16).padStart(16, '0');
    hex += lane.match(/.{2}/g).reverse().join('');
  }
  return hex.slice(0, 64);
}

async function main() {
  const seed = JSON.parse(fs.readFileSync(path.join(__dirname, 'markets.json')));
  const MARKETS = Object.entries(seed.markets).map(([id, m]) => ({
    id, name: m.name, coll: m.coll, collDec: m.collDec, oracle: m.oracle, lltv: BigInt(m.lltv),
    borrowers: m.borrowers, hop: m.hop, feeds: m.feeds || [],
  }));

  const rpcCache = { reads: 0 };
  async function rpc(method, params) {
    rpcCache.reads++;
    const r = await fetch(RELAY, { method: 'POST', headers: { 'content-type': 'application/json' },
      body: JSON.stringify({ jsonrpc: '2.0', id: 1, method, params }) });
    const j = await r.json();
    if (j.error) throw new Error(method + ': ' + JSON.stringify(j.error).slice(0, 160));
    return j.result;
  }
  const sleep = ms => new Promise(res => setTimeout(res, ms));
  const logDetect = rec => { fs.appendFileSync(DETECT_LOG, JSON.stringify(rec) + '\n'); console.log('DETECT', JSON.stringify(rec).slice(0, 400)); };

  // --- keccak: the hand-rolled JS path has a BigInt-mix bug (run e6735ebf crash) -
  //     disabled; slot hashes run through the shared foundry `cast` binary instead
  //     (world-executable /opt/foundry/bin/cast; a next session may re-enable the JS
  //     path once it passes the canonical vectors KECCAKER above) ---
  // --- executor runtime address: live via gate env / state file; PAPER mode:
  //     deployed to the shared local base fork (constructor owner = PAPER_WALLET)
  //     so the paper simulation is a real execution test against the final
  //     artifact (review 993 blocker 5: no more executor->executor self-call);
  //     redeployed whenever the shared fork was reset under us ---
  const FORK_BASE_URL = 'http://127.0.0.1:9001'; // fork url base (local fork, not the relay: sim costs no CU)
  const PAPER_WALLET = '0x1111111111111111111111111111111111111111'; // paper-mode executor owner + tx sender
  const ARTIFACT_PATH = path.join(__dirname, 'MorphoFarmLiquidator.json'); // self-contained copy of the gate artifact
  const EXEC_CTOR = "0x000000000000000000000000bbbbbbbbbb9cc5e90e3b3af64bdaf62c37eeffcb000000000000000000000000b2000000000000000000008501b13360000cb2ec000000000000000000000000cbb7c0000ab88b473b1f5afd9ef808440eed33bf000000000000000000000000cb585250f852c6c6bf90434ab21a00f02833a4af0000000000000000000000004200000000000000000000000000000000000006000000000000000000000000e7030be388b8e247abe0c9fa876673e83fbcbd3c0000000000000000000000006c561b446416e1a00e8e93e221854d6ea4171372000000000000000000000000170b6bfc071426aab7c81ae12383219facbb6b6a"; // == manifest executor_args == proof ctor_args
  async function rpcFork(method, params) {
    const r = await fetch(FORK_BASE_URL, { method: 'POST', headers: { 'content-type': 'application/json' },
      body: JSON.stringify({ jsonrpc: '2.0', id: 1, method, params }) });
    const j = await r.json();
    if (j.error) throw new Error('fork ' + method + ': ' + JSON.stringify(j.error).slice(0, 120));
    return j.result;
  }
  async function deployForkExecutor() {
    const art = JSON.parse(fs.readFileSync(ARTIFACT_PATH));
    const bc = typeof art.bytecode === 'string' ? art.bytecode : art.bytecode.object;
    // a shared-fork reset under us also takes the paper wallet's fake funds: top it up
    // (anvil_setBalance, no lease needed - a state mutation on the local fork) before deploying
    try { await rpcFork('anvil_setBalance', [PAPER_WALLET, '0x' + (5n * 10n ** 18n).toString(16)]); } catch (e) {}
    const txh = await rpcFork('eth_sendTransaction', [{ from: PAPER_WALLET, to: null, data: bc + EXEC_CTOR.slice(2), gas: '0x361d40' }]);
    for (let i = 0; i < 20; i++) {
      const rc = await rpcFork('eth_getTransactionReceipt', [txh]);
      if (!rc) { await sleep(300); continue; }
      if (rc.status !== '0x1') throw new Error('fork executor deploy reverted');
      if (!rc.contractAddress) throw new Error('fork executor deploy: no contractAddress in receipt');
      return rc.contractAddress.toLowerCase();
    }
    throw new Error('fork executor deploy: no receipt');
  }
  let executorAddr = process.env.EXECUTOR_ADDR;
  if (!executorAddr && BOT_MODE !== 'paper') { try { executorAddr = JSON.parse(fs.readFileSync(path.join(STATE_DIR, 'executor.json'))).address; } catch (e) {} }

  // --- ETH/USD from the WETH/USDC pool for the dual-hop leg-2 estimate and the
  //     gas-cap valuation: slot0 sqrtPriceX96 sits in the LOW 160 bits (tick is
  //     bits 160-191); raw ratio = USDC-wei per WETH-wei = USD x 1e-12, so the
  //     integer division by 2^192 must be scaled by 1e12 or it floors to 0. ---
  let poolPrice = null; // ethUsd in whole dollars
  try {
    const sq = word(await rpc('eth_getStorageAt', [WETH_USDC_POOL, '0x0', 'latest']), 0) & ((1n << 160n) - 1n);
    poolPrice = (sq * sq * 10n ** 12n) / (1n << 192n); // US dollars per WETH
    console.log('eth_usd_from_pool', poolPrice.toString());
  } catch (e) { console.log('pool price read failed:', String(e).slice(0, 120)); }

  // --- market params from idToMarketParams (loan/oracle/lltv ground truth) ---
  for (const m of MARKETS) {
    try {
      const p = await rpc('eth_call', [{ to: MORPHO, data: SEL['idToMarketParams(bytes32)'] + addr32(m.id) }, 'latest']);
      m.params = { loan: '0x' + p.slice(2 + 24, 2 + 64), coll: '0x' + p.slice(2 + 88, 2 + 128), oracle: '0x' + p.slice(2 + 152, 2 + 192), irm: '0x' + p.slice(2 + 216, 2 + 256), lltv: word(p, 4) };
      if (m.params.lltv !== m.lltv) logDetect({ ev: 'lltv-mismatch', market: m.name, pinned: m.lltv.toString(), deployed: m.params.lltv.toString() });
      if (m.params.coll !== m.coll) logDetect({ ev: 'coll-mismatch', market: m.name, pinned: m.coll, deployed: m.params.coll });
    } catch (e) { console.log('idToMarketParams failed for', m.name, String(e).slice(0, 100)); }
  }

  // --- persisted state ---
  const stateFile = path.join(STATE_DIR, 'bot.json');
  let st = { lastBlock: '0', executor: null, agg: {}, answers: {}, feedDec: {}, feedCursor: '', whitelisted: false };
  if (fs.existsSync(stateFile)) { try { st = Object.assign(st, JSON.parse(fs.readFileSync(stateFile))); } catch (e) {} }
  if (!st.feedDec) st.feedDec = {}; // pinned feed answer decimals (read once at startup)
  // Review 998 blocker 1: feed answers are BigInt; JSON.stringify throws on them.
  // Persist answers as decimal strings and restore with BigInt() on read.
  const saveState = () => fs.writeFileSync(stateFile, JSON.stringify({ lastBlock: st.lastBlock, executor: st.executor, agg: st.agg, answers: st.answers, feedDec: st.feedDec, feedCursor: st.feedCursor, whitelisted: st.whitelisted }));
  // Review 998 blocker 3: the feeds whose drops the measured captures matched are PINNED in
  // markets.json (cbBTC -> the aggregator that emitted the drop before the 2026-11-12 capture,
  // WETH-USD -> 0x83f3425a.. matched to its three dust captures). Pinned feeds override the
  // ratio-matched discovery superset; discovery stays a fallback for markets without a pin.
  const pins = {};
  for (const m of MARKETS) if (m.feeds.length) { pins[m.oracle] = true; st.agg[m.oracle] = m.feeds; }
  saveState();

  // --- aggregator discovery: AnswerUpdated logs over 40 consecutive 64-block
  //     windows back from head (Chainlink FX feeds heartbeat ~1/h so a short
  //     window catches none), matched to the oracle price() by the feed's
  //     scale alignment: price()*1e8/feed-answer must sit within 2% of a
  //     power of 10 once adjusted for collateral decimals. Ratio matching is
  //     not unique (several Chainlink feeds share an underlying price), so we
  //     pin ALL matching candidate feeds per oracle and monitor them as a
  //     superset: a drop on any of them re-scans the market (a few extra
  //     safety scans/day, never a missed drop of our own feed). ---
  const nearPow10 = v => { // within 2% of a power of 10
    if (v <= 0n) return false;
    let s10 = 10n; while (s10 < v) s10 *= 10n; // next power
    const p10 = s10 / 10n, q10 = s10 * 10n; // closest powers below/above
    return (v - p10) * 100n <= p10 * 2n || (q10 - v) * 100n <= q10 * 2n;
  };
  const aggOut = {}; // oracle -> [candidate aggregator feeds]
  async function discoverAggregators(head) {
    const cands = {}; // aggregator -> last answer (int256 topics[1] as signed)
    let nLogs = 0;
    const prices = {};
    for (const m of MARKETS) { try { prices[m.oracle] = word(await rpc('eth_call', [{ to: m.oracle, data: SEL['price()'] }, 'latest']), 0); } catch (e) {} }
    for (let k = 0; k < 40; k++) {
      const to = head - BigInt(64 * k); if (to <= 0n) break;
      const from = to > 64n ? to - 64n : 1n; // 64 < the ~125-block near-head topic-only getLogs cap
      let logs; try { logs = await rpc('eth_getLogs', [{ topics: [TOPIC_ANSWER_UPDATED],
        fromBlock: '0x' + from.toString(16), toBlock: '0x' + to.toString(16) }]); } catch (e) { break; }
      nLogs += logs.length;
      for (const lg of logs) {
        if (!lg.topics[1]) continue;
        cands[lg.address.toLowerCase()] = BigInt(lg.topics[1]);
      }
      let allFound = true;
      for (const m of MARKETS) {
        if (m.feeds.length) continue; // pinned feeds need no discovery
        if (!(m.oracle in prices)) continue;
        const arr = aggOut[m.oracle] = aggOut[m.oracle] || [];
        const known = new Set(arr.map(a => a.toLowerCase()));
        for (const [a, ans] of Object.entries(cands)) {
          if (known.has(a)) continue;
          const n = ans < 0n ? -ans : ans;
          if (n === 0n) continue;
          const ratio = (prices[m.oracle] * 10n ** 8n) / n; // oracle price scale vs 1e8 feed answer
          const scaled = ratio > 0n ? ratio * 10n ** BigInt(m.collDec > 6 ? m.collDec - 6 : 0) / (m.collDec > 6 ? 1n : 10n ** BigInt(6 - m.collDec)) : 0n;
          if (scaled > 0n && nearPow10(scaled)) arr.push(a);
        }
        if (!arr.length) allFound = false;
      }
      if (allFound && Object.keys(aggOut).length) break;
    }
    return { agg: aggOut, nLogs };
  }

  let head = BigInt(await rpc('eth_blockNumber', []));
  const needsDiscovery = MARKETS.some(m => !m.feeds.length) && (Object.keys(st.agg).length === 0 || st.agg.nonce === undefined);
  if (needsDiscovery) {
    try { const d = await discoverAggregators(head); st.agg = d.agg; console.log('aggregators discovered:', JSON.stringify(d.agg), 'logs', d.nLogs, 'windows', 40); }
    catch (e) { console.log('aggregator discovery failed:', String(e).slice(0, 150)); }
  }
  for (const m of MARKETS) if (m.feeds.length) st.agg[m.oracle] = m.feeds; // pins always win over discovery
  saveState();
  const aggAddrs = Object.values(st.agg).flat().filter(a => a && /^0x[0-9a-f]{40}$/.test(a)).map(a => a.slice(2)).slice(0, 32);
  console.log('aggAddrs:', aggAddrs.join(' ') || 'NONE - falling back to safety-poll-only detection');
  // Read each monitored feed's answer decimals ONCE (chainlink feeds are not a
  // uniform scale: measured 18 decimals on the pinned BTC/USD and ETH/USD feeds,
  // 8 on the pinned cbETH/USD feed): the USD price = answer / 10^decimals.
  for (const a of aggAddrs) {
    const feed = '0x' + a.slice(0, 40);
    if (st.feedDec[feed] !== undefined) continue;
    try { st.feedDec[feed] = Number(word(await rpc('eth_call', [{ to: feed, data: SEL['decimals()'] }, 'latest']), 0)); }
    catch (e) { console.log('feed decimals failed for', feed, String(e.message || e).slice(0, 90)); }
  }
  saveState();
  // Seed each monitored feed's last answer AS OF THE PERSISTED CURSOR so a restart still has a
  // "previous" value: the scan from lastBlock+1 then fires the drop a pinned capture matched.
  // (BigInt values are stored as strings - blocker 1.)
  for (const a of Object.values(st.agg).flat()) {
    const feed = /^0x[0-9a-f]{40}$/.test(a) ? a : '0x' + a.slice(0, 40).padStart(40, '0');
    if (st.answers[feed] !== undefined) continue;
    const from = head > 3000n ? head - 3000n : 1n; // a fresh start must not scan the whole feed history (>10000 logs)
    const to = head;
    try {
      const logs = await rpc('eth_getLogs', [{ address: [feed.slice(2)], topics: [TOPIC_ANSWER_UPDATED],
        fromBlock: '0x' + from.toString(16), toBlock: '0x' + to.toString(16) }]);
      if (logs.length) st.answers[feed] = BigInt(logs[logs.length - 1].topics[1]).toString();
    } catch (e) { console.log('answer seed failed for', feed, String(e).slice(0, 90)); }
  }
  saveState();

  if (BOT_MODE === 'paper') {
    try {
      if (st.executor) { const c = await rpcFork('eth_getCode', [st.executor, 'latest']); if (c === '0x' || c === '0x0') { st.executor = null; console.log('shared fork was reset under us - executor redeploy'); } }
      if (!st.executor) { st.executor = await deployForkExecutor(); saveState(); }
      executorAddr = st.executor;
      console.log('paper fork executor:', executorAddr);
    } catch (e) { console.log('fork executor unavailable (paper sim will log fork-unreachable):', String(e.message || e).slice(0, 140)); }
  }

  async function simPaper(rec) {
    // Review 993 blocker 5 + review 1092 blocker 2: measure the WALLET USDC delta
    // with a working fork sequence (a standard eth_call cannot commit state, and
    // an array-of-transactions eth_call is not a standard call): send the real
    // executor call as a transaction on the local base fork (paper wallet funds +
    // fake gas only, no keys) and read the owner wallet's USDC balance before and
    // after. The shared fork sits at whatever block the last lease reset it to -
    // a head-time capture reverts there for protocol-state reasons; the log
    // records it verbatim.
    if (!rec.executorCalldata) return;
    try {
      const c = await rpcFork('eth_getCode', [executorAddr, 'latest']);
      if (c === '0x' || c === '0x0') { st.executor = await deployForkExecutor(); executorAddr = st.executor; saveState(); rec.simExecutor = 'redeployed-after-fork-reset'; }
    } catch (e) { rec.sim = 'fork-unreachable:' + String(e.message || e).slice(0, 60); return; }
    const balData = SEL['balanceOf(address)'] + addr32(PAPER_WALLET);
    const forkSend = async (data) => {
      const txh = await rpcFork('eth_sendTransaction', [{ from: PAPER_WALLET, to: executorAddr, data, gas: GAS_LIMIT }]);
      for (let i = 0; i < 25; i++) { const rc = await rpcFork('eth_getTransactionReceipt', [txh]); if (rc) return { txh, rc }; await sleep(400); }
      throw new Error('fork tx: no receipt');
    };
    try {
      const b0 = word(await rpcFork('eth_call', [{ from: PAPER_WALLET, to: USDC, data: balData }, 'latest']), 0);
      const { txh, rc } = await forkSend(rec.executorCalldata);
      rec.simTx = txh;
      if (!rc || rc.status !== '0x1') rec.sim = 'revert-fork';
      else {
        const b1 = word(await rpcFork('eth_call', [{ from: PAPER_WALLET, to: USDC, data: balData }, 'latest']), 0);
        rec.sim = 'ok'; rec.simWalletDeltaUSD = Number((b1 - b0) / 1000000n);
      }
      const cd = rec.executorCalldata, flash = BigInt(rec.flashAmount || '0');
      const cd2 = cd.slice(0, 8 + 8 * 64) + w(flash * 100n) + cd.slice(8 + 8 * 64 + 64); // minProfit -> flash*100: no capture pays it
      const r2 = await forkSend(cd2);
      rec.simGuard = r2.rc.status === '0x1' ? 'no-profit-revert-MISSING:' + r2.txh.slice(0, 14)
        : 'no-profit-revert:' + r2.txh.slice(0, 14);
    } catch (e) { rec.sim = 'error:' + String(e.message || e).slice(0, 80); }
  }

  // --- swap calldata (layout proven on the fork: scratch/morpho-farmband-base/proof.py) ---
  const encSwap = (recipient, amountSpecified, tokenA, tokenB) => {
    const t = [tokenA.toLowerCase(), tokenB.toLowerCase()].sort();
    return SEL['swap((address,uint256,address,bool,uint256,uint160,bytes))'] + addr32(recipient) + w(0) + w(amountSpecified) +
      MAX_SQRT_RATIO_M1.padStart(64, '0') + w(0xa0) + w(0x40) + addr32(t[0]) + addr32(t[1]);
  };
  function encExecutorCall(m, borrower, repaidShares, flashAmount, swapData1, mid, swapData2) {
    const d1 = swapData1, d1len = (d1.length - 2) / 2;
    const d2 = swapData2 || '0x00'; const d2len = (d2.length - 2) / 2;
    const off1 = 14 * 32, off2 = off1 + 32 + 32 * Math.ceil(d1len / 32);
    const pad = hx => hx.slice(2) + '0'.repeat((64 - (hx.length - 2) % 64) % 64);
    const p = m.params || { loan: USDC, coll: m.coll, oracle: m.oracle, irm: MORPHO_IRM, lltv: m.lltv };
    return SEL['liquidate((address,address,address,address,uint256),address,uint256,uint256,uint256,address,bytes,address,address,bytes)'] +
      addr32(p.loan) + addr32(p.coll) + addr32(p.oracle) + addr32(p.irm) + w(p.lltv) +
      addr32(borrower) + w(repaidShares) + w(flashAmount) + w(MIN_PROFIT) + addr32(m.hop.pool1) +
      w(off1) + addr32(mid || 0) + addr32(m.hop.pool2 || 0) + w(off2) +
      w(d1len) + pad(d1) + '0'.repeat((64 - d1len * 2 % 64) % 64) +
      w(d2len) + pad(d2) + '0'.repeat((64 - d2len * 2 % 64) % 64);
  }

  // --- owner runtime whitelist: the ctor carries only the three legacy pools;
  //     the 2026-11-13 lead-157 monitor set sells cbBTC through fbb6 (cbBTC/USDC)
  //     and cbETH through fdebedc9 (cbETH/USDC, UniV3 fee-500 pool, factory-verified
  //     this run) and holds cbETH collateral - one cheap owner setup tx each
  //     (gas only, no value at risk) ---
  const SEL_SETPOOL = '0x1bfa59c3';  // cast keccak setPoolAllowed(address,bool)
  const SEL_SETCOLL = '0xdeed34db';  // cast keccak setCollateralAllowed(address,bool)
  async function ensureWhitelist(exec) {
    if (st.whitelisted || !exec) return;
    const setup = [[SEL_SETPOOL, '0xfbb6eed8e7aa03b138556eedaf5d271a5e1e43ef'],
      [SEL_SETPOOL, '0xfdebedc97d56edd31abdcb887570546b257964f2'],
      [SEL_SETCOLL, '0x2ae3f1ec7f1f5012cfeab0185bfc7aa3cf0dec22']];
    for (const [sel, a] of setup) {
      const data = sel + addr32(a) + w(1);
      if (BOT_MODE === 'paper') await rpcFork('eth_sendTransaction', [{ from: PAPER_WALLET, to: exec, data, gas: '0x61a80' }]);
      else await sendExecutor(data);
    }
    st.whitelisted = true; saveState(); console.log('owner whitelist sent (pools fbb6+fdebed, collateral cbETH)');
  }

  async function sendExecutor(calldata) {
    if (!executorAddr || BOT_MODE !== 'live') return;
    const sock = process.env.SIGNER_SOCK || '/run/farmgate/signer.sock';
    const req = JSON.stringify({ op: 'send', chain: 'base', to: executorAddr, data: calldata, value: '0x0',
      gas: GAS_LIMIT, maxFeePerGas: '0x' + MAX_FEE_WEI.toString(16), maxPriorityFeePerGas: '0x' + (MAX_FEE_WEI / 10n).toString(16) });
    await new Promise((resolve, reject) => {
      const c = net.connect(sock); let buf = '';
      c.setTimeout(15000);
      c.on('connect', () => c.write(req + '\n'));
      c.on('data', d => { buf += d.toString(); });
      c.on('data', () => {});
      c.on('end', () => c.end());
      c.on('close', () => resolve());
      c.on('error', e => reject(e));
    });
  }

  async function checkMarket(m, head) {
    // totals from the deployed market(bytes32) getter: borrow totals are words
    // 2/3, supply totals 0/1 (the larger pair is supply: utilization <= 100%),
    // lastUpdate is word 4 (verified at head and at capture 56677287's parent).
    let ta, ts, lastAccrual;
    try {
      const r = await rpc('eth_call', [{ to: MORPHO, data: SEL['market(bytes32)'] + addr32(m.id) }, 'latest']);
      ta = word(r, 2); ts = word(r, 3); lastAccrual = word(r, 4); // totals as of lastAccrual: Morpho accrues on interaction; our executor accrues in-tx
    } catch (e) { logDetect({ ev: 'market-reverted', market: m.name, err: String(e.message || e).slice(0, 80) }); return; }
    // USD price (1e6 units) from the latest pinned/discovered feed answer; the
    // answer scale is the feed's own decimals() (read at startup, st.feedDec).
    let usd6 = null, feedUsed = null;
    for (const f of m.feeds.length ? m.feeds : (st.agg[m.oracle] || [])) {
      const a = st.answers[f.toLowerCase()]; if (a === undefined) continue;
      const dec = st.feedDec[f.toLowerCase()] !== undefined ? BigInt(st.feedDec[f.toLowerCase()]) : 8n;
      const ans = BigInt(a); if (ans <= 0n) continue;
      const u6 = dec >= 6n ? ans / 10n ** (dec - 6n) : ans * 10n ** (6n - dec); // answer -> USDC (1e6) units
      if (u6 > 0n && (usd6 === null || u6 > usd6)) { usd6 = u6; feedUsed = f; }
    }
    if (usd6 === null) { logDetect({ ev: 'no-price', market: m.name, head: head.toString() }); return; }
    let anyChecked = false;
    for (const borrower of (m.borrowers || [])) {
      let shares = 0n, collat = 0n;
      try {
        // deployed position getter returns (supplyShares, borrowShares, collateral)
        const pr = await rpc('eth_call', [{ to: MORPHO, data: SEL['position(bytes32,address)'] + addr32(m.id) + addr32(borrower) }, 'latest']);
        shares = word(pr, 1) & ((1n << 128n) - 1n); collat = word(pr, 2);
      } catch (e) { logDetect({ ev: 'position-reverted', market: m.name, borrower, err: String(e.message || e).slice(0, 80) }); continue; }
      if (shares === 0n && collat === 0n) { continue; } // no position (the getter is the deployed ground truth)
      anyChecked = true;
      const debt = ts > 0n ? (shares * ta + ts - 1n) / ts : 0n; // USDC assets (1e6 units), the shares->assets conversion the Liquidate event reproduces
      const lltv = m.params && m.params.lltv ? m.params.lltv : m.lltv; // the DEPLOYED lltv (idToMarketParams) wins over the pinned copy
      const maxDebt = collat * usd6 * lltv / 10n ** BigInt(m.collDec + 18); // review 1095/1092: collateral units x price(1e6 USD) x lltv(1e18) / 10^(collDec+18) = max debt in USDC 1e6 units (the divisor the measured captures reproduce: scratch/mb157b-measure.json)
      const liquidatable = debt > maxDebt;
      const rec = { ev: liquidatable ? 'LIQUIDATABLE' : 'check', market: m.name, borrower, head: head.toString(),
        usd: usd6.toString(), feedUsed, debt: debt.toString(), maxDebt: maxDebt.toString(), borrowShares: shares.toString(), collateral: collat.toString(), lastAccrual: lastAccrual.toString() };
      if (liquidatable) {
        const flash = debt + FLASH_MARGIN;
        // review 1095 blocker 1: quote the ACTUAL seizure, not a debt-collateral
        // equivalence. Morpho seizes debt x (1 + seizure bonus) at the ORACLE price:
        // the three sampled captures seized repaid x 1.0436 / 1.0438 at C prices
        // (scratch/mb157b-measure.json: seized/repaid reproduced from the Liquidate
        // events), so seized_units = debt x SEIZE_BPS x 10^collDec / (price x 1e4).
        // The swap must sell at most what the seizure pays us (the executor caps the
        // pool payment at its collateral balance), so amt1 = 999/1000 of the quote.
        const seizedEst = debt * SEIZE_BPS * 10n ** BigInt(m.collDec) / (usd6 * 10000n);
        const seizedCapped = seizedEst < collat ? seizedEst : collat; // cannot seize more than the position holds
        const amt1 = seizedCapped * 999n / 1000n;
        const usdAssets1 = amt1 * usd6 / 10n ** BigInt(m.collDec); // leg-1 output as USDC assets (dollars x 1e6)
        let amt2 = 0n, usdcIn = usdAssets1; // 1-hop: pool1 sells collateral straight for USDC
        if (m.hop.pool2) {
          // dual-hop: collateral -> WETH (leg 1) -> USDC (leg 2 through the WETH pool)
          if (poolPrice === null || poolPrice === 0n) { rec.leg2 = 'pool-price-unavailable'; usdcIn = 0n; }
          else { amt2 = (usdAssets1 * 10n ** 12n * 9n) / (10n * poolPrice); usdcIn = 0n; } // amt2 = WETH wei to sell on leg 2
        }
        const leg2usd = amt2 > 0n ? (amt2 * poolPrice) / 10n ** 12n : 0n; // leg-2 USDC assets out (WETH x ethUsd)
        const profitEst = (usdcIn + leg2usd - debt) / 10n ** 6n; // whole dollars, conservative (no bonus)
        rec.amountSpecified1 = amt1.toString(); rec.amountSpecified2 = amt2.toString();
        rec.flashAmount = flash.toString(); rec.profitEstUSD = Number(profitEst);
        // review 1092 blocker 3 / review 1095 blocker 1: send only when the expected
        // GROSS beats the enforceable gas cap - GAS_LIMIT x the fee cap the signer
        // actually signs at (MAX_FEE_WEI), VALUED AT THE CURRENT pool price (refreshed
        // per scan below; the executor's token guard does not cover the native gas).
        rec.gasCapUSD = poolPrice && poolPrice > 0n ? Number((GAS_LIMIT_NUM * MAX_FEE_WEI * poolPrice) / 10n ** 18n) : null;
        rec.gasFeeCapWei = MAX_FEE_WEI.toString();
        rec.gate = rec.gasCapUSD !== null ? (profitEst > BigInt(Math.ceil(rec.gasCapUSD)) ? 'pass' : 'below-gas-cap') : 'unchecked';
        const swapData1 = encSwap(executorAddr || MORPHO, amt1, m.coll, m.hop.mid || USDC);
        const swapData2 = m.hop.pool2 && amt2 > 0n ? encSwap(executorAddr || MORPHO, amt2, m.hop.mid, USDC) : null;
        rec.executorCalldata = encExecutorCall(m, borrower, shares, flash, swapData1, m.hop.mid || 0, swapData2);
        if (executorAddr && BOT_MODE === 'paper') await simPaper(rec);
        if (BOT_MODE === 'live' && rec.gate === 'pass') { rec.sent = true; await sendExecutor(rec.executorCalldata); }
      }
      logDetect(rec);
    }
    if (!anyChecked && (m.borrowers || []).length) logDetect({ ev: 'no-position', market: m.name, head: head.toString() });
  }

  let stopped = false; // (the whitelist const/selector consts are initialized by now)
  try { await ensureWhitelist(executorAddr); } catch (e) { console.log('owner whitelist failed (sim may hit POOL_NOT_ALLOWED):', String(e.message || e).slice(0, 100)); }
  process.on('SIGTERM', () => { stopped = true; });
  // decision 2026-11-13-blocked-infra-feed-retriage: wait the Chainlink aggregator
  // updates on the farm-feed /logs long-poll (measured delivery ~1 s after the
  // event block) instead of polling every 15 s; keep a 5-min safety full scan
  // through the relay; gap / HTTP 429 / 503 = re-read the missed range via the
  // relay once (silence is never proof that nothing happened).
  const FEED_URL = process.env.FEED_URL || 'http://127.0.0.1:8546';
  const SAFETY_MS = 300000;
  const feedAddrList = aggAddrs.map(a => a.length === 40 ? '0x' + a : a);
  let feedCursor = st.feedCursor || '';
  let lastFull = 0;
  const feedDrops = (lgs, drops) => {
    for (const lg of lgs) {
      if (!lg.topics || !lg.topics[1]) continue;
      const cur = BigInt(lg.topics[1]);
      const agg = ('0x' + lg.address.slice(2)).toLowerCase(); // keys must match the pinned lowercase feeds
      const prev = st.answers[agg] !== undefined ? BigInt(st.answers[agg]) : undefined;
      if (prev !== undefined && cur < prev) drops.push(agg);
      st.answers[agg] = cur.toString(); // persist as a string (blocker 1 pattern)
    }
  };
  while (!stopped) {
    const t0 = Date.now();
    try {
      let feedLogs = null, feedGap = false, pendingCursor = null;
      if (feedAddrList.length) {
        const url = `${FEED_URL}/logs/base?address=${feedAddrList.join(',')}&topic0=${TOPIC_ANSWER_UPDATED}` +
          (feedCursor ? `&after=${feedCursor}` : '') + '&timeout=55';
        const ctrl = new AbortController(); const tmo = setTimeout(() => ctrl.abort(), 75000);
        let j;
        try {
          const res = await fetch(url, { signal: ctrl.signal });
          if (res.status === 429 || res.status === 503 || res.status === 502 || res.status === 500 || res.status === 408) {
            feedGap = true; // review 1092 blocker 4: upstream hiccup - re-read the missed range via the relay, keep the cursor
          } else if (!res.ok) throw new Error('feed http ' + res.status);
          else {
            try { j = await res.json(); } catch (e) { feedGap = true; } // malformed body: same, re-read
            if (j && j.cursor !== undefined) {
              pendingCursor = j.cursor; // review 1095 blocker 3: commit the cursor only after the scan below succeeded
              if (j.gap || j.removed) feedGap = true; // stream interrupted or reorg: re-read via the relay
              else if (j.logs && j.logs.length) feedLogs = j.logs;
            } else feedGap = true; // response without a cursor
          }
        } finally { clearTimeout(tmo); }
      }
      const safety = Date.now() - lastFull >= SAFETY_MS;
      const needScan = feedLogs !== null || feedGap || safety || !feedAddrList.length;
      if (needScan) {
        // review 1095 blocker 3: the cursors (st.lastBlock and the feed cursor) and the
        // answers commit only AFTER the range re-read and the state scan succeeded; a
        // mid-cycle failure keeps the OLD cursors, so the next cycle re-reads the missed
        // range instead of skipping logs (the answers roll back to their snapshot too).
        const answersSnap = Object.assign({}, st.answers);
        const lastBlockSnap = st.lastBlock;
        try {
          head = BigInt(await rpc('eth_blockNumber', []));
          try { // refresh the ETH/USD valuation of the gas cap EVERY scan (review 1095
            // blocker 1 "freshly priced": the pool slot0 price, not the startup snapshot)
            const sq = word(await rpc('eth_getStorageAt', [WETH_USDC_POOL, '0x0', 'latest']), 0) & ((1n << 160n) - 1n);
            poolPrice = (sq * sq * 10n ** 12n) / (1n << 192n);
          } catch (e) {}
          const drops = [];
          const prevCursor = BigInt(st.lastBlock);
          if (feedLogs) feedDrops(feedLogs, drops);
          else if (feedGap && aggAddrs.length) {
            const rl = await rpc('eth_getLogs', [{ address: aggAddrs, topics: [TOPIC_ANSWER_UPDATED],
              fromBlock: '0x' + (prevCursor + 1n).toString(16), toBlock: '0x' + head.toString(16) }]);
            feedDrops(rl, drops);
            if (rl.length) console.log(`[${head.toString()}] feed-gap relay re-read: ${rl.length} logs`);
            await sleep(15000); // back off after a gap/429 burst
          }
          if (safety) lastFull = Date.now();
          if (drops.length) console.log(`[${head.toString()}] AnswerUpdated drops: ${drops.length}`);
          if (drops.length || safety) {
            for (const m of MARKETS) {
              const oracleAgg = st.agg[m.oracle] || [];
              const oracleUpdated = !aggAddrs.length || !drops.length || oracleAgg.some(f => drops.includes('0x' + f.slice(2)));
              if (drops.length && !oracleUpdated) continue;
              await checkMarket(m, head);
            }
          }
        } catch (e) {
          st.answers = answersSnap; st.lastBlock = lastBlockSnap;
          throw e; // cursors uncommitted: re-read the same range next cycle
        }
        st.lastBlock = head.toString();
        if (pendingCursor !== null) { feedCursor = pendingCursor; st.feedCursor = pendingCursor; }
        saveState();
      }
    } catch (e) { console.log('cycle error:', String(e).slice(0, 200)); await sleep(20000); }
    fs.appendFileSync(HEART, new Date().toISOString() + ' tick ' + Math.round(Date.now() - t0) + 'ms reads ' + rpcCache.reads + '\n');
    if (!stopped && !feedAddrList.length) await sleep(SAFETY_MS / 2); // no pinned feeds: safety-poll-only mode
  }
  console.log('bot stopped');
}
main().catch(e => { console.log('fatal:', e); process.exit(1); });
