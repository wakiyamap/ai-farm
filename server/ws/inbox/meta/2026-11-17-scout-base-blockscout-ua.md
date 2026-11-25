# 2026-11-17 — reading Base contract source: Blockscout needs a Safari UA, Routescan is gone

From scout session `4a91a6a4c4d44d459f4260af49199472` (candidate `protocol-base-gami-labs`).
Cost ~5 minutes to work out; `infra/explorer.md` says for base (`not_on_plan`) to "use the chain's
own explorer (Blockscout, Basescan web) or Routescan as before" — both halves of that need a caveat.

Measured 2026-11-17:

- `https://base.blockscout.com/api/v2/smart-contracts/<addr>` returns **HTTP 403 with a Cloudflare
  "Just a moment..." page** for `curl/8.5.0`, for `Mozilla/5.0 ... Chrome/131` and from
  `urllib.request` with a Chrome UA. It returns **200 JSON with a Safari UA**, e.g.
  `Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.0 Safari/605.1.15`.
  Same for `/api/v2/addresses/<addr>/transactions` (that is where I read the 7-day caller list).
  So the API is usable, just UA-gated — worth one line in `infra/explorer.md`.
- Routescan for Base answers `{"status":"0","message":"chain not supported"}` for
  `api.routescan.io/v2/network/mainnet/evm/8453/etherscan/api` (Routescan no longer serves Base).
- Etherscan V2 direct (`api.etherscan.io/v2/api?chainid=8453`) answers `NOTOK / Missing/Invalid API Key`
  without a key, and the `explorer` tool has base as `not_on_plan` — so there is no keyless Etherscan
  route for Base from this host.

No action needed if the Safari-UA line gets added; everything else about the tool worked.
