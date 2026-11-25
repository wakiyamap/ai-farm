#!/usr/bin/env node
// morpho-watcher-base — Morpho Blue (v2) liquidation watcher on the farm's Base chain.
// Paper mode: tracks borrowers on the most-liquidated Morpho markets, computes health
// factors via Multicall3 (market + position + oracle price), logs opportunities and
// simulates liquidate() when a position goes underwater. Live mode: sends the same
// calldata through the signer socket with min-profit + gas-cap guards.
// Self-contained: node built-ins only. All constants measured on-chain 2026-11-03
// (run 14950527, scratch/morpho/probe.js + replay2.js + live_test.js).
'use strict';
const fs = require('fs');
const path = require('path');

const RELAY = process.env.RPC_RELAY_URL || 'http://127.0.0.1:8545';
const LANE = process.env.RPC_LANE || 'paper';
const BOT_MODE = process.env.BOT_MODE || 'paper';
const CHAIN = 'base';
const DIR = __dirname;

// --- measured constants ---
const MORPHO = '0xbbbbbbbbbb9cc5e90e3b3af64bdaf62c37eeffcb'; // Morpho Blue v2 singleton (ledger: 94 liquidations/36h)
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
const IRM_DEFAULT = '0x46415998764c29ab2a25cbea6254146d50d22687';

// Top-4 liquidated markets on base in the last 36h (38+27+14+8 = 87% of 94 events).
// All borrow USDC against: JitoSOL / SOL / cbZEC / cbBTC. loan decimals = 6 for all.
// pool = measured collateral-swap pool for the executor (null = watch-only:
// opportunity logged, no executor sim / live send until a pool is measured).
const MARKETS = [
  { id: '0x09276541cfecb6920a80679a1deced4dde3ae64bf5fc2c9c1f9c21e0c152e1a5', loan: '0x833589fcd6edb6e08f4c7c32d4f71b54bda02913', coll: '0x97be14dd8f994a5364573bc035d85309e7cb34de', ldec: 6, cdec: 9, oracle: '0x78f772f5fcc03256260cc1165e34da9bb3f9be1c', lltv: '625000000000000000', irm: '0x46415998764c29ab2a25cbea6254146d50d22687', pool: null },
  { id: '0x7dc02ff6c536b1d49d7fba770438d79f5bd1f1c78884629b7d1aaee19675782b', loan: '0x833589fcd6edb6e08f4c7c32d4f71b54bda02913', coll: '0x311935cd80b76769bf2ecc9d8ab7635b2139cf82', ldec: 6, cdec: 9, oracle: '0xe9725430f3a72611ac72eddc650625bce4f45dc7', lltv: '625000000000000000', irm: '0x46415998764c29ab2a25cbea6254146d50d22687', pool: null },
  { id: '0xe458a501c1103ca3b256f2bcb45d223263fb34b6349d82675494ce3a94ce1327', loan: '0x833589fcd6edb6e08f4c7c32d4f71b54bda02913', coll: '0xb2000000000000000000008501b13360000cb2ec', ldec: 6, cdec: 8, oracle: '0xa3cb2d7204f47a468b82c6fab1ca9675e9f7a272', lltv: '625000000000000000', irm: '0x46415998764c29ab2a25cbea6254146d50d22687', pool: '0xe7030be388b8e247abe0c9fa876673e83fbcbd3c' },
  { id: '0x9103c3b4e834476c9a62ea009ba2c884ee42e94e6e314a26f04d312434191836', loan: '0x833589fcd6edb6e08f4c7c32d4f71b54bda02913', coll: '0xcbb7c0000ab88b473b1f5afd9ef808440eed33bf', ldec: 6, cdec: 8, oracle: '0x663becd10dae6c4a3dcd89f1d76c1174199639b9', lltv: '860000000000000000', irm: '0x46415998764c29ab2a25cbea6254146d50d22687', pool: null },
];
const MAX_MARKETS = 8;

const HF_WARN = 1.05;
const CYCLE_MS = 20000;
const REFRESH_MS = 5 * 60 * 1000;
const CHUNK = 250;            // inner calls per multicall eth_call
const CAND_CAP = 300;         // per market, most recent kept (deep backfill needs headroom)
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
const MIN_PROFIT_USD = 2;     // live-mode guard: expected profit at oracle price
const MAX_GAS_PRICE_WEI = 200000000n; // 0.2 gwei cap for live send
const MAX_GAS_LIMIT = 1500000n;       // executor path (flash+liquidate+swap): fork-measured 531173 success / 569255 NO_PROFIT revert (2026-11-04 v2 artifact)

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
const SEL_POOL_SWAP = '0x128acb08';      // PancakeV3 pool.swap(address,bool,int256,uint160,bytes) — NOTE: PancakeV3 treats amountSpecified > 0 as exact INPUT (opposite of UniV3)
const MAX_SQRT_RATIO_M1 = '0xfffd8963efd1fc6a506488495d951d5263988d25';
const CAPITAL_REPAID_CAP = 398n * 1000000n; // seized such that repaid <= ~398 USDC (capital_usd 400)
const MIN_PROFIT_WEI = 1000000n;            // executor minProfit argument = 1 USDC
// Fail-closed runtime validation: the paper sim must exercise the REAL
// constructor-patched runtime (review 6950ca00 blocker: zero immutable slots
// made the sim run an empty-account call). All five MORPHO immutable slots
// must be non-zero, else sims are disabled (watch-only) instead of falling
// back to a fake runtime.
const IMMUTABLE_OFFSETS = [499, 1034, 1272, 1530, 3125]; // byte offsets of MORPHO in the v3 constructor-patched runtime
let RUNTIME_CODE = '';
let RUNTIME_OK = false;
try {
  RUNTIME_CODE = fs.readFileSync(RUNTIME_FILE, 'utf8').trim();
  RUNTIME_OK = IMMUTABLE_OFFSETS.every(o => RUNTIME_CODE.slice(2 + 2 * o, 2 + 2 * o + 40).toLowerCase() === MORPHO.slice(2).toLowerCase());
} catch (e) { /* sims disabled below */ }

// Native (gas) valuation, fresh every cycle from the Aave price oracle on
// base (measured 2026-11-03 by aave-watcher-base, run 79db4b40): live sends
// fail closed when it is stale. Used only for the conservative USD gas bound,
// never for profit sizing (profit is sized in loan-asset wei at oracle price).
const AAVE_ORACLE = '0x2cc0fc26ed4563a5ce5e8bdcfe1a2878676ae156';
const WETH = '0x4200000000000000000000000000000000000006';
const SEL_GET_ASSET_PRICE = '0xb3596f07'; // getAssetPrice(address) -> uint256, 8-dec USD
let ETH_USD = 0, ETH_USD_AT = 0;
const ETH_USD_STALE_MS = 15 * 60 * 1000;
// All-fee loss model for ONE live transaction (review 99cc9216 blocker 1: the
// fee bound is transaction/chain-enforced only in part; the wallet-balance leg
// is a funding POLICY the bot asks for, never a proven chain invariant — an EOA
// can receive ETH between the bot's balance read and inclusion, so the bot's
// latest-balance check is a validity check and a policy cap, not a bound).
// OP Stack charges a sequenced transaction three fee kinds (exec-engine spec
// "Fees" + isthmus/exec-engine.html "Operator Fee"):
//  (a) L2 execution fee (base + priority) — ENFORCED by the SIGNED transaction
//      fields: at most maxFeePerGas x gasLimit = MAX_GAS_PRICE_WEI x MAX_GAS_LIMIT.
//  (b) Operator fee (Isthmus) — operatorFeeScalar/1e6 x gasUsed +
//      operatorFeeConstant, charged pre-execution. ENFORCED cap: the fee
//      formula at gasUsed <= gasLimit; the parameters are read IN-PATH at every
//      live preflight from the L1 Block Info predeploy getters, and they move
//      only at L2 epoch changes (not between preflight and inclusion).
//  (c) L1 data fee — chain-computed over the FULL encoded signed transaction
//      bytes (known: the bot encodes them itself) against the L1 basefee/
//      blobBaseFee of the including block's L1 origin ("zeroes*4 + ones*16"
//      byte-weighting). No transaction field caps it: it drifts with L1 base-fee
//      blocks (EIP-1559: <= 12.5% per L1 block) between the bot's preflight
//      read and inclusion — pending/reorged inclusion can cross L1 origins and
//      L2 epochs, so the in-path preflight read does not freeze the inclusion-time
//      parameters (review 54ffa8cc blocker 1: no expiry/validity horizon). The bot
//      reads getL1Fee over the final type-2 bytes in-path and bounds the send by
//      FEE_BOUND_MARGIN (3x) on that ESTIMATE: the worst case it will not send is
//      totalWei x FEE_BOUND_MARGIN. No transaction field caps (c), so until a
//      genuine enforced all-fee cap exists, LIVE_FEE_CAP_ENFORCED=false keeps
//      live sends disabled (the reviewer's accepted alternative).
// The bot fails closed unless BOTH hold:
//  (i)  (a)+(b)+estimated(c) <= LIVE_FEE_ALLOWANCE_WEI — economic skip, where
//       estimated(c) = getL1Fee over the COMPLETE canonical type-2 transaction
//       bytes (signature r/s = maximum-entropy filler; an estimate, not a
//       claimed compressed maximum);
//  (ii) estimated (a)+(b)+(c) x FEE_BOUND_MARGIN <= 20 USD at the fresh
//       Aave-oracle WETH price (worstCaseGasLossUsd x margin), AND the wallet's
//       balance read <= LIVE_BALANCE_CAP_USD (funding policy: the gate is asked
//       to fund the gas float at most 18 USD; incoming ETH only affects
//       validity, and the chain still charges only (a)+(b)+(c) at inclusion).
const GAS_PRICE_ORACLE = '0x420000000000000000000000000000000000000f'; // OP Stack GasPriceOracle predeploy (base)
const L1BLOCK_INFO = '0x4200000000000000000000000000000000000015';     // L1 Block Info predeploy (base)
const SEL_L1FEE = '0x49948e0e';      // getL1Fee(bytes) — full encoded signed tx (the old l1Fee(bytes) 0x3fd1263d no longer exists on the Isthmus GasPriceOracle: relay eth_call reverts; measured 2026-11-04 run 807117915)
const SEL_OP_SCALAR = '0x4d5d9a2a';  // L1BlockInfo.operatorFeeScalar() (Isthmus)
const SEL_OP_CONSTANT = '0x16d3bc7f';// L1BlockInfo.operatorFeeConstant() (Isthmus)
const LIVE_FEE_ALLOWANCE_WEI = 2000000000000000n; // 0.002 ETH estimate allowance per live tx
const LIVE_BALANCE_CAP_USD = 18;     // funding policy + validity check (NOT a chain invariant): skip when the gas float exceeds 18 USD (review 99cc9216 blocker 1)
const LIVE_FEE_CAP_ENFORCED = false; // review 54ffa8cc blocker 1 (accepted alternative): NO transaction field caps the L1 data fee (c) at inclusion, no validity horizon binds the fee inputs read at preflight (pending inclusion can cross L1 origins and L2 epochs), and the 3x preflight margin is an estimate. Live sends stay DISABLED until a genuine enforced cap for every applicable fee exists; flip to true only with that cap.
const FEE_BOUND_MARGIN = 3;          // worst-case multiplier over the measured preflight (a)+(b)+(c) total: (c) drifts <= 12.5%/L1-block (EIP-1559 base fee) between preflight and inclusion, (b) params only at L2 epochs; the bot will not send unless measured total x margin <= 20 USD
function encBytesArg(data) {      // abi.encode(bytes) tail: offset 0x20, length, data padded to 32
  const len = (data.length - 2) / 2;
  return '00'.repeat(31) + '20' + BigInt(len).toString(16).padStart(64, '0') +
    data.slice(2) + '0'.repeat((32 - (len % 32)) % 32 * 2);
}
// Minimal RLP for the canonical EIP-1559 (type-2) transaction passed to getL1Fee:
// 0x02 || RLP([chainId, nonce, maxPriorityFee, maxFee, gasLimit, to, value,
//              data, accessList, yParity, r, s]) — EIP-1559 field order.
function rlpBytes(b) { // b: hex WITHOUT 0x prefix
  const len = b.length / 2;
  if (len === 1 && parseInt(b, 16) < 0x80) return b;
  let l;
  if (len < 56) return (0x80 + len).toString(16).padStart(2, '0') + b;
  l = len.toString(16); if (l.length % 2) l = '0' + l;
  return (0xb7 + l.length / 2).toString(16) + l + b; // long string prefix 0xb7 + lengthBytes (0xb8..0xbf) — review 99cc9216: the old 0xf7 + base produced non-integer bytes like 'f8.5' for len>=112
}
function rlpUint(n) {
  n = BigInt(n); // review 2d13ac44 blocker 2: normalize Number callers (the paper caller passed Number 0, so `n === 0n` was false and nonce 0 encoded as byte 00, not the canonical empty integer 80)
  if (n === 0n) return '80';
  let h = n.toString(16); if (h.length % 2) h = '0' + h;
  return rlpBytes(h);
}
function rlpList(items) {
  const len = items.length / 2;
  if (len < 56) return (0xc0 + len).toString(16).padStart(2, '0') + items;
  let l = len.toString(16); if (l.length % 2) l = '0' + l;
  return (0xf7 + l.length / 2).toString(16) + l + items; // canonical long-list prefix 0xf7 + lengthBytes (0xf8..0xff) — review 54ffa8cc blocker 2: the previous revision emitted 0xdf + lengthBytes (e.g. 0xe1 for a 713-byte payload), which a canonical decoder reads as a SHORT list declaring 33 bytes with 713 following
}
function encTxBytes(calldata, nonce) {
  const crypto = require('crypto');
  const sig = crypto.randomBytes(64).toString('hex'); // a real 65-byte signature is incompressible: maximum-entropy filler for r,s
  // EIP-1559 payload field order is EXACTLY [chainId, nonce, maxPriorityFeePerGas,
  // maxFeePerGas, gasLimit, to, value, data, accessList, yParity, r, s] — the fee
  // fields precede gasLimit, and data precedes accessList
  // (review 99cc9216 blocker 2: the previous revision placed gasLimit first, so
  // independent RLP decode read priority=1500000, maxFee=20000000, gasLimit=200000000
  // instead of the intended 20000000 / 200000000 / 1500000).
  const items = rlpUint(8453n) + rlpUint(nonce) +
    rlpUint(MAX_GAS_PRICE_WEI / 10n) + rlpUint(MAX_GAS_PRICE_WEI) + rlpUint(MAX_GAS_LIMIT) +
    rlpBytes(EXEC.slice(2).toLowerCase()) + rlpUint(0n) + rlpBytes(calldata.slice(2)) + 'c0' +
    rlpBytes('01') + rlpBytes(sig.slice(0, 64)) + rlpBytes(sig.slice(64, 128));
  return '0x02' + rlpList(items);
}
async function feeBound(calldataMax, nonce) {
  try {
    const [l1r, scr, cor] = await Promise.all([
      rpc('eth_call', [{ to: GAS_PRICE_ORACLE, data: '0x' + SEL_L1FEE.slice(2) + encBytesArg(encTxBytes(calldataMax, nonce)) }, 'latest']),
      rpc('eth_call', [{ to: L1BLOCK_INFO, data: SEL_OP_SCALAR }, 'latest']),
      rpc('eth_call', [{ to: L1BLOCK_INFO, data: SEL_OP_CONSTANT }, 'latest']),
    ]);
    const opScalar = BigInt(scr), opConstant = BigInt(cor);
    const opWei = opScalar * MAX_GAS_LIMIT / 1000000n + opConstant; // Isthmus fee formula at gas = gasLimit (worst case)
    const l1Wei = BigInt(l1r);   // estimate over the complete signed-tx bytes — NO multiplier
    const l2Wei = MAX_GAS_LIMIT * MAX_GAS_PRICE_WEI; // signed cap
    return { ok: l1Wei + l2Wei + opWei <= LIVE_FEE_ALLOWANCE_WEI,
      l1Wei: l1Wei.toString(), l2Wei: l2Wei.toString(), opWei: opWei.toString(),
      opScalar: opScalar.toString(), opConstant: opConstant.toString(),
      totalWei: (l1Wei + l2Wei + opWei).toString(), allowanceWei: LIVE_FEE_ALLOWANCE_WEI.toString() };
  } catch (e) { return { ok: false, error: String(e).slice(0, 140) }; }
}
function worstCaseGasLossUsd(feeBound) {
  if (!ETH_USD || !feeBound || !feeBound.ok) return null;
  return Number(BigInt(feeBound.totalWei)) / 1e18 * ETH_USD;
}

const LOGS = path.join(DIR, 'logs');
const STATE = path.join(DIR, 'state');
fs.mkdirSync(LOGS, { recursive: true });
fs.mkdirSync(STATE, { recursive: true });
const LOG = path.join(LOGS, 'bot.jsonl');
const STATE_FILE = path.join(STATE, 'state.json');

function log(obj) { fs.appendFileSync(LOG, JSON.stringify(obj) + '\n'); }
const addr = (a) => a.toLowerCase().replace(/^0x/, '').padStart(64, '0');
const hex = (x) => '0x' + BigInt(x).toString(16);

let rpcId = 0;
async function rpc(method, params, retry = 0) {
  const res = await fetch(`${RELAY}/${CHAIN}?lane=${LANE}`, {
    method: 'POST', headers: { 'content-type': 'application/json' },
    body: JSON.stringify({ jsonrpc: '2.0', id: ++rpcId, method, params }),
  });
  const j = await res.json();
  if (j.error) {
    if (retry < 3) { await new Promise(r => setTimeout(r, 2500 * (retry + 1))); return rpc(method, params, retry + 1); }
    throw new Error(`${method}: ${JSON.stringify(j.error).slice(0, 200)}`);
  }
  return j.result;
}

// Multicall3 tryAggregate, encoding measured against the farm relay (aave-watcher-base design)
async function tryAggregate(calls) {
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
  const r = await rpc('eth_call', [{ to: MULTICALL, data: enc }, 'latest']);
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
// sells ALL of it on the pool (PancakeV3 pool.swap, recipient = executor,
// amountSpecified = +seized = exact input of collateral — PancakeV3 treats a
// positive amountSpecified as exact input, opposite of UniV3; verified against
// the dominant liquidator's trace of tx 0x2d56cc60), lets Morpho pull the flash
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

// PancakeV3 pool.swap(recipient=executor, zeroForOne=false, amountSpecified=+seized,
// sqrtPriceLimit=MAX-1, data=abi.encode(token0, token1)) — sells the seized collateral
// into the pool; the pool pays the executor the loan asset and calls the executor's
// V3 swap callback, which pays the pool the collateral (auth'd to the armed pool).
function encPoolSwap(execAddr, collateralAmount, loan, coll) {
  const [t0, t1] = [loan.toLowerCase(), coll.toLowerCase()].sort();
  return SEL_POOL_SWAP + addr(execAddr) + '0'.repeat(64) +
    BigInt(collateralAmount).toString(16).padStart(64, '0') +
    MAX_SQRT_RATIO_M1.slice(2).padStart(64, '0') +
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
  const collValue = collateral * price / 10n ** 36n;   // mulDivDown, loan-asset wei
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
  const quoted = (seized * price + (10n ** 36n - 1n)) / 10n ** 36n;       // mulDivUp(seized, price, ORACLE_PRICE_SCALE)
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
  const proceeds = seized * price / 10n ** 36n; // conservative (floor) sale value at oracle
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
      const m = { id: mid, loan, coll, oracle, irm, lltv: '0x' + h.slice(256, 320), ldec: pm ? pm.ldec : null, cdec: pm ? pm.cdec : null, pool: pm ? pm.pool : null };
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
  // trim candidate sets, keep most recent
  for (const [mid, cmap] of state.candidates) {
    if (cmap.size > CAND_CAP) {
      const keep = [...cmap.entries()].sort((a, b) => b[1] - a[1]).slice(0, CAND_CAP);
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
    };
    fs.writeFileSync(STATE_FILE, JSON.stringify(o));
  } catch (e) { /* state persistence is best-effort */ }
}
function loadState() {
  try {
    const o = JSON.parse(fs.readFileSync(STATE_FILE, 'utf8'));
    const state = {
      markets: o.markets,
      candidates: new Map(o.candidates.map(([k, v]) => [k, new Map(v)])),
      cursor: o.cursor || null,
      deepCursor: 'deepCursor' in o ? o.deepCursor : undefined,
      deepDone: o.deepDone === true,
      liqCounts: new Map(o.liqCounts || []),
      underwaterSince: new Map(o.underwaterSince || []),
    };
    if (state.markets && state.markets.length && [...state.candidates.values()].every(c => c instanceof Map)) {
      // pinned fields (swap pool, irm) may be newer than the saved state
      for (const pm of MARKETS) {
        const sm = state.markets.find(x => x.id === pm.id);
        if (sm) { sm.pool = sm.pool || pm.pool; sm.irm = sm.irm || pm.irm; sm.lltv = sm.lltv || pm.lltv; }
      }
      return state;
    }
  } catch (e) { /* fall through to fresh */ }
  return { markets: MARKETS.map(m => ({ ...m })), candidates: new Map(MARKETS.map(m => [m.id, new Map()])), cursor: null, deepCursor: undefined, deepDone: false, liqCounts: new Map(), underwaterSince: new Map() };
}

async function simulateLiquidation(m, user, seized, repaid, proceeds, collValue, sizingBranch) {
  if (!m.pool) {
    log({ ts: new Date().toISOString(), type: 'opportunity_watch_only', market: m.id, borrower: user, reason: 'no measured collateral swap pool for this market' });
    return;
  }
  if (!RUNTIME_OK) {
    log({ ts: new Date().toISOString(), type: 'opportunity_watch_only', market: m.id, borrower: user, reason: 'executor runtime missing or immutable slots unpatched (fail closed)' });
    return;
  }
  // Flash enough to cover the repaid debt (rational +0.5% headroom, CEIL
  // division, rounded up to loan units, plus a 2-unit dust buffer); the
  // excess is repaid out of the sale. If the sale proceeds fall short of
  // repaid + flash pull-back, the tx reverts: gas only.
  const loanUnit = 10n ** BigInt(m.ldec);
  const flashAmount = ((repaid * 1005n + 999n) / 1000n / loanUnit + 1n) * loanUnit + 2n * loanUnit;
  const swapData = encPoolSwap(EXEC, seized, m.loan, m.coll);
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
    const code = await rpc('eth_getCode', [EXEC, 'latest']).catch(() => null);
    if (!code || code === '0x') { skip('executor has no deployed code (gate has not deployed)'); return; }
    let owner;
    try { owner = '0x' + (await rpc('eth_call', [{ to: EXEC, data: SEL_EXEC_OWNER }, 'latest'])).slice(-40); } catch (e) { skip('owner() read failed'); return; }
    if (owner.toLowerCase() !== me.toLowerCase()) { skip(`executor owner ${owner} != our wallet ${me}`); return; }
    try { nonce = BigInt(await rpc('eth_getTransactionCount', [me, 'latest'])); } catch (e) { skip('nonce read failed'); return; }
    simFrom = me; // no code override: simulate the deployed executor from our wallet
  }
  let fbound = await feeBound(calldataMax, nonce); // estimate at the nonce the live send uses
  if (BOT_MODE === 'live' && !fbound.ok) { skip('all-fee estimate unavailable or over 0.002 ETH allowance: ' + JSON.stringify(fbound)); return; }
  const gasUsd = worstCaseGasLossUsd(fbound); // null => fail closed for live sends
  // On-chain minProfit = POST-FEE profit floor in loan-asset wei (review
  // c7693f9e blocker 3): the executor reverts unless realized sale proceeds
  // exceed the repaid debt by MIN_PROFIT_USD + the all-fee gas bound, instead
  // of a fixed 1 USDC that ignored fees. Recomputed whenever the fee bound is.
  let minProfitOn = MIN_PROFIT_WEI; // paper fallback
  if (gasUsd !== null) {
    minProfitOn = (BigInt(Math.ceil((MIN_PROFIT_USD + gasUsd) * 1e6)) * loanUnit + 999999n) / 1000000n;
  }
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
  if (BOT_MODE !== 'live') callParams.push({ [EXEC]: { code: RUNTIME_CODE } });
  const sim = await rpc('eth_call', callParams)
    .then(() => ({ ok: true }))
    .catch(e => ({ ok: false, revert: String(e).slice(0, 200) }));
  // Selected-proceeds profit at oracle price, minus the all-fee USD bound
  // (fresh native valuation) for the live decision.
  const profitWei = profitEstimate(m, proceeds, repaid);
  const profitUsd = Number(profitWei / loanUnit);
  const needUsd = MIN_PROFIT_USD + (gasUsd || Infinity);
  log({
    ts: new Date().toISOString(), type: 'simulate', market: m.id, borrower: user,
    seize_amount: seized.toString(), repaid_est: repaid.toString(), proceeds_est: proceeds.toString(),
    flash_amount: flashAmount.toString(),
    debt_usd: Number(repaid / loanUnit), coll_value_usd: Number(collValue / loanUnit),
    profit_usd_oracle: profitUsd, gas_bound_usd: gasUsd, min_profit_usd: needUsd,
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
  if (BOT_MODE === 'live' && sim.ok && gasUsd !== null && profitUsd >= needUsd) {
    try {
      const skip = (reason) => log({ ts: new Date().toISOString(), type: 'live_skip', borrower: user, reason });
      if (!LIVE_FEE_CAP_ENFORCED) { skip('live sends disabled: no enforced inclusion-time all-fee cap (review 54ffa8cc blocker 1 accepted alternative)'); return; }
      if (gasUsd * FEE_BOUND_MARGIN > 20) { skip(`measured all-fee bound x margin ${(gasUsd * FEE_BOUND_MARGIN).toFixed(2)} USD > 20`); return; } // review 99cc9216 blocker 1: the bot refuses to send when its in-path measured fee total, times the (c)-drift margin, exceeds L
      if (!me) { skip('no signer address'); return; }
      const sock = process.env.SIGNER_SOCK;
      if (!sock) { skip('no SIGNER_SOCK'); return; }
      const net = require('net');
      const req = JSON.stringify({ op: 'send', chain: CHAIN, to: EXEC, data: calldata, value: '0x0',
        gas: '0x' + MAX_GAS_LIMIT.toString(16), maxFeePerGas: '0x' + MAX_GAS_PRICE_WEI.toString(16),
        maxPriorityFeePerGas: '0x' + (MAX_GAS_PRICE_WEI / 10n).toString(16) });
      const res = await new Promise((resolve) => {
        const c = net.connect(sock, () => c.write(req + '\n'));
        let buf = '';
        c.on('data', (d) => { buf += d; try { resolve(JSON.parse(buf)); } catch (e) { /* wait */ } });
        c.on('error', () => resolve({ error: 'sock_error' }));
        setTimeout(() => resolve({ error: 'timeout' }), 10000);
      });
      log({ ts: new Date().toISOString(), type: 'live_send', borrower: user, to: EXEC, gas_bound_usd: gasUsd, profit_usd_oracle: profitUsd, result: res });
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
async function scanCycle(state) {
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
    calls.push({ to: AAVE_ORACLE, data: SEL_GET_ASSET_PRICE + '0'.repeat(24) + WETH.slice(2) }); // fresh native valuation for the gas bound
    let i = 0;
    for (const u of state.candidates.get(m.id)?.keys() || []) {
      if (i++ >= CAND_CAP) break;
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
    const wr = res[base + 4]; // fresh native (gas) valuation, once per market slot
    if (wr && wr.success && wr.returnData.length >= 66) {
      const p = BigInt('0x' + wr.returnData.slice(2, 66));
      if (p > 0n) { ETH_USD = Number(p) / 1e8; ETH_USD_AT = Date.now(); }
    }
    mstate.set(m.id, { totBorAssets, totBorShares, price });
  }
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
    await simulateLiquidation(m, u, sizing.seized, sizing.repaid, sizing.proceeds, econ.collValue, sizing.branch);
  }
  log({ ts: now, type: 'heartbeat', scanned, debtors, markets: state.markets.length, min_hf: minHfRow ? minHfRow.hf : null, min_hf_row: minHfRow, underwater_now: underwater.length, eth_usd: ETH_USD, eth_usd_age_ms: ETH_USD_AT ? Date.now() - ETH_USD_AT : null, executor: EXEC, runtime_ok: RUNTIME_OK });
}

async function main() {
  log({ ts: new Date().toISOString(), type: 'start', mode: BOT_MODE, relay: RELAY, lane: LANE, morpho: MORPHO, markets_pinned: MARKETS.length, executor: EXEC, executor_owner_sim_from: EXEC_OWNER, runtime_ok: RUNTIME_OK, runtime_len: RUNTIME_CODE.length / 2 });
  const state = loadState();
  state.underwaterSince = state.underwaterSince || new Map();
  // Heartbeats start immediately and never depend on refresh success.
  setInterval(async () => {
    try {
      await scanCycle(state);
    } catch (e) {
      log({ ts: new Date().toISOString(), type: 'error', msg: String(e).slice(0, 300), stack: String(e.stack).split('\n').slice(0, 4).join(' | ') });
    }
  }, CYCLE_MS);
  // Refresh loop with retry + backoff: an RPC error must never kill the
  // process (the startup crash cause). On failure it retries until it
  // succeeds; the cursor only advances on a fully successful scan.
  let backoff = 5000;
  for (;;) {
    let wait = REFRESH_MS;
    try {
      await refreshCandidates(state);
      saveState(state);
      backoff = 5000;
    } catch (e) {
      log({ ts: new Date().toISOString(), type: 'refresh_error', msg: String(e).slice(0, 300), retry_in_ms: backoff });
      backoff = Math.min(backoff * 2, 60000);
      wait = backoff;
    }
    await new Promise(r => setTimeout(r, wait));
  }
}
// Reusable by fork-evidence harnesses (scratch/morpho-fix-511fc3e7/): the exact
// sizing/fee-bound code paths reviewed here run unmodified against the fork.
module.exports = { MARKETS, marketEconomics, incentiveFactor, repaidChain, seizeFor,
  encExecutorCall, encPoolSwap, encTxBytes, feeBound, worstCaseGasLossUsd,
  pickEvictVictim, pinnedMeta,
  refreshCandidates, scanCycle, loadState, saveState, getLogsPaged, tryAggregate,
  rpc, RUNTIME_OK, RUNTIME_CODE, EXEC, EXEC_OWNER, CAPITAL_REPAID_CAP, MIN_PROFIT_WEI,
  MAX_GAS_PRICE_WEI, MAX_GAS_LIMIT, FEE_BOUND_MARGIN };
if (require.main === module) main();
