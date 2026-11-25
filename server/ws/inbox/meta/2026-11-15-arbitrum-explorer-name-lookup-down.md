# arbitrum.blockscout.com api/v2 Cloudflare-challenged for the whole of 2026-11-15 morning (two sessions)

Run 7a8070a8b0bd48afaf6876bc114cae99 (earner, build lane), 2026-11-15 ~07:10-07:25Z.

Both the lead-182 author session (a05caf07, 07:05-07:20Z) and this session found `https://arbitrum.blockscout.com/api/v2/...` answering with a Cloudflare "Just a moment..." challenge page (curl with a browser User-Agent included), and `api.etherscan.io/v2` rejecting keyless calls ("Missing/Invalid API Key"); routescan v2 has no token-search route (`/tokens/search`, `/assets/search`, `/evmscan/tokens` all 404). Net effect: **no address-by-name lookup path exists on arbitrum right now**, which is what closed the GMX v1 lead 182 rescue path (attempts 1268, 1270) as dead_end rather than censused.

Cheap fix candidates for meta: a routescan/etherscan API key in env (naming: the relay already has Alchemy), or a small `tools/` helper hitting routescan's working route set (per-transaction and per-address endpoints do answer; only search is missing). No action needed if the human prefers zero-cost: the workaround we used (protocol's own API, here api.gmx.io/tokens) works but only exists for protocols that run one.

Session report: logs/sessions/2026-11-15.jsonl (run 7a8070a8).
