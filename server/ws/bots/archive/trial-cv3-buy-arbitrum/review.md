# Review 2026-11-17 21:55 UTC — promote (cheap-chain trial)

Decision: **promote — cheap-chain trial**. `next_review_at: null`. Reviewer run `34931d202bf643759aef873e877ceff4`.

Prior independent technical approval and fork success/guard reproduction stand. Current bot, manifest and named executor source hashes match the reviewed hashes; `manifest-check.py --all` passes. Human decision `2026-11-18-trial-slots-20.md` raises live trial capacity to 20; `gate status` showed 10 live `trial-*` bots, $1,041.59 total capital, no freeze. This was among the oldest approved waiting trials (06:07 UTC). CU/day, paid entry, loss cap and wallet return are documented in the earlier review.

# Review 2026-11-17 20:25 UTC — wait (cheap-chain trial capacity)

Decision: **wait — prior cheap-chain trial technical approval stands; ten live trial slots are occupied**. `next_review_at: 2026-11-17T22:30:00Z`. Reviewer run `35ea4b72d5d749ce8831417bf672d3a9`.

Bot code, manifest and named Solidity executor source are byte-identical to the hashes in the prior technical approval. `manifest-check.py --all` passes. Only paper state changed since the previous review. `gate status` at 20:22 UTC shows ten live `trial-*` directories and no freeze. This includes `trial-aave-optimism`, whose promotion funded a $15.02 wallet but failed to deploy its executor; it is inactive, still counts toward X and the live trial cap, and was reported to the human. Recheck capacity after operator recovery. No new fork reproduction is needed for unchanged approved source.

# Review 2026-11-17 17:10 UTC — wait (cheap-chain trial capacity)

Decision: **wait — prior cheap-chain trial technical approval stands; ten trial bots remain live**. `next_review_at: 2026-11-17T19:00:00Z`. Reviewer run `4f7118b6333f4ef9999b9ea8aeca8f55`.

Bot code, manifest and named executor source remain byte-identical to the SHA-256 hashes in the previous technical review. Only paper state changed. `gate status` at 17:07 UTC showed ten live `trial-*` bots and no freeze; the human decision `2026-11-17-cheap-chain-trials.md` limits simultaneous live trials to ten. Recheck when a slot opens.

# Review 2026-11-17 15:35 UTC — wait (cheap-chain trial capacity)

Decision: **wait — prior cheap-chain trial technical approval stands; ten trial bots remain live**. `next_review_at: 2026-11-17T17:00:00Z`. Reviewer run `eb3285a1ce6249b1be5637d795995098`.

Bot code, manifest and named executor source match the SHA-256 hashes in the prior review. Only paper state files changed. `gate status` at 15:33 UTC showed ten live `trial-*` bots, no freeze and no available trial slot. Recheck capacity when a slot opens.

# Review 2026-11-17 12:27 UTC — wait (cheap-chain trial capacity)

Decision: **wait — prior cheap-chain trial technical approval stands; ten trial bots remain live**. `next_review_at: 2026-11-17T14:30:00Z`. Reviewer run `b2721ac28d8e4729967be7e40bb6a2a2`.

Only paper state files changed since the previous review. Bot and manifest modification times predate that review; the previous independent fork success, guard revert and executor checks stand. `gate status` shows ten live `trial-*` bots and no freeze, so no capacity is available. Recheck when a trial slot opens.

Source SHA-256: bot `48df13be51f7d151ba0ceea6eec97b32adbf8c0ab6120eaf69277b552cd2597f`; manifest `674fe1a290be732c359fb5845084b630c64e1c905bdce8c2b04c6e249878cb72`; executor source `97d9839c61e0a6a62e6e9eadc9eac75bbd1c56644a63cc39d813cfaf5171e5e1`.

# Review 2026-11-17 09:19 UTC — wait (cheap-chain trial capacity)

Decision: **wait — prior cheap-chain trial technical approval stands; ten trial bots remain live**. `next_review_at: 2026-11-17T11:30:00Z`. Reviewer run `99cd382d51904b98816c9497e673b64f`.

Only paper state files changed since the 06:07 review; bot, manifest and executor source are unchanged. `manifest-check.py` still passes. The previous review independently reproduced success, `NoProfit` guard revert, empty executor and the bot's paper send path, with $0.95 gas cap and about 10,000 CU/day ($0.0053/day). `gate status` again shows ten live `trial-*` bots. Recheck capacity at the next review; no fork rerun is warranted for unchanged code.

# Review 2026-11-17 06:07 UTC — wait (cheap-chain trial capacity)

Decision: **wait — cheap-chain trial passes technical review; ten trial bots are live, the policy cap**. `next_review_at: 2026-11-17T08:15:00Z`. Reviewer run `ede2e9362aad4dd5951d1c6f67165c34`.

`manifest-check.py` PASS. `forge build` PASS. Current source `Cv3FlashBuyOut.sol` has only owner as constructor argument; comet, collateral and pools are per-call arguments. The owner-only `buy()` flash swaps collateral for the comet base token, buys public reserve collateral in the callback, converts USDT surplus to USDC when needed, reverts unless USDC gain exceeds `minProfit`, then pays all USDC to the owner. The current bot code uses `EXECUTOR_ADDR` live, the signer address as a dict, and imports the signer after adding `/opt/farm/lib`; paper has no signer call. No setup or leftover approval is needed.

I independently reran `scratch/trial-cv3-buy-arbitrum/proof.py` on the Arbitrum fork. At parent block 524328184, guard tx `0x35480cf9...e2f9154fe` reverted NoProfit with owner USDC unchanged. Success tx `0x2e064b15...9a0dd111069c0` used 412,231 gas and added 2.107212 USDC to the owner. Executor USDC, USDT, WETH, native and USDT approval were all zero. Nonowner and exhausted-reserve calls reverted. The cUSDCv3 route independently added 0.118458 USDC at parent block 524319772. The bot's own `paper_selftest.py` found the cUSDTv3 residue, calculated 2.107212 USDC gross, estimated 641,818 gas with margin, set a $0.5134544 gas cap and emitted `paper_sim` success. Normal paper logs show reserve safety polling without errors; natural capture is waived for trials.

Past-seven-day paid-entry evidence: residue buys `0x8dd4d06d...06ec` (2.06 USDT gross, about $1 gas) and `0x2e7b1c22...f91d` (9.44 USDT gross, about $2.1 gas), both at the public `buyCollateral` entry, 1 block after absorb; the buyer's priority was 1.5-1.9 gwei. Two executors made the four residue buys. The bot is a timer plus feed `/logs` watcher, not a pending-tx watcher. Capital $10, loss/tx < $1 at the current ETH price: gas limit is `eth_estimateGas` x 1.25, refused over 1.2M; max fee <=0.2 gwei, priority <=25% simulated gross, and code sends only if simulated gross exceeds this send's gas cap. Every send logs result, gas used and winner block. Live reads about 10,000 CU/day = $0.0053/day at $0.53/M CU, below the 100,000 CU/day trial limit (relay hard cap 60,000 plus about 5,800 feed CU).

`gate status` at review showed ten live `trial-*` bots after Base promotion. Do not promote while the cheap-chain trial cap remains full. Recheck capacity at `next_review_at`; if a slot opens, the mechanism and send guard have already been independently reproduced.
