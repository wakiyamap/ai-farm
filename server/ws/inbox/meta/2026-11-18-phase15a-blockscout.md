# phase 15a: Blockscout behind `explorer`, and the trial slot count (human, 2026-11-18)

Answers your note inbox/human/2026-11-17-meta-hai-wiki-base-explorer.md, item 2.

## 1. `explorer` now has a Blockscout backend

The human got a Blockscout PRO API key. farm-explorer keeps it next to the Etherscan key; nobody else
sees either. Same commands as before:

- Etherscan is asked first. Blockscout (`api.blockscout.com/v2/api`, the same Etherscan-style calls) is
  asked when Etherscan says the chain is not on its plan, unsupported, or the key is invalid, and for
  `source` / `abi` when Etherscan has no verified source. Every answer says `via etherscan` or
  `via blockscout`.
- `explorer chains` shows both backends per chain, e.g. `base: ok via blockscout (... etherscan
  not_on_plan, blockscout ok)`. A chain with no backend ok has no keyed route: use relay reads.
- `source` reads Blockscout's multi-file layout (AdditionalSources) and proxy fields
  (IsProxy / ImplementationAddress); `--out DIR` writes all files.
- Limits: Blockscout 4 calls per second and 20,000 a day for the whole farm, apart from the Etherscan
  limit. `source` / `abi` / `creation` are cached for a day. No bulk loops.

What I ask of you:

1. `roles/TOOLS.md`, the `explorer` row: replace "not on this API key's plan is final, use the chain's
   own explorer or Routescan" with "Etherscan, then Blockscout; `explorer chains` shows which chain each
   serves". Keep it one row.
2. Wiki `infra/explorer.md`: Base (and whatever `explorer chains` shows as ok via blockscout) now has a
   keyed route. The UA-spoofing ban stays as written; it is no longer needed.
3. In your next report: which chains `explorer chains` shows ok, and whether a scout or builder read a
   Base / optimism / bsc source through it.

## 2. The reviewer's trial count is wrong

Since the HAI stop (11-17 09:18 UTC) there have been fewer than ten live trial bots: 7, then 8 after
trial-flux-bsc was promoted (14:46 UTC). Your gate status at 15:07Z showed 8 of 10. Yet paper-reviewer
(gpt-6-sol) wrote at 15:35 UTC for nine bots: "gate status at 15:33 UTC showed ten live trial-* bots ...
no available trial slot", and builder-claude repeated it. Two approved trial bots have been waiting on a
cap that is not full.

Please make paper-reviewer.md count it from `gate status` exactly: live bots whose id starts with
`trial-` (non-trial live bots such as gearbox, morpho-nextblock and bold do not count), and write the
count and the ids in review.md when it decides `wait` for capacity. The human would fill the open
slots with trial-cv3-buy-optimism first, then the hyperevm bots (note 2026-11-17-human-hai-stop-usdc.md).
