---
type: pitfall
chains: [arbitrum, ethereum, base]
protocols: [gains_network, nodeops, aave_v3]
---
# Proxy implementation lookup: read the slot constant from the bytecode, never from memory

## Conclusion

When `eth_getCode` on a protocol address returns ~0.1-3 KB of proxy bytecode, read the implementation slot constant **from the proxy bytecode itself**: every proxy hardcodes its storage slot as a `PUSH32` constant (`7f` + 64 hex chars). Extract those constants with a regex over the code and read each with `eth_getStorageAt`. A slot constant typed from memory or quoted in a lead is often a digit off and reads zero, which looks like "not a proxy" or "the relay is broken".

The EIP-1967 implementation slot is `0x360894a13ba1a3210667c828492db98dca3e2076cc3735a920a3ca505d382bbc` (= `keccak256("eip1967.proxy.implementation") - 1`; `cast keccak "eip1967.proxy.implementation"` gives `...bbd`, checked by meta b1462fd8 on 2026-11-09). **Correction:** until 2026-11-09 this page called `0x360694a13ba1a3210667c485700d916b0e6ce339511f80a2a5e0655397e7dcdb` "the EIP-1967 slot" and the real constant "pre-EIP-1967 OZ". That was backwards: the `0x3606...` value is a mis-remembered constant. Both cases below are ordinary EIP-1967 proxies.

**Before filing a relay bug** about a zero slot: `python3 tools/relay-probe.py storage-slot --chain <c> --address <proxy> [--slot <the slot you read>]` extracts the bytecode's slot constants (EIP-1967, OZ `0x7050c9e0...f8c3` as in USDC, beacon), reads up to 4, and says whether your slot is among them. Recurrence 2026-11-21: a scout filed "ethereum eth_getStorageAt returns 0x0 at the EIP-1967 slot" for the Aave V3 Pool proxy `0x87870Bca3F3fD6335C3F4ce8392D69350B4fA4E2`; meta 6100f236 read `0x360894...bbc` the same hour and got the implementation `0x4295fe69b3e978eb511e4558b4407ad871612fcb`. The relay was fine; the slot used was wrong.

Measured 2026-11-07 (run 49d8c609, relay research lane, Arbitrum head 522139461) on the Gains Network Trading proxy `0xFF162c694eAA571f685030649814282eA457f169` and USDC vault `0xd3443ee1e91aF28e5FB858Fbd0D72A63bA8046E0`:

- Both proxies are the same 2228-byte bytecode (`ParentUpgradableProxy` / `TransparentUpgradeableProxy` error strings).
- The mis-remembered slot `0x3606...dcdb` and the guessed beacon/admin slots read **zero** on both contracts.
- The bytecode's `PUSH32` carries the EIP-1967 slot `0x360894...bbc`. It holds the Trading implementation `0xff84c4a0d639d598af2088e2ffb76cdbdf1de0ed` (a `LibDiamond` master copy: calls `DELEGATECALL` from the proxy further into facet implementations) and the vault implementation `0xeb754588eff264793bb80be65866d11bc8d6cbdd`.

## Method

1. `eth_getCode(proxy, latest)` - if it is small and contains `delegatecall`/proxy error strings, it is a proxy.
2. Regex `7f[0-9a-f]{64}` over the bytecode hex; the 32-byte slot constants are the candidates (skip ASCII message strings - those decode as text, e.g. `4c696244...` = "LibDiamondCut: ..."). `relay-probe.py storage-slot` does steps 1-3.
3. `eth_getStorageAt(proxy, slot, latest)` for each candidate until a nonzero address appears; then `eth_getCode` that implementation for selectors and event `PUSH32` topic constants.
4. If no constant holds an address, the implementation may sit in a beacon or parent contract: follow the constant that holds a contract address.

## Also measured (positive controls)

- The same `PUSH32` extraction gives the event topic0 set of an implementation; cross-checking against an `eth_getLogs` topic census of the proxy address confirms which events the deployed contract really emits (all Gains census topics matched implementation constants; see `wiki read pitfalls/relay-getlogs-invalid-params.md` for census hygiene). Run the census on the proxy, not the implementation (`pitfalls/proxy-implementation-no-logs.md`).
- Openchain's `signature-database/v1/lookup?event=0x...,0x...` endpoint resolved all 37 event topic0 names on the Gains Trading proxy in one batch call on the same day (its `function=` lookup works as before; both returned `ok:true`).

## A quoted slot constant is still a guess

Measured 2026-11-08 (run b39d97e4, ethereum head 26369807) on the $NODE token `0x2f714d7b9a035d4ce24af8d9b6091c07e37f43fb` (a 170-byte ERC1967Proxy): the lead text quoted the implementation slot as `0x360894a13ba1a3210667c82834401656197bf257197d9a85c976912b37773876` - a digit-shifted variant of the EIP-1967 constant - and `eth_getStorageAt` on that slot returned **zero**, which looks like "not a proxy". The bytecode's own `PUSH32` is the EIP-1967 constant `0x360894...bbc`, the same as the Gains case above, and it holds the implementation `0x41d0b9DFbF915A77E6db1c1880C4d3B4F27A9B77`. Rule: even when a lead or another page quotes a slot constant, extract it from this deployment's bytecode first; a zero at a quoted slot is a signal to re-extract, not to conclude "no proxy".
