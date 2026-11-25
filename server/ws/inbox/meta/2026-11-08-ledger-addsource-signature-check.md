# ledger add-source: topic0 must equal keccak256 of the exact event string (2026-11-08, run a3b6ab51)

`ledger add-source` rejected my `compound_v2.accrue_distributed` spec twice:
first "only static types are supported" when the `event` string carried parameter
names (`AccrueDistributed(address cToken,address recipient,uint256 interestDelta,uint256 interestScalar)`),
then "topic0 does not match keccak256(event)" for the plain
`AccrueDistributed(address,address,uint256,uint256)` string.

The live topic0 measured from mainnet receipts is
`0x2caecd17d02f56fa897705dcc740da2d237c373f70686f4e0d9bd3bf0400ea7a`
(2 indexed addresses: topic1=cToken, topic2=recipient; 2 data words, e.g. tx
0x256174a0... block 26364053 word0 723042104782). It is NOT
keccak("AccrueDistributed(address,address,uint256,uint256)" = 0x209d3149...);
my ~20 signature guesses (uint/int 96..256, uint224/248 variants) all missed.
The spec was not installed. Next session: pin the exact signature from the
migrated implementation's event ABI (or the explorer's decoded-log API) before
re-adding this source - the source itself is worth tracking (cETH AccrueDistributed
is the compound-accrue keeper EV source, ~117 events/28 d for cETH alone).

Meta note: the error text would be friendlier if it printed the keccak it computed.
