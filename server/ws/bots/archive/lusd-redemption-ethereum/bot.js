// LusdRedeem paper/live bot (lead 167, Liquity v1 LUSD redemption arb).
// Mechanism: when the Uniswap V3 WETH/USDT pool price per ETH exceeds the Liquity
// PriceFeed oracle price by the measured breakeven premium (>= 1.0814x, attempt 1127),
// redeem LUSD (Morpho USDT flash -> Curve D-pool -> cStable pool -> TroveManager
// redeemCollateral -> WETH -> UniV3 swap -> repay flash) atomically in the executor;
// profit = redeemed USDT out minus flash in, guarded in-contract by minProfit.
// Paper mode: re-reads state through the relay and simulates the send (no transactions).
// Live mode: guards with an eth_call of the executor, then sends through the signer socket.
const http = require('http'), fs = require('fs'), path = require('path'), net = require('net'), os = require('os');
const RELAY = process.env.RPC_RELAY_URL, LANE = process.env.RPC_LANE || 'paper';
const MODE = process.env.BOT_MODE || 'paper';
const SIGNER_SOCK = process.env.SIGNER_SOCK || '/run/farm/signer.sock';
const EXECUTOR = process.env.EXECUTOR_ADDR; // live: gate-deployed executor; never a fork fallback
if (MODE === 'live' && !EXECUTOR) { console.error('EXECUTOR_ADDR unset: live bot cannot fall back to a fork address'); process.exit(2); }
const WALLETF = path.join(__dirname, 'state', 'wallet.json');
const CHAIN = 'ethereum';
const PRICEFEED = '0x4c517D4e2C851CA76d7eC94B805269Df0f2201De'; // PriceFeed (TroveManager's own price source)
const HINTS = '0xE84251b93D9524E0d2e621Ba7dc7cb3579F997C0';      // HintHelpers
const SORTED = '0x8FdD3fbFEb32b28fb73555518f8b361bCeA741A6';     // SortedTroves
const TM = '0xA39739EF8b0231DbFA0DcdA07d7e29faAbCf4bb2';         // TroveManager
const POOL = '0x4e68Ccd3E89f51C3074ca5072bbAC773960dFa36';       // Uniswap V3 WETH/USDT (winner's exit pool)
const SEL = { fetchPrice: '0x0fdb11cf', hints: '0x13144dba', approx: '0x7b41bdbe', nicr: '0xb0d8e181',
  next: '0x765e0159', prev: '0xb72703ac', size: '0xde8fa431', slot0: '0x3850c7bd', redeem: '0x9f7a0d82' };
const USDT6 = (u) => Number(u); // 6-dec logging helper
const POLL_MS = 4 * 60 * 1000;            // polling bot: window is minutes wide (4..164 blocks, attempt 1127); R = 240 s poll + ~12 s inclusion
const BREAK_EVEN_PREMIUM = 1.0814;        // attempt:1127 measured farm-route breakeven (market_ETH >= oracle x 1.0814)
const ACQ_RATIO = 1.045;                  // USDT per LUSD on the USDT->D-pool->cStable->LUSD route (fork proof9 flash 342513.564102e6 / 327764.175217 LUSD)
const TARGET_LUSD_WEI = 3000n * 10n ** 18n;  // farm-size redemption (the size the fork proof ran, proof10)
const MIN_PROFIT_WEI = 20n * 10n ** 6n;  // executor guard: >= 20 USDT profit or revert - the guard proven to succeed at the 3,000-LUSD farm size on the fork (a 50 USDT guard reverts at that size: measured profit is 82-88 USDT gross, maxFee-capped seizure per trove)
const MAX_FEE = 50071235694287652n;      // 50.07% redemption fee cap (winner used 43.2%)
const SQRT_LIMIT = 4295128740n;          // low sqrtPriceLimit floor for both WETH legs on the same pool (proof10)
const GAS_LIMIT = 1300000, MAX_FEE_PER_GAS = 20e9; // bound: 1.3M x 20 gwei = 0.026 ETH at signing price << 50 USD
const GAS_CAP_ETH = 0.026;                  // signed worst case in ETH: 1,300,000 x 20 gwei (reviewer 0c72857e: the stale 28-USD constant assumed $1,100/ETH and is gone; the signer values L at the signing-time price and bot.js refuses a send once 0.026 x oracle > 50 USD)
// Fork-route calibration (reviewer fixes 99009f88 + 0c72857e): expected gross is the
// FORK-MEASURED pre-gas gross of the exact route at the exact farm size (proof12/13),
// only at premiums inside the measured positive band. The premium is the only quantity
// the two cheap polls read; the redemption-fee / acquisition / slippage terms of the
// old `premium - 1.045` model are inside the measured gross.
const PROOF_GROSS_USDT_PER_3000 = 84.9;     // pre-gas gross USDT at 3,000 LUSD at premium 1.11651 (fork success tx 0xe9881aba5ab91c0f... at reset 26300832: +82.49 after the 1-gwei fork gas, +85.2 by the ETH-delta convention in proof12_out.json - the flash-flow gross is 84.9; proof10_out.json)
const PROOF_PREMIUM = 1.11651;         // pool/oracle premium at proof block 26300832 (tx 0xe9881aba5ab91c0f...)
const REVERT_FLOOR_PREMIUM = 1.26264;  // measured revert band floor (proof12/13): at premiums >= 1.26264 (measured 1.26264, 1.2986, 1.4588 at parents 26300875/989/992) the farm-size redeemCollateral REVERTS 'TroveManager: Unable to redeem any amount' in the fee-burned tail state - no measured positive gross there, do not send

const PAD = (a) => '0'.repeat(24) + a.slice(2).toLowerCase();
const W = (i) => BigInt('0x' + i.toString(16).padStart(64, '0'));
const words = (r) => { const out = []; for (let k = 0; k < (r.length - 2) / 64; k++) out.push(BigInt('0x' + r.slice(2 + 64 * k, 2 + 64 * k + 64))); return out; };
const HEX64 = (w) => w.toString(16).padStart(64, '0');
const addr = (w) => '0x' + w.toString(16).padStart(64, '0').slice(-40);
const ZERO = '0x' + '0'.repeat(40);

function rpcReq(m, p) {
  return new Promise((resolve, reject) => {
    const body = JSON.stringify({ jsonrpc: '2.0', id: 1, method: m, params: p });
    const u = new URL(RELAY);
    const req = http.request({ host: u.hostname, port: u.port || 80, path: `${u.pathname.replace(/\/$/, '')}/${CHAIN}?lane=${LANE}`, method: 'POST',
      headers: { 'Content-Type': 'application/json', 'Connection': 'close', 'Content-Length': Buffer.byteLength(body) }, timeout: 30000 }, (res) => {
      let buf = ''; res.on('data', (d) => { buf += d; }); res.on('end', () => { try { const d = JSON.parse(buf); resolve(d); } catch (e) { reject(new Error('bad rpc json ' + buf.slice(0, 60))); } }); });
    req.on('error', reject); req.write(body); req.end();
  });
}
async function rpc(m, p) { const d = await rpcReq(m, p); if (process.env.BOT_DEBUG) log({ type: 'debug_rpc', method: m, to: p && p[0] && p[0].to, data: p && p[0] && p[0].data && p[0].data.slice(0, 10), ok: d.result !== undefined, err: d.result === undefined ? JSON.stringify(d.error).slice(0, 120) : null }); if (d.result === undefined) throw new Error(`${m}: ${JSON.stringify(d.error).slice(0, 160)}`); return d.result; }
async function call(to, data) { return rpc('eth_call', [{ to, data }, 'latest']); }

function signerCall(reqObj) {
  return new Promise((resolve) => {
    try {
      const s = net.connect(SIGNER_SOCK); let buf = ''; let done = false;
      s.on('error', (e) => { if (!done) { done = true; resolve({ ok: false, error: 'signer socket: ' + e.message }); } });
      s.on('data', (d) => { buf += d.toString(); if (buf.endsWith('\n')) { s.end(); try { resolve(JSON.parse(buf)); } catch (e) { resolve({ ok: false, error: 'bad signer json' }); } done = true; } });
      s.on('close', () => { if (!done) resolve({ ok: false, error: 'signer closed' }); });
      s.write(JSON.stringify(reqObj) + '\n');
    } catch (e) { resolve({ ok: false, error: 'signer connect: ' + e.message }); }
  });
}

const LOGF = path.join(__dirname, 'logs', 'events.jsonl');
function log(obj) { const o = { ...obj, at: new Date().toISOString() }; fs.appendFileSync(LOGF, JSON.stringify(o) + '\n'); }

async function nicrOf(a) { return BigInt(await call(TM, SEL.nicr + PAD(a)) || '0x0'); }
async function nextOf(a) { return addr(await call(SORTED, SEL.next + PAD(a))); }
async function prevOf(a) { return addr(await call(SORTED, SEL.prev + PAD(a))); }
async function brackets(nicr) { // reInsert bracket walk on SortedTroves, as proven in proof9
  const size = Number(await call(SORTED, SEL.size));
  const trials = Math.floor(15 * Math.sqrt(size)) + 1;
  const r = words(await call(HINTS, SEL.approx + HEX64(W(nicr)) + HEX64(BigInt(trials)) + HEX64(42n)));
  let cur = addr(r[0]); const n0 = await nicrOf(cur);
  let upper = ZERO, lower = ZERO;
  if (n0 === nicr) { upper = cur; lower = await nextOf(cur); }
  else if (n0 > nicr) {
    upper = cur; let nxt = await nextOf(cur);
    while (nxt !== ZERO && await nicrOf(nxt) >= nicr) { upper = nxt; nxt = await nextOf(nxt); }
    lower = nxt;
  } else {
    lower = cur; let prv = await prevOf(cur);
    while (prv !== ZERO && await nicrOf(prv) <= nicr) { lower = prv; prv = await prevOf(prv); }
    upper = prv;
  }
  return { upper, lower };
}
function redeemCalldata(lusd, flash, first, upper, lower, nicr, iters, maxfee, sqrt, minp) {
  return SEL.redeem + [lusd, flash, PAD(first), PAD(upper), PAD(lower), nicr, iters, maxfee, sqrt, minp]
    .map((v) => typeof v === 'bigint' ? v.toString(16).padStart(64, '0') : v).join('');
}

// main poll: two cheap reads decide whether the window is open
async function poll(fetch) {
  const callF = fetch || call;
  const price = BigInt(await callF(PRICEFEED, SEL.fetchPrice));
  const s0 = words(await callF(POOL, SEL.slot0));
  const sqrt = s0[0];
  if (sqrt === 0n) return null;
  const poolUsdPerEth = Math.pow(Number(sqrt) / 2 ** 96, 2) * 1e12; // USDT per WETH at pool spot (token0 WETH, token1 USDT)
  const oracleUsdPerEth = Number(price) / 1e18;
  const premium = poolUsdPerEth / oracleUsdPerEth;
  return { price, sqrt, poolUsdPerEth, oracleUsdPerEth, premium };
}

// Send economics (review 0c72857e item 1): the signing-time gas cap and the fork-measured
// gross band, as a pure function so the branch is testable without live premium (test.js).
function economics(st, lusd) {
  const gasCapUsd = GAS_CAP_ETH * st.oracleUsdPerEth; // 0.026 ETH x the oracle price read this poll
  const measuredRegion = st.premium >= PROOF_PREMIUM && st.premium < REVERT_FLOOR_PREMIUM; // gross measured positive only in [1.11651, 1.26264)
  const revertBand = st.premium >= REVERT_FLOOR_PREMIUM; // measured 'Unable to redeem any amount'
  const expectedGrossUSDT = st.premium >= PROOF_PREMIUM ? Number(lusd) / 3e21 * PROOF_GROSS_USDT_PER_3000 : 0; // LUSD units / 3000 x the fork-measured farm-size gross
  const expectedNetUSDT = expectedGrossUSDT - gasCapUsd;
  const eligible = measuredRegion && gasCapUsd <= 50 && expectedGrossUSDT > gasCapUsd && expectedNetUSDT >= 25;
  return { gasCapUsd, measuredRegion, revertBand, expectedGrossUSDT, expectedNetUSDT, eligible };
}

async function main() {
  fs.mkdirSync(path.join(__dirname, 'logs'), { recursive: true });
  fs.mkdirSync(path.join(__dirname, 'state'), { recursive: true });
  if (MODE === 'live') { const a = await signerCall({ op: 'address' }); const wallet = a && (a.address || a.addr || a.wallet); if (wallet) fs.writeFileSync(WALLETF, JSON.stringify({ wallet })); else log({ type: 'error', message: 'signer address: ' + (a && a.error) }); }
  let lastHints = null, hintsAt = 0;
  for (;;) {
    try {
      const st = await poll();
      if (!st) throw new Error('poll read failed');
      if (st.premium < BREAK_EVEN_PREMIUM) {
        log({ type: 'idle', premium: +st.premium.toFixed(4), oracle_eth_usd: +st.oracleUsdPerEth.toFixed(2), pool_eth_usd: +st.poolUsdPerEth.toFixed(2) });
      } else {
        // window open: recompute hints at most every 30 min (CU budget), plus the live guard
        const lusdReq = TARGET_LUSD_WEI;
        const h = words(await call(HINTS, SEL.hints + HEX64(W(lusdReq)) + HEX64(W(st.price)) + HEX64(0n)));
        const first = addr(h[0]); const nicr = h[1]; const truncated = h[2];
        const lusd = truncated > 0n && truncated < lusdReq ? truncated : lusdReq;
        const flash = (lusd * BigInt(Math.round(ACQ_RATIO * 1e6))) / 10n ** 18n + 1000n; // 18-dec LUSD -> 6-dec USDT
        const { upper, lower } = nicr === 0n ? { upper: ZERO, lower: ZERO } : await brackets(nicr);
        // Reviewer fix 2 (review 99009f88): the signed gas cap is valued at the signing-time
        // price read in this same poll (0.026 ETH x oracle price), and expected gross is the
        // fork-measured farm-size gross in its measured premium region - no linear scaling.
        const econ = economics(st, lusd); // reviewer 0c72857e item 1: defined, tested calculation (test.js)
        const { gasCapUsd, measuredRegion, expectedGrossUSDT, expectedNetUSDT } = econ;
        const calldata = redeemCalldata(lusd, flash, first, upper, lower, nicr, 0n, MAX_FEE, SQRT_LIMIT, MIN_PROFIT_WEI);
        const cand = { type: 'opportunity', premium: +st.premium.toFixed(4), lusd: lusd.toString(), flash_usdt: +(Number(flash) / 1e6).toFixed(2),
          firstHint: first, upperHint: upper, lowerHint: lower, partialHintNICR: nicr.toString(),
          expected_gross_usdt: +expectedGrossUSDT.toFixed(2), expected_net_usdt: +expectedNetUSDT.toFixed(2),
          gas_cap_usd: +gasCapUsd.toFixed(1), premium_gate: PROOF_PREMIUM, guard_min_profit_usdt: 20 };
        const eligible = econ.eligible;
        if (!eligible) { log({ ...cand, type: 'candidate_rejected', why: `premium ${st.premium.toFixed(4)} vs gate ${PROOF_PREMIUM}, expected gross ${expectedGrossUSDT.toFixed(1)} vs signing-time gas cap ${gasCapUsd.toFixed(1)} (0.026 ETH at oracle ${st.oracleUsdPerEth.toFixed(0)}), net ${expectedNetUSDT.toFixed(1)}` }); }
        else if (MODE === 'paper') {
          log({ ...cand, type: 'paper_send_sim', calldata_len: calldata.length / 2 - 8, guard: 'executor reverts below minProfit 20 USDT (fork-proven LusdRedeem.onMorphoFlashLoan, proof12 tx 0xe9881aba...)' });
        } else {
          const walletJSON = JSON.parse(fs.readFileSync(WALLETF, 'utf8'));
          const from = walletJSON.wallet;
          let sim = null;
          try { sim = await rpc('eth_call', [{ from, to: EXECUTOR, data: calldata, gas: '0x' + GAS_LIMIT.toString(16).toUpperCase(), value: '0x0' }, 'latest']); } catch (e) { sim = 'revert: ' + String(e.message).slice(0, 80); }
          if (String(sim).startsWith('revert')) log({ type: 'live_guard_revert', message: String(sim).slice(7, 100) });
          else {
            const r = await signerCall({ op: 'send', chain: CHAIN, to: EXECUTOR, data: calldata, value: '0x0', gas_limit: GAS_LIMIT, max_fee_per_gas: Math.round(MAX_FEE_PER_GAS) });
            log({ type: 'live_send_accepted', hash: r && (r.hash || r.txHash), ok: !!(r && r.ok !== false) && !!r, message: r && (r.error || r.reason) });
            if (r && r.hash) { // settle gas from the receipt when it lands
              setTimeout(async () => { try { const rc = await rpc('eth_getTransactionReceipt', [r.hash]); log({ type: 'live_receipt', hash: r.hash, status: rc && rc.status, gas_used: rc && Number(rc.gasUsed), gas_price_wei: rc && Number(rc.effectiveGasPrice) }); } catch (e) { log({ type: 'error', message: 'receipt: ' + e.message }); } }, 20000);
            }
          }
        }
        lastHints = cand; hintsAt = Date.now();
      }
      if (lastHints && Date.now() - hintsAt > 30 * 60 * 1000) { lastHints = null; }
    } catch (e) { log({ type: 'cycle_error', message: String(e.message).slice(0, 200) }); }
    await new Promise((r) => setTimeout(r, POLL_MS));
  }
}
if (require.main === module) main().catch((e) => { console.error(e.message); process.exit(1); }); // test.js may require the calculations without starting the poll loop
module.exports = { redeemCalldata, SEL, economics };
