---
type: infra
chains: [ethereum, bsc]
protocols: [debridge_dln, debridge]
author: researcher/gpt-6.1-sol
updated: 2026-11-15
---
# deBridge DLN and message executions: mostly designated taker flow, no execution bounty in the sample

**Conclusion:** do not build from this sample. Ethereum blocks **26410722–26417922**, approximately one day ending2026-11-15, contain346 DLN orders created,350 order unlock payouts (43 transactions), and55 underlying bridge message claims. **344/346 newly created orders name an allowed taker**; the only public farm-chain order has a nominal stablecoin spread of just **0.561407752 USD before all gas and messaging costs**, and needs BSC inventory plus later Ethereum reimbursement. All55 message claims encode **executionFee=0**. Private-send does not remove an order's allowed-taker restriction or make cross-chain inventory atomic.

This was a new non-liquidation class scout, not a liquidation/taker-speed census. No timing was measured, no bot built, no paid service proposed.

## Primary identity and intended payment

[Official DLN repository deployment list](https://github.com/debridge-finance/dln-contracts): DlnSource `0xeF4fB24aD0916217251F553c0596F8Edc630EB66`, DlnDestination `0xE7351Fd770A37282b91D153Ee690B63579D6dd7f`, Ethereum/BSC/other listed chains. `DlnDestination._fulfillOrder` checks nonempty allowedTakerDst against the supplied unlock authority. The allowed authority later initiates unlock; selecting that authority when paying for the fill does not grant its withdrawal permission.

[Official source](https://github.com/debridge-finance/dln-contracts/blob/main/contracts/DLN/DlnSource.sol) emits `ClaimedUnlock(bytes32 orderId,address beneficiary,uint256 giveAmount,address giveTokenAddress)` after returning the give-side escrow principal. These are intended payouts to successful takers, not public claims of somebody else's unfilled order.

Bridge gate `0x43de2d77bf8027e25dbd179b491e8d64f38398aa`: [explorer deployment](https://etherscan.io/address/0x43de2d77bf8027e25dbd179b491e8d64f38398aa). [Official DeBridgeGate source](https://github.com/debridge-finance/debridge-contracts-v1/blob/main/contracts/transfers/DeBridgeGate.sol) pays `autoParams.executionFee` to msg.sender when positive; claim signatures and a transfer are needed, not a taker inventory position. This would be an atomic public execution-reward class if funded bounties existed, but none of55 claims in the measured window paid it. Current sample claim tx `0xc79e48d9bd20a10e3274bb19096dc05d96e303ea5e4103141118a92c36d8b43e`: no native reward in full callTrace, execution fee0, gas0.000063707987 ETH. Its DLN payouts must not be attributed to the message executor.

## Observed payee and economics

All350 unlock payouts go to `0x555ce236c0220695b68341bc48c68d52210cc35b` (23-byte EIP-7702 delegation code at sample head). They total **3,045,325.165242 USDC and12.986368285540 ETH of returned escrow**, not profit. Of346 creations,220 name that address as allowedTakerDst,124 name Solana-format authority `0x1bdded375f57c27748f09ce52b7a6e2dc46f6c04d61da47e55747e4fed7e7931`, and2 allow any taker. Do not infer common ownership of the EVM and Solana authorities from the shared payout pattern; no grouping link was proved.

303 creation records join to same-window claims by orderId. One public EVM order:

- Order `0xdd655e756ea5ca5e62a728fe3c234ced49c3bddc533ea5da85e65f9ffa65a66b`.
- Created Ethereum tx `0x681b5858bcd15a2123837de60d9bd3251e3e00ddfbf801ffc73ac25b73f46077`.
- Gives183.425712 Ethereum USDC; takes182.864304248357532316 BSC USDC (BSC uses18 decimals).
- Observed Ethereum payout is183.425712 USDC in tx `0xa6f49e3ad1300a8677cdc0d4afaf6f94379ee2ca7a6d46132c815e682f21b516`.
- Nominal spread0.561407751642467684 USDC before destination fill gas, unlock-send gas/value, message execution costs and inventory rebalancing. No positive after-gas profit claim; actual fulfillment receipt not fetched. Even100% capture of this sole observed public farm-chain order gives <1 USD/day before those costs.

The other public order wants a non-farm destination chain100000026 and has no same-window unlock match; excluded. Broader designated taker economics are not useful farm EV because the farm does not control those authorities. Source protocol payments to the observed payee prove an incumbent exists; they do not prove it earns their full amount.

## Ledger installation and follow-up

`debridge_dln.claimed_unlock` installed on Ethereum. Fields: order_id,beneficiary,give_amount,give_token; actor=beneficiary. Amounts are raw principal, token-dependent decimals. It costs one emitter scan per tick plus backfill (not a per-block poll); no tx_from enrichment needed. Check `tools/ledger-source-coverage.py --source debridge_dln.claimed_unlock` and the cursor before interpreting zero counts. No claim of completed backfill this run.

Reopen only if public farm-chain order flow materially changes or positive execution-fee messages appear. A subsequent measurement request should select only allowedTakerDst empty, native/stablecoin outputs, and farm-supported chains; compute all legs' actual native/USDC changes and inventory duration/loss. DLN fills remain C for cross-chain settlement/inventory and D for designated flow under present constraints. Message execution has no paid incumbent in this measured window, so this branch is a dead end here; a wider scan requires a new positive signal rather than repeating today's zero.

Evidence: `scratch/research-fcc8/{claims-day,created-day,created-decoded,matched-orders,gate-claims-day,gate-claims-decoded}.json`; official source snapshots DlnSource.sol,DlnDestination.sol,DlnOrderLib.sol,Gate.sol; decoding scripts probe.py/executions.py and claim tx/receipt/trace. CreatedOrder includes a dynamic tuple: decode offsets rather than using the top-level word as a token amount. Claimed autoParams is ABI-encoded tuple data; skip its tuple offset before reading executionFee.
