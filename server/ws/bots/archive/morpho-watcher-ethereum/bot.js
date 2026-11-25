#!/usr/bin/env node
// morpho-watcher-ethereum — Morpho Blue (v2) liquidation watcher on the farm's Ethereum chain.
// Paper mode: tracks borrowers on the two measured collateral-sellable Morpho markets
// factors via Multicall3 (market + position + oracle price), logs opportunities and
// simulates liquidate() when a position goes underwater. Live mode: sends the same
// calldata through the signer socket with min-profit + gas-cap guards.
// Self-contained: node built-ins only. All constants measured on-chain 2026-11-04
// (lead 14 measurement + fork proof, scratch/morpho-eth-proof.js / morpho-eth-markets.js).
'use strict';
const fs = require('fs');
const path = require('path');

const RELAY = process.env.RPC_RELAY_URL || 'http://127.0.0.1:8545';
const LANE = process.env.RPC_LANE || 'paper';
const BOT_MODE = process.env.BOT_MODE || 'paper';
const CHAIN = 'ethereum';
const DIR = __dirname;

// --- measured constants ---
const MORPHO = '0xbbbbbbbbbb9cc5e90e3b3af64bdaf62c37eeffcb'; // Morpho Blue v2 singleton (ledger: 119 liquidation events/7d on ethereum)
const MULTICALL = '0xca11bde05977b3631167028862be2a173976ca11'; // Multicall3
const SEL = {
  market: '0x5c60e39a',          // market(bytes32) -> 5 words
  position: '0x93c52062',        // position(bytes32,address) -> (supplyShares, borrowShares, collateral)
  idToMarketParams: '0x2c3c9157',// idToMarketParams(bytes32) -> (loan, collateral, oracle, irm, lltv)
  price: '0xa035b1fe',           // price() on MorphoChainlinkOracle (NOT 0x3ddac953)
  decimals: '0x313ce567',
  tryAggregate: '0xbce38bd7',    // Multicall3 tryAggregate(bool,(address,bytes)[])
  accrue: '0x151c1ade',          // Morpho.accrueInterest((address,address,address,address,uint256)) — inner call inside the scan multicall
};
const LIQ_TOPIC = '0xa4946ede45d0c6f06a0f5ce92c9ad3b4751452d2fe0e25010783bcab57a67e41';
// topic0 of position-changing events (verified against live logs + 4byte):
// Borrow, Repay, SupplyCollateral, WithdrawCollateral, Supply, Withdraw, Liquidate
const OWNER_TOPICS = [
  '0x570954540bed6b1304a87dfe815a5eda4a648f7097a16240dcd85c9b5fd42a43',
  '0x52acb05cebbd3cd39715469f22afbf5a17496295ef3bc9bb5944056c63ccaa09',
  '0xa3b9472a1399e17e123f3c2e6586c23e504184d504de59cdaa2b375e880c6184',
  '0xe80ebd7cc9223d7382aab2e0d1d6155c65651f83d53c8b9b06901d167e321142',
  '0xedf8870433c83823eb071d3df1caa8d008f12f6440918c20d75a3602cda30fe0',
  '0xa56fc0ad5702ec05ce63666221f796fb62437c32db1aa1aa075fc6484cf58fbf',
  LIQ_TOPIC,
];
const IRM_DEFAULT = '0x870ac11d48b15db9a138cf899d20f13f79ba00bc';

// Top-4 liquidated markets on base in the last 36h (38+27+14+8 = 87% of 94 events).
// All borrow USDC against: JitoSOL / SOL / cbZEC / cbBTC. loan decimals = 6 for all.
// pool = measured collateral-swap pool for the executor (null = watch-only:
// opportunity logged, no executor sim / live send until a pool is measured).
const MARKETS = [
  { id: '0x94b823e6bd8ea533b4e33fbc307faea0b307301bc48763acc4d4aa4def7636cd', loan: '0xa0b86991c6218b36c1d19d4a2e9eb0ce3606eb48', coll: '0xc02aaa39b223fe8d0a0e5c4f27ead9083c756cc2', ldec: 6, cdec: 18, oracle: '0x0f948cba8231db7898ef36a4212581ad7b1b4580', lltv: '860000000000000000', irm: '0x870ac11d48b15db9a138cf899d20f13f79ba00bc', pool: '0x88e6a0c2ddd26feeb64f039a2c41296fcb3f5640', zeroForOne: false }, // UniV3 USDC/WETH 0.05%: token0=USDC (measured), selling WETH = token1 -> zeroForOne=false
  { id: '0x3a85e619751152991742810df6ec69ce473daef99e28a64ab2340d7b7ccfee49', loan: '0xa0b86991c6218b36c1d19d4a2e9eb0ce3606eb48', coll: '0x2260fac5e5542a773aa44fbcfedf7c193bc2c599', ldec: 6, cdec: 8, oracle: '0xdddd770badd886df3864029e4b377b5f6a2b6b83', lltv: '860000000000000000', irm: '0x870ac11d48b15db9a138cf899d20f13f79ba00bc', pool: '0x9a772018fbd77fcd2d25657e5c547baff3fd7d16', zeroForOne: true }, // UniV3 WBTC/USDC pool: token0=WBTC (measured) -> zeroForOne=true
];
// Morpho's oracle price divisor is a PROTOCOL CONSTANT, not a per-market or
// per-oracle choice: SharesMathLib computes value = collateral x price / 1e36
// where the 1e18-scale price ALREADY absorbs both tokens' decimals (a 18/6-dec
// pair and an 8/6-dec pair differ in the RAW magnitude of the price, not in the
// scale). The old per-market pdiv 39 for WBTC/USDC undercounted collateral
// value by 1000 and produced false underwater candidates (reviewer 1c01613e,
// relay block 26343570 borrower 0x7659fc26: submitted math HF 0.0013129 vs
// canonical 1.312906189788, and the protocol's own withdrawCollateral(1)
// eth_call succeeds — healthy). Persisted-state migration: the divisor is now
// fixed in code, so an old persisted pdiv 39 row (state.json) no longer drives
// any computation — loadState still pins the canonical row for pinned markets.
const ORACLE_DIV = 10n ** 36n;
const MAX_MARKETS = 8;

const HF_WARN = 1.05;
const CYCLE_MS = 20000;
const REFRESH_MS = 5 * 60 * 1000;
const CHUNK = 250;            // inner calls per multicall eth_call
const CAND_CAP = 300;         // per market, most recent kept (deep backfill needs headroom)
// PIN_CAND_CAP (run 2637916d, attempt 203): the CAND_CAP trim evicted exactly the
// deep-backfill-discovered DORMANT debtors in the pinned markets — the class the
// 450k-block backfill exists to cover. Measured loss: pinned WBTC capture block
// 26349648 (repaid 525.62 USD, hf_parent 1.0059764) victim 0x5e1b7fff was last
// scanned 2026-11-04T19:15:14Z and has ZERO candidate-stamping logs in the 60k
// steady window before its liquidation (scratch/mw-cand-presig.js: 163 unique
// stamped addrs in-window vs a pinned set at the 300 cap) — CAND_CAP eviction,
// not the oracle race, is why the bot never scanned it. Pinned markets keep far
// more candidates; discovered markets keep the old cap.
const PIN_CAND_CAP = 1200;    // per PINNED market: deep-discovered dormant debtors are not evicted below this
const LOG_BLOCKS = 60000;     // steady-state candidate window ONLY (~33h). The measured 261k-block
                              // pre-capture gap (winner tx 0x2d56cc60's borrowers last acted 261k/265k
                              // blocks before capture) is NOT closed by raising this window — it is
                              // closed by the COLD_START_BLOCKS deep backfill (review 2d13ac44 blocker 4).
const COLD_START_BLOCKS = 450000; // deep cold-start backfill: covers the measured 261,222/260,573-block
                                  // pre-capture inactivity of winner tx 0x2d56cc60's borrowers with margin
                                  // (~10.4 days at 2 s/block; review 511fc3e7 blocker 3)
const DEEP_BATCH_BLOCKS = 80000;  // blocks scanned per refresh during the deep phase (40 pages x (4 tracked markets + 1 all-liquidations) log queries)
const LOG_PAGE_BLOCKS = 2000; // initial getLogs page; halved on relay max-results errors
const CURSOR_LOOKBACK = 8;    // blocks re-scanned on resume so boundary events are not missed
const MIN_PROFIT_USD = 2;     // POST-FEE profit floor in loan-asset USD; the on-chain minProfit and the live gate add the EXPECTED fee (feePolicy below)
// Fee policy (revision 8b738b25, review a1438eb0 blocker 2): the fixed 0.2 gwei cap was includable
// only while the inclusion block's base fee stayed ≤ 0.2 gwei. Measured base fees: the natural
// catchable case's winner block 26302109 charged 5.9174 gwei (the 2026-10-30 cluster era measured
// 4.6-16.1 gwei at 26301784-26302195), the current head header reads ~0.038 gwei — no single fixed
// cap covers both eras. maxFeePerGas is therefore DERIVED each cycle from the live base fee read
// from the latest block header (the relay rejects eth_baseFee — the header is the bot's own read):
// maxFee = basefee×9/8 + FEE_TIP_WEI, capped at FEE_CAP_WEI (17.5 gwei, the observed-era bound).
// The ENFORCED worst case stays a product of signed fields: maxFeePerGas × MAX_GAS_LIMIT;
// 460000 × 17.5 gwei = 0.00805 ETH ≤ 20 USD at any fresh native valuation ≤ 2484 USD/ETH
// (the live path refuses when the bound times the margin exceeds 20 USD — fail closed),
// and at today's derived maxFee ≈ 0.044 gwei it is ≈ 0.02 USD.
const MAX_GAS_LIMIT = 460000n;        // executor path: fork-measured gasUsed 307335 (success) .. 419323 (WBTC NO_PROFIT guard) plus margin
const FEE_TIP_WEI = 1000000n;         // 0.001 gwei priority (measured same-era tip as the cv3 watcher)
const FEE_CAP_WEI = 17500000000n;     // 17.5 gwei cap on the DERIVED maxFee (observed historical era upper bound 16.1 gwei; 17.5 gwei x 460000 = 0.00805 ETH = LIVE_FEE_ALLOWANCE_WEI)
const EXPECTED_GAS_WEI = 420000n;     // gasUsed upper bound for the EXPECTED-fee floor leg (below the 460k enforced cap)

// --- executor path (live sends go HERE, never directly to Morpho) ---
// The gate deploys the artifact at promotion (through the bot wallet, which
// becomes the executor owner) and allows the deployed address in the signer
// policy. The address below is the fork-deployed executor of record used for
// paper sims: eth_call with a code state-override carrying the exact
// CONSTRUCTOR-PATCHED runtime bytecode, so the simulated calldata and the
// immutable slots are the same bytes that live would run. EXECUTOR_ADDR env
// overrides it when a gate deployment exists.
const EXEC = process.env.EXECUTOR_ADDR || '0xb464f7314d55ec6a9a0cf6f7f6df17af8ed5b352'; // fork-deployed MorphoLiquidator v3 (forge build 2026-11-04)
const RUNTIME_FILE = path.join(DIR, 'executor-runtime.hex');
const EXEC_OWNER = '0xfffffffffffffffffffffffffffffffffffffffe'; // owner() baked into the runtime (fork deployer of record); paper sims call from it
const SEL_EXEC_OWNER = '0x8da5cb5b';     // owner() — live path requires owner() == our wallet
const SEL_EXEC_LIQUIDATE = '0xcf1f5981'; // liquidate((address,address,address,address,uint256),address,uint256,uint256,uint256,address,bytes)
const SEL_POOL_SWAP = '0x128acb08';      // UniV3 V3Swap.swap(address,bool,int256,uint160,bytes) — same selector as the base bot's PancakeV3 pool; UniV3 core: amountSpecified > 0 = exact input, < 0 = exact output (IUniswapV3PoolActions; the old comment claiming < 0 was exact input was wrong and broke the fork proof)
const MAX_SQRT_RATIO_M1 = '0xfffd8963efd1fc6a506488495d951d5263988d25';   // UniV3 MAX_SQRT_RATIO-1
const MIN_SQRT_RATIO_P1 = '0x1000276a4';                                     // UniV3 MIN_SQRT_RATIO+1 (4295128740): the pool requires the limit strictly ABOVE the minimum
const CAPITAL_REPAID_CAP = 398n * 1000000n; // seized such that repaid <= ~398 USDC (capital_usd 400)
const MIN_PROFIT_WEI = 1000000n;            // executor minProfit argument = 1 USDC
// Pool-allow initialization (review a41d9200 blocker 2): the constructor whitelists
// only the WETH pool immutable; the WBTC route needs the executor OWNER's one init
// tx setPoolAllowed(pool, true) on the DEPLOYED contract. The live path verifies
// the initialized state with the getter (isPoolAllowed, selector d1e71c94 measured
// on the fork) and, while it does not hold, sends that single init tx through the
// signer once per pool — the promotion flow is proven by the deployed state, not
// by manifest prose. setPoolAllowed(address,bool) selector measured with
// `cast sig`: 0x1bfa59c3 (fork-verified init tx 0xfa60cf60... / 0xd978164e...).
const SEL_EXEC_IS_POOL_ALLOWED = '0xd1e71c94';
const SEL_EXEC_SET_POOL_ALLOWED = '0x1bfa59c3';
const poolInitSent = new Set(); // pools whose init tx this process already sent (a signer rejection is final)
// Paper sims override ONLY the executor's code. The live (promoted) executor
// additionally holds ONE storage slot: the owner's one-time init transaction
// setPoolAllowed(WBTC pool, true) — the constructor whitelists the P0=WETH
// pool as an immutable (review 1c01613e blocker 3: 'allowedPool is storage;
// code-only override does not carry setPoolAllowed: model the WBTC executor
// state initialized on paper'). allowedPool is mapping slot 1, so the WBTC
// pool's slot is keccak256(pool address word ++ uint256(1)) (measured):
// 0xfa2a8da10ebaa196ea21dc474321e5b03a94fb3684bdc473b2250a6ef99e5010.
// Fork-verified 2026-11-04: after the owner init tx
// 0xfa60cf60ecbf621ea593765cba2de6d5f192051158200b3b99e432920a096d9b,
// eth_getStorageAt(executor, slot) == 0x...01 and isPoolAllowed(WBTC pool)
// returns true (selector d1e71c94). The relay accepts this slot->value map
// form of the state override (geth/erigon style; a list of pairs is rejected).
const POOL_ALLOWED_INIT = {
  '0xfa2a8da10ebaa196ea21dc474321e5b03a94fb3684bdc473b2250a6ef99e5010': '0x0000000000000000000000000000000000000000000000000000000000000001',
};
// Fail-closed runtime validation: the paper sim must exercise the REAL
// constructor-patched runtime (review 6950ca00 blocker: zero immutable slots
// made the sim run an empty-account call). All five MORPHO immutable slots
// must be non-zero, else sims are disabled (watch-only) instead of falling
// back to a fake runtime.
// Fail-closed validation: the constructor-patched runtime must embed ALL FOUR
// non-zero immutables of this deployment (MORPHO, WETH, WBTC, WETH/USDC pool) as raw
// address bytes; a zero-patched artifact (the failure review 6950ca00 caught) embeds
// none. Offsets measured from the fork-deployed runtime (scratch/morpho-eth-fork-runtime.hex).
const NEEDLE_ADDRS = [MORPHO, '0xc02aaa39b223fe8d0a0e5c4f27ead9083c756cc2', '0x2260fac5e5542a773aa44fbcfedf7c193bc2c599', '0x88e6a0c2ddd26feeb64f039a2c41296fcb3f5640'];
let RUNTIME_CODE = '';
let RUNTIME_OK = false;
try {
  RUNTIME_CODE = fs.readFileSync(RUNTIME_FILE, 'utf8').trim();
  RUNTIME_OK = RUNTIME_CODE.length > 20000 && NEEDLE_ADDRS.every(a => RUNTIME_CODE.toLowerCase().includes(a.slice(2).toLowerCase()));
} catch (e) { /* sims disabled below */ }

// Native (gas) valuation, fresh every cycle from the UniV3 WETH/USDC pool's
// slot0() spot (the same pool the executor sells WETH through): live sends
// fail closed when it is stale. Used only for the conservative USD gas bound,
// never for profit sizing (profit is sized in loan-asset wei at oracle price).
const GAS_MARKET = '0x94b823e6bd8ea533b4e33fbc307faea0b307301bc48763acc4d4aa4def7636cd'; // the WETH/USDC market's own oracle price doubles as the native gas valuation (USDC per WETH at 1e36 scale) — the bot's own pricing, no external feed
let ETH_USD = 0, ETH_USD_AT = 0;
const ETH_USD_STALE_MS = 15 * 60 * 1000;
// Fix (review 2939f16e, 2026-11-09): this cycle's fresh gas valuation flag, set in
// scanCycle when the valuation slot read succeeds and cleared at cycle start. The
// live send paths consult it: while confirmed gas receipts are still pending and
// THIS cycle has no fresh valuation, no signer send proceeds (the old up-to-15-minute
// price cache let sends continue while pending gas was never valued, so the $30 stop
// could stay understated forever).
let GAS_VALUED_THIS_CYCLE = false;
// Fee model for ONE live transaction on Ethereum (plain public mainnet, EIP-1559):
// the chain charges at most maxFeePerGas x gasUsed, gasUsed <= gasLimit — both are
// SIGNED transaction fields, so maxFeePerGas x gasLimit is an ENFORCED worst case
// (no OP-Stack L1 data fee, no operator fee, no L1-origin drift: the base bot's
// unenforceable leg has no analogue here). LIVE_FEE_CAP_ENFORCED=true: the loss bound
// is enforced by the transaction itself, as L requires. The wallet balance check in
// the live path remains the gate's funding-policy validity check (18 USD gas float).
const LIVE_FEE_ALLOWANCE_WEI = 8050000000000000n; // 0.00805 ETH = the enforced worst case at the FEE_CAP: MAX_GAS_LIMIT x FEE_CAP_WEI (460000 x 17.5 gwei)
const LIVE_BALANCE_CAP_USD = 18;     // funding policy + validity check (NOT a chain invariant): skip when the gas float exceeds 18 USD
const LIVE_FEE_CAP_ENFORCED = true;  // Ethereum: maxFeePerGas x gasLimit is enforced by the signed transaction fields — the leg the base bot could not enforce does not exist here
const FEE_BOUND_MARGIN = 1;          // no drift margin needed: both factors are signed fields fixed at signing
let feePolicy = null; // { baseFeeWei, maxFeeWei, headerBlock } — DERIVED from the latest block header each cycle
async function updateFeePolicy() { // one header read per scan cycle (the relay rejects eth_baseFee; baseFeePerGas is a header field)
  try {
    const b = await rpc('eth_getBlockByNumber', ['latest', false]);
    if (!b || !b.baseFeePerGas) return null;
    const baseFeeWei = BigInt(b.baseFeePerGas);
    if (baseFeeWei < 0n) return null;
    let maxFeeWei = baseFeeWei * 9n / 8n + FEE_TIP_WEI; // 12.5% headroom over the live base fee + tip
    if (maxFeeWei > FEE_CAP_WEI) maxFeeWei = FEE_CAP_WEI;
    feePolicy = { baseFeeWei, maxFeeWei, headerBlock: parseInt(b.number, 16) };
    return feePolicy;
  } catch (e) { return null; } // fail closed: without a policy, feeBound.ok is false and live sends nothing
}
function expectedFeeUsd(f) { // the EXPECTED-fee leg of the profit floor: expected gasUsed upper bound x (live base fee + tip) at the fresh valuation
  if (!f || !ETH_USD || Date.now() - ETH_USD_AT > ETH_USD_STALE_MS) return null;
  return Number(EXPECTED_GAS_WEI * (f.baseFeeWei + FEE_TIP_WEI)) / 1e18 * ETH_USD;
}
function feeBound(calldataMax, nonce) {
  // (calldataMax/nonce kept in the signature for harness symmetry.) The bound is the product of the
  // SIGNED maxFeePerGas the send will use (the per-cycle derived policy) and the SIGNED gasLimit.
  const f = feePolicy;
  if (!f) return { ok: false, l2Wei: '0', totalWei: '0', allowanceWei: LIVE_FEE_ALLOWANCE_WEI.toString(), reason: 'fee policy missing (header read failed — fail closed)' };
  const totalWei = MAX_GAS_LIMIT * f.maxFeeWei; // enforced: maxFeePerGas x gasLimit — both signed fields
  const includable = f.maxFeeWei >= f.baseFeeWei + FEE_TIP_WEI; // a capped-derived fee below the live base fee + tip is never includable
  return { ok: totalWei <= LIVE_FEE_ALLOWANCE_WEI && includable, l2Wei: totalWei.toString(),
    totalWei: totalWei.toString(), allowanceWei: LIVE_FEE_ALLOWANCE_WEI.toString(),
    baseFeeWei: f.baseFeeWei.toString(), maxFeeWei: f.maxFeeWei.toString(), headerBlock: f.headerBlock };
}
function worstCaseGasLossUsd(feeBound) {
  if (!ETH_USD || !feeBound || !feeBound.ok) return null;
  return Number(BigInt(feeBound.totalWei)) / 1e18 * ETH_USD;
}

const LOGS = process.env.BOT_LOGS_DIR || path.join(DIR, 'logs'); // BOT_LOGS_DIR: offline stop-tests keep their lines out of the paper audit trail
const STATE = process.env.BOT_STATE_DIR || path.join(DIR, 'state'); // BOT_STATE_DIR: offline stop-tests point state/ at scratch/
fs.mkdirSync(LOGS, { recursive: true });
fs.mkdirSync(STATE, { recursive: true });
const LOG = path.join(LOGS, 'bot.jsonl');
const STATE_FILE = path.join(STATE, 'state.json');

function log(obj) { fs.appendFileSync(LOG, JSON.stringify(obj) + '\n'); }
const addr = (a) => a.toLowerCase().replace(/^0x/, '').padStart(64, '0');
const hex = (x) => '0x' + BigInt(x).toString(16);

let rpcId = 0;
// Measured RPC use (review 1c01613e blocker 4: 'demonstrate completed supervised
// cycles and measured RPC use against the declared 60 reads/min'). Every relay
// request — including a bounded retry attempt — increments RPC_TOTAL; each
// completed scanCycle logs the reads it spent (rpc_cycle) so a heartbeat proves
// both the completed cycle and its measured cost against rpc_reads_per_min.
let RPC_TOTAL = 0, RPC_CYCLE_START = 0;
async function rpc(method, params, retry = 0, cap = 3) {
  RPC_TOTAL++; // counted per attempt: retries are real relay reads
  // A stalled relay request (measured: relay eth_call under pressure can take minutes;
  // one fetch that never settles froze every scanCycle of the pre-fix bot — no heartbeats
  // for the whole supervised run) gets a hard 45 s timeout and the same bounded backoff
  // retry as an RPC error.
  let res;
  try {
    res = await fetch(`${RELAY}/${CHAIN}?lane=${LANE}`, {
      method: 'POST', headers: { 'content-type': 'application/json' },
      body: JSON.stringify({ jsonrpc: '2.0', id: ++rpcId, method, params }),
      signal: AbortSignal.timeout(45000),
    });
  } catch (e) {
    if (retry < cap) { await new Promise(r => setTimeout(r, 2500 * (retry + 1))); return rpc(method, params, retry + 1, cap); }
    throw new Error(`${method}: fetch ${String(e.message || e).slice(0, 120)}`);
  }
  const j = await res.json();
  if (j.error) {
    if (retry < cap) { await new Promise(r => setTimeout(r, 2500 * (retry + 1))); return rpc(method, params, retry + 1, cap); }
    throw new Error(`${method}: ${JSON.stringify(j.error).slice(0, 200)}`);
  }
  return j.result;
}

// Multicall3 tryAggregate, encoding measured against the farm relay (aave-watcher-base design)
// blockTag: the scan always reads 'latest'; the window-measurement harness (run f3f12ccc,
// scratch/morpho-eth-window/) re-reads the SAME call shape at historical block tags.
async function tryAggregate(calls, blockTag = 'latest') {
  const roundup = (n) => Math.ceil(n / 32) * 32;
  const starts = [];
  let acc = 0x20 * calls.length;
  for (const c of calls) { starts.push(acc); acc += 0x60 + roundup((c.data.length - 2) / 2); }
  let enc = SEL.tryAggregate + addr('0') + '0000000000000000000000000000000000000000000000000000000000000040' + calls.length.toString(16).padStart(64, '0');
  calls.forEach((c, i) => { enc += starts[i].toString(16).padStart(64, '0'); });
  calls.forEach((c) => {
    enc += addr(c.to) + '0000000000000000000000000000000000000000000000000000000000000040' +
      ((c.data.length - 2) / 2).toString(16).padStart(64, '0') + c.data.slice(2) +
      '0'.repeat(roundup((c.data.length - 2) / 2) * 2 - (c.data.length - 2));
  });
  const r = await rpc('eth_call', [{ to: MULTICALL, data: enc }, blockTag]);
  const h = r.slice(2);
  const base = 64;
  const n = Math.min(parseInt(h.slice(base, base + 64), 16), calls.length);
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

// Executor calldata: MorphoLiquidator.liquidate(marketParams, borrower, seized,
// flashAmount, minProfit, swapTarget, swapData). The executor flash-loans the
// loan asset from Morpho, repays the borrower's debt, seizes `seized` collateral,
// sells ALL of it on the pool (UniV3 pool.swap, recipient = executor,
// amountSpecified = -seized = exact input of collateral), lets Morpho pull the flash
// back and reverts "NO_PROFIT" unless its loan-asset balance rose by minProfit.
function encExecutorCall(m, borrower, seized, flashAmount, minProfit, swapData) {
  return SEL_EXEC_LIQUIDATE +
    addr(m.loan) + addr(m.coll) + addr(m.oracle) + addr(m.irm || IRM_DEFAULT) + BigInt(m.lltv).toString(16).padStart(64, '0') +
    addr(borrower) +
    BigInt(seized).toString(16).padStart(64, '0') +
    BigInt(flashAmount).toString(16).padStart(64, '0') +
    BigInt(minProfit).toString(16).padStart(64, '0') +
    addr(m.pool) +
    (11 * 32).toString(16).padStart(64, '0') +   // bytes offset: 10 head words + the offset word itself
    (swapData.length / 2 - 1).toString(16).padStart(64, '0') +
    swapData.slice(2);
}

// UniV3 pool.swap(recipient=executor, zeroForOne, amountSpecified=+seized (EXACT
// INPUT — IUniswapV3PoolActions: positive = exact input, negative = exact output; the
// base bot's PancakeV3-style comment claiming UniV3 was "opposite" was wrong, both
// use positive = exact input; the earlier -seized encoding was exact OUTPUT and
// reverted every fork swap with SWAP_FAILED, measured 2026-11-04), sqrtPriceLimit = MAX-1 (token1 sold) or
// MIN+1 (token0 sold; the pool requires the limit STRICTLY inside the ratio bounds —
// exact MIN_SQRT_RATIO reverts SPL, reviewer b44cbd98 measured), data=abi.encode(token0,
// token1)) — sells the seized collateral into the pool; the pool pays the executor the
// loan asset and calls the executor's V3 swap callback, which pays the pool the
// collateral (auth'd to the armed pool). zeroForOne follows the measured pool
// orientation: WETH pool token0=USDC (token1 sold), WBTC pool token0=WBTC.
function encPoolSwap(execAddr, collateralAmount, loan, coll, zeroForOne) {
  const [t0, t1] = [loan.toLowerCase(), coll.toLowerCase()].sort();
  const amt = BigInt(collateralAmount).toString(16).padStart(64, '0'); // +seized as int256: UniV3 positive amountSpecified = exact input
  return SEL_POOL_SWAP + addr(execAddr) + (zeroForOne ? '1'.padStart(64, '0') : '0'.repeat(64)) +
    amt + (zeroForOne ? MIN_SQRT_RATIO_P1.slice(2) : MAX_SQRT_RATIO_M1.slice(2)).padStart(64, '0') +
    'a0'.padStart(64, '0') + '40'.padStart(64, '0') + addr(t0) + addr(t1);
}

// Protocol-exact liquidation incentive factor (Morpho Blue):
// min(1.15e18, 1e18*1e18/(1e18 - 0.3e18*(1e18-lltv)/1e18)).
// Verified to the wei against both Liquidate events of winner tx 0x2d56cc60
// (1.1267605634e18 at lltv 0.625; 1.0438417e18 at 0.86).
function incentiveFactor(lltv) {
  const spread = (300000000000000000n * (1000000000000000000n - BigInt(lltv))) / 1000000000000000000n;
  const f = (1000000000000000000n * 1000000000000000000n) / (1000000000000000000n - spread);
  return f > 1150000000000000000n ? 1150000000000000000n : f;
}

// Protocol-exact eligibility and liquidation economics (Morpho Blue, Morpho.sol
// _isHealthy + SharesMathLib, verified 2026-11-04 against the protocol's own
// withdrawCollateral code path on 56/56 boundary probes and against both
// Liquidate events of winner tx 0x2d56cc60 to the wei):
//   borrowed  = toAssetsUp(borrowShares, tba, tbs)
//             = ceil(borrowShares * (tba + VIRTUAL_ASSETS) / (tbs + VIRTUAL_SHARES))
//     with VIRTUAL_ASSETS = 1, VIRTUAL_SHARES = 1e6 (review 021de292 blocker 3:
//     the old ceil(borrowShares*tba/tbs) omitted both virtual terms and the
//     accrued totals — the totals fed here are ACCRUED by Morpho.accrueInterest
//     running as a Multicall3 inner call, see scanCycle),
//   maxBorrow = floor(floor(coll*price/1e36) * lltv / 1e18)
//   healthy   iff maxBorrow >= borrowed.
function marketEconomics(m, collateral, borrowShares, totBorAssets, totBorShares, price) {
  if (totBorShares === 0n || borrowShares === 0n) return null;
  const vShares = totBorShares + 1000000n;
  const debtAssets = (borrowShares * (totBorAssets + 1n) + vShares - 1n) / vShares; // toAssetsUp
  if (debtAssets === 0n) return null;
  const collValue = collateral * price / ORACLE_DIV;   // mulDivDown at the protocol's fixed 1e36 oracle scale (see ORACLE_DIV: the divisor is a protocol constant, not per-market — reviewer 1c01613e)
  const maxDebt = collValue * BigInt(m.lltv) / 10n ** 18n; // floor — protocol eligibility boundary
  const healthy = maxDebt >= debtAssets;
  return {
    healthy,
    hf: Number(maxDebt * 10n ** 12n / debtAssets) / 1e12,
    debtAssets,
    collValue,
  };
}

// Seize size: full collateral capped BOTH by the bot's capital (capital_usd
// 400: repaid(seized) <= cap) and by the borrower's debt coverage (Morpho
// seizes at most debt*incentiveFactor worth of collateral; requesting more
// than seizable reverts). repaid estimate =
// min(floor(floor(seized*price/1e36)*1e18/inc), debtAssets): Morpho repays
// min(computed-from-seize, actual borrow assets) and rounds to borrow
// shares. Verified against winner tx 0x2d56cc60 where the seize was
// debt-limited: repaid == the borrower's actual borrow assets (13203398612),
// not the seize-derived 13203398609.
// Protocol-exact repaid chain for a given seize, on the ACCRUED market totals
// (Morpho.liquidate: seizedAssetsQuoted = mulDivUp(seized, price, 1e36);
//  repaidShares = wDivUp(quoted, incentiveFactor).toSharesUp(tba, tbs), clamped
//  at the borrower's borrowShares; repaidAssets = repaidShares.toAssetsUp(tba, tbs)).
// Verified to the wei against BOTH Liquidate events of winner tx 0x2d56cc60
// (13203398612 and 414167285) on the reconstructed execution-time state
// (scratch/morpho-econ/fork-verify.json, fork 53447309 + forced oracle price).
function repaidChain(seized, price, tba, tbs, lltv, borrowShares) {
  const quoted = (seized * price + ORACLE_DIV - 1n) / ORACLE_DIV;       // mulDivUp(seized, price, protocol oracle scale 1e36)
  const inc = incentiveFactor(lltv);
  let shares = (quoted * 10n ** 18n + inc - 1n) / inc;                    // wDivUp — Morpho computes EXACTLY this when seizedAssets > 0
  shares = (shares * (tbs + 1000000n) + (tba + 1n) - 1n) / (tba + 1n);    // toSharesUp — Morpho SUBTRACTS this from the borrower's shares (review 511fc3e7 blocker 2: no clamp exists; excess = underflow panic 0x11)
  const vShares = tbs + 1000000n;
  const repaidAssets = (shares * (tba + 1n) + vShares - 1n) / vShares;    // toAssetsUp
  return { shares, repaidAssets, debtOk: shares <= borrowShares };        // debtOk: the computed shares must stay <= the borrower's actual shares
}
// Seize size: full collateral capped by BOTH limits, each found by binary
// search on the EXACT protocol chain above (monotone in seized):
//  (1) DEBT limit — the largest seize whose computed repaidShares stays
//      <= the borrower's actual borrowShares (Morpho.liquidate with
//      seizedAssets>0 derives repaidShares from the seize and reverts on
//      excess; repaidShares=0 is NOT a clamp and is NOT clamped to the
//      borrower — review 511fc3e7 blocker 2: the previous silent clamp hid
//      this and produced panic 0x11 whenever the borrower's debt was below
//      the 398 USDC capital cap);
//  (2) CAPITAL limit — repaid <= ~398 USDC of the 400 capital.
// seized = min(both); `branch` records which one bound. The flash is sized
// from the same repaid amount the protocol will charge (plus headroom).
function seizeFor(m, collateral, price, totBorAssets, totBorShares, borrowShares) {
  const chainAt = (s) => repaidChain(s, price, totBorAssets, totBorShares, m.lltv, borrowShares);
  const maxOk = (pred) => { // largest s in [0, collateral] with pred(chain(s)) — predicate monotone in s
    if (collateral === 0n) return 0n;
    if (pred(chainAt(collateral))) return collateral;
    if (!pred(chainAt(0n))) return 0n;
    let a = 0n, b = collateral;
    for (let i = 0; i < 96; i++) {
      const mid = (a + b) / 2n;
      if (mid === a) break;
      if (pred(chainAt(mid))) a = mid; else b = mid;
    }
    return a;
  };
  const debtCap = maxOk(c => c.debtOk);
  const capitalCap = maxOk(c => c.repaidAssets <= CAPITAL_REPAID_CAP);
  const seized = debtCap < capitalCap ? debtCap : capitalCap;
  const branch = debtCap < capitalCap ? 'debt_limited' : 'capital_limited';
  const { repaidAssets: repaid, shares: repaidShares } = chainAt(seized);
  const proceeds = seized * price / ORACLE_DIV; // conservative (floor) sale value at oracle at the protocol 1e36 scale
  return { seized, repaid, repaidShares, proceeds, branch, debtCap, capitalCap };
}

// Selected-proceeds profit estimate (review 6950ca00 blocker 3): profit is
// computed on the SEIZED amount's sale proceeds at the oracle price, NOT the
// borrower's whole collateral value: profit = proceeds(seized) - repaid.
// The live send gate additionally subtracts the conservative gas bound in
// USD (worstCaseGasLossUsd, fresh native valuation) and requires the
// residual to clear MIN_PROFIT_USD.
function profitEstimate(m, proceeds, repaid) {
  if (proceeds <= repaid) return 0n;
  return proceeds - repaid;
}

// Bounded log reads (review 294ea30f blocker: one oversized eth_getLogs threw
// in main() before the scan interval registered, crashing the bot every ~45s).
// Pages of LOG_PAGE_BLOCKS; a page the relay rejects for exceeding its
// max-results cap is halved recursively, bottoming out at single blocks.
const logStats = { calls: 0 };
async function getLogsRange(topics, from, to) {
  try {
    logStats.calls++;
    return await rpc('eth_getLogs', [{ fromBlock: hex(from), toBlock: hex(to), address: MORPHO, topics }]);
  } catch (e) {
    if (to <= from || !/max results/i.test(String(e))) throw e;
    const mid = from + Math.floor((to - from) / 2);
    return [].concat(await getLogsRange(topics, from, mid), await getLogsRange(topics, mid + 1, to));
  }
}
async function getLogsPaged(topics, from, to) {
  let out = [];
  for (let s = from; s <= to; s += LOG_PAGE_BLOCKS) {
    out = out.concat(await getLogsRange(topics, s, Math.min(s + LOG_PAGE_BLOCKS - 1, to)));
  }
  return out;
}

// Eviction victim (pure, exported for the harness — review 99cc9216 blocker 3):
// drop the least-recently-liquidated DISCOVERED market. The pinned (configured
// MARKETS) entries carry the measured swap pools and are never evicted: the old
// sort-shift keyed on lastLiq (undefined -> 0 for pinned entries until an event
// refreshed it) and evicted a pinned market, after which discovery re-added it
// with pool=null — the supervised log market_added 11:58:20.632Z re-added the
// pinned cbZEC market that way and the running process stayed watch-only.
// Only when every tracked market is pinned (pinned count >= MAX_MARKETS) can a
// pinned entry be evicted, oldest first.
function pickEvictVictim(markets) {
  let victim = null, oldest = Infinity;
  for (const m of markets) {
    const t = m.lastLiq || 0;
    if (!MARKETS.some(p => p.id === m.id) && t <= oldest) { oldest = t; victim = m; }
  }
  if (victim) return victim;
  let v2 = null, o2 = Infinity;
  for (const m of markets) { const t = m.lastLiq || 0; if (t <= o2) { o2 = t; v2 = m; } }
  return v2;
}
function pinnedMeta(mid) { return MARKETS.find(p => p.id === mid) || null; }

async function refreshCandidates(state) {
  const tip = parseInt(await rpc('eth_blockNumber', []), 16);
  // Deep cold-start backfill (review 511fc3e7 blocker 3): a 60k-block window
  // cannot reach borrowers that last acted 261k+ blocks before a capture, so
  // the cold-start candidate path provably misses supported borrowers. On a
  // fresh state we page back COLD_START_BLOCKS in bounded batches across
  // refreshes (state.deepCursor, persisted): each refresh scans at most
  // DEEP_BATCH_BLOCKS per market, oldest -> newest, until caught up; the
  // persisted candidate set then provably covers the full pre-capture activity
  // window of real borrowers without oversized reads.
  if (state.deepCursor === undefined) state.deepCursor = (state.cursor == null) ? Math.max(tip - COLD_START_BLOCKS, 0) : null;
  // Migration (review 2d13ac44 blocker 3): a state persisted with a cursor but no
  // deepCursor was NEVER backfilled — its candidate set only contains blocks it
  // already saw (the 60k steady window), so the deployed candidate set could not
  // discover a borrower whose last action was 261k+ blocks before a capture.
  // Such a state now gets the deep backfill ONCE (state.deepDone marks it done;
  // it is persisted, so the backfill does not repeat after restarts).
  if (state.deepCursor == null && state.cursor != null && state.deepDone !== true)
    state.deepCursor = Math.max(tip - COLD_START_BLOCKS, 0);
  let from, to, deepStart = state.deepCursor, deepNext = null;
  if (deepStart != null) {
    from = deepStart;
    to = Math.min(tip, from + DEEP_BATCH_BLOCKS - 1);
    // deepCursor advances only AFTER the batch scan completed (below, with the
    // cursor commit): a mid-refresh RPC failure re-reads the SAME batch instead
    // of skipping the failed segment (review 2d13ac44 blocker 3).
    deepNext = to >= tip ? null : to + 1;
  } else {
    // Cursor resume: scan only blocks not yet seen, with a small overlap.
    // state.cursor is stored after every scan below succeeded, so a failure
    // re-reads the same range (idempotent: candidate timestamps get re-stamped).
    from = state.cursor ? Math.max(state.cursor + 1 - CURSOR_LOOKBACK, tip - LOG_BLOCKS) : tip - LOG_BLOCKS;
    to = tip;
  }
  state.liqCounts = state.liqCounts || new Map();
  const liqByMkt = state.liqCounts; // cumulative per-market liquidation counts (persisted)
  logStats.calls = 0;
  const t0 = Date.now();
  for (const m of state.markets) {
    const logs = await getLogsPaged([OWNER_TOPICS, m.id], from, to);
    const cmap = state.candidates.get(m.id);
    for (const lg of logs) {
      if (lg.topics[0] === LIQ_TOPIC) liqByMkt.set(m.id, (liqByMkt.get(m.id) || 0) + 1);
      if (lg.topics.length === 4) {
        const a = '0x' + lg.topics[3].slice(-40);
        if (a !== '0x0000000000000000000000000000000000000000') cmap.set(a, Date.now());
      }
    }
  }
  // new-market discovery: liquidations on markets we do not track yet
  {
    const logs = await getLogsPaged([LIQ_TOPIC], from, to);
    for (const lg of logs) liqByMkt.set(lg.topics[1], (liqByMkt.get(lg.topics[1]) || 0) + 1);
  }
  // Cursors commit only after the FULL scan completed (saveState in main() runs
  // only on refresh success): an RPC failure re-reads the same blocks, and the
  // deep batch is never skipped (review 2d13ac44 blocker 3). The batch endpoint
  // `to` is used everywhere, never `tip`.
  state.cursor = to;
  state.deepCursor = deepNext;
  if (deepStart != null && deepNext === null) state.deepDone = true;
  // market discovery: any newly seen market with >=2 liquidations in window
  for (const [mid, cnt] of liqByMkt) {
    if (cnt < 2 || state.markets.some(m => m.id === mid)) continue;
    if (state.markets.length >= MAX_MARKETS) {
      const victim = pickEvictVictim(state.markets); // discovered markets only; pinned routes stay
      state.markets.splice(state.markets.indexOf(victim), 1);
      state.candidates.delete(victim.id);
      liqByMkt.delete(victim.id); // needs 2 fresh liquidations to come back
    }
    try {
      const r = await rpc('eth_call', [{ to: MORPHO, data: SEL.idToMarketParams + mid.slice(2) }, 'latest']);
      const h = r.slice(2);
      const loan = '0x' + h.slice(24, 64);
      const coll = '0x' + h.slice(64 + 24, 128);
      const oracle = '0x' + h.slice(128 + 24, 192);
      const irm = '0x' + h.slice(192 + 24, 256); // keep the actual IRM — encoding must match the created market
      const pm = pinnedMeta(mid); // a previously evicted PINNED market re-added: inherit the pinned metadata (measured pool/irm/decimals) — never a watch-only pool=null (review 99cc9216 blocker 3)
      const m = { id: mid, loan, coll, oracle, irm, lltv: '0x' + h.slice(256, 320), ldec: pm ? pm.ldec : null, cdec: pm ? pm.cdec : null, pool: pm ? pm.pool : null, zeroForOne: pm ? pm.zeroForOne : null };
      const dec = await tryAggregate([
        { to: loan, data: SEL.decimals }, { to: coll, data: SEL.decimals },
      ]);
      if (dec[0].success && dec[1].success) {
        m.ldec = parseInt(dec[0].returnData, 16); m.cdec = parseInt(dec[1].returnData, 16);
        state.markets.push(m);
        state.candidates.set(mid, new Map());
        log({ ts: new Date().toISOString(), type: 'market_added', id: mid, loan, coll, oracle, ldec: m.ldec, cdec: m.cdec, pool: m.pool, pinned: !!pm, events_in_window: cnt });
      }
    } catch (e) { log({ ts: new Date().toISOString(), type: 'error', msg: 'market_add ' + String(e).slice(0, 160) }); }
  }
  for (const [mid, cnt] of liqByMkt) {
    const m = state.markets.find(x => x.id === mid);
    if (m) m.lastLiq = Date.now();
  }
  // trim candidate sets, keep most recent (pinned markets use PIN_CAND_CAP so the
  // deep-discovered dormant debtors — the class the backfill exists for — are not
  // evicted by the freshest window addrs; run 2637916d, attempt 203)
  for (const [mid, cmap] of state.candidates) {
    const cap = pinnedMeta(mid) ? PIN_CAND_CAP : CAND_CAP;
    if (cmap.size > cap) {
      const keep = [...cmap.entries()].sort((a, b) => b[1] - a[1]).slice(0, cap);
      state.candidates.set(mid, new Map(keep));
    }
  }
  const totals = [...state.candidates.values()].reduce((s, c) => s + c.size, 0);
  log({ ts: new Date().toISOString(), type: 'candidates_refreshed', markets: state.markets.length, candidates: totals, from_block: from, to_block: to, tip_block: tip, getlogs_calls: logStats.calls, ms: Date.now() - t0 }); // review 99cc9216: to_block is the ACTUAL batch endpoint; tip logged separately
}

function saveState(state) {
  try {
    const o = {
      markets: state.markets,
      candidates: [...state.candidates].map(([k, v]) => [k, [...v]]),
      cursor: state.cursor || null,
      deepCursor: state.deepCursor === undefined ? null : state.deepCursor,
      deepDone: state.deepDone === true, // persisted once the deep backfill completed (review 2d13ac44 blocker 3 migration)
      liqCounts: [...(state.liqCounts || [])],
      underwaterSince: [...(state.underwaterSince || [])],
      liveLoss: state.liveLoss || { usd: 0, pending: [] },
    };
    const tmp = STATE_FILE + '.tmp';
    fs.writeFileSync(tmp, JSON.stringify(o));
    fs.renameSync(tmp, STATE_FILE); // review 13c85970 blocker 4: atomic write (temp + rename) — a crash mid-write must not truncate the loss state
    return true;
  } catch (e) { return false; } // review 233973f5: persistence failure must be visible — the loss state is NOT best-effort anymore
}
// Fix (review 2026-11-09 run 233973f5): the §5 loss state (liveLoss.usd, pending
// send hashes, stopLogged) was updated every scan but saved only on the five-minute
// refreshCandidates path, so a restart after a send or receipt could reload an old
// total and lose a pending hash — cumulative loss could cross 30 USD without a stop.
// persistState writes durably after EVERY such change and fails closed: while the
// last write failed, live sends are refused until a later write succeeds.
let stateWriteFailed = false;
function persistState(state) { const ok = saveState(state); stateWriteFailed = !ok; return ok; }
// Fix (review 2026-11-09 run 13c85970, checklist items 8/9): state/STOPPED.json is the
// durable stop marker — at LIVE startup its mere existence means the previous run
// reached the $30 stop, and this restart must refuse sending: the stop is sticky across
// restarts. The persisted total is raised to the threshold too, so the pre-send check
// (usd >= LIVE_LOSS_STOP_USD) enforces it even if the file's total was lost.
// Fix (review 2026-11-09 run 7ba9c267, checklist item 9): failing closed until the first
// scanCycle persistState() is NOT enough — that write succeeds, clears the flag and
// sends resume with a SILENTLY ZEROED loss total (the prior pending hashes and realized
// loss were in the damaged file; STOPPED.json was never written because the stop was
// never crossed). The halt must be kept until the prior loss history is RECOVERED, or
// made durable by a stop marker. Recovery source: the bot's own append-only log.
// Fix (review 2026-11-09 run c0654dd1, checklist item 9): the old SECOND-TO-LAST-heartbeat
// cutoff assumed a receipt settles within ~2 ticks of its send; it does not. A failed
// receipt read, a failed valuation or a malformed gas field keeps a hash pending through
// MANY heartbeats (the send gate holds every send meanwhile — checklist item 2), so a
// receipt older than two heartbeats can still be uncounted. Recovery now keeps ALL
// accepted send hashes whose settlement is NOT durably recorded: liveLossSettle logs a
// {type:'live_loss_settled', hash, live_loss_usd} event the moment it counts a receipt,
// and every hash covered by such an event (or by a later heartbeat total) is inside the
// total. Unsettled hashes stay pending: their gas lands again once the receipt is re-read
// — over-, never under-count. The recovered total is the LAST total durably recorded: a
// heartbeat (written at the end of the tick, after settlement) or a settlement event (a
// crash between settlement and the heartbeat leaves no heartbeat carrying that charge; the
// event itself carries the new total). A log with live sends but NO total recorded
// anywhere, an unreadable log, or no log after a real run: history not restorable — keep
// the halt and make it durable (set the total to the threshold, stopLogged, write the
// STOPPED.json marker; sends stay blocked across restarts). No log file / empty log: no
// prior live run to lose, a zero total is the truth.
function recoverLossFromLogs() {
  let raw;
  try { raw = fs.readFileSync(LOG, 'utf8'); } catch (e) { return { fresh: true }; } // no log file: no prior live run
  if (!raw || !raw.trim()) return { fresh: true }; // empty log: no prior run
  const lines = raw.split('\n');
  const sends = [];
  const settled = new Set();
  let lastUsd = null; // append order: the LAST durably recorded total wins (heartbeat or settlement event)
  for (const ln of lines) {
    if (!ln || (ln.indexOf('"type":"live_send"') < 0 && ln.indexOf('"type":"pool_init_sent"') < 0 && ln.indexOf('"type":"heartbeat"') < 0 && ln.indexOf('"type":"live_loss_settled"') < 0)) continue;
    let o = null; try { o = JSON.parse(ln); } catch (e) { continue; }
    if (!o || typeof o !== 'object' || typeof o.ts !== 'string') continue;
    if (o.type === 'heartbeat' && typeof o.live_loss_usd === 'number' && Number.isFinite(o.live_loss_usd)) {
      lastUsd = o.live_loss_usd;
    } else if (o.type === 'live_loss_settled' && typeof o.live_loss_usd === 'number' && Number.isFinite(o.live_loss_usd) && typeof o.hash === 'string' && /^0x[0-9a-fA-F]{10,}$/.test(o.hash)) {
      lastUsd = o.live_loss_usd; settled.add(o.hash); // settlement logged with its new total: this hash is durably counted
    } else if ((o.type === 'live_send' || o.type === 'pool_init_sent') && o.result && o.result.ok
      && typeof (o.result.txHash || o.result.hash) === 'string' && /^0x[0-9a-fA-F]{10,}$/.test(o.result.txHash || o.result.hash)) {
      sends.push(o.result.txHash || o.result.hash);
    }
  }
  if (lastUsd === null) return sends.length ? null : { fresh: true }; // sends logged with NO total recorded anywhere: not restorable
  const pending = []; const seen = new Set();
  for (const h of sends) if (!settled.has(h) && !seen.has(h)) { seen.add(h); pending.push(h); } // retain ALL accepted hashes whose settlement is not durably recorded (review c0654dd1)
  return { usd: lastUsd, pending };
}
function writeStartupStopMarker(reason) {
  try {
    const p = path.join(STATE, 'STOPPED.json');
    fs.writeFileSync(p + '.tmp', JSON.stringify({ reason, live_loss_usd: LIVE_LOSS_STOP_USD, at: new Date().toISOString() }) + '\n');
    fs.renameSync(p + '.tmp', p);
    return true;
  } catch (e) { return false; }
}
function stoppedFileGate(liveLoss) {
  let stoppedPresent = false;
  try { stoppedPresent = BOT_MODE === 'live' && fs.existsSync(path.join(STATE, 'STOPPED.json')); } catch (e) { stoppedPresent = false; }
  if (!stoppedPresent) return { stoppedPresent, liveLoss: liveLoss || { usd: 0, pending: [] } };
  const l = liveLoss || { usd: 0, pending: [] };
  l.stopLogged = true; // STOPPED.json exists: never re-write the reason this run
  l.usd = Math.max(l.usd, LIVE_LOSS_STOP_USD);
  return { stoppedPresent, liveLoss: l };
}
function loadState() {
  try {
    const o = JSON.parse(fs.readFileSync(STATE_FILE, 'utf8'));
    const gated = stoppedFileGate(o.liveLoss); // cumulative live-loss stop (§5): absent in pre-2026-11-09 state files
    const state = {
      markets: o.markets,
      candidates: new Map(o.candidates.map(([k, v]) => [k, new Map(v)])),
      cursor: o.cursor || null,
      deepCursor: 'deepCursor' in o ? o.deepCursor : undefined,
      deepDone: o.deepDone === true,
      liqCounts: new Map(o.liqCounts || []),
      underwaterSince: new Map(o.underwaterSince || []),
      liveLoss: gated.liveLoss,
    };
    if (state.markets && state.markets.length && [...state.candidates.values()].every(c => c instanceof Map)) {
      // pinned fields (swap pool, irm) may be newer than the saved state
      for (const pm of MARKETS) {
        const sm = state.markets.find(x => x.id === pm.id);
        if (sm) { sm.pool = sm.pool || pm.pool; sm.irm = sm.irm || pm.irm; sm.lltv = sm.lltv || pm.lltv; sm.zeroForOne = sm.zeroForOne ?? pm.zeroForOne; sm.pdiv = pm.pdiv; } // pinned metadata is authoritative: an old persisted row (e.g. the pre-fix pdiv 39) is OVERWRITTEN, never preserved over the pinned value (review 1c01613e migration)
      }
      return state;
    }
  } catch (e) { /* fall through to fresh */ }
  // Fix (review 13c85970 blocker 4): in LIVE mode a missing or malformed state file must not
  // silently reload the cumulative loss as zero — checklist item 9 fails closed: every send is
  // refused (stateWriteFailed gates the live send paths) until the next successful state write.
  // Fix (review 2026-11-09 run 7ba9c267, checklist item 9): the fail-closed flag alone rearms
  // on the first successful persistState with a zeroed total — recover the prior loss history
  // from the durable log, or write the durable stop marker; never rearm on a silent zero.
  const gated = stoppedFileGate(null);
  if (BOT_MODE === 'live') stateWriteFailed = true;
  let liveLoss = gated.liveLoss;
  if (BOT_MODE === 'live' && !gated.stoppedPresent) {
    const rec = recoverLossFromLogs();
    if (rec && rec.fresh) {
      // no prior live run: the zero total is the history
    } else if (rec) {
      liveLoss = { usd: rec.usd, pending: rec.pending.slice() };
      log({ ts: new Date().toISOString(), type: 'state_recovered', live_loss_usd: rec.usd, pending_hashes: rec.pending.length, source: 'logs/bot.jsonl heartbeats + live_send/pool_init_sent hashes' });
    } else {
      liveLoss = { usd: LIVE_LOSS_STOP_USD, pending: [], stopLogged: true };
      writeStartupStopMarker('live state file missing or unreadable at startup and the loss history is not restorable from the logs: fail-closed durable stop marker written at startup, sending blocked');
      log({ ts: new Date().toISOString(), type: 'state_unrecoverable', live_loss_usd: liveLoss.usd, note: 'STOPPED.json marker written at startup; sends stay blocked across restarts' });
    }
  }
  return { markets: MARKETS.map(m => ({ ...m })), candidates: new Map(MARKETS.map(m => [m.id, new Map()])), cursor: null, deepCursor: undefined, deepDone: false, liqCounts: new Map(), underwaterSince: new Map(), liveLoss };
}

async function simulateLiquidation(m, user, seized, repaid, proceeds, collValue, sizingBranch, state) {
  if (!m.pool) {
    log({ ts: new Date().toISOString(), type: 'opportunity_watch_only', market: m.id, borrower: user, reason: 'no measured collateral swap pool for this market' });
    return;
  }
  if (!RUNTIME_OK) {
    log({ ts: new Date().toISOString(), type: 'opportunity_watch_only', market: m.id, borrower: user, reason: 'executor runtime missing or immutable slots unpatched (fail closed)' });
    return;
  }
  // Deterministic-revert skip BEFORE any RPC (review 1c01613e blocker 4: ~15
  // RPC reads per WBTC opportunity were spent on simulations that ALWAYS
  // revert — a dust position with debt_usd 22 / coll_value_usd 23 logged
  // profit_usd_oracle 0 every cycle and the executor reverts unless sale
  // proceeds exceed the repaid debt by minProfit). At ORACLE price the
  // selected-proceeds outcome is known without a call: if it cannot clear the
  // on-chain minProfit floor, the sim reverts for sure — skip it. Positions
  // whose oracle proceeds clear the floor still pay one sim RPC; the swap
  // realized price may move a marginal case into profit, which the sim catches.
  // Floor = the EXACT on-chain minProfit the sim on this cycle enforces
  // (MIN_PROFIT_USD + the expected fee leg, review b87263e4: the fixed 1-USD
  // floor still let the 22/30-USD dust wave borrowers through every cycle —
  // oracle profit 1.01/1.34 USD clears 1 USD but cannot clear the enforced
  // 2.13-2.22 USD floor, so their sims reverted NO_PROFIT 12/12 deterministically).
  // A profit below this floor could never be SENT either: the live gate
  // requires profitWei >= MIN_PROFIT_USD + expected fee (the same number), so
  // the skip loses no sendable opportunity. Without a fresh fee policy the
  // floor falls back to the static MIN_PROFIT_WEI (fail-open, sim as today).
  const loanUnit = 10n ** BigInt(m.ldec);
  const expFeeEarlyUsd = expectedFeeUsd(feePolicy); // null when policy/valuation stale
  const scanFloorWei = expFeeEarlyUsd === null ? MIN_PROFIT_WEI
    : (BigInt(Math.ceil((MIN_PROFIT_USD + expFeeEarlyUsd) * 1e6)) * loanUnit + 999999n) / 1000000n;
  const profitScanWei = profitEstimate(m, proceeds, repaid);
  if (profitScanWei < scanFloorWei) {
    log({ ts: new Date().toISOString(), type: 'simulate_skip', market: m.id, borrower: user,
      debt_usd: Number(repaid / loanUnit), profit_usd_oracle: Number(profitScanWei / loanUnit),
      reason: `oracle-price proceeds ${proceeds} <= repaid ${repaid} + minProfit floor ${scanFloorWei}: executor reverts deterministically, no RPC spent` });
    return;
  }
  // Flash enough to cover the repaid debt (rational +0.5% headroom, CEIL
  // division, rounded up to loan units, plus a 2-unit dust buffer); the
  // excess is repaid out of the sale. If the sale proceeds fall short of
  // repaid + flash pull-back, the tx reverts: gas only.
  const flashAmount = ((repaid * 1005n + 999n) / 1000n / loanUnit + 1n) * loanUnit + 2n * loanUnit;
  const swapData = encPoolSwap(EXEC, seized, m.loan, m.coll, m.zeroForOne);
  // All-fee estimate runs on a MAX-CONTENT calldata through the COMPLETE
  // canonical type-2 transaction bytes (maximum-entropy signature filler; the
  // enforced bound below does not depend on the estimate):
  const calldataMax = encExecutorCall(m, user, seized, flashAmount, (1n << 256n) - 1n, swapData);
  const skip = (reason) => log({ ts: new Date().toISOString(), type: 'live_skip', borrower: user, reason });
  let simFrom = EXEC_OWNER;
  let me = null;
  let nonce = 0n;
  // Live pre-flight — signer address, fresh native valuation, deployed code,
  // executor ownership and the account nonce — completes BEFORE every derived
  // fee/economic value, which is then computed from the SAME nonce the live
  // send will use (review 2d13ac44 blocker 2: gasUsd/minProfitOn/calldata were
  // computed at nonce 0 and never refreshed after the live nonce read).
  if (BOT_MODE === 'live') {
    const w = await signerCall({ op: 'address' });
    if (!w.ok) { skip('no signer address: ' + String(w.error).slice(0, 80)); return; }
    me = '0x' + String(w.address).slice(-40);
    if (!ETH_USD || Date.now() - ETH_USD_AT > ETH_USD_STALE_MS) { skip('native valuation missing or stale'); return; }
    // Fix (review 2939f16e, 2026-11-09): the §5 $30 cumulative-loss stop must gate
    // EVERY signer send, including the pool-init setPoolAllowed tx below — the old
    // order let a new pool spend gas after the stop was reached (STOPPED.json was
    // already written). Check the stop BEFORE this preflight's first possible send.
    if (state.liveLoss.usd >= LIVE_LOSS_STOP_USD) {
      if (!state.liveLoss.stopLogged) { if (liveLossStopWrite(state)) state.liveLoss.stopLogged = true; persistState(state); } // review 13c85970 blocker 5: flag only once the STOPPED.json write succeeded — a failed write is retried
      log({ ts: new Date().toISOString(), type: 'send_stop', borrower: user, live_loss_usd: state.liveLoss.usd, max_usd: LIVE_LOSS_STOP_USD, reason: 'pre-send stop check — gates every signer send, pool initialization included' });
      return;
    }
    // Fix (review 2939f16e, then review 13c85970 blocker 1): block sends while ANY
    // confirmed gas receipt is pending — not only when the price is not freshly
    // valued. The old condition let a fresh price permit pool-init and liquidation
    // sends while a failed receipt read had left its receipt pending, so unvalued
    // gas kept growing past the pending send (checklist item 2). Settlement runs
    // earlier in the same cycle, so receipts confirmed in a previous cycle clear
    // this gate before this cycle can send; a send's own hash stays pending (and
    // blocks further sends) until the next cycle's settlement values it.
    if (state.liveLoss.pending.length > 0) { skip('confirmed gas receipts pending — fail closed, no send until settlement values them (every signer send is blocked, review 13c85970)'); return; }
    const code = await rpc('eth_getCode', [EXEC, 'latest']).catch(() => null);
    if (!code || code === '0x') { skip('executor has no deployed code (gate has not deployed)'); return; }
    let owner;
    try { owner = '0x' + (await rpc('eth_call', [{ to: EXEC, data: SEL_EXEC_OWNER }, 'latest'])).slice(-40); } catch (e) { skip('owner() read failed'); return; }
    if (owner.toLowerCase() !== me.toLowerCase()) { skip(`executor owner ${owner} != our wallet ${me}`); return; }
    try { nonce = BigInt(await rpc('eth_getTransactionCount', [me, 'latest'])); } catch (e) { skip('nonce read failed'); return; }
    if (!feePolicy) { skip('fee policy missing (header base-fee read failed — fail closed, nothing is sent without a derived maxFee)'); return; }
    // Pool-allow init on the DEPLOYED executor (review a41d9200 blocker 2): the
    // constructor whitelists only the WETH pool; every other executable pool must
    // have been armed by this owner's setPoolAllowed tx. Verify the deployed
    // getter before advertising/sending the route; while false, send the one init
    // tx through the signer (a signer rejection is final: sent-once per pool)
    // and skip this opportunity until the getter proves the armed state.
    if (m.pool) {
      let allowed = false;
      try {
        const ar = await rpc('eth_call', [{ to: EXEC, data: SEL_EXEC_IS_POOL_ALLOWED + addr(m.pool) }, 'latest']);
        allowed = /^0x[0-9a-f]{62}01$/.test(ar.toLowerCase());
      } catch (e) { skip('isPoolAllowed read failed'); return; }
      if (!allowed) {
        if (!poolInitSent.has(m.pool)) {
          // Fix (review 13c85970 blocker 2): the pool-init signer send lacked the stateWriteFailed
          // gate — after a failed state write every signer send must be refused, initialization included.
          if (stateWriteFailed) { skip('state persistence failed — fail closed, no send (pool initialization included) until the next successful state write'); return; }
          poolInitSent.add(m.pool);
          const r = await signerCall({ op: 'send', chain: CHAIN, to: EXEC,
            data: SEL_EXEC_SET_POOL_ALLOWED + addr(m.pool) + '0'.repeat(63) + '1',
            gas: '0x186a0', maxFeePerGas: '0x' + feePolicy.maxFeeWei.toString(16),
            maxPriorityFeePerGas: '0x' + FEE_TIP_WEI.toString(16) });
          log({ ts: new Date().toISOString(), type: 'pool_init_sent', pool: m.pool, market: m.id, result: r });
          if (r && r.ok && (r.txHash || r.hash)) { state.liveLoss.pending.push(r.txHash || r.hash); persistState(state); } // the init tx pays gas too; review 233973f5: persist the accepted hash BEFORE another send
        }
        skip(`pool not initialized on deployed executor (isPoolAllowed(${m.pool.slice(0, 10)}..)=false)`); return;
      }
    }
    simFrom = me; // no code override: simulate the deployed executor from our wallet
  }
  let fbound = await feeBound(calldataMax, nonce); // estimate at the nonce the live send uses
  if (BOT_MODE === 'live' && !fbound.ok) { skip('fee bound unavailable / over allowance (460k x derived maxFee > 0.00805 ETH, maxFee < base fee + tip, or policy missing): ' + JSON.stringify(fbound)); return; }
  const gasUsd = worstCaseGasLossUsd(fbound); // null => fail closed for live sends
  // On-chain minProfit = POST-FEE profit floor in loan-asset wei (review
  // c7693f9e blocker 3): the executor reverts unless realized sale proceeds
  // exceed the repaid debt by MIN_PROFIT_USD + the fee leg, instead of a fixed
  // 1 USDC that ignored fees. (Revision 8b738b25, review a1438eb0 blocker 2: the
  // fee leg is the EXPECTED fee the chain will actually charge — EXPECTED_GAS_WEI
  // x (live base fee + tip) at the fresh native valuation — not the worst-case
  // signed-cap product. With the old fixed 0.2 gwei cap the two were the same
  // 0.0003 ETH, but under a DERIVED maxFee the worst case (x gasLimit) is a
  // loss bound, while the floor must reflect the fee the transaction actually
  // pays: the 26302109-class capture (oracle profit ~2.37 USDC) is a real profit
  // at the current base fee, yet the worst-case bound suppressed every send.
  // The L bound stays enforced separately: feeBound.totalWei = maxFeePerGas x
  // gasLimit is the signed-field worst case, checked against LIVE_FEE_ALLOWANCE_WEI
  // here and against the 20 USD L cap below.)
  let minProfitOn = MIN_PROFIT_WEI; // paper fallback
  const expFeeUsd = expectedFeeUsd(feePolicy); // null => stale valuation / no policy: fail closed below
  if (gasUsd !== null && expFeeUsd !== null) {
    minProfitOn = (BigInt(Math.ceil((MIN_PROFIT_USD + expFeeUsd) * 1e6)) * loanUnit + 999999n) / 1000000n;
  } else if (BOT_MODE === 'live') { skip('expected fee unavailable (stale native valuation or missing policy) — no send'); return; }
  const calldata = encExecutorCall(m, user, seized, flashAmount, minProfitOn, swapData);
  // All-fee loss bound (review 99cc9216 blocker 1: honest enforcement split).
  // What the chain ENFORCES per transaction: (a) the signed-field L2 cap
  // maxFeePerGas x gasLimit; (b) the operator-fee formula at gasUsed <=
  // gasLimit (parameters read in-path, moving only at L2 epochs); (c) the L1
  // data fee the chain computes over our final tx bytes at the inclusion
  // block's L1 origin — the only leg no transaction field caps (EIP-1559 base
  // fee drifts <= 12.5% per L1 block between our preflight read and
  // inclusion). The bot bounds (c) by FEE_BOUND_MARGIN x its in-path getL1Fee
  // measurement and refuses to send when measured total x margin > 20 USD —
  // an ESTIMATE with a drift margin, not an inclusion-time cap: while
  // LIVE_FEE_CAP_ENFORCED=false the live path logs live_skip and sends nothing
  // (review 54ffa8cc blocker 1, the reviewer's accepted alternative).
  // The wallet-balance check below is a VALIDITY check plus the gate's
  // requested funding policy (<= LIVE_BALANCE_CAP_USD gas float): the bot
  // cannot enforce that an EOA never receives ETH, an inflow only affects
  // fee-validity, never raises the fee the chain charges ((a)+(b)+(c)).
  let worstCaseFeeUsd = gasUsd === null ? null : gasUsd * FEE_BOUND_MARGIN; // measured preflight total x margin
  if (BOT_MODE === 'live') {
    let balWei;
    try { balWei = BigInt(await rpc('eth_getBalance', [me, 'latest'])); } catch (e) { skip('wallet balance read failed'); return; }
    const capWei = BigInt(Math.floor(LIVE_BALANCE_CAP_USD / ETH_USD * 1e15)) * 1000n; // funding-policy cap in wei at the fresh price
    if (balWei > capWei) { skip(`wallet balance ${(Number(balWei) / 1e18).toFixed(6)} ETH exceeds the ${LIVE_BALANCE_CAP_USD} USD gas-float funding policy at ETH/USD ${ETH_USD.toFixed(1)} — funding cap breached`); return; }
  }
  // Simulate the EXACT live calldata (the bytes computed from the final fee
  // bound above — nothing here is estimated at a stale nonce). Paper: from
  // EXEC_OWNER (the owner baked into the constructor-patched runtime) with a
  // code state-override. Live: from OUR wallet against the DEPLOYED code with
  // NO override — review c7693f9e blocker 1: overriding with the paper runtime
  // (owner 0xff..fe) made every non-fork-deployer caller hit ONLY_OWNER, so
  // the live sim could never succeed for the real wallet.
  const callParams = [{ from: simFrom, to: EXEC, data: calldata }, 'latest'];
  // Paper: code override PLUS the one storage slot the live promotion flow leaves behind
  // (owner init tx setPoolAllowed(WBTC pool) — slot keccak(pool word ++ allowedPool mapping slot 1),
  // verified on the fork after init tx 0xfa60cf60ecbf621ea593765cba2de6d5f192051158200b3b99e432920a096d9b:
  // eth_getStorageAt == 0x...01, isPoolAllowed(WBTC pool) = true). Reviewer 1c01613e blocker 3:
  // 'allowedPool is storage; code-only override does not carry setPoolAllowed — model the WBTC
  // executor state initialized on paper'. The relay accepts the state as a slot->value map.
  if (BOT_MODE !== 'live') callParams.push({ [EXEC]: { code: RUNTIME_CODE, state: POOL_ALLOWED_INIT } });
  // A deterministic execution revert (POOL_NOT_ALLOWED, NO_PROFIT, position-is-healthy) must NOT
  // be retried — the old 4-attempt/15 s-retry loop made 1054 failed simulations spend 30 s of
  // wall time each and starve the scan (reviewer 1c01613e blocker 4: zero completed heartbeats).
  const sim = await rpc('eth_call', callParams, 0, 0)
    .then(() => ({ ok: true }))
    .catch(e => ({ ok: false, revert: String(e).slice(0, 200) }));
  // Selected-proceeds profit at oracle price, minus the all-fee USD bound
  // (fresh native valuation) for the live decision.
  const profitWei = profitEstimate(m, proceeds, repaid);
  // The integer division profitWei/loanUnit truncated cents (review 2e9cbbaa: an actual
  // 2.041431317 USD profit reached the live gate as the integer 2 and was suppressed
  // despite sim_ok). Keep full sub-cent precision for logs and compare the gate in
  // raw loan units — exact, no float or truncation loss.
  const profitUsd = Number(profitWei * 1000000n / loanUnit) / 1e6;
  const needUsd = MIN_PROFIT_USD + (expFeeUsd || Infinity); // live gate: expected post-fee profit floor = MIN_PROFIT_USD + the fee the send will actually pay
  const needRaw = Number.isFinite(needUsd) ? BigInt(Math.ceil(needUsd * 1e6)) : null; // the USD floor in loan-asset raw
  log({
    ts: new Date().toISOString(), type: 'simulate', market: m.id, borrower: user,
    seize_amount: seized.toString(), repaid_est: repaid.toString(), proceeds_est: proceeds.toString(),
    flash_amount: flashAmount.toString(),
    debt_usd: Number(repaid / loanUnit), coll_value_usd: Number(collValue / loanUnit),
    profit_usd_oracle: profitUsd, gas_bound_usd: gasUsd, expected_fee_usd: expFeeUsd, min_profit_usd: needUsd,
    fee_bound: fbound, min_profit_onchain: minProfitOn.toString(), sizing_branch: sizingBranch,
    nonce: nonce.toString(), worst_case_fee_usd: worstCaseFeeUsd === null ? null : worstCaseFeeUsd,
    sim_from: simFrom, code_override: BOT_MODE !== 'live', sim_ok: sim.ok, sim_revert: sim.revert || null,
    to: EXEC, calldata,
  });
  // Live path (all fail closed, rejections final, no retry loop): the
  // pre-flight checks above already verified the signer wallet, fresh native
  // valuation, deployed code, owner() == our wallet and the all-fee bound;
  // the pre-send sim of the EXACT bytes from our wallet succeeded, and the
  // oracle-price profit minus the all-fee bound clears MIN_PROFIT_USD.
  if (BOT_MODE === 'live' && sim.ok && gasUsd !== null && needRaw !== null && profitWei >= needRaw) {
    try {
      const skip = (reason) => log({ ts: new Date().toISOString(), type: 'live_skip', borrower: user, reason });
      if (stateWriteFailed) { skip('state persistence failed — fail closed, no send until the next successful state write (review 233973f5)'); return; }
      if (!LIVE_FEE_CAP_ENFORCED) { skip('live sends disabled: no enforced inclusion-time all-fee cap (review 54ffa8cc blocker 1 accepted alternative)'); return; }
      if (state.liveLoss.usd >= LIVE_LOSS_STOP_USD) { // §5 cumulative-loss stop: stop sending, reason in state/STOPPED.json
        if (!state.liveLoss.stopLogged) { if (liveLossStopWrite(state)) state.liveLoss.stopLogged = true; persistState(state); } // review 233973f5: persist the flag with the reason; review 13c85970 blocker 5: flag only after a durable STOPPED.json write
        log({ ts: new Date().toISOString(), type: 'send_stop', borrower: user, live_loss_usd: state.liveLoss.usd, max_usd: LIVE_LOSS_STOP_USD });
        return;
      }
      if (gasUsd * FEE_BOUND_MARGIN > 20) { skip(`measured all-fee bound x margin ${(gasUsd * FEE_BOUND_MARGIN).toFixed(2)} USD > 20`); return; } // review 99cc9216 blocker 1: the bot refuses to send when its in-path measured fee total, times the (c)-drift margin, exceeds L
      if (!me) { skip('no signer address'); return; }
      const sock = process.env.SIGNER_SOCK;
      if (!sock) { skip('no SIGNER_SOCK'); return; }
      const net = require('net');
      const req = JSON.stringify({ op: 'send', chain: CHAIN, to: EXEC, data: calldata, value: '0x0',
        gas: '0x' + MAX_GAS_LIMIT.toString(16), maxFeePerGas: '0x' + feePolicy.maxFeeWei.toString(16),
        maxPriorityFeePerGas: '0x' + FEE_TIP_WEI.toString(16) });
      const res = await new Promise((resolve) => {
        const c = net.connect(sock, () => c.write(req + '\n'));
        let buf = '';
        c.on('data', (d) => { buf += d; try { resolve(JSON.parse(buf)); } catch (e) { /* wait */ } });
        c.on('error', () => resolve({ error: 'sock_error' }));
        setTimeout(() => resolve({ error: 'timeout' }), 10000);
      });
      log({ ts: new Date().toISOString(), type: 'live_send', borrower: user, to: EXEC, gas_bound_usd: gasUsd, profit_usd_oracle: profitUsd, result: res });
      if (res && res.ok && (res.txHash || res.hash)) { state.liveLoss.pending.push(res.txHash || res.hash); persistState(state); } // settle its realized gas once the receipt is visible; review 233973f5: persist the accepted hash BEFORE another send
    } catch (e) { log({ ts: new Date().toISOString(), type: 'error', msg: 'live_send ' + String(e).slice(0, 160) }); }
  }
}

// One JSON line over the signer unix socket (live mode only): op 'address'
// returns our wallet so the live path can verify the executor owner.
function signerCall(obj) {
  return new Promise((resolve) => {
    const sock = process.env.SIGNER_SOCK;
    if (!sock) return resolve({ ok: false, error: 'no SIGNER_SOCK' });
    const net = require('net');
    const c = net.connect(sock, () => c.write(JSON.stringify(obj) + '\n'));
    let buf = '';
    c.on('data', (d) => { buf += d; try { resolve(JSON.parse(buf)); } catch (e) { /* wait */ } });
    c.on('error', (e) => resolve({ ok: false, error: String(e).slice(0, 80) }));
    setTimeout(() => resolve({ ok: false, error: 'timeout' }), 10000);
  });
}

const now0 = () => new Date().toISOString();

// --- cumulative live-loss stop (decisions/human/2026-11-09-promote-criteria.md §5) ---
// Realized loss = gas actually paid (gasUsed x effectiveGasPrice from the confirmed
// receipt, valued at the bot's fresh ETH/USD) plus any realized principal loss; the
// executor reverts unless its balance ends higher, so a failed send costs gas only.
// The bot stops sending at LIVE_LOSS_STOP_USD cumulative loss and writes the reason
// to state/STOPPED.json.
const LIVE_LOSS_STOP_USD = 30;
async function liveLossSettle(state, freshValuation, fetchReceipt) {
  const keep = [];
  const getReceipt = fetchReceipt || ((h) => rpc('eth_getTransactionReceipt', [h])); // offline tests inject a receipt stub (checklist item 10)
  // Fix (review 7cbf8b95, 2026-11-09): settle a confirmed receipt only after THIS
  // cycle's fresh gas valuation succeeded. The old top-of-cycle call valued the gas
  // at a cached price from an earlier cycle — if the oracle read failed while ETH/USD
  // rose, every settled receipt was counted too cheaply and the persisted cumulative
  // loss could stay below the $30 stop threshold forever. A cycle without a fresh
  // valuation keeps every receipt pending (fail closed) and defers settlement.
  if (!freshValuation) return; // keep all receipts pending: this cycle has no fresh gas valuation
  for (const h of state.liveLoss.pending) {
    let r = null;
    try { r = await getReceipt(h); } catch (e) {}
    if (!r) { keep.push(h); continue; } // receipt not visible yet
    // Fix (review 2026-11-09, attempt 677 parity): a CONFIRMED receipt must not be
    // dropped while the valuation is missing — on a live service restart ETH_USD
    // initializes to 0, so settling it now would omit that send's gas from
    // liveLoss.usd forever. Keep it pending while ETH_USD <= 0 and count it
    // exactly once when a positive fresh valuation exists.
    if (ETH_USD <= 0) { keep.push(h); continue; }
    // Fix (review 13c85970 blocker 3): a missing or malformed gas field must NOT default to
    // zero and drop the receipt (the old r.gasUsed || '0x0' settled a corrupt receipt at a
    // zero gas charge and removed it from pending forever) — keep it pending until the
    // actual gas is decoded from a valid quantity hex.
    const gu = r.gasUsed, ep = r.effectiveGasPrice;
    if (typeof gu !== 'string' || !/^0x[0-9a-fA-F]*$/.test(gu) || typeof ep !== 'string' || !/^0x[0-9a-fA-F]*$/.test(ep)) { keep.push(h); continue; }
    const gasEth = Number(BigInt(gu) * BigInt(ep)) / 1e18; // wei product kept exact, then float ETH (Number stays exact well below 2^53 at these gas sizes)
    state.liveLoss.usd += gasEth * ETH_USD;
    // Fix (review 2026-11-09 run c0654dd1, checklist item 9): durable proof that this hash is
    // now inside the total — startup recovery keeps every accepted send hash UNLESS a
    // live_loss_settled event (or a later heartbeat) covers it, regardless of how many
    // heartbeats the pending receipt spanned.
    log({ ts: new Date().toISOString(), type: 'live_loss_settled', hash: h, live_loss_usd: state.liveLoss.usd });
  }
  state.liveLoss.pending = keep;
}
// Fix (review 13c85970 blocker 5): liveLossStopWrite used to swallow the write error while
// the caller still set stopLogged — the flag then suppressed every later retry, so the
// stop reason could stay unpersisted forever. It now returns the write result; the caller
// sets stopLogged ONLY when the reason is durable, and the cycle-level check retries it.
// The write itself is atomic (temp + rename) like the state file.
function liveLossStopWrite(state) {
  try {
    const p = path.join(STATE, 'STOPPED.json');
    fs.writeFileSync(p + '.tmp',
      JSON.stringify({ reason: `cumulative live loss ${state.liveLoss.usd.toFixed(2)} USD reached ${LIVE_LOSS_STOP_USD} USD: stop sending`, live_loss_usd: state.liveLoss.usd, at: new Date().toISOString() }) + '\n');
    fs.renameSync(p + '.tmp', p);
    return true;
  } catch (e) { return false; }
}
// Fix (review 2026-11-09, attempt 677 parity): persist the §5 stop reason AS SOON AS
// settlement reaches the threshold — the send-time check in the live branch only
// fires when another qualifying candidate appears, so without this the reason is
// never written while the threshold sits crossed with no new opportunities.
// Called from scanCycle right after liveLossSettle; writes STOPPED.json exactly once
// (the persisted stopLogged flag also guards the send-time branch below).
function liveLossStopCheck(state) {
  if (BOT_MODE === 'live' && state.liveLoss.usd >= LIVE_LOSS_STOP_USD && !state.liveLoss.stopLogged) {
    if (liveLossStopWrite(state)) state.liveLoss.stopLogged = true; // review 13c85970 blocker 5: set the flag ONLY when the reason is durable; a failed write is retried by this cycle-level check
    persistState(state); // review 233973f5: STOPPED.json and the state total must stay consistent — persist the flag with the reason
    log({ ts: new Date().toISOString(), type: 'send_stop', live_loss_usd: state.liveLoss.usd, max_usd: LIVE_LOSS_STOP_USD, reason: 'settlement reached the stop threshold without a new opportunity: STOPPED.json persisted, sending stopped' });
  }
}

async function scanCycle(state) {
  RPC_CYCLE_START = RPC_TOTAL; // measure this cycle's relay reads (see RPC_TOTAL above)
  GAS_VALUED_THIS_CYCLE = false; // review 2939f16e: fresh-valuation flag is per cycle, cleared at start and set below only when this cycle's valuation slot read succeeds
  // Fix (review 7cbf8b95, 2026-11-09): liveLossSettle used to run HERE, at the top of
  // the cycle, before this cycle's gas valuation was read — settlement then used the
  // PREVIOUS cycle's cached ETH_USD. It now runs below, after the market/oracle loop,
  // only when this cycle's fresh valuation actually succeeded.
  const fpOk = await updateFeePolicy(); // one latest-header read per cycle: the base fee the chain charges at inclusion (review a1438eb0 blocker 2: a fixed cap is era-bound; maxFeePerGas is DERIVED from this read)
  if (!fpOk) feePolicy = null; // review 2e9cbbaa: a FAILED header refresh must not leave the previous cycle's policy usable — stale feePolicy fails closed (nothing is sent or priced on an unread header)
  const calls = [];
  const owners = [];
  const mslots = []; // { m, base } — call index of each market's market() call
  for (const m of state.markets) {
    mslots.push({ m, base: calls.length });
    // Accrued market state (review 021de292 blocker 3): Morpho.accrueInterest
    // runs as a REGULAR inner call inside the Multicall3 eth_call, so the
    // market() read AFTER it returns exactly the totals the protocol's own
    // _isHealthy/liquidate compute against (interest accrued to this second,
    // via the market's real IRM). Ephemeral: nothing is mutated on mainnet.
    calls.push({ to: MORPHO, data: SEL.market + m.id.slice(2) });            // raw (pre-accrual)
    calls.push({ to: MORPHO, data: SEL.accrue + addr(m.loan) + addr(m.coll) + addr(m.oracle) + addr(m.irm || IRM_DEFAULT) + BigInt(m.lltv).toString(16).padStart(64, '0') });
    calls.push({ to: MORPHO, data: SEL.market + m.id.slice(2) });            // accrued
    calls.push({ to: m.oracle, data: SEL.price });
    calls.push({ to: m.oracle, data: SEL.price }); // native (gas) valuation slot: for the WETH market this is the same oracle price read (USDC per WETH)
    let i = 0;
    const scanCap = pinnedMeta(m.id) ? PIN_CAND_CAP : CAND_CAP; // pinned sets are scanned past the discovery cap (run 2637916d)
    for (const u of state.candidates.get(m.id)?.keys() || []) {
      if (i++ >= scanCap) break;
      owners.push({ m, u, idx: calls.length });
      calls.push({ to: MORPHO, data: SEL.position + m.id.slice(2) + addr(u) });
    }
  }
  const res = [];
  for (let i = 0; i < calls.length; i += CHUNK) {
    const part = await tryAggregate(calls.slice(i, i + CHUNK));
    if (part.length !== calls.slice(i, i + CHUNK).length) log({ ts: now0(), type: 'debug', chunk_at: i, got: part.length, want: calls.slice(i, i + CHUNK).length });
    res.push(...part);
  }
  const now = new Date().toISOString();
  const mstate = new Map();
  let gasValuedThisCycle = false; // set when this cycle's WETH-oracle gas valuation read succeeds (review 7cbf8b95)
  for (const { m, base } of mslots) {
    const mres = res[base], ares = res[base + 1], mres2 = res[base + 2], pres = res[base + 3];
    if (!mres || !mres.success || mres.returnData.length < 130 || !mres2 || !mres2.success || mres2.returnData.length < 130 || !pres || !pres.success || pres.returnData.length < 10) {
      log({ ts: now, type: 'error', msg: `market_state_missing ${m.id.slice(0, 12)} m=${mres && mres.returnData.length} a=${ares && ares.success} p=${pres && pres.returnData.length}` });
      mstate.set(m.id, null);
      continue;
    }
    // fail closed when the accrual inner call failed (unaccrued totals would
    // mis-detect near the boundary): skip the market for this cycle.
    if (!ares || !ares.success) {
      log({ ts: now, type: 'error', msg: `accrue_inner_failed ${m.id.slice(0, 12)} — market skipped (fail closed)` });
      mstate.set(m.id, null);
      continue;
    }
    const mh = mres2.returnData.slice(2);
    const totBorAssets = BigInt('0x' + mh.slice(128, 192));
    const totBorShares = BigInt('0x' + mh.slice(192, 256));
    const price = BigInt('0x' + pres.returnData.slice(2));
    const wr = res[base + 4]; // native (gas) valuation slot — the WETH market's oracle price (USDC per WETH at its measured 1e36 scale)
    if (wr && wr.success && wr.returnData.length >= 66 && m.id === GAS_MARKET) {
      const gp = BigInt('0x' + wr.returnData.slice(2, 66));
      if (gp > 0n) { ETH_USD = Number(gp / 10n ** 24n); ETH_USD_AT = Date.now(); gasValuedThisCycle = true; } // measured 2026-11-04 (review 1c01613e): the oracle price is USDC-per-WETH at the protocol 1e36 scale — 1e36/1e18 = 1e24, NOT 1e33. Actual relay block 26343570 price 2418076957920000000000000000 -> 2418.07695792 USD per ETH with 18/6 token decimals; the old gp/1e33 integer-divided to 0, so every live send failed closed on 'native valuation missing'.
    }
    mstate.set(m.id, { totBorAssets, totBorShares, price });
  }
  // Fix (review 7cbf8b95, 2026-11-09): settlement moved from the top of the cycle to
  // here — after this cycle's valuation slot has been read — so confirmed receipts are
  // valued at the ETH/USD price measured IN THIS CYCLE, never at a cached earlier one.
  // Without a fresh valuation (oracle read failed or GAS_MARKET state missing) every
  // receipt stays pending and the cumulative loss is never understated.
  GAS_VALUED_THIS_CYCLE = gasValuedThisCycle; // review 2939f16e: publish THIS cycle's fresh-valuation result to the live send gates before settlement and before any candidate can send
  await liveLossSettle(state, gasValuedThisCycle); // settle confirmed live sends' realized gas into the cumulative loss (§5) at this cycle's fresh valuation
  liveLossStopCheck(state); // persist the §5 stop reason as soon as settlement crosses the threshold (no new candidate required)
  persistState(state); // review 233973f5: settlement changed liveLoss.usd/pending — persist it before this cycle can send
  let scanned = 0, debtors = 0, minHf = 10, minHfRow = null;
  const underwater = [];
  for (const { m, u, idx } of owners) {
    const r = res[idx];
    scanned++;
    if (!r || !r.success || r.returnData.length < 194) continue;
    const h = r.returnData.slice(2);
    const borrowShares = BigInt('0x' + h.slice(64, 128));
    const collateral = BigInt('0x' + h.slice(128, 192));
    if (borrowShares === 0n) continue;
    debtors++;
    const st = mstate.get(m.id);
    if (!st) continue;
    const econ = marketEconomics(m, collateral, borrowShares, st.totBorAssets, st.totBorShares, st.price);
    if (!econ) continue;
    if (econ.hf < minHf) { minHf = econ.hf; minHfRow = { market: m.id, user: u, hf: econ.hf, debt_usd: Number(econ.debtAssets / 10n ** BigInt(m.ldec)) }; }
    if (econ.hf < HF_WARN) {
      log({ ts: now, type: 'opportunity', market: m.id, user: u, hf: econ.hf, healthy: econ.healthy, debt_usd: Number(econ.debtAssets / 10n ** BigInt(m.ldec)), coll_value_usd: Number(econ.collValue / 10n ** BigInt(m.ldec)) });
    }
    if (!econ.healthy) {
      underwater.push({ m, u, collateral, borrowShares, econ });
      if (!state.underwaterSince.has(m.id + u)) state.underwaterSince.set(m.id + u, Date.now());
    } else if (state.underwaterSince.has(m.id + u)) {
      const elapsed = Date.now() - state.underwaterSince.get(m.id + u);
      state.underwaterSince.delete(m.id + u);
      log({ ts: now, type: 'underwater_closed', market: m.id, user: u, visible_ms: elapsed, note: 'was underwater on a previous cycle, now healthy/gone — opportunity window measured' });
    }
  }
  for (const { m, u, collateral, borrowShares, econ } of underwater) {
    const st2 = mstate.get(m.id);
    if (!st2) continue;
    const sizing = seizeFor(m, collateral, st2.price, st2.totBorAssets, st2.totBorShares, borrowShares);
    await simulateLiquidation(m, u, sizing.seized, sizing.repaid, sizing.proceeds, econ.collValue, sizing.branch, state);
  }
  log({ ts: now, type: 'heartbeat', scanned, debtors, markets: state.markets.length, min_hf: minHfRow ? minHfRow.hf : null, min_hf_row: minHfRow, underwater_now: underwater.length, eth_usd: ETH_USD, eth_usd_age_ms: ETH_USD_AT ? Date.now() - ETH_USD_AT : null, executor: EXEC, runtime_ok: RUNTIME_OK,
    fee_policy: feePolicy ? { header_block: feePolicy.headerBlock, base_fee_wei: feePolicy.baseFeeWei.toString(), max_fee_wei: feePolicy.maxFeeWei.toString(), gas_limit: MAX_GAS_LIMIT.toString() } : null,
    rpc_cycle: RPC_TOTAL - RPC_CYCLE_START, rpc_total: RPC_TOTAL, live_loss_usd: state.liveLoss.usd, live_loss_stop_usd: LIVE_LOSS_STOP_USD });
}

async function main() {
  log({ ts: new Date().toISOString(), type: 'start', mode: BOT_MODE, relay: RELAY, lane: LANE, morpho: MORPHO, markets_pinned: MARKETS.length, executor: EXEC, executor_owner_sim_from: EXEC_OWNER, runtime_ok: RUNTIME_OK, runtime_len: RUNTIME_CODE.length / 2 });
  const state = loadState();
  state.underwaterSince = state.underwaterSince || new Map();
  // Serialized refresh->scan tick chain (review 1c01613e blocker 4: the old
  // design ran scanCycle on a 20 s setInterval AND refreshCandidates in a
  // concurrent loop, so a slow scan overlapped the next cycle and a full
  // rediscovery — RPC reads multiplied, scans never completed, and the
  // supervised run logged zero heartbeats). One self-scheduling chain: a tick
  // starts only after the previous one finished; refresh runs at most every
  // REFRESH_MS inside the same tick (retry + backoff on RPC error, an RPC
  // error must never kill the process — the startup crash cause — and the
  // cursor only advances on a fully successful refresh).
  let backoff = 5000;
  let lastRefresh = 0; // ms epoch of the last SUCCESSFUL refresh (0: first tick refreshes immediately)
  let refreshPending = false; // last refresh attempt failed: a bounded retry is pending
  let nextRetryAt = 0; // ms epoch: a failed refresh is retried no earlier than this
  async function tick() {
    const t0 = Date.now();
    // Cadence (review a41d9200 blocker 3): the old condition
    // (!refreshPending || t0 - lastRefresh >= REFRESH_MS) re-ran the FULL refresh
    // after every successful tick — refreshPending is cleared on success, so the
    // 300 s cadence was never honored (supervised logs: getLogs rediscovery every
    // ~23 s, not 300 s) — while after a failure it waited the full REFRESH_MS
    // since the last success instead of the promised next-tick retry.
    // Now: on success, refresh only every REFRESH_MS; a failure retries no
    // earlier than nextRetryAt (bounded exponential backoff 5 s..60 s), and the
    // next scheduled refresh due keeps working regardless.
    // Cadence (review e7daaefc blocker 1): the old condition above OR-ed the
    // overdue-cadence leg with the failure deadline — so whenever the last
    // SUCCESS was already older than REFRESH_MS (startup lastRefresh=0, and any
    // steady-state overdue slice) the FULL refresh fired on the next tick and
    // BYPASSED nextRetryAt: the reviewer's exact-tick fixture with injected
    // failures assigned 10 s/20 s/40 s deadlines, and the 1060000 tick after
    // the third failure refreshed anyway. Now a pending failure deadline takes
    // precedence over the ordinary overdue cadence: with a failure pending the
    // tick refreshes only at t0 >= nextRetryAt; without one, on the cadence.
    // retry_in_ms logs the ASSIGNED doubled deadline, not the old one.
    const cadenceDue = t0 - lastRefresh >= REFRESH_MS;
    if (refreshPending ? t0 >= nextRetryAt : cadenceDue) {
      try {
        await refreshCandidates(state);
        persistState(state);
        backoff = 5000;
        refreshPending = false;
        lastRefresh = t0;
      } catch (e) {
        backoff = Math.min(backoff * 2, 60000); // the doubled deadline ASSIGNED by this failure
        nextRetryAt = t0 + backoff; // bounded failure retry (ticks fire every CYCLE_MS)
        refreshPending = true;
        log({ ts: new Date().toISOString(), type: 'refresh_error', msg: String(e).slice(0, 300), retry_in_ms: backoff });
      }
    }
    try {
      await scanCycle(state);
      persistState(state); // review 233973f5: scanCycle changed cursors/liveLoss — persist after EVERY scan, not only on the refresh cadence
    } catch (e) {
      log({ ts: new Date().toISOString(), type: 'error', msg: String(e).slice(0, 300), stack: String(e.stack).split('\n').slice(0, 4).join(' | ') });
    }
    setTimeout(tick, CYCLE_MS); // next cycle never overlaps this one
  }
  setTimeout(tick, 0); // heartbeats start immediately and never depend on refresh success
}
// Reusable by fork-evidence harnesses (scratch/morpho-fix-511fc3e7/): the exact
// sizing/fee-bound code paths reviewed here run unmodified against the fork.
module.exports = { MARKETS, marketEconomics, incentiveFactor, repaidChain, seizeFor,
  encExecutorCall, encPoolSwap, feeBound, worstCaseGasLossUsd,
  pickEvictVictim, pinnedMeta,
  refreshCandidates, scanCycle, loadState, saveState, getLogsPaged, tryAggregate,
  liveLossSettle, liveLossStopCheck, liveLossStopWrite, LIVE_LOSS_STOP_USD, persistState, // review 13c85970 checklist item 10: the offline stop-test drives these through the module (BOT_STATE_DIR points state/ at scratch/)
  getStateWriteFailed: () => stateWriteFailed,
  rpc, RUNTIME_OK, RUNTIME_CODE, EXEC, EXEC_OWNER, CAPITAL_REPAID_CAP, MIN_PROFIT_WEI,
  MAX_GAS_LIMIT, FEE_TIP_WEI, FEE_CAP_WEI, EXPECTED_GAS_WEI, FEE_BOUND_MARGIN,
  updateFeePolicy, expectedFeeUsd, getFeePolicy: () => feePolicy,
  setFeePolicy: (p) => { feePolicy = p; }, setEthUsd: (v) => { ETH_USD = v; ETH_USD_AT = Date.now(); } };
if (require.main === module) main();
