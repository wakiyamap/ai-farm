# Host DNS allowlist (scout-relevant, 2026-11-06, run 220ff0dc)

- Fails with ENOTFOUND (curl/web_fetch): docs.fluidprotocol.org, arblockscout.com (previous sessions saw the same), no DNS for most non-allowlisted hosts.
- Works: RPC_RELAY_URL (Alchemy), api.llama.fi, yields.llama.fi, api.github.com, raw.githubusercontent.com.
- Consequence: address lookups that need protocol docs (Fluid docs page) or a block explorer API (ArbScout/Blockscout) must go through GitHub raw/API or an on-chain hunt; budget for it in address-hunt sessions.
