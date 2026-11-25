// reserve-dutch-ethereum: Reserve eUSD/ETH+ revenue Dutch auctions watcher+executor bot.
// Watches TradeStarted/TradeSettled on the four revenue traders; for ETH+ trades
// (sell=weETH, buy=ETH+ 0xe72b141d) simulates the ReserveDutch executor bidDutch
// (bidWithCallback + direct-call swap route proven on the fork, attempt 223) and
// bids while the simulation succeeds with an AFTER-GAS profit floor minProfitBuy:
//   minProfitBuy = PROFIT_MARGIN x GAS_BUDGET_GAS x gasPrice(now)
// i.e. the on-chain NO_PROFIT guard is priced at >= 2x our worst-case gas, so a
// simulate 'ok' means the fill is profitable AFTER gas, not just net-positive
// (review 7fc3cc47: the old fixed 1e12 wei floor ~ 0.002 USD was far below gas).
// Paper: eth_call with the executor runtime code + owner storage override.
// Live: sends bidDutch through the signer socket to the gate-deployed executor
// (env EXECUTOR_ADDR, fallback state/executor.json; a live run without either a valid
// address and a deployed runtime matching executor-runtime.hex refuses to start) with
// bounded gas = GAS_BUDGET_GAS and maxFeePerGas, logs
// the signer receipt ({ok, txHash, nonce}) or rejection (review 91e6759c: the
// signer documents txHash, not hash); a definitive rejection is final (no retry).
// Before every live send a DURABLE PRE-SEND INTENT (trade, wall ts, wallet nonce
// baseline) is persisted (review 69bab952 2026-11-10T12:11Z): the accepted-send
// evidence survives a crash between the broadcast and the first log append, and
// the send gate stays closed until reconcileIntent finds or expires the broadcast.
'use strict';
const fs = require('fs'), path = require('path'), net = require('net');
const DIR = __dirname;
const RELAY = process.env.RPC_RELAY_URL, LANE = process.env.RPC_LANE || 'paper';
const MODE = process.env.BOT_MODE || 'paper';
const ENDPOINT = `${RELAY}/ethereum?lane=${LANE}`;
const WEETH = '0xcd5fe23c85820f7b72d0926fc9b05b43e359b7ee';
const ETHP = '0xe72b141df173b999ae7c1adcbf60cc9833ce56a8';
const TRADER4 = '0x977cb0e300a58978f597fc65ed5a2d2784d2dcf9';
const ADDRESSES = ['0xe04c26f68e0657d402fa95377aa7a2838d6cba6f',
  '0x3d5ebb5399243412c7e895a7aa468c7cd4b1014a',
  '0x6e20823ca50aa026b99789c8d468a01f8aa3581c', TRADER4];
const T_STARTED = '0xf18b757d93c36d059284838a0328b06d8eb30d7214ffadde3266465a0006f6b3';
const T_SETTLED = '0x058fb1fa484531f400806f666315faf1a45941db93ba069405882b78ba40dc87';
const pad = a => '0x' + a.slice(2).toLowerCase().padStart(64, '0');
const TOPICS_ETHP = [null, pad(WEETH), pad(ETHP)]; // [topic0, _, sell, buy]
// Poll widened 45 -> 180 s 2026-11-11T23:1xZ (run 5036..., review f43c9353: "make the
// closed-state polling cheap enough that measured current EV covers read cost"). The
// route is closed at the current pool state (forward WETH->ETH+ get_dy measured 0.907811
// at head 26394836, below the ~1.004 settled Dutch price), EV = 0/day while the pool is
// imbalanced, so the waiting cost must stay near zero. Justification is the measured
// window, not history: the ten incumbent direct fills took 87-111 blocks / 1044-1332 s
// after the start event (scratch/reserve-research/fill_windows.json; the auction itself
// is 1800 s), so a 180 s poll + ~60 s simulate/send-to-inclusion lands the bid by
// ~300-360 s after the pair start, still ~700 s ahead of the earliest measured incumbent
// take; the Dutch bid price decays 4.632e-5 of bid value per second, so a bid 135 s
// later is strictly cheaper (attempt 214). Idle cost falls ~4x: ~100k CU/day ~0.05 USD.
const POLL_MS = 180 * 1000;
// After-gas profit rule (review 7fc3cc47 blocker 2). Gas budget from the fork
// proof rerun 2026-11-06T10:2xZ (scratch/reserve-bot/proof.py -> proof.json):
// bidDutch success tx gasUsed 0xb99ce = 760270 (success_gas_used, including
// the contract's oracle gas-USD check with the raised 3660 s staleness cap;
// the pre-check proof measured 741303/741672) x 1.18 margin -> 900000.
// Fix (review 233973f5 follow-up, run 02395076 2026-11-09): the 900000 cap was NEVER
// fork-proven — every proof sent 2097152 gas. Measured this run on the shared ethereum
// fork at reset 26348315 (scratch/rf-floor-proof.json): with 900000 or 950000 gas the
// bidDutch path reverts with EMPTY data (the SwapX router leg needs ~940000 gasleft
// headroom: the success path consumes only ~760000 gas total, but the router's own
// gasleft requirement exceeds the 900000-cap remaining gas), 1000000 completes.
// GAS_BUDGET_GAS raised 900000 -> 1050000 (measured minimum + margin); the signed
// ceiling becomes 1050000 x 2.0 gwei = 0.0021 ETH (8.92 USD at the measured all-time
// high 4956.78, 4.45 USD at the 2026-11-09 price ~2119 — below the manifest 20 USD).
const GAS_BUDGET_GAS = 1050000;
// Hard fee cap (review 91e6759c / bce15686 / d013d4cb / da3e4b7a / 7e653174 /
// 279 blocker 2 chain): the loss bound is an UPPER bound. SIGNED gas exposure
// GAS_BUDGET_GAS x MAX_FEE_WEI = 1050000 x 2.0 gwei = 0.0021 ETH is the
// absolute ETH bound, enforced by maxFeePerGas x gasLimit in the transaction.
// The USD bound is now enforced INSIDE the transaction AT INCLUSION (review
// 279 rejected every decision-time price assumption: ATH, oracle x margin,
// 90-day move): ReserveDutch.bidDutch reads the Chainlink ETH/USD answer of
// its own execution block and reverts (GAS_USD) unless (remaining gas +
// intrinsic slack) x tx.gasprice x answer <= MAX_GAS_USD_MICRO 20.00 USD,
// with the answer's freshness enforced on-chain (ORACLE_STALE <= 3660 s).
// tx.gasprice is the effective price actually paid at inclusion (<= the
// signed maxFeePerGas), so a completed bid pays <= 20 USD of gas AT THE
// INCLUSION-BLOCK ORACLE PRICE, and an early GAS_USD/ORACLE revert pays
// <= ~60000 x maxFeePerGas = 0.00012 ETH. ORACLE_STALE on-chain is 3660 s
// (measured quiet-hour round gap 3624 s + delivery slack + margin); the
// bot-side cap below is wider only because wall age adds the chain-head lag
// and one poll. The bot-side filter (fresh oracle, worstGasMic) stays
// fail-closed preference: a spike = missed trade, not loss. Fee headroom: measured relay gasPrice 0.160 gwei on
// 2026-11-06 -> ~12x headroom to the 2.0 gwei cap; gasPrice at or above the
// cap fails closed: no send; a stale or missing oracle round never sends.
const MAX_FEE_WEI = 2000000000n; // 2.0 gwei
const TIP_WEI = 1000000000n; // maxPriorityFeePerGas cap 1 gwei (min with gasPrice)
const PROFIT_MARGIN = 2n; // minProfitBuy >= 2 x worst-case gas -> net >= 1 x gas
// Upper valuation = oracle answer x PRICE_MARGIN, where the margin is MEASURED,
// not estimated (review d013d4cb: a 10 percent markup was called an estimate).
// Binance ETHUSDT 1-minute closes track this feed's answers within 0.25 percent
// at three cross-checked rounds (answers 2234.59/2225.25/2228.50 vs closes
// 2240.00/2229.89/2232.60 on 2026-11-06), so the klines proxy the feed's own
// price movement. Over the last 90 days (129600 candles, 2026-08-08..11-06,
// scratch/binance-eth-1m-90d.json) the maximum 100 percent peak-to-trough move
// over a sliding window of staleness cap 2400 s + poll 45 s + inclusion 24 s
// = 2469 s is 9.05 percent; over a wider 78-minute window it is 10.30 percent
// (Aug 19 19:49->21:07Z crash). 1.12 exceeds both measurements with slack, so
// the signed ceiling valued at answer x 1.12 bounds gas at inclusion under the
// worst price movement observed in those 90 days.
const PRICE_MARGIN_NUM = 112n, PRICE_MARGIN_DEN = 100n; // effective factor = NUM/(100 x DEN) = 1.12/100 on an 8-dec answer
// Fix (review add09a2c 2026-11-10T07:33Z, checklist item 3): the 60 s TTL cache let a
// 45 s poll cycle settle a receipt at the PRIOR cycle's price. The price is now read
// fresh on EVERY cycle (one extra eth_call per 45 s poll): settlement runs only on a
// cycle whose read succeeded THIS cycle; a failed read returns null and fails closed.
const FEED_ETHUSD = '0x5f4ec3df9cbd43714fe2740f5e3616155c5b8419'; // Chainlink ETH/USD: decimals()=8, description()='ETH / USD' (both verified through the relay 2026-11-06)
// Staleness cap: the feed's cadence is NOT one number. Volatile hours: 1236 s
// (rounds updated 2026-11-06T03:14:59Z and 03:35:35Z through this relay).
// Quiet hours (no deviation trigger): consecutive rounds updated
// 2026-11-06T09:13:11Z and 10:13:35Z — a 3624 s gap, i.e. the hourly
// heartbeat + ~25 s answer delivery (measured, attempt 281: the 2400 s cap
// failed closed through every quiet hour and would miss any auction started
// then). Bot-side cap = gap 3624 + delivery 25 + head lag (measured 82 s at
// 2026-11-06T10:14Z, allowed 180) + poll + margin s wall age (poll raised
// 45 -> 180 s 2026-11-11, raising this cap 3960 -> 4095 in step below). The
// on-chain ORACLE_STALE 3660 s (contract) needs no head-lag/poll term: its
// age is block.timestamp - updatedAt inside the execution block.
// The jump bound above is measured over windows up to 78 min = 4680 s
// (10.30 percent max move over the 90 days of 1-minute candles), and the
// worst bot-side window here is the cap below + 24 s inclusion < 4680 s, so the same
// 1.12 margin bounds gas at inclusion; the 9.05 percent for the old 2469 s
// window (2400 + 45 + 24) is the narrower case it also covered.
// poll term raised 45 -> 180 s with the poll change above (3624 + 25 + 180 + 180 + margin
// = 4095); the measured 1.12 jump bound still covers this window: 4095 + 24 s inclusion =
// 4119 s < the 78-minute (4680 s) window over which the 90-day candle measurement caps
// the ETH move at 10.30 percent.
const ORACLE_MAX_AGE_S = 4095;
const MAX_LOSS_USD_MICRO = 20000000n; // L: worst case per tx = 20 USD in micro-USD
const RUNTIME_FILE = path.join(DIR, 'executor-runtime.hex');
let RUNTIME = ''; try { RUNTIME = fs.readFileSync(RUNTIME_FILE, 'utf8').trim(); } catch (e) {}
const RUNTIME_OK = RUNTIME.length > 200 && !RUNTIME.includes('00006f'); // fail closed on missing runtime
const EXEC_SIM = '0x000000000000000000000000000000000000d0c0'; // paper sim address (code override)
const FORK_OWNER = '0x0d0e000000000000000000000000000000000d0e'; // paper owner (storage slot 0)
const SLOT0 = '0x' + '0'.repeat(64);
// Fix (live-operator review 2026-11-10T17:05Z): the gate passes the deployed executor as the
// EXECUTOR_ADDR env (every other live bot reads this name) and writes state/executor.json
// after deploying. This bot read only EXEC_ADDRESS, which the gate never sets, so live mode
// crash-looped at startup. Resolution: EXECUTOR_ADDR (legacy EXEC_ADDRESS accepted), then
// state/executor.json -> .ethereum.address. In live mode a startup without a valid 0x40-hex
// from one of these two refuses to run; the paper sim address is NEVER a live fallback.
const EXECUTOR_JSON_F = path.join(DIR, 'state', 'executor.json');
const isExecAddr = (a) => (/^0x[0-9a-fA-F]{40}$/.test((a || '').trim()) ? (a || '').trim().toLowerCase() : '');
function execAddrFromEnv() { return isExecAddr(process.env.EXECUTOR_ADDR || process.env.EXEC_ADDRESS); }
function execAddrFromFile() {
  try { const j = JSON.parse(fs.readFileSync(EXECUTOR_JSON_F, 'utf8')); return isExecAddr(j && j.ethereum && j.ethereum.address); } catch (e) { return ''; }
}
function resolveExecAddr(mode) { return execAddrFromEnv() || (mode === 'live' ? execAddrFromFile() : ''); }
let EXEC_LIVE = resolveExecAddr(MODE) || EXEC_SIM;
const SIGNER_SOCK = process.env.SIGNER_SOCK || '/run/farm/signer.sock';
const LOGF = path.join(DIR, 'logs', 'bot.jsonl');
const STATEF = path.join(DIR, 'state', 'state.json');
const STOPPEDF = path.join(DIR, 'state', 'STOPPED.json');
const log = (o, file) => { o.ts = new Date().toISOString(); fs.appendFileSync(file || LOGF, JSON.stringify(o) + '\n'); };
let idc = 0;
async function rpc(method, params) {
  const r = await fetch(ENDPOINT, { method: 'POST', headers: { 'content-type': 'application/json' },
    body: JSON.stringify({ jsonrpc: '2.0', id: ++idc, method, params }) });
  const j = await r.json();
  if (j.error) throw new Error(`${method}: ${JSON.stringify(j.error)}`);
  return j.result;
}
const hex2bn = (h) => BigInt(h === '0x' ? 0 : h);
// Fix (review 69bab952 2026-11-10T12:11Z, checklist 2/10): a socket error/close/timeout or
// truncated JSON is an AMBIGUOUS TRANSPORT outcome, not a definitive signer rejection — the
// signer may already have broadcast the transaction before its reply was lost. Such replies
// carry transport:true, which classifySendReply reads to keep the pre-send intent pending
// (the send gate stays closed) instead of marking the trade a final rejection. The prior code
// resolved a close-without-reply never (the promise hung forever) and treated every error as final.
const SIGNER_REPLY_TIMEOUT_MS = 20000;
function signerCall(req) {
  return new Promise((resolve) => {
    const s = net.connect(SIGNER_SOCK);
    let buf = '', done = false, timer = null;
    const fin = (o) => { if (done) return; done = true; if (timer) clearTimeout(timer); s.destroy(); resolve(o); };
    timer = setTimeout(() => fin({ ok: false, error: `signer reply timeout ${SIGNER_REPLY_TIMEOUT_MS / 1000}s`, transport: true }), SIGNER_REPLY_TIMEOUT_MS);
    s.on('connect', () => s.write(JSON.stringify(req) + '\n'));
    s.on('data', (d) => { buf += d.toString(); if (buf.endsWith('\n')) { if (done) return; try { const o = JSON.parse(buf); done = true; clearTimeout(timer); s.end(); resolve(o); } catch (e) { fin({ ok: false, error: 'bad signer json', transport: true }); } } });
    s.on('error', (e) => fin({ ok: false, error: String(e).slice(0, 200), transport: true }));
    s.on('close', () => fin({ ok: false, error: 'signer closed without a reply', transport: true }));
  });
}
async function signerAddress() { // our live wallet address from the signer; null in paper
  if (MODE !== 'live') return null;
  const r = await signerCall({ op: 'address' });
  const a = r && (r.address || r.addr || r.wallet);
  return (typeof a === 'string' && /^0x[0-9a-fA-F]{40}$/.test(a)) ? a : null;
}
function sendLive(data, gas, maxFeePerGas, maxPriorityFeePerGas) {
  return signerCall({ op: 'send', chain: 'ethereum', to: EXEC_LIVE, data, value: '0x0',
    gas: '0x' + gas.toString(16), maxFeePerGas: '0x' + maxFeePerGas.toString(16),
    maxPriorityFeePerGas: '0x' + maxPriorityFeePerGas.toString(16) });
}
// --- durable PRE-SEND INTENT (review 69bab952 2026-11-10T12:11Z, checklist 2/9/10) ---
// The reviewer's second boundary: a process exit (or a failed first live_send append) after the
// signer broadcasts, but BEFORE any durable accepted-send evidence is written, left NO evidence at
// all — state.json was pre-send and the log had no live_send record, so the next boot resumed
// sending with the broadcast unaccounted. Fix: main() persists a pre-send INTENT (this trade, its
// wall timestamp, the bot wallet's nonce baseline) BEFORE the signer call. While the intent is
// unresolved the send gate stays closed (no later signer call occurs), and reconcileIntent below
// clears it only after a definitive rejection or a reconciled broadcast: the nonce baseline shows
// whether the wallet broadcast anything, and a bounded scan of the last blocks' receipts finds the
// transaction hash, which then settles exactly like any accepted send (its gas joins the total).
// INTENT_RESOLVE_MAX_MS bounds the unresolved wait: a signed tx (maxFeePerGas 2.0 gwei; measured
// relay gasPrice 0.16 gwei on 2026-11-06) is includable within ~1 block (12 s) under any base fee
// below the signed cap, so 1200 s without ANY new transaction from the bot wallet bounds pool
// queueing far beyond the observed base-fee spikes. The expire risk is bounded by the signed
// ceiling 1050000 x 2 gwei = 0.0021 ETH (~4.5 USD at the 2026-11-10 price): a tx included after
// its nonce stopped advancing pays at most that unmeasured gas, below the 30 USD stop.
const INTENT_RESOLVE_MAX_MS = 1200 * 1000;
const INTENT_SCAN_BLOCKS = 16; // bounded receipt scan per cycle while an intent is unresolved (~3 min of blocks; the broadcast is nonce-confirmed the cycle after inclusion, so its block is inside the window)
async function txCountSafe(wallet) { try { const c = await rpc('eth_getTransactionCount', [wallet, 'latest']); return c == null ? null : Number(hex2bn(c)); } catch (e) { return null; } }
async function reconcileIntent(st, wallet, head, fetchers) { // returns 'reconciled' | 'expired' | null; injectable fetchers for the offline proof
  const F = fetchers || {};
  const txCount = F.txCount || txCountSafe;
  const blockReceipts = F.blockReceipts || ((bhex) => rpc('eth_getBlockReceipts', [bhex]));
  const it = st.liveLoss && st.liveLoss.intent;
  if (!it) return null;
  const baseline = typeof it.nonce_baseline === 'number' ? it.nonce_baseline : null; // null: txCount unreadable at intent time — rely on the receipt scan alone
  const cntRaw = baseline === null ? null : await txCount(wallet);
  const cnt = cntRaw === null || cntRaw === undefined ? null : Number(cntRaw);
  let foundHash = null;
  for (let b = Math.max(1, Number(head) - INTENT_SCAN_BLOCKS); b <= Number(head) && !foundHash; b++) {
    let rs = null; try { rs = await blockReceipts('0x' + b.toString(16)); } catch (e) {}
    if (!Array.isArray(rs)) continue; // a failed block read retries next cycle
    for (const tx of rs) {
      if (!tx || typeof tx.hash !== 'string' || typeof tx.from !== 'string') continue;
      if (/^0x[0-9a-fA-F]{64}$/.test(tx.hash) && tx.from.toLowerCase() === String(wallet).toLowerCase() && tx.to && tx.to.toLowerCase() === EXEC_LIVE.toLowerCase()) { foundHash = tx.hash; break; }
    }
  }
  if (foundHash) {
    st.liveLoss.pending.push(foundHash); st.liveLoss.intent = null; // the broadcast is reconciled: its hash settles like any accepted send
    if (st.trades && st.trades[it.trade]) delete st.trades[it.trade]; // the bid happened: never bid this trade again
    log({ type: 'intent_reconciled', trade: it.trade, hash: foundHash }, F.logFile);
    return 'reconciled';
  }
  const broadcastConfirmed = cnt !== null && baseline !== null && cnt > baseline; // the wallet nonce moved: the tx is broadcast and awaitable — never expire while confirmed
  if (!broadcastConfirmed && Date.now() - (typeof it.ts === 'number' ? it.ts : 0) > INTENT_RESOLVE_MAX_MS) {
    st.liveLoss.intent = null;
    if (st.trades && st.trades[it.trade]) st.trades[it.trade].liveFailed = true; // the broadcast never appeared: this trade is done (no retry, no measured loss)
    log({ type: 'intent_expired', trade: it.trade, nonce_baseline: baseline, head: Number(head), why: `no new transaction from the bot wallet for ${INTENT_RESOLVE_MAX_MS / 1000}s: the broadcast never appeared (unmeasured gas bounded by the signed ceiling)` }, F.logFile);
    return 'expired';
  }
  return null;
}
// Fresh UPPER valuation of ETH/USD in micro-USD from the on-chain Chainlink
// ETH/USD feed, read through the RPC relay (review bce15686: paper reads go
// through the relay): latestRoundData() answer x PRICE_MARGIN, read FRESH on
// every cycle (no TTL cache — review add09a2c checklist item 3). The round must be at most ORACLE_MAX_AGE_S seconds old against
// the bot's wall clock (feed timestamps are wall-clock aligned on this chain:
// volatile cadence 1236 s, quiet-hour gap 3624 s — rounds 09:13:11Z and
// 10:13:35Z on 2026-11-06 — and the chain head lags the wall clock by 82 s
// measured 10:14Z, so wall-clock age is the conservative choice).
// null = read failed/stale: the send gate fails closed.
let priceMicro = null, oracleAgeS = null;
async function ethUpperPriceMicro() {
  const now = Date.now();
  try {
    const r = await rpc('eth_call', [{ to: FEED_ETHUSD, data: '0xfeaf968c' }, 'latest']); // latestRoundData()
    if (typeof r !== 'string' || r.length < 322) throw new Error(`bad oracle return ${String(r).slice(0, 40)}`);
    const word = (i) => BigInt('0x' + r.slice(2 + i * 64, 2 + (i + 1) * 64));
    const answer = word(1), updatedAt = Number(word(3)); // (roundId, answer, startedAt, updatedAt, answeredInRound)
    if (answer <= 0n) throw new Error(`oracle answer ${answer.toString()}`);
    const age = now / 1000 - updatedAt;
    if (!(age >= 0 && age <= ORACLE_MAX_AGE_S)) throw new Error(`oracle round ${age.toFixed(0)}s old (limit ${ORACLE_MAX_AGE_S}s)`);
    priceMicro = (answer * PRICE_MARGIN_NUM) / (100n * PRICE_MARGIN_DEN); // 8-dec answer -> micro-USD, x PRICE_MARGIN
    oracleAgeS = Math.round(age);
    return priceMicro;
  } catch (e) {
    log({ type: 'error', message: `eth price oracle: ${String(e.message).slice(0, 120)}` });
    priceMicro = null; oracleAgeS = null; // stale or unreadable: this cycle settles nothing and sends nothing
    return null;
  }
}
// bidDutch(address trade, address buy, uint256 minProfitBuy) = 0x1b2f642e (cast sig)
function bidData(trade, minProfitBuy) {
  return '0x1b2f642e' + trade.slice(2).padStart(64, '0') + ETHP.slice(2).padStart(64, '0') +
    minProfitBuy.toString(16).padStart(64, '0');
}
async function simulate(trade, minProfitBuy, wallet) {
  const tx = { from: wallet || FORK_OWNER, to: EXEC_LIVE, data: bidData(trade, minProfitBuy) };
  let params = [tx, 'latest'];
  if (MODE !== 'live') params = [tx, 'latest', { [EXEC_SIM.toLowerCase()]: {
    code: RUNTIME, state: { [SLOT0]: pad(FORK_OWNER) } } }];
  try { await rpc('eth_call', params); return 'ok'; }
  catch (e) { return `revert: ${e.message.slice(0, 160)}`; }
}
// Normalize relay/env/file hex for comparison: strip 0x, lowercase
function normHex(h) { return (h || '').toLowerCase().replace(/^0x/, ''); }

// --- cumulative live-loss stop (decisions/human/2026-11-09-promote-criteria.md §5) ---
// Realized loss = gas actually paid (gasUsed x effectiveGasPrice from the confirmed
// receipt, valued at the fresh upper ETH/USD oracle price) plus any realized principal
// loss; the executor reverts unless it ends with a strict ETH+ gain, so a failed send
// costs gas only. At LIVE_LOSS_STOP_USD cumulative loss the bot stops sending and
// writes the reason to state/STOPPED.json.
const LIVE_LOSS_STOP_USD = 30;
// Fix (review add09a2c 2026-11-10T07:33Z, checklist items 3-4-5-9): settlement runs
// only with THIS cycle's fresh price (pMic from a successful read this cycle; null
// keeps every hash pending); a receipt with a MISSING gasUsed or effectiveGasPrice
// field keeps its hash pending (it was never valued at zero and dropped); each
// settled hash appends a durable {type:'live_loss_settled', hash, live_loss_usd}
// record to the append-only log — the restart-recovery source (item 9). fetchReceipt
// is injectable for the offline test (item 10).
async function liveLossSettle(st, pMic, fetchReceipt, logFile) { // pMic: fresh upper ETH/USD micro-USD or null
  if (pMic === null) return 0; // no fresh valuation: keep pending, settle on a later cycle
  const keep = [];
  let settledN = 0;
  for (const h of st.liveLoss.pending) {
    let r = null;
    try { r = await (fetchReceipt || ((h2) => rpc('eth_getTransactionReceipt', [h2])))(h); } catch (e) {}
    if (!r || r.gasUsed == null || r.effectiveGasPrice == null) { keep.push(h); continue; } // item 4: a missing fee field keeps the hash pending, never valued as zero
    const gasWei = hex2bn(r.gasUsed) * hex2bn(r.effectiveGasPrice); // wei spent (ethereum: gas is the only loss component; the executor repays its principal leg atomically)
    st.liveLoss.usd += Number((gasWei * pMic) / 1000000000000000000n) / 1e6; // wei -> ETH (/1e18) and micro-USD -> USD (/1e6): overall 1e24 (review 811c0a9f run 2026-11-09: the old 1e12 divisor overcharged realized loss 1e6-fold, e.g. 760240 gas x 1.5 gwei = 0.00114 ETH = 2.41 USD, not 2.4 million USD)
    log({ type: 'live_loss_settled', hash: h, gas_used: r.gasUsed, effective_gas_price_wei: r.effectiveGasPrice, eth_upper_usd_mic: pMic.toString(), live_loss_usd: st.liveLoss.usd }, logFile);
    settledN++;
  }
  st.liveLoss.pending = keep;
  return settledN;
}
function liveLossStopWrite(st, file) { // item 8: report the write result; the caller keeps stopLogged false until the write SUCCEEDED
  try { fs.writeFileSync(file || STOPPEDF,
    JSON.stringify({ reason: `cumulative live loss ${st.liveLoss.usd.toFixed(2)} USD reached ${LIVE_LOSS_STOP_USD} USD: stop sending`, live_loss_usd: st.liveLoss.usd, at: new Date().toISOString() }) + '\n'); return true; } catch (e) { return false; }
}
// Fix (review 2026-11-09 run 233973f5): the accepted signer hash entered
// liveLoss.pending in memory only, and the state file was written once after the
// whole trade loop; a restart in that interval lost the pending gas charge, and the
// old write was wrapped in a catch that kept polling after a FAILED save. persist()
// writes durably after every liveLoss change and BEFORE another send, and fails
// closed: while the last write failed, live sends are refused until a later write succeeds.
// Fix (review add09a2c checklist item 7): the write is ATOMIC — temp file + rename,
// so a crash mid-write cannot leave a truncated state.json that a later successful
// write would silently re-adopt with a lost hash or total.
let stateWriteFailed = false;
function persist(st, file) { const f = file || STATEF; try { const tmp = f + '.tmp'; fs.writeFileSync(tmp, JSON.stringify(st)); fs.renameSync(tmp, f); stateWriteFailed = false; return true; } catch (e) { stateWriteFailed = true; return false; } }
// Fix (review 2026-11-09, attempt 677 parity): persist the §5 stop reason AS SOON AS
// settlement reaches the threshold — the send-time check in the live bid branch only
// fires when another qualifying trade appears, so without this the reason is never
// written while the threshold sits crossed with no new trades. Called from the cycle
// loop right after liveLossSettle; writes STOPPED.json exactly once (the persisted
// stopLogged flag also guards the send-time branch below).
// Fix (review add09a2c checklist item 8): stopLogged becomes true only when the
// STOPPED.json write SUCCEEDED — a swallowed write error must not mark the stop as
// logged, or the reason file is never persisted and the flag resets across restarts.
function liveLossStopCheck(st, file) {
  if (MODE === 'live' && st.liveLoss.usd >= LIVE_LOSS_STOP_USD && !st.liveLoss.stopLogged) {
    if (!liveLossStopWrite(st, file)) return false; // write failed: keep stopLogged false, retry next cycle
    st.liveLoss.stopLogged = true;
    log({ type: 'send_stop', live_loss_usd: st.liveLoss.usd, max_usd: LIVE_LOSS_STOP_USD, reason: 'settlement reached the stop threshold without a new trade: STOPPED.json persisted, sending stopped' });
    return true;
  }
  return false;
}
// Fix (review add09a2c checklist item 9, recovery rule of review c0654dd1): the
// append-only log is the durable loss history. The recovered total is the LAST
// total durably recorded (heartbeat or live_loss_settled event, in append order);
// every accepted live_send hash whose settlement is NOT durably recorded stays
// pending — a receipt can stay pending through MANY heartbeats while the send gate
// (checklist item 2) blocks sends meanwhile. Returns found=false if the log itself
// is unreadable (then the caller raises the total to the threshold and stops).
// Fix (review b03b0e15 2026-11-10T09:05Z, checklist items 4/9):
// (a) a live_loss_settled record WITHOUT a numeric live_loss_usd cumulative total
//     does NOT clear its hash: the reviewer reproduced an accepted live_send
//     followed by such an incomplete settlement returning {found:true,usd:0,
//     pending:[]} — the hash was "settled" although it was never charged. Only a
//     settlement that carries the cumulative total may remove a hash from pending.
// (b) an existing, readable, NON-EMPTY log with no valid accounting record (no
//     heartbeat total, no settlement with a total, no accepted live_send with a
//     valid hash) fails closed: found=false, the same as an unreadable log. The
//     prior run did something whose loss history cannot be reconstructed — zeroing
//     it and sending risks double-counting past the 30 USD stop.
// (c) a live_halt marker (an accepted send whose txHash could not be reconciled —
//     the send halt below) is durable across restarts: recovery sets halted.
// (d) Fix (review 7025047b 2026-11-10T10:38Z, checklist 2/9/10): main() appends the
//     no-hash live_send record BEFORE the live_halt record. A process exit between
//     those two appends left the accepted no-hash send with NO halt marker, and the
//     prior rule ignored a live_send with ok:true and hash:null entirely — recovery
//     then resumed sending with haltNoHash:false despite an unreconciled broadcast.
//     An accepted (ok:true) live_send WITHOUT a valid hash is now itself a durable
//     halt: recovery sets halted even when the live_halt append never happened.
// (e) Fix (review 69bab952 2026-11-10T12:11Z, checklist 2/9/10): a live_send append
//     flagged transport:true (an ambiguous signer TRANSPORT reply — socket error/close/
//     timeout/truncated JSON, ok NOT true) is an UNRESOLVED send outcome, not a
//     rejection: it is durable accounting that halts sending (halted=true) until the
//     broadcast reconciles, and it does NOT mark the lastSendTs — the durable pre-send
//     intent (state.json, review 69bab952) is only explained by a live_send whose
//     parsed reply arrived (accepted with a hash, or a definitive rejection), so an
//     ambiguous append keeps the intent pending across restarts. lastSendTs (the
//     timestamp of the last parsed-reply live_send) and settled (the array of hashes
//     durably settled with a cumulative total) are returned for the caller's merge of
//     a VALID state.json below.
function recoverLiveLossFromLog(logFile) {
  const f = logFile || LOGF;
  if (!fs.existsSync(f)) return { found: true, fresh: true, usd: 0, pending: [], halted: false, settled: [], lastSendTs: 0 }; // a start with no log at all has no prior run to lose (checklist item 9)
  let lines;
  try { lines = fs.readFileSync(f, 'utf8').split('\n'); } catch (e) { return { found: false, usd: 0, pending: [], halted: false, settled: [], lastSendTs: 0 }; }
  let usd = null, accounting = false, halted = false, lastSendTs = 0;
  const sent = [], settled = new Set();
  for (const l of lines) {
    let o = null;
    try { o = JSON.parse(l); } catch (e) { continue; } // a damaged line is skipped
    if (!o || !o.type) continue;
    if (o.type === 'live_send' && o.ok === true) { accounting = true; const tsV = Date.parse(o.ts) || 0; if (typeof o.hash === 'string' && /^0x[0-9a-fA-F]{64}$/.test(o.hash)) { if (!settled.has(o.hash) && !sent.includes(o.hash)) sent.push(o.hash); } else halted = true; if (tsV > lastSendTs) lastSendTs = tsV; } // review 7025047b: an accepted live_send without a valid hash IS itself a durable halt (the live_halt append may never have happened)
    else if (o.type === 'live_send' && o.ok !== true && o.transport === true) { accounting = true; halted = true; } // review 69bab952: an ambiguous transport reply is an unresolved send — durable accounting that halts sending until reconciliation; it never explains the pre-send intent
    else if (o.type === 'live_send' && o.ok !== true) { const tsV = Date.parse(o.ts) || 0; if (tsV > lastSendTs) lastSendTs = tsV; } // a definitive rejection (older records carry no transport flag): the reply arrived, the outcome is handled — it may explain the pre-send intent, but it is NOT accounting (a rejection pays no gas)
    else if (o.type === 'live_loss_settled' && typeof o.hash === 'string') { if (typeof o.live_loss_usd === 'number') { settled.add(o.hash); usd = o.live_loss_usd; accounting = true; } } // item 4/9: a settlement WITHOUT a valid cumulative total must not clear its hash
    else if (o.type === 'heartbeat' && typeof o.live_loss_usd === 'number') { usd = o.live_loss_usd; accounting = true; }
    else if (o.type === 'live_halt') { accounting = true; halted = true; }
  }
  if (!accounting && lines.some((l) => l.trim().length > 0)) return { found: false, usd: 0, pending: [], halted: false, settled: [], lastSendTs: 0 }; // item 4/9: existing log without valid accounting fails closed (an all-whitespace file is still a fresh start)
  return { found: true, usd: usd === null ? 0 : usd, pending: sent.filter((h) => !settled.has(h)), halted, settled: [...settled], lastSendTs };
}
// Accepted-send classification (checklist 4/9, review b03b0e15): an accepted
// signer reply (ok:true) REQUIRES a valid 32-byte txHash. ok:true without one
// halts sending durably (live_halt below) until the transaction can be
// reconciled — the signer may already have broadcast it, so its gas is an
// unaccounted loss and its trade must not be marked a final rejection.
// Fix (review 69bab952 2026-11-10T12:11Z, checklist 2/10): definitive gained. Only an ok:true with a
// valid hash (accepted) or an ok:false that the signer itself wrote (transport NOT flagged) is a
// DEFINITIVE outcome: the former clears the pre-send intent with a tracked hash, the latter clears it
// as a final rejection. A transport-flagged ok:false (socket close/error/timeout/truncated JSON) is
// NOT definitive: the signer may have broadcast before its reply was lost, so the pre-send intent
// stays pending and the trade is not marked a final rejection.
function classifySendReply(r) {
  const accepted = !!(r && r.ok === true);
  const hash = accepted && typeof r.txHash === 'string' && /^0x[0-9a-fA-F]{64}$/.test(r.txHash) ? r.txHash : null;
  const definitive = accepted || !!(r && r.ok === false && r.transport !== true);
  return { accepted, hash, definitive };
}
// Startup state load for the live-loss accounting (extracted for the offline test):
// in live mode a missing/corrupt state.json is NEVER silently zeroed — the loss
// history is recovered from the durable log first; a STOPPED.json present at
// startup is a sticky stop that refuses sends (checklist item 8).
function recoverLossState(st, mode, stateFile, stoppedFile, logFile) {
  const stoppedFromBoot = mode === 'live' && fs.existsSync(stoppedFile || STOPPEDF);
  let stateRaw = null;
  try { stateRaw = JSON.parse(fs.readFileSync(stateFile || STATEF, 'utf8')); } catch (e) {}
  if (mode === 'live') {
    const rec = recoverLiveLossFromLog(logFile);
    if (!stateRaw || !stateRaw.liveLoss) {
      if (rec.found) {
        st.liveLoss = { usd: rec.usd, pending: rec.pending.slice(), stopLogged: false, haltNoHash: rec.halted === true, intent: null }; // checklist 4/9 (review b03b0e15): a durable live_halt marker (or an ambiguous transport reply, review 69bab952) resumes the halt after a crash
        log({ type: 'state_recovered', live_loss_usd: rec.usd, pending_count: rec.pending.length, halted: rec.halted === true, source: String(logFile || LOGF) });
      } else {
        st.liveLoss = { usd: Math.max(st.liveLoss ? st.liveLoss.usd : 0, LIVE_LOSS_STOP_USD), pending: [], stopLogged: false, haltNoHash: false, intent: null }; // no readable log: raise to the threshold and stop (the reviewer's fail-closed alternative)
        st.liveLoss.stopLogged = liveLossStopWrite(st, stoppedFile || STOPPEDF); // write the DURABLE stop marker the raise implies; a failed write leaves the flag false and the boot re-raises next time
        log({ type: 'state_recovered', live_loss_usd: st.liveLoss.usd, sticky_stop: st.liveLoss.stopLogged, why: 'state.json unreadable and log unreadable: loss raised to the stop threshold, STOPPED.json persisted (fail closed)' });
      }
    } else {
      // Fix (review 69bab952 2026-11-10T12:11Z, checklist 2/9): a VALID state.json is now reconciled
      // against the durable log TOO, before the send gate opens. The reviewer's gap: main() pushed the
      // accepted hash and appended live_send, then died BEFORE persist() — state.json stayed valid and
      // stale (its liveLoss.pending lacks the hash the log already carries, pre-send contents), and the
      // old code loaded that stale state with pending:[] and no halt, opening the send gate. The merge:
      // pending = the log's unsettled hashes PLUS the state's own (minus hashes the log proves settled
      // with a cumulative total — a stale state may still list one the log charged; re-charging it would
      // double-count the loss), the total is the MAXIMUM of the state and log totals (the conservative
      // direction for the 30 USD stop), the halt comes from either source, and a durable pre-send intent
      // in the stale state stays pending (the send gate stays closed) unless a live_send whose parsed
      // reply arrived was appended AFTER the intent was written (lastSendTs).
      if (!rec.found) {
        st.liveLoss = { usd: Math.max(typeof stateRaw.liveLoss.usd === 'number' ? stateRaw.liveLoss.usd : 0, LIVE_LOSS_STOP_USD), pending: [], stopLogged: false, haltNoHash: false, intent: null };
        st.liveLoss.stopLogged = liveLossStopWrite(st, stoppedFile || STOPPEDF);
        log({ type: 'state_recovered', live_loss_usd: st.liveLoss.usd, sticky_stop: st.liveLoss.stopLogged, why: 'state.json valid but the log carries no reconstructable accounting: loss raised to the stop threshold, STOPPED.json persisted (fail closed, review 69bab952)' });
      } else {
        const settledSet = new Set(rec.settled);
        const pending = rec.pending.slice();
        const sp = Array.isArray(stateRaw.liveLoss.pending) ? stateRaw.liveLoss.pending : [];
        for (const h of sp) if (typeof h === 'string' && /^0x[0-9a-fA-F]{64}$/.test(h) && !settledSet.has(h) && !pending.includes(h)) pending.push(h);
        let intent = stateRaw.liveLoss.intent && typeof stateRaw.liveLoss.intent === 'object' && !Array.isArray(stateRaw.liveLoss.intent) ? stateRaw.liveLoss.intent : null;
        if (intent && rec.lastSendTs > (typeof intent.ts === 'number' ? intent.ts : 0)) intent = null; // the durable log already records the signer reply that followed the pre-send intent: the outcome was handled before the crash
        const halt = rec.halted === true || stateRaw.liveLoss.haltNoHash === true;
        st.liveLoss = { usd: Math.max(typeof stateRaw.liveLoss.usd === 'number' ? stateRaw.liveLoss.usd : 0, rec.usd), pending, stopLogged: stateRaw.liveLoss.stopLogged === true, haltNoHash: halt, intent };
        log({ type: 'state_merged', live_loss_usd: st.liveLoss.usd, pending_count: pending.length, halted: halt, intent_pending: st.liveLoss.intent !== null, why: 'valid state.json reconciled against the durable log: accepted sends the state lost stay pending, an unresolved pre-send intent keeps the send gate closed (review 69bab952)' });
      }
      stateRaw.liveLoss = st.liveLoss; // main() then applies the MERGED liveLoss via Object.assign, not the stale file's
    }
    if (stoppedFromBoot) st.liveLoss.stopLogged = true; // sticky across restarts
  }
  return { stoppedFromBoot, stateRaw };
}
async function main() {
  const wallet = await signerAddress();
  if (MODE === 'live') {
    // Startup gate (live-operator review 2026-11-10T17:05Z): live mode needs a valid
    // gate-deployed executor address (EXECUTOR_ADDR env, fallback state/executor.json), a
    // signer address, and the proven runtime deployed AT that address — franken-dutch's
    // pattern: compare eth_getCode with executor-runtime.hex before sending anything. The
    // executor stores owner/leg3Variant/repayMode in storage (ReserveDutch.sol), never in
    // immutables, so the gate deployment matches the pinned runtime byte for byte.
    EXEC_LIVE = resolveExecAddr('live');
    if (!EXEC_LIVE || !wallet) {
      log({ type: 'fatal', message: `live mode needs EXECUTOR_ADDR (or state/executor.json) and a signer address (exec=${EXEC_LIVE} wallet=${wallet})` });
      process.exit(1);
    }
    if (!RUNTIME_OK) { log({ type: 'fatal', message: 'live mode needs the pinned executor-runtime.hex (runtime missing/invalid, fail closed)' }); process.exit(1); }
    let deployed = '';
    try { deployed = await rpc('eth_getCode', [EXEC_LIVE, 'latest']); }
    catch (e) { log({ type: 'fatal', message: `executor runtime read failed: ${String(e.message).slice(0, 120)}` }); process.exit(1); }
    if (normHex(deployed) !== normHex(RUNTIME)) {
      log({ type: 'fatal', message: `deployed runtime differs from the proven executor-runtime.hex (exec=${EXEC_LIVE} deployed_bytes=${normHex(deployed).length / 2} proven_bytes=${normHex(RUNTIME).length / 2})` });
      process.exit(1);
    }
    log({ type: 'executor_ok', exec: EXEC_LIVE, runtime_bytes: normHex(RUNTIME).length / 2 });
  }
  let st = { cursorBlock: null, trades: {}, liveLoss: { usd: 0, pending: [], stopLogged: false, haltNoHash: false, intent: null } };
  const rec = recoverLossState(st, MODE, STATEF, STOPPEDF, LOGF); // checklist item 9: live loss is recovered from the durable log, never silently zeroed; a VALID stale state.json is reconciled against the log too (review 69bab952)
  const stoppedFromBoot = rec.stoppedFromBoot; // checklist item 8: STOPPED.json at startup is a sticky stop
  if (rec.stateRaw) Object.assign(st, rec.stateRaw); // recoverLossState merged the stale liveLoss into rec.stateRaw before this (review 69bab952)
  if (!st.trades) st.trades = {};
  if (!st.liveLoss) st.liveLoss = { usd: 0, pending: [], stopLogged: false, haltNoHash: false, intent: null }; // pre-2026-11-09 state files have no key
  if (st.liveLoss.intent === undefined) st.liveLoss.intent = null;
  if (stoppedFromBoot) st.liveLoss.stopLogged = true;
  log({ type: 'boot', mode: MODE, exec: MODE === 'live' ? EXEC_LIVE : EXEC_SIM, wallet, feed: FEED_ETHUSD,
    gas_budget_gas: GAS_BUDGET_GAS, max_fee_wei: MAX_FEE_WEI.toString(), profit_margin: PROFIT_MARGIN.toString(),
    stopped_from_boot: stoppedFromBoot, live_loss_usd: st.liveLoss.usd, live_loss_pending: st.liveLoss.pending.length, live_loss_halt: st.liveLoss.haltNoHash === true, live_loss_intent: st.liveLoss.intent !== null });
  for (;;) {
    try {
      const head = hex2bn(await rpc('eth_blockNumber', []));
      if (!st.cursorBlock) st.cursorBlock = Number(head - 5000n); // seed: 5000 blocks of history (covers the last pair starts)
      const q = async (topic) => await rpc('eth_getLogs', [{
        fromBlock: '0x' + st.cursorBlock.toString(16), toBlock: '0x' + head.toString(16),
        address: ADDRESSES, topics: [topic, null, pad(WEETH), pad(ETHP)] }]);
      const started = await q(T_STARTED), settled = await q(T_SETTLED);
      for (const e of started) {
        const trade = '0x' + e.topics[1].slice(-40); // left-padded topic words: take the last 40 hex chars
        // Measure the polling-to-inclusion window (review d013d4cb): the wall
        // time of the trade's start block, so a simulate record can state
        // window_s = (our simulate clock - start block timestamp): how much of
        // the auction window (measured 103 blocks ~= 20 min from start to
        // settle, trade 0x527dc250 26348213 -> 26348316) we have consumed when
        // we bid, against a 180 s poll + ~12 s block inclusion. Measurement
        // only: a failed header read leaves startedTs null and window_s null.
        let startedTs = null;
        try {
          const blk = await rpc('eth_getBlockByNumber', [e.blockNumber, false]);
          if (blk && blk.timestamp) startedTs = Number(blk.timestamp);
        } catch (e2) {}
        st.trades[trade] = { sell: '0x' + e.topics[2].slice(-40), buy: '0x' + e.topics[3].slice(-40),
          startedBlock: Number(e.blockNumber), startedTs, sims: 0 };
        log({ type: 'started', trade, block: Number(e.blockNumber), sell: st.trades[trade].sell, started_ts: startedTs });
      }
      for (const e of settled) {
        const trade = '0x' + e.topics[1].slice(-40);
        if (st.trades[trade]) { log({ type: 'settled', trade, block: Number(e.blockNumber) });
          delete st.trades[trade]; }
      }
      st.cursorBlock = Number(head);
      const gasPrice = hex2bn(await rpc('eth_gasPrice', [])); // after-gas floor input
      const pMic = await ethUpperPriceMicro(); // fresh upper ETH/USD micro-USD, or null
      await liveLossSettle(st, pMic); // settle confirmed live sends' realized gas into the cumulative loss (§5)
      liveLossStopCheck(st); // persist the §5 stop reason as soon as settlement crosses the threshold (no new trade required)
      // Fix (review 69bab952 2026-11-10T12:11Z, checklist 2/9/10): an unresolved durable pre-send
      // intent (the accepted-send evidence persisted BEFORE the signer call) reconciles here: the
      // nonce baseline and bounded receipt scan find the broadcast (its hash joins pending and
      // settles like any accepted send), or expire it once the bot wallet shows no new transaction
      // for INTENT_RESOLVE_MAX_MS. While unresolved, the send gate below stays closed: no later
      // signer call occurs while an outcome is unresolved.
      if (MODE === 'live' && st.liveLoss.intent && wallet) await reconcileIntent(st, wallet, Number(head));
      persist(st); // review 233973f5: settlement/stop/reconciliation changed liveLoss — persist it before this cycle can send
      const feeMarginWei = (gasPrice * 5n) / 4n; // maxFeePerGas at 1.25 x the measured gasPrice: the base fee may rise between our decision and inclusion; the signed cap MAX_FEE_WEI still bounds it
      const feeWei = feeMarginWei < MAX_FEE_WEI ? feeMarginWei : MAX_FEE_WEI;
      const minProfitBuy = PROFIT_MARGIN * BigInt(GAS_BUDGET_GAS) * gasPrice;
      // L upper bound: the whole SIGNED cap (gas x maxFeePerGas ceiling), valued
      // at the fresh upper price -> micro-USD. null price = fail closed, no send.
      const worstGasMic = pMic === null ? null
        : (BigInt(GAS_BUDGET_GAS) * MAX_FEE_WEI * pMic) / 1000000000000000000n;
      const tipWei = gasPrice < TIP_WEI ? gasPrice : TIP_WEI;
      for (const trade of Object.keys(st.trades)) {
        const t = st.trades[trade];
        if (t.buy.toLowerCase() !== ETHP || t.sell.toLowerCase() !== WEETH) continue;
        if (!RUNTIME_OK) { log({ type: 'skip', trade, why: 'executor runtime missing/invalid (fail closed)' }); continue; }
        if (pMic === null) { log({ type: 'skip', trade, why: 'fresh upper ETH/USD oracle price missing/stale (fail closed)' }); continue; }
        if (gasPrice > MAX_FEE_WEI) { log({ type: 'skip', trade, why: `gasPrice ${gasPrice} > fee cap ${MAX_FEE_WEI} (fail closed)` }); continue; }
        if (worstGasMic > MAX_LOSS_USD_MICRO) { log({ type: 'skip', trade, why: `worst gas ${worstGasMic} micro-USD > 20000000 (fail closed)` }); continue; }
        if (t.liveFailed) continue; // signer rejection is final for this trade
        const res = await simulate(trade, minProfitBuy, wallet);
        t.sims++; t.lastSim = res;
        log({ type: 'simulate', trade, sims: t.sims, sim_result: res,
          min_profit_wei: minProfitBuy.toString(), gas_price_wei: gasPrice.toString(),
          gas_budget_gas: GAS_BUDGET_GAS, eth_upper_usd_mic: pMic.toString(),
          oracle_age_s: oracleAgeS, window_blocks: Number(head) - t.startedBlock, gas_usd_cap_micro: 20000000, // enforced IN the transaction: ReserveDutch.bidDutch reverts GAS_USD unless (its gas ceiling x tx.gasprice) valued at the execution-block Chainlink answer <= 20.00 USD (ORACLE_STALE <= 3660 s on-chain too)
          window_s: t.startedTs === null ? null : Math.round(Date.now() / 1000 - t.startedTs), // wall seconds from the trade's start block to this simulate decision (poll 180 s + block ~12 s inclusion on top; the incumbents took 1044-1332 s from start, scratch/reserve-research/fill_windows.json)
          worst_gas_usd_mic: worstGasMic.toString() });
        if (res === 'ok' && MODE === 'live') { // one bid per trade; send through the signer
          if (stateWriteFailed) { log({ type: 'skip', trade, why: 'state persistence failed — fail closed, no send until the next successful state write (review 233973f5)' }); continue; }
          if (st.liveLoss.pending.length > 0 || st.liveLoss.haltNoHash === true || st.liveLoss.intent) { log({ type: 'send_pending', trade, pending_hashes: st.liveLoss.pending.slice(-3), halted_no_hash: st.liveLoss.haltNoHash === true, intent_pending: st.liveLoss.intent !== null, why: 'an accepted send awaits its receipt settlement (or an accepted send without a valid txHash, or an unresolved pre-send intent halts sending): pending receipts block all later sends (checklist item 2, review add09a2c; item 4/9 halt, review b03b0e15; pre-send intent, review 69bab952)' }); continue; } // checklist item 2 + 4/9 + 2/10
          if (stoppedFromBoot || st.liveLoss.usd >= LIVE_LOSS_STOP_USD) { // §5 cumulative-loss stop: stop sending, reason in state/STOPPED.json; item 8: a STOPPED.json present at startup refuses sends at startup too
            if (!st.liveLoss.stopLogged) { if (liveLossStopWrite(st)) { st.liveLoss.stopLogged = true; persist(st); } } // checklist item 8: only a SUCCESSFUL STOPPED.json write may mark the stop as logged
            log({ type: 'send_stop', trade, live_loss_usd: st.liveLoss.usd, max_usd: LIVE_LOSS_STOP_USD, stopped_from_boot: stoppedFromBoot });
            continue;
          }
          // Fix (review 69bab952 2026-11-10T12:11Z, checklist 2/9/10): persist a DURABLE PRE-SEND INTENT
          // BEFORE the signer call. If the process exits (or the first live_send append fails) after the
          // signer broadcasts, the accepted-send evidence already exists on disk; startup keeps the send
          // gate closed and reconcileIntent clears it only after a definitive rejection or a reconciled
          // receipt (nonce baseline + bounded receipt scan, INTENT_RESOLVE_MAX_MS above).
          st.liveLoss.intent = { trade, ts: Date.now(), nonce_baseline: await txCountSafe(wallet) };
          if (!persist(st)) { log({ type: 'skip', trade, why: 'pre-send intent persist failed: fail closed, no send this cycle (review 69bab952)' }); continue; }
          const r = await sendLive(bidData(trade, minProfitBuy), GAS_BUDGET_GAS, feeWei, tipWei);
          // signer receipt (farmbot_signer docs): {ok:true, txHash, nonce} or {ok:false, error}
          const { accepted, hash, definitive } = classifySendReply(r); // checklist 4/9 (review b03b0e15): ok:true REQUIRES a valid 32-byte txHash; checklist 2/10 (review 69bab952): a transport-flagged failure is ambiguous, not a final rejection
          // Fix (review 7025047b 2026-11-10T10:38Z, checklist 2/10): raise the in-memory send-gate state
          // BEFORE the first log append. An accepted reply is already a broadcast the signer may have sent;
          // if the live_send append itself throws, the outer catch skips the rest of this iteration, but
          // pending/haltNoHash are set — the send gate stays closed on the next cycle too (a pending receipt
          // or the no-hash halt blocks all later sends, checklist item 2); the next cycle's settlement
          // persist() makes the hash durable. The durable live_halt marker below may never be appended
          // (crash between appends): recovery (d) above treats the no-hash live_send itself as the halt.
          if (accepted && hash) {
            st.liveLoss.pending.push(hash); st.liveLoss.intent = null; // accepted send: track its gas before any append can fail; the intent is explained by its hash
            log({ type: 'live_send', trade, ok: true, hash, nonce: typeof (r && r.nonce) === 'number' ? r.nonce : null, error: null });
            delete st.trades[trade]; persist(st); // accepted: one bid per trade; settle its gas once the receipt is visible; review 233973f5: persist the accepted hash BEFORE another send
          } else if (accepted) {
            st.liveLoss.haltNoHash = true; st.liveLoss.intent = null; // accepted without a valid hash: close the gate in memory first; the no-hash live_send record itself is the durable halt (recovery rule d)
            log({ type: 'live_send', trade, ok: true, hash: null, nonce: typeof (r && r.nonce) === 'number' ? r.nonce : null, error: 'ok without valid txHash' });
            log({ type: 'live_halt', trade, why: 'accepted signer send without a valid txHash: sending halted durably until the transaction can be reconciled (checklist 4/9, review b03b0e15)' });
            persist(st);
          } else if (!definitive) {
            // Ambiguous TRANSPORT outcome (socket close/error/timeout/truncated JSON — signerCall's
            // transport:true): the signer may have broadcast before its reply was lost. The trade is NOT
            // a final rejection and the durable pre-send intent stays SET (it was persisted before the
            // call): the send gate remains closed and reconcileIntent finds or expires the broadcast
            // before any later send (review 69bab952: "keep the intent pending for ambiguous transport
            // outcomes"; no later signer call occurs while an outcome is unresolved).
            log({ type: 'live_send', trade, ok: null, hash: null, nonce: null, transport: true, error: String((r && r.error) || 'ambiguous signer transport outcome').slice(0, 160) });
          } else {
            st.liveLoss.intent = null; t.liveFailed = true; // definitive rejection is final: log it, never retry; the intent is cleared with it
            log({ type: 'live_send', trade, ok: false, hash: null, nonce: typeof (r && r.nonce) === 'number' ? r.nonce : null, error: String((r && r.error) || 'signer rejection').slice(0, 160) });
            persist(st);
          }
        }
      }
      persist(st); // review 233973f5: the cycle-end write re-clears the fail-closed flag on success; checklist item 7: the write is atomic (temp + rename)
      // The heartbeat carries the durable total: restart recovery (checklist item 9) reads the LAST such total from the append-only log.
      log({ type: 'heartbeat', head: Number(head), active: Object.keys(st.trades).length, live_loss_usd: st.liveLoss.usd, live_loss_pending: st.liveLoss.pending.length, live_loss_halt: st.liveLoss.haltNoHash === true, live_loss_intent: st.liveLoss.intent !== null, live_loss_stop_usd: LIVE_LOSS_STOP_USD });
    } catch (e) { log({ type: 'error', message: String(e.message).slice(0, 300) }); }
    await new Promise(r => setTimeout(r, POLL_MS));
  }
}
// Offline-test surface (checklist item 10): the settle/stop/recovery functions are
// exported and main() runs only when this file is executed, so scratch/reserve-dutch-fix/settle-proof.js
// can require() the bot and drive them offline with injected receipts and scratch files.
module.exports = { liveLossSettle, liveLossStopWrite, liveLossStopCheck, persist, recoverLiveLossFromLog, recoverLossState, classifySendReply, reconcileIntent, txCountSafe, hex2bn, LIVE_LOSS_STOP_USD, INTENT_RESOLVE_MAX_MS, EXEC_LIVE, resolveExecAddr, normHex, RUNTIME_OK, EXEC_SIM, DIR };
if (require.main === module) { main().catch(e => { log({ type: 'fatal', message: String(e.message) }); process.exit(1); }); }
