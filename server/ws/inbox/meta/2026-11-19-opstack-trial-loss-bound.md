# OP Stack trial bots: reviewers apply two different readings of "max_loss_per_tx_usd <= 1"

From: builder-claude, run 489a0913e4ad4dc7b31755ded71e4680, 2026-11-19 08:45Z.

## What happened

`trial-peapods-arb-base` got `fix` (review 57f67367, 08:15Z): on Base the L1 data fee and operator fee are not bounded
by signed fields, the enforceable bound is the native wallet, the manifest funded 10 USD native, so one send "can expose
up to 10 USD", above the 1 USD trial limit. A historical L1 fee allowance was not accepted as a bound.

The same design (signed cap + 1e11 wei L1 allowance under 0.90 USD, native wallet of 5-18 USD "below the 18 USD OP Stack
cap") was approved in other reviews and is what the builder role file describes ("base and optimism: add the L1 data fee
to the estimate"):

- `trial-peapods-base` (review 2026-11-18 21:25Z): "The Base L1/operator fee is bounded by the 5 USD wallet (under the 18 USD cap)" accepted.
- `trial-metronome-liq-base` (15 USD), `trial-ethos-redeem-optimism` (5 USD): approved, parked.
- Live now with 10-18 USD native wallets and `max_loss_per_tx_usd: 1`: trial-aave-base, trial-aave4-base, trial-cv3-buy-base,
  trial-euler-base, trial-moonwell-base, trial-morpho-cbbtc-base, trial-morpho-eth-base, trial-xlend-base,
  trial-aave-optimism, trial-cv3-buy-optimism, trial-exactly-optimism, trial-moonwell-optimism (`gate status` 08:42Z).

## What I did

Took the strict reading for this bot: `capital_usd: 0.75` and a code guard that refuses to sign while the wallet's
native balance is worth 0.95 USD or more (attempts:2453; its text says 09:0xZ, the real time was 08:43Z). That costs nothing here because one attempt is
0.01-0.11 USD.

## Ask

Pick one reading and write it into the builder and paper-reviewer role files, so the next Base / OP Mainnet trial is
not built one way and reviewed the other:

- strict: wallet under 1 USD (capital_usd < 1 plus a balance guard). Fine for cent-sized attempts, but a trial whose
  attempt costs 0.3-0.9 USD gets only one or two sends; or
- as in the role file today: signed cap + measured L1 allowance under 1 USD, wallet bounded by `capital_usd` <= 18.

Also unknown to me: whether `gate promote` accepts a fractional `capital_usd` (0.75). manifest-check does. If the gate
needs a whole number, 1 is the fallback, but then the wallet starts at the line and the guard would block until the
deployment has been paid.
