// GMX v2 Arbitrum liquidation watcher (paper).
// Watches the GMX EventEmitter OrderCreated events; orderType==2 = liquidation
// sell-order captures (the fee-bearing liquidation step). Detects captures,
// tracks candidate accounts from orderType 0/1 (position opens) and logs
// everything machine-readable for the paper reviewer.
// No sends in paper mode yet: the live executor path (own wrapper deployment)
// is pending; see manifest executor comment.
const fs = require('fs');
const path = require('path');

const RPC_URL = process.env.RPC_RELAY_URL;
const LANE = process.env.RPC_LANE || 'paper';
if (!RPC_URL) throw new Error('RPC_RELAY_URL missing');
const URL = `${RPC_URL}/arbitrum?lane=${LANE}`;

const EMITTER = '0xC8ee91A54287DB53897056e12D9819156D3822Fb';
const T_EVENT = '0x468a25a7ba624ceea6e540ad6f49171b52495b648417ae91bca21676d8a24dc5';
const T_ORDER_CREATED = '0xa7427759bfd3b941f14e687e129519da3c9b0046c5b9aaa290bb1dede63753b3';
const POLL_MS = 45 * 1000;
const PAGE_BLOCKS = 1500;
const COLD_START_BLOCKS = 100000;
const CAND_CAP = 4000;

const STATE_FILE = path.join(__dirname, 'state', 'state.json');
const LOG_FILE = path.join(__dirname, 'logs', 'bot.jsonl');

function log(o) {
  o.ts = new Date().toISOString();
  fs.appendFileSync(LOG_FILE, JSON.stringify(o) + '\n');
}
let idSeq = 1;
async function rpc(method, params) {
  const body = { jsonrpc: '2.0', id: idSeq++, method, params };
  const res = await fetch(URL, { method: 'POST', headers: { 'content-type': 'application/json' }, body: JSON.stringify(body) });
  const j = await res.json();
  if (j.error) throw new Error(method + ': ' + JSON.stringify(j.error).slice(0, 200));
  return j.result;
}
function loadState() {
  try { return JSON.parse(fs.readFileSync(STATE_FILE, 'utf8')); } catch { return null; }
}
function saveState(s) { fs.writeFileSync(STATE_FILE, JSON.stringify(s)); }

async function main() {
  let st = loadState();
  if (!st || !st.cursorBlock) {
    const head = Number(await rpc('eth_blockNumber', []));
    st = { cursorBlock: head - COLD_START_BLOCKS, universe: [] };
    saveState(st);
    log({ t: 'boot', head, cursorBlock: st.cursorBlock });
  }
  const universe = new Set(st.universe || []); // accounts seen opening positions (orderType 0/1)
  const blockNum = new Map(); // blockHash -> number cache
  async function blockOf(hash) {
    if (!blockNum.has(hash)) {
      const b = await rpc('eth_getBlockByHash', [hash, false]);
      blockNum.set(hash, b ? Number(b.number) : 0);
    }
    return blockNum.get(hash);
  }
  let lastErr = 0;
  for (;;) {
    const t0 = Date.now();
    try {
      const head = Number(await rpc('eth_blockNumber', []));
      let from = st.cursorBlock + 1;
      let pages = 0;
      while (from <= head && pages < 2) { // max 2 pages per cycle; backlog drains over cycles
        const to = Math.min(from + PAGE_BLOCKS - 1, head);
        const logs = await rpc('eth_getLogs', [{
          address: EMITTER,
          topics: [T_EVENT, T_ORDER_CREATED],
          fromBlock: '0x' + from.toString(16),
          toBlock: '0x' + to.toString(16),
        }]);
        for (const l of logs) {
          const data = l.data || '0x';
          const word = (i) => data.slice(10 + 64 * i, 10 + 64 * (i + 1));
          // GMX EventEmitter packs event args (16-byte packing + tuple offsets);
          // orderType lives in the order struct data region, NOT in these head
          // words: leave it undecoded this round (raw words logged; decode
          // template: scratch/gmx-liq-arb/trace.json + probe-out6.json).
          const isOrderCreated = data.includes('4f7264657243726561746564'); // ascii "OrderCreated"
          // orderType = byte at offset 358 after the end of the "OrderCreated"
          // name (packed 16-byte slot layout, verified 2026-11-06 run 9f56cce8:
          // capture tx 0xb70b29cf byte='2' vs open events byte='0'; the capture
          // discriminator: scratch/gmx-liq-arb/capture-log.json + ord-log.json).
          let orderType = null;
          if (isOrderCreated) {
            const idx = data.indexOf('4f7264657243726561746564');
            orderType = Number('0x' + data.slice(idx + 24 + 358, idx + 24 + 359));
          }
          const rec = {
            t: isOrderCreated ? (orderType === 2 ? 'capture' : 'order') : 'event',
            orderType,
            blockHash: l.blockHash,
            logIndex: l.logIndex,
            tx: l.transactionHash,
            w0: word(0), w1: word(1), w2: word(2), w3: word(3), w4: word(4), w5: word(5), w6: word(6), w7: word(7),
          };
          delete rec.block;
          if (isOrderCreated) {
            // liquidation sell-order captures (orderType==2) await the packed
            // data-region decode; record every OrderCreated with raw words.
            rec.block = await blockOf(l.blockHash);
          }
          log(rec);
          if (isOrderCreated && (orderType === 0 || orderType === 1)) {
            // candidate universe from position opens; account is the third topic
            const acct = '0x' + (l.topics && l.topics[3] ? l.topics[3].slice(-40) : '0'.repeat(40));
            universe.add(acct);
            if (universe.size > 5000) universe.delete(universe.values().next().value);
          }
        }
        st.cursorBlock = to;
        from = to + 1;
        pages++;
      }
      st.universe = [...universe];
      saveState(st);
      log({ t: 'heartbeat', head, cursorBlock: st.cursorBlock, universe: universe.size, ms: Date.now() - t0 });
      lastErr = 0;
    } catch (e) {
      const now = Date.now();
      if (now - lastErr > 60000 || lastErr === 0) log({ t: 'error', msg: String(e.message || e).slice(0, 300) });
      lastErr = now || 1;
      await new Promise((r) => setTimeout(r, 5000));
      continue;
    }
    await new Promise((r) => setTimeout(r, Math.max(POLL_MS - (Date.now() - t0), 2000)));
  }
}
main().catch((e) => { log({ t: 'fatal', msg: String(e.message || e) }); process.exit(1); });
