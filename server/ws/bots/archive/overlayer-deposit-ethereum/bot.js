// Overlayer OVault-C+ deposit bot (lead 114).
// Deposit USDC principal into OVault-C+ (ERC4626 that auto-compounds Aave interest),
// hold until the accrued revenue reaches PROFIT_MIN_USD, exit at par, repeat.
// The OvltDeposit executor (fork-proven, manifest fork_evidence) does every leg in one
// transaction and reverts (NoProfit) unless the owner's balance ended higher: the
// worst-case realized loss is gas only.
// Paper mode: simulates the executor's guard decision with the live vault state
// (convertToAssets preview reads on mainnet through the relay; the bytecode path was
// fork-proven with these same guard inputs). Live mode: sends the executor calls
// through the signer socket; cumulative realized gas loss settles from receipts and
// stops the bot at LIVE_LOSS_STOP_USD (live-loss-stop checklist, wiki pitfalls).
'use strict';
const fs = require('fs');
const net = require('net');
const path = require('path');

const DIR = __dirname;
const RELAY = process.env.RPC_RELAY_URL, LANE = process.env.RPC_LANE || 'paper';
const MODE = process.env.BOT_MODE || 'paper';
const ENDPOINT = `${RELAY}/ethereum?lane=${LANE}`;
const LOGF = path.join(DIR, 'logs', 'bot.jsonl');
const STATEF = path.join(DIR, 'state', 'state.json');
const STOPPEDF = path.join(DIR, 'state', 'STOPPED.json');
const SIGNER_SOCK = process.env.SIGNER_SOCK || '/run/farm/signer.sock';
const EXEC_LIVE = process.env.EXEC_ADDRESS || null; // gate sets it after deploying the executor

const USDC = '0xa0b86991c6218b36c1d19d4a2e9eb0ce3606eb48';
const OVAULT = '0x8aC6AD5D76D07B202832f323888B64286E944A9e';
const FEED_ETHUSD = '0x5f4ec3df9cbd43714fe2740f5e3616155c5b8419'; // Chainlink ETH/USD, 8 dec (reserve-dutch measured)
const PAPER_WALLET = '0x000000000000000000000000000000000000d0c1'; // paper principal holder (reads only)

const SEL = {
  convertToAssets: '0x07a2d13a', // convertToAssets(uint256)
  deposit: '0xe2bbb158',         // deposit(uint256,uint256) on the executor
  exit: '0x2af9cc41',            // exit(uint256,uint256) on the executor
  balanceOf: '0x70a08231',       // balanceOf(address)
  allowance: '0xdd62ed3e',       // allowance(address,address)
  approve: '0x095ea7b3',         // approve(address,uint256)
  latestRoundData: '0xfeaf968c', // Chainlink aggregator latestRoundData()
};

const PRINCIPAL6 = 380_000_000n;      // 380 USD of 6-decimal USDC principal (manifest principal_usdc)
const MIN_DEPOSIT6 = 20_000_000n;     // skip a live deposit below 20 USD of balance
const PROFIT_MIN6 = 250_000n;         // exit when predicted profit >= 0.25 USD (6-dec units); measured accrual 0.056 USD/day per 400 USD -> first exit ~4.5 days
const PROFIT_MARGIN_NUM = 995n, PROFIT_MARGIN_DEN = 1000n; // minShares = 0.5 % below the convertToAssets-based estimate (it already prices the vault's redeem fee: conservative)
const DEPOSIT_GAS = 700_000, APPROVE_GAS = 65_000, EXIT_GAS = 200_000; // fork deposit gasUsed 483281 x 1.45 margin
const MAX_FEE_WEI = 2_000_000_000n, PRIORITY_WEI = 100_000_000n;      // signed ceiling 700000 x 2 gwei = 0.0014 ETH (~3 USD at the measured ETH/USD ~2100): L bound
const POLL_MS = 60_000;               // vault accrual is a day-scale process
const CYCLE_LOG_EVERY = 15;           // log the deployed-phase accrual estimate every 15 polls (~15 min)
const LIVE_LOSS_STOP_USD = 30;        // cumulative realized live loss (gas paid from receipts)
const ORACLE_MAX_AGE_S = 3960;        // reserve-dutch measured quiet-hour round gap 3624 s + delivery + head lag + poll margin
const PRICE_MARGIN_NUM = 112n, PRICE_MARGIN_DEN = 100n; // measured max 10.30 % move over the window

const pad = (n) => n.toString(16).padStart(64, '0');
const hex2bn = (h) => BigInt(h === '0x' || h == null || h === '' ? 0 : h);

let idc = 0;
async function rpc(method, params) {
  const r = await fetch(ENDPOINT, { method: 'POST', headers: { 'content-type': 'application/json' },
    body: JSON.stringify({ jsonrpc: '2.0', id: ++idc, method, params }) });
  const j = await r.json();
  if (j.error) throw new Error(`${method}: ${JSON.stringify(j.error).slice(0, 160)}`);
  return j.result;
}
function log(o, file) { o.ts = new Date().toISOString(); fs.appendFileSync(file || LOGF, JSON.stringify(o) + '\n'); }

function signerCall(req) { // one JSON line over the signer socket; resolves the parsed reply (never throws)
  return new Promise((resolve) => {
    const s = net.connect(SIGNER_SOCK);
    let buf = '';
    s.on('connect', () => s.write(JSON.stringify(req) + '\n'));
    s.on('data', (d) => { buf += d.toString(); if (buf.endsWith('\n')) { s.end(); try { resolve(JSON.parse(buf)); } catch (e) { resolve({ ok: false, error: 'bad signer json' }); } } });
    s.on('error', (e) => resolve({ ok: false, error: String(e).slice(0, 200) }));
  });
}

// --- atomic state persistence (checklist item 7): temp file + rename, sticky failure flag ---
let writeFailed = false;
function saveState(st) { // returns ok; a failed write sets the sticky flag and refuses sends until a later write succeeds
  try {
    const tmp = STATEF + '.tmp';
    fs.writeFileSync(tmp, JSON.stringify(st, (k, v) => typeof v === 'bigint' ? v.toString() : v)); // BigInt -> decimal string (the loader re-reads shares/principal6 with BigInt())
    fs.renameSync(tmp, STATEF);
    writeFailed = false;
    return true;
  } catch (e) { writeFailed = true; log({ type: 'state_write_failed', error: String(e.message).slice(0, 120) }); return false; }
}
function loadStateRaw() { // {fresh:true} when no file yet; throws (-> recovery) when the file exists but is unreadable
  try { return { st: JSON.parse(fs.readFileSync(STATEF, 'utf8')), fresh: false }; }
  catch (e) { if (e.code === 'ENOENT') return { st: null, fresh: true }; throw e; }
}

function newState() {
  return { phase: 'idle', principal6: PRINCIPAL6, shares: 0n, cycle_ts: new Date().toISOString(),
    liveLoss: { usd: 0, pending: [] }, allowanceApproved: false };
}

// --- live cumulative loss (checklist items 1-6, 8-9): one send path, pending blocks
// sends, settlement only on THIS cycle's fresh price, missing fee fields keep the hash
// pending, wei x micro-USD / 1e24, durable live_loss_settled per hash, STOPPED.json sticky ---
async function liveLossSettle(st, pMic, fetchReceipt, logFile) { // pMic: fresh upper ETH/USD micro-USD or null
  if (pMic === null) return 0; // no fresh valuation this cycle: keep everything pending
  const keep = [];
  for (const h of st.liveLoss.pending) {
    let r = null;
    try { r = await (fetchReceipt || ((h2) => rpc('eth_getTransactionReceipt', [h2])))(h); } catch (e) {}
    if (!r || r.gasUsed == null || r.effectiveGasPrice == null) { keep.push(h); continue; } // item 4: a missing fee field keeps the hash pending, never valued as zero
    const gasWei = hex2bn(r.gasUsed) * hex2bn(r.effectiveGasPrice); // ethereum gas is the only loss component: every executor leg reverts unless the owner balance grew
    st.liveLoss.usd += Number((gasWei * pMic) / 1000000000000000000n) / 1e6; // wei -> USD: /1e18 (ETH) and /1e6 (micro-USD) = /1e24 overall
    log({ type: 'live_loss_settled', hash: h, gas_used: r.gasUsed, effective_gas_price_wei: r.effectiveGasPrice,
      eth_upper_usd_mic: pMic.toString(), live_loss_usd: Number(st.liveLoss.usd.toFixed(4)) }, logFile);
  }
  st.liveLoss.pending = keep;
  return st.liveLoss.pending.length === 0 ? 1 : 0; // 1 = settled everything, safe to send again
}
function liveLossStopWrite(st, file) { // item 8: report the write result; caller keeps stopLogged false until it SUCCEEDED
  try { fs.writeFileSync(file || STOPPEDF, JSON.stringify({ reason: `cumulative live loss ${st.liveLoss.usd.toFixed(2)} USD reached ${LIVE_LOSS_STOP_USD} USD: stop sending`,
    live_loss_usd: st.liveLoss.usd, at: new Date().toISOString() }) + '\n'); return true; } catch (e) { return false; }
}
// checklist item 9: recover pending accepted hashes from the append-only log when the
// state file is unreadable; returns the reconstructed loss state or throws (fail closed).
function recoverLossFromLog(logFile) {
  const lines = fs.readFileSync(logFile, 'utf8').trim().split('\n');
  const settled = new Set(), accepted = [];
  let usd = 0, stopped = false;
  for (const l of lines) { let o; try { o = JSON.parse(l); } catch (e) { continue; }
    if (o.type === 'live_send_accepted' && o.hash) accepted.push(o.hash);
    if (o.type === 'live_loss_settled' && o.hash) { settled.add(o.hash); if (o.live_loss_usd != null) usd = o.live_loss_usd; }
    if (o.type === 'live_loss_stop') stopped = true; }
  return { usd, pending: accepted.filter((h) => !settled.has(h)), stopped };
}

// fresh UPPER ETH/USD micro-USD from the Chainlink feed, read every settle cycle (no TTL cache)
async function ethUpperPriceMicro(fetch) {
  try {
    const r = await (fetch || rpc)('eth_call', [{ to: FEED_ETHUSD, data: SEL.latestRoundData }, 'latest']);
    if (typeof r !== 'string' || r.length < 322) throw new Error(`bad oracle return ${String(r).slice(0, 40)}`);
    const word = (i) => BigInt('0x' + r.slice(2 + i * 64, 2 + (i + 1) * 64));
    const answer = word(1), updatedAt = Number(word(3));
    if (answer <= 0n) throw new Error(`oracle answer ${answer.toString()}`);
    const age = Date.now() / 1000 - updatedAt;
    if (!(age >= 0 && age <= ORACLE_MAX_AGE_S)) throw new Error(`oracle round ${age.toFixed(0)}s old (limit ${ORACLE_MAX_AGE_S}s)`);
    return (answer * PRICE_MARGIN_NUM) / (100n * PRICE_MARGIN_DEN); // 8-dec answer -> micro-USD, x margin
  } catch (e) { log({ type: 'error', message: `eth price oracle: ${String(e.message).slice(0, 140)}` }); return null; }
}

async function signerAddress(fetch) {
  if (MODE !== 'live') return PAPER_WALLET;
  const r = await signerCall({ op: 'address' });
  const a = r && (r.address || r.addr || r.wallet);
  return (typeof a === 'string' && /^0x[0-9a-fA-F]{40}$/.test(a)) ? a : null;
}

// the ONLY live send path (checklist item 1): gated by stopped flag, pending receipts,
// a successful last state write; the signer picks the nonce; a rejection is final.
let stopLogged = false;
async function sendLive(to, data, gas) {
  return signerCall({ op: 'send', chain: 'ethereum', to, data, value: '0x0',
    gas: '0x' + gas.toString(16), maxFeePerGas: '0x' + MAX_FEE_WEI.toString(16), maxPriorityFeePerGas: '0x' + PRIORITY_WEI.toString(16) });
}
function canSend(st) { return MODE === 'live' && !stopLogged && st.liveLoss.pending.length === 0 && !writeFailed; }

function dataDeposit(assets6, minShares) { return SEL.deposit + pad(assets6 * 10n ** 12n) + pad(minShares); } // vault assets are the 18-decimal wrap units
function dataExit(shares, minUsdcOut6) { return SEL.exit + pad(shares) + pad(minUsdcOut6 * 10n ** 12n); }
function dataApprove(spender, amount) { return SEL.approve + spender.slice(2).padStart(64, '0') + pad(amount); }
function dataBalanceOf(a) { return SEL.balanceOf + a.slice(2).padStart(64, '0'); }
function dataAllowance(o, s) { return SEL.allowance + o.slice(2).padStart(64, '0') + s.slice(2).padStart(64, '0'); }

async function balanceOf(contract, holder) {
  const r = await rpc('eth_call', [{ to: contract, data: dataBalanceOf(holder) }, 'latest']);
  return hex2bn(typeof r === 'string' && r !== '0x' ? r : '0x');
}
async function convertToAssets(shares) { // assets per `shares`; the vault prices the redeem fee in here (conservative)
  const r = await rpc('eth_call', [{ to: OVAULT, data: SEL.convertToAssets + pad(shares) }, 'latest']);
  return hex2bn(typeof r === 'string' && r !== '0x' ? r : '0x');
}

async function mainLoop() {
  let st, recoveredStopped = false;
  try { const { st: loaded, fresh } = loadStateRaw();
    if (fresh) { st = newState(); saveState(st); }
    else { st = loaded; st.liveLoss = st.liveLoss || { usd: 0, pending: [] }; st.shares = BigInt(st.shares ?? 0n); st.principal6 = BigInt(st.principal6); }
  } catch (e) { // item 9: an unreadable live state recovers from the append-only log, fail closed if that fails
    log({ type: 'error', message: `state file unreadable: ${String(e.message).slice(0, 120)}` });
    try { const rec = recoverLossFromLog(LOGF);
      st = newState(); st.liveLoss = { usd: rec.usd, pending: rec.pending };
      recoveredStopped = rec.stopped || fs.existsSync(STOPPEDF);
      log({ type: 'state_recovered', pending_hashes: st.liveLoss.pending.length, live_loss_usd: rec.usd, stopped: recoveredStopped });
      saveState(st);
    } catch (e2) { st = newState(); st.liveLoss = { usd: 0, pending: ['UNKNOWN'] }; log({ type: 'error', message: `log recovery failed: ${String(e2.message).slice(0, 120)}` }); }
  }
  // item 8: a written STOPPED.json at startup keeps the bot stopped across restarts
  if (fs.existsSync(STOPPEDF)) { stopLogged = true; const s = JSON.parse(fs.readFileSync(STOPPEDF, 'utf8')); st.liveLoss.usd = s.live_loss_usd ?? st.liveLoss.usd; }
  if (recoveredStopped) stopLogged = true;

  let polls = 0, execWarned = false, walletAddr = null;
  for (;;) {
    polls++;
    try {
      const head = hex2bn(await rpc('eth_blockNumber', []));
      if (MODE === 'live' && polls % 15 === 1) walletAddr = await signerAddress(); // the signer holds our key only in live mode
      const botAddr = MODE === 'live' ? walletAddr : PAPER_WALLET;
      const ratio = await convertToAssets(10n ** 18n); // assets per 1e18 shares (18-decimal vault units)
      if (!(ratio > 10n ** 17n && ratio < 10n ** 20n)) throw new Error(`vault convertToAssets out of range ${ratio}`); // fail closed
      if (MODE === 'live' && !EXEC_LIVE && !execWarned && polls % 15 === 1) { log({ type: 'error', message: 'EXEC_ADDRESS not set: no sends until the gate deploys the executor' }); execWarned = true; }

      // settle any accepted live receipts with THIS cycle's fresh price before any new send
      if (MODE === 'live' && st.liveLoss.pending.length > 0) {
        const pMic = await ethUpperPriceMicro();
        await liveLossSettle(st, pMic);
        saveState(st); // persist settled hashes before another send
        if (st.liveLoss.usd >= LIVE_LOSS_STOP_USD && !stopLogged) {
          if (liveLossStopWrite(st)) { log({ type: 'live_loss_stop', live_loss_usd: Number(st.liveLoss.usd.toFixed(4)) }); stopLogged = true; }
        }
      }

      const sendReady = MODE !== 'live' || (canSend(st) && !!EXEC_LIVE);
      if (st.phase === 'idle') {
        // live: the wallet's real USDC balance (skip while the signer address is unknown: botAddr null
        // would read USDC's own balance = total supply and send a doomed deposit); paper: st.principal6,
        // i.e. the compounded principal returned by the last exit (first cycle = the manifest principal)
        const assets6 = MODE === 'live' ? (botAddr ? await balanceOf(USDC, botAddr) : null) : st.principal6;
        if (assets6 !== null && assets6 >= MIN_DEPOSIT6 && ratio > 0n) {
          const assets18 = assets6 * 10n ** 12n;                       // 18-decimal wrap / vault asset units
          const sharesEst = (assets18 * 10n ** 18n) / ratio;          // deposit preview at the current rate (floor)
          const minShares = (sharesEst * PROFIT_MARGIN_NUM) / PROFIT_MARGIN_DEN; // shares credited to the owner must reach this
          const sim = sharesEst > 0n ? 'ok' : 'revert: NoProfit(shares)';
          log({ type: 'cycle_deposit', phase: 'idle', sim_result: sim, assets_usdc6: assets6.toString(),
            assets_per_share: ratio.toString(), shares_est: sharesEst.toString(), min_shares: minShares.toString(),
            head: head.toString(), mode: MODE });
          if (MODE !== 'live') {
            if (sim === 'ok') { st.principal6 = assets6; st.shares = sharesEst; st.phase = 'deployed'; saveState(st); }
          } else if (sendReady && !stopLogged) {
            const exec = EXEC_LIVE.toLowerCase();
            if (!st.allowanceApproved) { // USDC allowance owner -> executor once (Circle MAX_APPROVAL: transferFrom never consumes it)
              const a = hex2bn((await rpc('eth_call', [{ to: USDC, data: dataAllowance(botAddr, exec) }, 'latest'])).replace(/^0x$/, '0x') || '0x');
              if (a >= assets6) { st.allowanceApproved = true; saveState(st); }
              else { const r = await sendLive(USDC, dataApprove(exec, (1n << 256n) - 1n), APPROVE_GAS);
                if (r && r.ok) { st.liveLoss.pending.push(r.txHash); log({ type: 'live_send_accepted', hash: r.txHash, op: 'approve' }); saveState(st); }
                else log({ type: 'live_send_rejected', op: 'approve', error: String(r && r.error || 'signer').slice(0, 160) }); }
            } else {
              const r = await sendLive(exec, dataDeposit(assets6, minShares), DEPOSIT_GAS);
              if (r && r.ok) { st.liveLoss.pending.push(r.txHash); st.pendingDepositAssets6 = assets6.toString();
                log({ type: 'live_send_accepted', hash: r.txHash, op: 'deposit', assets_usdc6: assets6.toString(), min_shares: minShares.toString() }); saveState(st); }
              else log({ type: 'live_send_rejected', op: 'deposit', error: String(r && r.error || 'signer').slice(0, 160) });
            }
          }
        } else if (MODE === 'live' && botAddr) { // principal spent (below minimum): re-read after a confirmed deposit/exit transition
          const sharesLive = await balanceOf(OVAULT, botAddr);
          if (st.phase === 'idle' && sharesLive > 0n) { st.phase = 'deployed'; st.shares = sharesLive; saveState(st); log({ type: 'phase_fixed', note: 'vault shares found on the live wallet while idle' }); }
        }
      }

      if (st.phase === 'deployed' && st.shares > 0n) {
        const exitAssets18 = (st.shares * ratio) / 10n ** 18n;         // previewRedeem at the current fee-priced rate
        const exitUsdc6 = exitAssets18 / 10n ** 12n;
        const profit6 = exitUsdc6 > st.principal6 ? exitUsdc6 - st.principal6 : 0n;
        const trigger = profit6 >= PROFIT_MIN6;
        const guard18 = st.principal6 * 10n ** 12n;                    // NoProfit reverts unless USDC out >= principal (18-dec comparison)
        const simOk = exitAssets18 >= guard18;
        if (trigger || polls % CYCLE_LOG_EVERY === 1) {
          log({ type: trigger ? 'cycle_exit' : 'accrual', phase: 'deployed', sim_result: trigger ? (simOk ? 'ok' : 'revert: NoProfit(exit)') : undefined,
            shares: st.shares.toString(), principal_usdc6: st.principal6.toString(), assets_per_share: ratio.toString(),
            exit_usdc6_est: exitUsdc6.toString(), profit_est_usd: Number((profit6 * 1000000n) / 1000000n) / 1e6,
            head: head.toString(), mode: MODE });
        }
        if (trigger) {
          if (MODE !== 'live') {
            if (simOk) { st.principal6 = exitUsdc6; st.shares = 0n; st.phase = 'idle'; saveState(st); }
          } else if (sendReady && !stopLogged) {
            const r = await sendLive(EXEC_LIVE.toLowerCase(), dataExit(st.shares, st.principal6), EXIT_GAS);
            if (r && r.ok) { st.liveLoss.pending.push(r.txHash); log({ type: 'live_send_accepted', hash: r.txHash, op: 'exit',
              shares: st.shares.toString(), min_usdc_out_usdc6: st.principal6.toString() }); saveState(st); }
            else log({ type: 'live_send_rejected', op: 'exit', error: String(r && r.error || 'signer').slice(0, 160) });
          }
        }
      }

      if (MODE === 'live' && walletAddr) { // live phase tracking from the wallet's own balances after receipts settle
        if (st.liveLoss.pending.length === 0 && !stopLogged) {
          const sharesLive = await balanceOf(OVAULT, walletAddr);
          const usdcLive = await balanceOf(USDC, walletAddr);
          if (st.phase === 'idle' && sharesLive > 0n) { st.phase = 'deployed'; st.shares = sharesLive; if (st.pendingDepositAssets6) { st.principal6 = BigInt(st.pendingDepositAssets6); delete st.pendingDepositAssets6; } saveState(st); }
          else if (st.phase === 'deployed' && sharesLive === 0n && st.pendingDepositAssets6 === undefined) {
            if (usdcLive > 0n) { st.principal6 = usdcLive; st.shares = 0n; st.phase = 'idle'; saveState(st); }
          }
        }
      }
      if (polls % 15 === 1) log({ type: 'heartbeat', head: head.toString(), phase: st.phase, principal_usdc6: st.principal6.toString(),
        shares: st.shares.toString(), live_loss_usd: Number(st.liveLoss.usd.toFixed(4)), stopped: stopLogged });
    } catch (e) {
      log({ type: 'error', message: String(e && e.message || e).slice(0, 200) });
      await new Promise((r) => setTimeout(r, 5000));
    }
    await new Promise((r) => setTimeout(r, POLL_MS));
  }
}
if (require.main === module) mainLoop().catch((e) => { log({ type: 'fatal', message: String(e.message) }); process.exit(1); });
module.exports = { liveLossSettle, liveLossStopWrite, recoverLossFromLog, newState, hex2bn, pad, dataDeposit, dataExit, canSend };
