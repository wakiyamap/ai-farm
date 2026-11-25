# base.blockscout.com timing out for scouts (2026-11-18)

While scouting KiloEx on base (run 32ead678b7b6433080ec4328b82e57bf, ~21:55-22:15 UTC), every
Base Blockscout call was slow or failed:

- `explorer source base <addr>` worked for the three proxies but `explorer txs base <addr>` and
  `explorer abi` failed with "blockscout upstream failed: The read operation timed out"
  (base has no etherscan on our plan, so Blockscout is the only keyed route there).
- Direct `https://base.blockscout.com/api/v2/addresses/<a>` (python, User-Agent set) timed out
  at 40 s for 4 of 6 addresses; one returned HTTP 520.
- Routescan's etherscan-compatible endpoint for chain 8453 returned 404.

Consequence for scouts: on base there is currently no reliable way to get an unverified
implementation's ABI or a contract's recent tx list, so "which functions does this contract
expose" has to be answered by selector probing through the relay, not by the explorer. Worth a
look whether the explorer service's blockscout timeout is too short or the upstream is degraded.
