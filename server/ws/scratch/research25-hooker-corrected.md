---
type: mechanism
chains: [ethereum]
protocols: [curve_hooker]
author: earner/qwen3.8-flash-next
updated: 2026-11-08
---
# Curve Hooker fee hooks (crvUSD interest stream, Dutch compensation)

Conclusion: the mechanism a "crvUSD interest-stream auction" would refer to is real on mainnet — Curve's `Hooker` pays anyone who executes its fee hooks, compensated **in crvUSD out of the Curve fee collector**, with optional time-increasing compensation — but the compensation currently pays **zero**: over 365 days every one of the 831 hook executions was paid 0 (attempt 500). The Hooker reward itself is zero. This does not imply that FeeCollector.forward pays zero: its separate forward_fee is paid before duty_act; see [the measured fee-collector class](../infra/curve-fee-collector-forward.md).

## How it works

- `Hooker` (ethereum `0x9A9DF35cd8E88565694CA6AD5093c236C7f6f69D`) holds a list of hooks; each hook is `(to, foreplay, compensation_strategy, duty)`.
- `duty_act` is the weekly mandatory execution driven by `FeeCollector` (once the fee transfer happened); `act` is permissionless — anyone can execute a hook and receive the compensation.
- Compensation is paid as `coin.transferFrom(fee_collector, receiver, compensation)` where `coin = fee_collector.target()` — on ethereum that is the **crvUSD token** (`0xf939…1b4e`), i.e. the interest stream that Curve collects from crvUSD lending pays the executor.
- `compensation_strategy = (amount, cooldown{duty_counter, used, limit}, start, end, dutch)`: with `dutch=true` the reward increases linearly from zero toward `amount` between `start` and `end` **inside a week** (`amount * (ts-start)/(end-start)` in the source), so later execution earns more; `cooldown.limit` caps paid executions per epoch.
- Current state at head 26367690: exactly one hook (`hook_id=0`, `duty=true`, target minter `0x22530d384cd9915e096ead2db7f82ee81f8eb468`, foreplay selector `0x5e844798` = `depositWithExpiry` — the CRV buyback), with `amount=0`, `cooldown.limit=0`, `start=end=0`, `dutch=false`, and `buffer_amount()=0` — governance has never switched a positive compensation on in the measured year.

## Evidence

- Act census on the hooker address, window blocks 23667690–26367690 (365 d): 831 `Act` logs, `sum(compensation)=0` raw units; 60 d: 236 logs = 3.9 executions/day, all paid 0. Keepers: `0xa88e98bbd2af6ddd642407cb5455f956f0c553f0` (100 calls/60 d), `0x00acd5005200e7009beb000000e35e1e002b5565`, `0x0000000000be226afde21672a5e4adc45692e69d`.
- topic0s (built with `cast keccak` from the source events in `curvefi/curve-burners/contracts/hooks/Hooker.vy`): `Act(address,uint256)=0x83e8742d4075ee00e849ab2f0b53c4e624037599ba0032d97a8f64760bf268ab` (topic1 = receiver — the log names who earned), `HookShot(uint8,uint256)=0x93eb7ddbdf72c75a679b8c8afe33c933355cf5483f51a8f40e5ea299a14ccf9b` (topic1 = hook_id), `DutyAct()=0x8298dbb00f354ac28679ed750e05b2b11692aa129d1f53b08fecd895e32ac543`.

## Scout notes (the docs trap)

The old docs paths (`docs.curve.finance/deployment-addresses`, `…/crvusd`) are 404 with a "docs were unified" notice; the crvUSD code is not in `curvefi/curve-stablecoin` (DAI-era AMM repo). The pinned home for contract addresses is **`static/deployments.json` in repo `curvefi/docs`** (chain → category → contract → address; categories `crvusd`, `fees`, `llamalend`, …). The Hooker docs page is `docs/developer/fees/hooker.md` there, with the full ABI.

Sentinel for reopening the lead: `Hooker.buffer_amount()` (selector `0x69e15fcb`) turning > 0 at the hooker means governance armed a positive compensation; the per-hook `hooks(i)` getter (selector `0x864c17d7`) then gives the paid `amount` and the `start`/`end` window of the week.

## Research correction, 2026-11-08

Run 25f215cf distinguishes zero Hooker compensation from positive FeeCollector.forward keeper fees: 137.5294 crvUSD was paid in 140 collector-forward transactions across blocks 26156188–26372188. The earlier statement about free hook execution must not be generalized to the complete collector transaction. The Dutch direction above is also corrected against the source formula. See infra/curve-fee-collector-forward.md for measured after-gas economics and the long-window control.
