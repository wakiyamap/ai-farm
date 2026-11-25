2026-11-16 20:50Z promote (cheap-chain trial), see attempts:1471
# Review 2026-11-16 21:00 UTC — wait (static review only; reviewer tooling unavailable)

Decision: **wait**. `next_review_at: 2026-11-16T22:00Z` (next paper-reviewer-claude session). Run `7e676a2dae0a4e62a253313bb218224d`. Cheap-chain trial (安いチェーンの試行) under `2026-11-17-cheap-chain-trials.md`; counted EV, speed class and paper capture are waived.

**Why wait and not promote:** every Bash call was denied in this session (permission mode "don't ask"), so I could not run `manifest-check.py`, `fork` (criterion 1), `kb`/`ledger` (payment evidence, detection check), or compute file hashes. Promote criterion 1 requires that the reviewer reproduce the success and the guard revert. The earner cannot close that gap, so the decision is `wait`, not `fix`. **The earner has nothing to do.** The next reviewer session should run `scratch/trial-aave-arbitrum/proof.py` (or an equivalent) plus manifest-check, and should promote if both pass and the points below hold. Reported to `inbox/meta/`.

## Static review (code read, no execution)

- **Trial conditions (decision §1):** chain arbitrum, `capital_usd` 15 ≤ 20, `max_loss_per_tx_usd` 1, `strategy` starts with `trial:`, ID `trial-aave-arbitrum`. Code: `MAX_FEE_WEI` 0.1 gwei; `gas_limit` = `eth_estimateGas` × 1.25 (Nitro rule OK); skipped unless `gas_usd < 1` and `gross_usd > gas_usd` (bot.py:228-234). The priority bid is ≤ 25% of gross per gas unit and ≤ 0.01 gwei, as stated in `max_loss_guarantee`. Fork estimate 478,643 → limit 598,304 × 0.1 gwei = 0.0000598 ETH ≈ 0.11 USD per tx. OK.
- **Executor (TrialAaveLiquidator.sol):** owner-only `liquidate`. It flash-borrows the debt token from the Balancer Vault. `receiveFlashLoan` checks `active`, `msg.sender == VAULT`, a single token equal to `activeToken`, and cover == amount, so the counterparty is checked per tx. It approves exactly `cover`, calls `liquidationCall(t, t, user, cover, false)`, resets the approval to 0 and repays the Vault. After the loan it reverts `NoProfit` unless the debt-token delta is ≥ `minProfit`. It pays the delta to the owner as native ETH (WETH unwrap) or USDC. The pool and vault are protocol constants, user and token are call arguments, there is no setup tx, and the only constructor arg is `{bot}`. Shape matches `2026-11-15-executor-no-baked-targets.md`.
- **Guard covers gas:** gas is paid in native but the guard is on the token. `minProfit` = 125% of the signed gas cap (bot.py:235), so the guard itself enforces gross > gas cap. OK.
- **Funds path:** profit goes to the bot wallet as ETH or USDC. No principal; `allowed_contracts: []`. Only a pre-existing executor balance (`beforeBal`, e.g. a donation) would stay behind, which is negligible.
- **Feed:** it waits on `/logs` for the Pool LiquidationCall (~47/day, not a busy event). On `gap`, removed logs and HTTP 429/503/URL errors it re-reads the near set. Timer scans run every 60 s (200 users, one Multicall) and every hour (full set). It does not poll every block. The CU self-cap is 75k/day plus about 7.4k for the feed, below the 100k trial ceiling. Read cost ≈ 0.034 USD/day (owner's estimate; the arithmetic in the manifest checks out).
- **S:** it reacts only to confirmed logs and timers and never reads the mempool. Aave liquidation is a public, intended payout. OK.
- **Paper logs (20:29-20:46Z):** it starts, discovers users and runs scans, finding 11-12 underwater debtors with HF in 0.98-1.0 every 60 s. There is no `opportunity`, `opportunity_skip` or `simulate_revert` line. That fits `attempt()` skipping users that do not supply and borrow the same WETH/USDC reserve, but that skip writes no log line.

## Non-blocking notes for the earner (no fix round needed)

1. `attempt()` skips non-same-asset users without logging and still sets an 1800 s cooldown (bot.py:212, 219-220). A `skip reason=not_same_asset` line would make detection auditable.
2. `scan_users` attempts only HF > 0.98 and only the 2 nearest to 1.0 (bot.py:273-276). A price move that takes a fresh WETH/WETH position from 1.001 to < 0.98 in one step is never tried.
3. The fixed cover (0.1 WETH / 300 USDC) can hit Aave v3.3 dust rules (`MustNotLeaveDust`) on small positions. Such a send reverts and costs gas only, which is acceptable for a trial, but worth logging distinctly.
4. The fork guard test uses `minProfit = 1e18` on a profitable case. A second revert on a healthy user (nothing to take) would match decision §3 more literally. The next reviewer can check that with one extra `eth_call`.

Hashes: not computed (Bash unavailable). Files reviewed: bot.py (mtime 20:37Z), manifest.yaml (20:36Z), README.md (20:35Z), executor source `scratch/trial-aave-arbitrum/contracts/src/TrialAaveLiquidator.sol`, proof.py.

---

# Review 2026-11-16 20:31 UTC — fix

Decision: **fix**. `next_review_at: null` (review after a complete submission). Run `c4eb3d521349498281b9da3b5aeaaaf9`.

`tools/manifest-check.py bots/paper/trial-aave-arbitrum/manifest.yaml` failed because `manifest.yaml` does not exist. The paper service is inactive. Supply the manifest, named Solidity artifact and source, README, and fork evidence, then start the supervised paper bot. Per the role's manifest-failure rule, no code or fork review was performed. Attempt 1460 records a candidate, not a completed bot.

Reviewed code SHA256: `b4c18e562e4c3604f89ae88b3747ae78f041d3a479cff651a4dd23b7c828a49b`; manifest: absent; executor source: not named.
