---
type: pitfall
chains: [any]
protocols: [any]
author: meta/opus
updated: 2026-11-15
---
# Executors: no baked-in targets, no setup transactions, no leftover approvals

**Rule (human decision `decisions/human/2026-11-15-executor-no-baked-targets.md`, applies to new bots and bots returned with `fix`; the 3 bots live on 11-15 stay as they are):**

1. **Targets are call arguments.** Market id, borrower, collateral and debt tokens, exit pool and swap route go in the arguments of the execution tx, never in constructor args, storage or constants. Constructor args = the owner (`{bot}`) only. Protocol singletons that are the same for every market (Morpho Blue, a flash-loan provider) may be constants.
2. **No setup transaction.** The executor works with its deployment plus one tx per opportunity. No post-deploy `setPoolAllowed`, `approve`, `register`, config call. Only if truly unavoidable: send all of them at live startup, log `executor armed`, one README line saying why (`pitfalls/executor-setup-at-startup.md`). A reviewer answers `fix` when a setup tx could have been a call argument.
3. **Callbacks without a stored allow-list.** The owner-only entry records "this tx's counterparty" (pool / flash lender) in a transient slot (or storage cleared before return); each callback checks `msg.sender` against it; a callback reached outside the entry reverts.
4. **Approvals and balances.** Approve only the amount used, inside the tx, and reset to 0 at the end; never unlimited or standing approvals. Nothing (tokens or native) stays in the executor after the tx. The reviewer checks, after the fork success tx, that the executor's balances and the approvals it gave are 0.
5. **One-shot bots** (`oneshot-*`) send their first execution right after live start, not at the next poll.
6. **Unchanged:** Solidity only (no Yul / Huff / hand bytecode executors: the reviewer must read the profit guard and owner-only withdrawal). Never publish executor source (explorer verify, public repos). Deploy-and-execute in one creation tx needs signer/gate work by the human; the signer refuses a creation tx from a bot until then. Entry owner-only, revert unless profit, profit returned to the bot wallet in the same tx as native or USDC.

## Why

The gate deploys the executor at promotion, long before it acts. Constructor args, storage and setup txs are public: anyone can read which market and exit pool the farm watches, exactly as the farm reads rivals in crash-postmortem 2-1 (`methods/executor-techniques.md`). For a contested liquidation it barely matters; for a one-shot left-over or an opportunity nobody else watches it announces the target. Standing approvals and stored settings are also attack surface.

The trigger: morpho-nextblock-ethereum (live) has 7 constructor args (Morpho + 4 collateral tokens + pools) and spent its first send on `setPoolAllowed` (`pitfalls/executor-setup-at-startup.md`). Rivals already do it the new way: ed989's direct entry carries borrower, market and route in calldata (`infra/bot-census/op-ed989ee2.md`).

## Shape

```solidity
address immutable owner; // = msg.sender, or the {bot} constructor arg
IMorpho constant MORPHO = IMorpho(0x...); // singleton: allowed
address transient expectedCaller;          // or a storage slot zeroed before return

function take(MarketParams calldata mp, address borrower, uint256 seize,
              address exitPool, bytes calldata route, uint256 minProfit) external {
    require(msg.sender == owner);
    uint256 before = IERC20(USDC).balanceOf(owner);
    expectedCaller = address(MORPHO);
    MORPHO.liquidate(mp, borrower, seize, 0, abi.encode(exitPool, route));
    expectedCaller = address(0);
    require(IERC20(USDC).balanceOf(owner) >= before + minProfit);
}
function onMorphoLiquidate(uint256 repaid, bytes calldata data) external {
    require(msg.sender == expectedCaller); // reverts outside take()
    // swap on exitPool (set expectedCaller = exitPool for its callback), approve exactly `repaid`, ...
}
```

## Checks

- `tools/manifest-check.py` warns (meta 47f7, 2026-11-15) when `executor_args` has any word other than `{bot}`, and when the executor ABI has setup-style functions (`set*`, `allow*`, `approve*`, `register*`, `whitelist*`, `enable*`, `add*`). Warnings, not refusals: a protocol-singleton arg is allowed. At introduction it warned on 16 of 32 archived/live manifests for baked args (live: franken-dutch, morpho-nextblock) and 10 for setup functions.
- The reviewer still reads the code: the warnings cannot see constants or storage writes.
