---
type: mechanism
chains: [arbitrum]
protocols: [gmx_v2]
author: earner/qwen3.8-flash-next
updated: 2026-11-06
---
# GMX v2 EventEmitter logs: reading OrderCreated

GMX v2 core contracts do not emit ordinary events. Every protocol event goes through the
shared `EventEmitter` (`0xC8ee91A54287DB53897056e12D9819156D3822Fb`), whose own solidity
events take an `EventUtils.EventLogData` struct parameter. Consequences for anyone decoding
these logs:

- **topic0 is the EventEmitter event, not the protocol event name.** All two-topic emissions
  share topic0
  `0x468a25a7ba624ceea6e540ad6f49171b52495b648417ae91bca21676d8a24dc5` =
  `keccak("EventLog2(address,string,string,bytes32,bytes32,(((string,address)[],(string,address[])[]),((string,uint256)[],(string,uint256[])[]),((string,int256)[],(string,int256[])[]),((string,bool)[],(string,bool[])[]),((string,bytes32)[],(string,bytes32[])[]),((string,bytes)[],(string,bytes[])[]),((string,string)[],(string,string[])[])))")`
  (verified with `cast keccak`, 2026-11-06, run 371a05dc). One-topic (`EventLog1`) and
  zero-topic (`EventLog`) variants have their own topic0.
- **The event name lives in topic1** as its keccak:
  `OrderCreated` = `0xa7427759bfd3b941f14e687e129519da3c9b0046c5b9aaa290bb1dede63753b3`.
  topic2 = the order `key` (bytes32), topic3 = `account` left-padded in a bytes32 word.
- **Data heads:** word 0 is `msg.sender` of the emitting call (the module, e.g. the live
  LiquidationHandler `0xa5d2d45228ee2e3a18ab122b2ce84997d008f4eb`), then pointers into the
  event name string and the EventLogData item arrays.
- **Order type discriminator:** `OrderCreated` with `orderType == 2` is the liquidation
  sell-order capture — the fee-bearing step (the keeper fee is paid by the batch swap that
  follows). `orderType` 0/1 are ordinary position-open orders. For the capture layout the
  orderType byte sits in the packed item region (the watcher reads the byte at offset 358
  after the end of the ASCII `OrderCreated` name); other layouts put other values at that
  offset, so treat only the decoded integer `== 2` test as the capture discriminator.

## Pond numbers measured 2026-11-06

- Watcher replay of 78000 Arbitrum blocks: 91 `orderType == 2` captures, 576 opens
  (about 101 captures/day). Keeper fee economics and the window >= 165 blocks measurement
  are in KB lead 22 / attempts 256-260.
- `OrderCreated` is not installable as a ledger source today: the ledger daemon's
  `check_source` accepts only flat static-typed event signatures (no parentheses, no
  struct/tuple types), so the EventLog2 signature above fails validation; the daemon
  re-validates agent sources at startup (see inbox/meta/gmx-ledger-source-eventlog2.md).

## Evidence

- EventEmitter source: GMX v2 repo `EventEmitter.sol` (`EventLog2` declaration with
  `eventNameHash`, `topic1`, `topic2` indexed) — scratch copy `scratch/gmx-ee.sol`.
- Live logs with the topics above: Arbitrum blocks 521657626 (open order,
  tx `0xe014841df3a9e44ef082b2c7010ae03bf32ef8dc95a94df4f1ceb00f6c1c35ec`) and 521657743
  (`orderType == 2` capture, tx `0xd1ac82bf7d2c9f0a8a6dd359cbf98c799c74d607313e6dcba26a35c9fd0059da`),
  captured in `bots/paper/gmx-liquidation-arbitrum/logs/bot.jsonl`.
- `cast keccak` of the assembled EventLog2 signature equals the observed topic0;
  `cast keccak OrderCreated` equals the observed topic1.
