// test.js — lusd-redemption-ethereum opportunity-branch calculation (review 0c72857e item 1).
// The branch used GAS_CAP_ETH and PROOF_GROSS_USDT_PER_3000 before they were defined and
// threw ReferenceError at premium >= 1.0814. economics() is the same calculation the main
// loop runs; these cases come from the fork measurement (README windows table, proof12/13):
//   proof premium 1.11651: gross 84.9 USDT pre-gas at 3,000 LUSD (tx 0xe9881aba...);
//   revert band 1.26264/1.2986/1.4588: 'TroveManager: Unable to redeem any amount';
//   signing cap: 1,300,000 x 20 gwei = 0.026 ETH at the signing-time oracle price,
//   refused above 50 USD (Oct19 price 2,388.50 -> 62.1 USD, refused).
const assert = require('assert');
const { economics } = require('./bot.js');

const LUSD = 3000n * 10n ** 18n;
const near = (a, b, eps, m) => assert(Math.abs(a - b) < eps, m + ` (got ${a})`);

// 1. proof-region premium at a submit-eligible oracle price: the send case
let e = economics({ premium: 1.11651, oracleUsdPerEth: 1901.49 }, LUSD);
near(e.gasCapUsd, 0.026 * 1901.49, 0.01, 'gas cap = 0.026 ETH at signing price');
near(e.expectedGrossUSDT, 84.9, 0.01, 'fork-measured gross per 3,000 LUSD');
near(e.expectedNetUSDT, 84.9 - 49.44, 0.02, 'net = gross - cap');
assert(e.measuredRegion && !e.revertBand && e.eligible, 'eligible in the measured band');

// 2. below the proof premium: no measured positive gross -> reject (Oct29 crossing rows
//    between 1.0814 and 1.11651 were never measured positive at farm size)
e = economics({ premium: 1.10, oracleUsdPerEth: 1901.49 }, LUSD);
assert(!e.measuredRegion && e.expectedGrossUSDT === 0 && !e.eligible, 'below proof premium rejected');

// 3. measured revert band: 3,000 LUSD reverts 'Unable to redeem any amount'
for (const p of [1.26264, 1.2986, 1.4588]) {
  e = economics({ premium: p, oracleUsdPerEth: 1901.49 }, LUSD);
  assert(e.revertBand && !e.measuredRegion && !e.eligible, `revert band ${p} rejected`);
}

// 4. signing-time price above the L bound: 0.026 x 2388.50 = 62.1 USD > 50 -> refuse
e = economics({ premium: 1.12, oracleUsdPerEth: 2388.50 }, LUSD);
near(e.gasCapUsd, 62.10, 0.01, 'Oct19-price gas cap');
assert(!e.eligible && e.gasCapUsd > 50, 'L-bound refusal at high oracle price');

// 5. partial hint truncation scales the measured gross linearly in the LUSD units
e = economics({ premium: 1.4588, oracleUsdPerEth: 1901.49 }, 2778863152157358539616n);
near(e.expectedGrossUSDT, 84.9 * 2778.863152157358539616 / 3000, 0.01, 'gross scales per LUSD');

console.log('test.js OK:', JSON.stringify(economics({ premium: 1.11651, oracleUsdPerEth: 1901.49 }, LUSD)));
