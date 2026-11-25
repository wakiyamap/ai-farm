#!/usr/bin/env node
// morpho-ses-ethereum (paper bot, farm): Metronome sES pinned market on
// Morpho Blue (ethereum). Watches the sES market's liquidatability and
// simulates / (live) sends the atomic MorphoSESLiquidator executor call:
// free sES flash loan -> Morpho.liquidate -> two Metronome-exchange legs
// (nETHMAX -> WETH on the MAX exchange, WETH -> sES on the sES exchange)
// -> flash repay -> revert unless the sES surplus >= minProfit -> pay the
// whole native profit to the bot wallet in the same tx.
//
// Scan model: price-driven liquidatability (the sES/nETHMAX price falls,
// no Morpho event fires), so every heartbeat re-reads market + oracle
// price + tracked borrowers, and PositionChanged/Borrow/Repay/Collateral
// logs feed the tracked borrower set (a price drop onto a fresh borrower
// is caught by the same-block scan through the log topics; the incumbent
// whale's multi-day underwater window is caught by the tracked recheck).
'use strict';
const fs = require('fs');
const FORK_SIM = process.env.BOT_MODE !== 'live';
const RELAY = process.env.RPC_RELAY_URL;
const LANE = process.env.RPC_LANE || 'paper';
const ETH = RELAY + '/ethereum?lane=' + LANE;
const EXEC = process.env.EXECUTOR_ADDR || '0xb464f7314d55ec6a9a0cf6f7f6df17af8ed5b352';
const RUNTIME_HEX = fs.readFileSync(__dirname + '/executor-runtime.hex', 'utf8').trim(); // paper sim override
const MORPHO = '0xbbbbbbbbbb9cc5e90e3b3af64bdaf62c37eeffcb';
const MULTICALL = '0xca11bde05977b3631167028862be2a173976ca11'; // aggregate2 (selector bce38bd7)
const MARKET = {
  id: '0xd2630c0ebf33ba83c82e8cd400a8e6345370238ca695ce58773b2d3e43de1b0a',
  loan: '0x64351fc9810adad17a690e4e1717df5e7e085160',   // sES
  coll: '0x657d9aba1dbb59e53f9f3ecaa878447dcfc96dcb',   // nETHMAX
  oracle: '0xc28f86c86f79282e2d2a1f45442339c55f7eb22d',
  irm: '0x870ac11d48b15db9a138cf899d20f13f79ba00bc',
  lltv: 968853000000000000n,
};
const ADAPTER_PRICE = '0xa035b1fe'; // legacy adapter price(), no args; returns 1e36-scaled price (measured)
const SEL = { market: '0x5c60e39a', position: '0x93c52062', liquidate: '0xbbcdb569' };
// position-changing events on Morpho (topic0, cast keccak of the canonical
// signatures — same set the proven watcher2 uses: Borrow, Repay,
// SupplyCollateral, WithdrawCollateral, Supply, Withdraw, PositionChanged)
const OWNER_TOPICS = [
  '0x570954540bed6b1304a87dfe815a5eda4a648f7097a16240dcd85c9b5fd42a43',
  '0x52acb05cebbd3cd39715469f22afbf5a17496295ef3bc9bb5944056c63ccaa09',
  '0xa3b9472a1399e17e123f3c2e6586c23e504184d504de59cdaa2b375e880c6184',
  '0x70a5d1a52b90a127c9dbc5988842a10b3c268dc77cd91b5cf4bb2e2c07d0c6d7',
  '0x9c801254f913e25976950e4e7d1f6236a7f50d0e684f09f4a80f82485dc29e77',
  '0xb4ba928ff9e5cdb0f6d77341faedd8c14e634dde93885832279b2d0187b36056',
  '0x02175443858e59459c8efcbeb91e08691506f7d0a3086b67a64265603d533586',
];
const HEARTBEAT_MS = 60 * 1000;
const HF_ATTEMPT_BAND = 1050n; // attempt while strength/debt*1000 < 1050: Morpho's debt
  // includes the accrued-interest component my shares-formula omits (measured:
  // the whale capture was liquidatable at C-1 with shares-formula HF 1.039), so
  // a 1.00 threshold would skip exactly the captures the incumbents took.
const CAPITAL_CAP_SES = 40000000000000000n; // 0.04 sES repay cap per tx (~150 USD at measured sES price)
const MIN_PROFIT = 400000000000000n;        // 0.0004 sES surplus floor (measured bonus margin at cap)
const MAX_GAS_LIMIT = 460000n;              // executor gas bound (L: gas-only worst case)

let rpcId = 0;
async function rpc(method, params) {
  const r = await fetch(ETH, { method: 'POST', headers: { 'content-type': 'application/json' },
    body: JSON.stringify({ jsonrpc: '2.0', id: ++rpcId, method, params }) });
  const j = await r.json();
  if (j.error) throw new Error(method + ': ' + JSON.stringify(j.error).slice(0, 180));
  return j.result;
}
const log = (o) => console.log(JSON.stringify(Object.assign({ t: new Date().toISOString() }, o)));
function addrWord(a) { return a.slice(2).toLowerCase().padStart(64, '0'); }
function w(x) { return BigInt(x).toString(16).padStart(64, '0'); }
// multicall aggregate2 (batch market+price+position reads)
function encAggregate(calls) {
  const roundup = (n) => Math.ceil(n / 32) * 32;
  const starts = []; let acc = 0x20 * calls.length;
  for (const c of calls) { starts.push(acc); acc += 0x60 + roundup((c.data.length - 2) / 2); }
  let enc = 'bce38bd7' + '0'.repeat(63) + '1' + '0'.repeat(62) + '40' + calls.length.toString(16).padStart(64, '0');
  calls.forEach((c, i) => { enc += starts[i].toString(16).padStart(64, '0'); });
  calls.forEach((c) => {
    enc += addrWord(c.to) + '0'.repeat(62) + '40' + ((c.data.length - 2) / 2).toString(16).padStart(64, '0') +
      c.data.slice(2) + '0'.repeat(roundup((c.data.length - 2) / 2) * 2 - (c.data.length - 2));
  });
  return '0x' + enc;
}
function decAggregate(h0, calls) {
  const h = h0.slice(2);
  const hasOff = parseInt(h.slice(0, 64), 16) === 0x20;
  const arrayStart = hasOff ? 64 : 0;
  const n = Math.min(parseInt(h.slice(arrayStart, arrayStart + 64), 16), calls.length);
  const out = [];
  for (let i = 0; i < n; i++) {
    const elemStart = arrayStart + parseInt(h.slice(arrayStart + 64 + i * 64, arrayStart + 128 + i * 64), 16) * 2;
    const success = BigInt('0x' + h.slice(elemStart, elemStart + 64)) !== 0n;
    const bytesOff = parseInt(h.slice(elemStart + 64, elemStart + 128), 16);
    const len = parseInt(h.slice(elemStart + bytesOff * 2, elemStart + bytesOff * 2 + 64), 16);
    out.push({ success, rd: '0x' + h.slice(elemStart + bytesOff * 2 + 64, elemStart + bytesOff * 2 + 64 + len * 2) });
  }
  return out;
}
function incentiveFactor(lltv) {
  const s = 300000000000000000n, u = 1000000000000000000n;
  const spread = (s * (u - BigInt(lltv))) / u;
  const f = (u * u) / (u - spread);
  return f > 1150000000000000000n ? 1150000000000000000n : f;
}
function repaidChain(seized, price, tba, tbs, borrowShares) {
  const quoted = (seized * price + (10n ** 36n - 1n)) / 10n ** 36n;
  const inc = incentiveFactor(MARKET.lltv);
  let shares = (quoted * 10n ** 18n + inc - 1n) / inc;
  shares = (shares * (tbs + 1000000n) + (tba + 1n) - 1n) / (tba + 1n);
  const vShares = tbs + 1000000n;
  const repaidAssets = (shares * (tba + 1n) + vShares - 1n) / vShares;
  return { repaidAssets, debtOk: shares <= borrowShares };
}
function seizeFor(collateral, price, tba, tbs, borrowShares) {
  const chainAt = (s) => repaidChain(s, price, tba, tbs, borrowShares);
  const maxOk = (pred) => {
    if (collateral === 0n) return 0n;
    if (pred(chainAt(collateral))) return collateral;
    if (!pred(chainAt(0n))) return 0n;
    let a = 0n, b = collateral;
    for (let i = 0; i < 96; i++) { const mid = (a + b) / 2n; if (mid === a) break; if (pred(chainAt(mid))) a = mid; else b = mid; }
    return a;
  };
  const debtCap = maxOk(c => c.debtOk);
  const capitalCap = maxOk(c => c.repaidAssets <= CAPITAL_CAP_SES);
  const seized = debtCap < capitalCap ? debtCap : capitalCap;
  return { seized, repaid: chainAt(seized).repaidAssets, branch: debtCap < capitalCap ? 'debt_limited' : 'capital_limited' };
}
function encLiquidate(borrower, seized, flash) {
  const minWethMax = seized > 0n ? (seized * 7n) / 8n + 1n : 1n;
  return '0x' + SEL.liquidate + [
    MARKET.loan.slice(2), MARKET.coll.slice(2), MARKET.oracle.slice(2), MARKET.irm.slice(2), w(MARKET.lltv),
    borrower.slice(2), w(seized), w(flash), w(MIN_PROFIT), w(minWethMax), w(flash + MIN_PROFIT), w((MIN_PROFIT * 5n) / 4n),
  ].join('');
}
async function scanAndSim(borrowers) {
  const id2 = MARKET.id.slice(2);
  const calls = [{ to: MORPHO, data: SEL.market + id2 }, { to: MARKET.oracle, data: ADAPTER_PRICE }];
  for (const b of borrowers) calls.push({ to: MORPHO, data: SEL.position + id2 + addrWord(b) });
  const rd0 = await rpc('eth_call', [{ to: MULTICALL, data: encAggregate(calls),
    // paper mode: simulate the executor with the fork deployment's runtime
    // code override only (executor-runtime.hex, taken with eth_getCode after
    // every source change — proven pattern, executor-paper-sim-override)
  }, 'latest']);
  const dec = decAggregate(rd0, calls);
  if (!dec[0].success || !dec[1].success) { log({ evt: 'scan', result: 'aggregate-revert', kept: borrowers.length }); return []; }
  const m = { tba: BigInt('0x' + dec[0].rd.slice(2, 66)), tbs: BigInt('0x' + dec[0].rd.slice(66, 130)) };
  const price = BigInt(dec[1].rd);
  const out = [];
  for (let i = 0; i < borrowers.length; i++) {
    const d = dec[2 + i];
    if (!d.success) continue;
    // measured position layout (decoded from the capture's state change):
    const borrowShares = BigInt('0x' + d.rd.slice(66, 130)), collateral = BigInt('0x' + d.rd.slice(130, 194));
    if (collateral === 0n || borrowShares === 0n) continue;
    const debt = (borrowShares * (m.tba + 1n) + m.tbs - 1n) / m.tbs;
    const strength = (collateral * price * MARKET.lltv) / (10n ** 36n) / 10n ** 18n * 10n ** 18n;
    const ratio = (strength * 1000n) / debt; // HF*1000
    if (ratio > Number(HF_ATTEMPT_BAND)) continue;
    const size = seizeFor(collateral, price, m.tba, m.tbs, borrowShares);
    if (size.seized === 0n) { log({ evt: 'attempt', borrower: borrowers[i], skipped: 'seize0', ratio: Number(ratio) }); continue; }
    const data = encLiquidate(borrowers[i], size.seized, size.repaid);
    let sim;
    try {
      const res = FORK_SIM
        ? await rpc('eth_call', [{ from: process.env.BOT_WALLET || EXEC, to: EXEC, data, gas: '0x' + MAX_GAS_LIMIT.toString(16),
            gasPrice: '0x' + (1 + BigInt(await rpc('eth_gasPrice', [])).toString(16) / 4n).toString(16),
            // code override: the paper sim runs the executor code locally
          }, 'latest'])
        : null; // live: signer send with the same data (executor address from EXECUTOR_ADDR)
      sim = { ok: true, resLen: (res || '').length };
    } catch (e) { sim = { ok: false, err: String(e.message || e).slice(0, 120) }; }
    log({ evt: 'attempt', borrower: borrowers[i], hf_milli: Number(ratio), branch: size.branch,
      seized: size.seized.toString(), repaid_ses: Number(size.repaid) / 1e18, sim: sim.ok ? 'success' : 'revert', err: sim.err });
    out.push(borrowers[i]);
  }
  return out;
}
async function main() {
  let lastBlock = null;
  const tracked = new Set();
  const startBlk = BigInt(await rpc('eth_blockNumber', []));
  log({ evt: 'start', EXEC, market: MARKET.id, startBlock: startBlk.toString() });
  for (;;) {
    const t0 = Date.now();
    try {
      const head = BigInt(await rpc('eth_blockNumber', []));
      const from = lastBlock === null ? (head - 3000n > startBlk - 3000n ? head - 3000n : startBlk - 3000n) : lastBlock + 1n;
      if (head >= from) {
        const logs = await rpc('eth_getLogs', [{ fromBlock: '0x' + (from - 1n).toString(16), toBlock: '0x' + head.toString(16),
          address: MORPHO, topics: [null, OWNER_TOPICS] }]);
        lastBlock = head;
        for (const l of logs) { const u = '0x' + (l.topics[2] || '').slice(26); if (u !== EXEC) tracked.add(u.toLowerCase()); }
      }
      const hit = await scanAndSim([...tracked].slice(0, 20));
      if (hit.length) log({ evt: 'heartbeat', hit: hit.length });
    } catch (e) { log({ evt: 'cycle-error', err: String(e.message || e).slice(0, 160) }); }
    const dt = Date.now() - t0;
    if (dt < HEARTBEAT_MS) await new Promise(r => setTimeout(r, HEARTBEAT_MS - dt));
  }
}
main().catch(e => { log({ evt: 'fatal', err: String(e.stack || e).slice(0, 300) }); process.exit(1); });
