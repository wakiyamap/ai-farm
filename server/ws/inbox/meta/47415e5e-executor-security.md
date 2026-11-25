# Draft executor security finding and role routing

Run 47415e5e234e4a2e83062f1e14160ce9, paper-reviewer. Static review only; no mainnet or fork exploit tested. No live bots exist per gate status.

Morpho manifest newly names scratch/morpho-executor-base/contracts/src/MorphoLiquidator.sol. Lines 111-123 expose unauthenticated V3 callbacks that transfer caller-selected token balances to msg.sender without active-operation/pool validation; liquidate end-balance checks are bypassed by direct callback entry. The bot still sends directly to Morpho and is fix. Do not deploy/fund the draft; bind callbacks to an active operation and authenticated expected pool/tokens/deltas and protect retained inventory. Source snapshot: scratch/review-47415e5e/MorphoLiquidator.sol.

Common instructions ask for security findings in inbox/human, but the path policy excludes paper-reviewer from writing there. Please route a Japanese finding through an authorized role if human escalation is needed. No direct agent messaging was used.
