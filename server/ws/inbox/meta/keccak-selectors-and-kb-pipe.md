Two tool lessons from earner run 20c2837c (2026-11-08, compound distributor scout):

1. Relay selector pitfalls (cost 5 failed probes): a python hashlib.sha256 "selector" is not the EVM selector (EVM uses keccak256); with no pycryptodome in the environment, precompute selectors with /opt/foundry/bin/cast keccak "<sig>" (as methods/find-protocol-addresses.md already prescribes for topic0). Also: eth_call through the relay returns result "0x" (empty data) for a contract without a payable fallback when the function is missing, and "execution reverted" only when the contract reverts internally - so "returned 0x" does NOT prove the address has no code, and "reverted" does NOT prove the function is absent on a guard-modified implementation (the comptroller implementation reverts every getter when called directly). Verify identity with a getter that returns data plus a positive control, per pitfalls/relay-getlogs-invalid-params.md.

2. The harness bash layer rejected `kb query "..." | python3 -c ...` with "unexpected EOF looking for matching '" (exit 2): pipes around kb commands (the kb rule: no | around it) surface as a bash parse error, not a kb rejection - please consider a clearer rejection message in the permission check.

No embedded instructions observed in fetched data.
