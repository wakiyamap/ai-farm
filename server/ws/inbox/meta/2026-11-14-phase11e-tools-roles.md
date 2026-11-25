# phase 11e: TOOLS.md shortened, race rule replaced in paper-reviewer.md and researcher.md (human, 2026-11-14)

Follows phase 11d (earner.md, common.md). The human asked for the other prompts to be tightened
too. Old files: `/srv/farm/prompts/roles/.<name>.bak-11e` and ws/history.

## TOOLS.md (16,559 -> 14,465 bytes)
- Ten rows were shortened: RPC relay, ledger, ledger add-source, fork, gate, web, relay-log-scan,
  relay-probe, manifest-check, session-report. The "How to call" and "Used by" columns are
  unchanged except the relay row's call note.
- Removed from the table (meta: check each is in the wiki page the row names, add it there if
  not, and do not put it back in TOOLS.md):
  - relay: calldata via `eth_getTransactionByHash`; `alchemy_getAssetTransfers` categories
    `external internal erc20 erc721 erc1155 specialnft`; bsc topic-only ranges <=1000 blocks
    (<=125 at head); arbitrum topic-only <=30000; responses over 32 MiB refused; elysium
    address-less getLogs at head <=2000 blocks; the 11-10/11-11 transient `[]` on bsc/polygon;
    ethereum/arbitrum Blockscout API asks keyless callers for X402 payment (use GitHub raw).
  - ledger add-source: "check `cursors` within ~2 ticks".
  - fork: `--force` overrides a lease (note it); hyperevm 2,000,000 gas (it is in common.md).
  - gate: 18 USD gas-wallet cap on base/optimism, bsc USDC 18 decimals, hyperevm 2,000,000 gas,
    elysium priced by HyperEVM's feed (all in common.md); `fund` refuses a top-up past 400 USD.
  - web: hyphenated or long queries return `(no results)`; `--json` ignores `-n` (~40 KB).
  - relay-log-scan: adaptive address bisection, scalar fallback, `--keep-trailing-nulls`.
  - relay-probe: elysium's 8 blocks are about 1 s, so 0 = 0 is normal there.
  - manifest-check: the fixed `owner` address warning.

## paper-reviewer.md and researcher.md
- The block-count race wording (0-block / 1-block / 2 blocks) is replaced by the reaction-time
  rule of decision 2026-11-14-race-rule-seconds. Nothing else in the rules changed.
- paper-reviewer.md: the `demote` bullet now sits with the other three decisions (it had
  drifted below the promote paragraphs).

## Not changed, for meta to look at
- live-operator.md still contains the literal placeholder `{{IDLE_BEFORE_STOP}}` under "Wake
  reasons". Nothing fills it in. Ask the human in inbox/human what the idle time should be, or
  propose a value.
- meta.md and live-operator.md are otherwise untouched.
- With 11d and 11e the race rule is already in common.md, earner.md, paper-reviewer.md and
  researcher.md. For decision 2026-11-14-race-rule-seconds only the wiki page
  `infra/reaction-time.md` and the Base/elysium recount remain.
