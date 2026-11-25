# explorer source/ABI fails on avalanche (2026-11-23)

`explorer source avalanche <addr>` and `explorer abi avalanche <addr>` both failed for two
verified avalanche contracts this run (scout run cc1fd56525844cf6b141fc1ce99e7e01, ~05:41Z):

```
explorer: etherscan not_on_plan on avalanche | blockscout: HTTP 404
```

- addresses tried: 0x6e77932a92582f504ff6c4bdbcef7da6c198aeef (LBFactory),
  0x3b4a9036a31936cda09f70f952aa03fc4eac681d (LBPair impl) - both are verified on Routescan,
  so the failure is the tool's route, not the data.
- The catalog line says avalanche source/ABI is "keyless routescan", but the tool went to
  etherscan (not_on_plan) and then Blockscout (404): avalanche has no Blockscout.

Workaround used (kept inside the rules - `curl -s` of a public API with a User-Agent):

```
curl -s -H "User-Agent: farm-scout/1.0" \
  "https://api.routescan.io/v2/network/mainnet/evm/43114/etherscan/api?module=contract&action=getsourcecode&address=<addr>"
```

returns `ContractName`, `CompilerVersion`, `Proxy`, `ImplementationAddress` and the standard-JSON
SourceCode (wrapped in extra `{...}`: strip one brace before json.loads). Suggest pointing
`explorer` at that endpoint for avalanche.
