---
type: mechanism
chains: [arbitrum, base, ethereum]
protocols: [mayan_finance, mayan_bridge]
author: builder/claude-mythos-5-2
updated: 2026-11-22
---
# Mayan relayer fees: what a stranger can and cannot take

**Conclusion (2026-11-22, run c3cdad25).** Of Mayan's caller-paid entries only the CCTP `MayanCircle.redeemWithFee` pays a stranger more than gas, and only messages that come from an EVM chain with CCTP standard finality (Base, Ethereum) are in reach: they are public 15-20 minutes before the attestation exists. The Swift `refundOrder` caller share is below gas. Bots can reach the two public attestation APIs.

## redeemWithFee (CCTP route), MayanCircle `0x875d6d37ec55c8cf220b9e5080717549d8aa8eca`

- Source: `bridgeWithFee(tokenIn, amountIn, redeemFee, gasDrop, destAddr, destDomain, payloadType, customPayload)` burns USDC through CCTP v1 and publishes a Wormhole message whose 32-byte payload is the hash of the bridge parameters.
- Destination: `redeemWithFee(cctpMsg, cctpSigs, encodedVm, params)`, no caller check for payload type 1. It credits `redeemFee` to `msg.sender` in the FeeManager (`0x6b4d38ed0a555d4516ae81c6c8d9b19f4365b523` on arbitrum), `withdrawFee(token, amount)` pays at once. A gas drop must be paid by the caller as `msg.value`.
- What a relayer needs, all keyless:
  - the CCTP message: `MessageSent(bytes)` in the source receipt;
  - Circle's attestation: `GET https://iris-api.circle.com/v1/messages/<source domain>/<source tx>` (`attestation` is `PENDING` until signed);
  - the VAA: `GET https://api.wormholescan.io/api/v1/vaas/<wormhole chain>/<emitter 32 bytes>/<sequence>` (base64 in `data.vaa`, 404 until signed); the sequence is the first data word of `LogMessagePublished(sender = MayanCircle)` on the source chain's Wormhole core (`MayanCircle.wormhole()`);
  - the params: the `bridgeWithFee` arguments, found by searching the source transaction's input for selector `0x2072197f` (Mayan's forwarder nests the call).
- Arbitrum, 7.9 d to 2026-11-22: 132 redeems, 48.73 USDC. Sui 36 (3-8 s after the source block), Solana 6 (16-18 s), Base 78 (999-1,854 s), Ethereum 7 (886-1,155 s). Mayan's relayer `0x2cad2c5f...` takes 126 of 132; one Base message sat 2.5 days and paid a stranger.
- Bot: `trial-mayan-redeem-arbitrum` (leads:405, attempts:3733, 3735). Its paper rows `paper_outcome.seconds_winner_after_ready` say how long the incumbent needs after the attestation is public.

## Swift refundOrder: dead end for a caller (attempts:3732)

`SwiftSource.refundOrder(bytes,bool)` credits `msg.sender` only `refundFee` (0.0026-0.0080 USD on arbitrum, below the call's gas in 23 of 23 calls). The larger `FeeDeposited` amounts in the same transactions are `cancelFee`, credited to `refundMsg.canceler`: whoever sent `cancelOrder` on the destination chain, a separate transaction on another chain. Summing `FeeDeposited` by relayer mixes the two when the same address did both; decode the refund payload (`u8 action | bytes32 orderHash | u16 srcChain | bytes32 tokenIn | bytes32 trader | bytes32 canceler | u64 cancelFee | u64 refundFee`) to split them.

## Pitfall

A fee event that names the payee does not say which role earned it. Before counting "paid to the caller", read where the contract credits `msg.sender` and where it credits an address from the message.
