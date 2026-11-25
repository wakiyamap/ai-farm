# Review — trial-flux-bsc

## 2026-11-17T15:0xZ — promote (cheap-chain trial). Reviewer run `2f2ab75c0bef417b99dbfd07c7dce7be` (paper-reviewer-claude)

**Decision: promote** under `decisions/human/2026-11-17-cheap-chain-trials.md` ("cheap-chain trial"). Reaction-time classes, EV and the CU-vs-EV test are waived for trials and were not used. `next_review_at`: none (live; the 7-day result goes to attempts at 2026-11-24).

Files reviewed (current at review): `bot.py`, `manifest.yaml`, `README.md`, `executor-runtime.hex`, `scratch/trial-flux-bsc/contracts/src/TrialFluxLiquidator.sol` + artifact `out/TrialFluxLiquidator.sol/TrialFluxLiquidator.json` (rebuilt with `forge build`, no change).

Trial checks:
- Chain bsc (not ethereum); `capital_usd: 10` (≤20); `max_loss_per_tx_usd: 1`; `strategy` starts `trial:`; id `trial-flux-bsc`. `manifest-check` OK. `allowed_contracts: []`, `executor_args: "{bot}"`, `send_route: public`.
- Paid in the last 7 days: LogLiquidate at block 133649352 (2026-11-15 01:40Z), tx `0x4068686b44687d99829a7e8dbe7e9982eb8db18a439f2e240782d223e3a19bd4`, liquidator `0x5ac9bc14…`, 0.0927 BNB collateral for 50.95 USDC debt (so the gross is a few USD). The README example `0xcd4d4f58…` (block 133552990) gave +6.34 USDC net at 594,681 gas × 0.1 gwei ≈ 0.035 USD. The gross is far above one send's gas.
- Callable by anyone: Fluid `liquidate(uint256,uint256,address,bool)` is public. I quoted it from the stranger 0x1111 and ran the success from a freshly deployed executor.
- Read cost: a 30 s timer with one eth_call (26 CU) = 74,880 CU/day, and a code cap of 90,000 (`bot.py:49`). The paper state showed 676 CU at 13 min after start, i.e. 2 quotes/min, as stated. That is ≤100,000 and costs ≈ 0.048 USD/day.
- Send condition in code: `bot.py:221` and `bot.py:164` skip unless the simulated gross is above the gas cap in USD. The on-chain `minProfit` is the gas cap + 1 wei (`bot.py:224`).
- Loss bound: gasLimit is fixed at 1,200,000. `maxFee = min(0.85 USD / (1.2·oracleBNB·gasLimit), max(2·gasPrice, 25 % gross bid))` (`bot.py:214-216`, repeated at `155-159`), so the signed `gasLimit × maxFee` is ≤ 0.85 USD at 1.2× the Aave/Chainlink BNB price. That is < 1 USD at the signer's price. value = 0. The priority bid is ≤ 25 % of the gross and capped by the same 0.85 USD (BID_SHARE), as stated in `max_loss_guarantee`. At about 590 USD/BNB the cap is ≈ 1 gwei; observed competitor prices are 0.05–0.3 gwei.
- Logging per send: `send_result` has won/lost/unknown, gas_used, gas_cost_wei, send_block, winner_block and blocks_from_winner (`bot.py:181,192-194`).
- Executor rules: one tx (Aave flashLoanSimple → Fluid liquidate → wrap → Pancake V3 swap → repay). It reverts `NoProfit` unless the USDC balance grows by ≥ minProfit (`TrialFluxLiquidator.sol:68`) and sends all profit to the owner (= bot wallet) in USDC (`:70`). All targets are call arguments: no constructor targets, no storage targets. The callbacks check the per-call counterparty and initiator (`:74,76,91`). Approvals are exact and reset to 0 (`:77,79,65`). Solidity. Only the owner can call it.
- Paper/live separation: paper uses a code override at PAPER_EXEC and from 0x1111, and sends nothing. Live uses `EXECUTOR_ADDR_BSC`/`EXECUTOR_ADDR` only (it exits if unset, no hard-coded fallback). `my_address()["address"]` is used. `sys.path.append('/opt/farm/lib')` is present. Reads go only through the relay. `executor-runtime.hex` equals the artifact's deployedBytecode except for the 3 immutable-owner slots (filled with 0x1111). S: a public liquidation reward read from confirmed state on a timer. No mempool, no front-running.
- BSC USDC has 18 decimals: the bot treats it as 1e18 throughout.

Fork reproduction (my own script `scratch/review-trial-flux-bsc/repro.py`, result `scratch/review-trial-flux-bsc/result.json`). Reset bsc to 133551277, deployed the current artifact with constructor(0x1111), and used the bot's own `quote_data`/`take_data` encoders:
- Quote: FluidLiquidateResult, debt 221.359 USDC. Simulated gross 6.549340376 USDC.
- Non-owner revert: `0xc3c9980cf028894cacabd27834db0ac6b24e0193f626eca1ec9ce983d62bfbb9` (status 0).
- Guard revert (minProfit = gross + 1): `0xc08cd1e13bf9df0a28dcf41318aa1eae05242ae4088797b2fe2ccfb1c020f219` (status 0). Owner USDC unchanged.
- Success with minProfit = 0.85 USDC + 1: `0xa2c391b0ef8dbeecfb24afb5772e55f67e329c5fc2dcce54415827d520430aed`, 487,228 gas, owner +6.549340376368010137 USDC.
- Repeat (case exhausted) revert: `0x46dce7cb05761ee345ba3cd0862c83794a9978f0789a87d9e7c9bedcef17ddf3`. Owner unchanged.
- After the runs, the executor holds 0 USDC, 0 WBNB and 0 BNB. Allowances: USDC→vault 0, USDC→Aave 0, WBNB→pool 0.

Detection: paper started 14:33Z, so there is no event since then. The last event was on 11-15 and the timer quote was shown to work on the fork. Natural captures are waived for trials.

Live trial count before promote: 7 (`ls bots/live | grep trial-`), below the cap of 10.

Notes for live: a 30 s timer against 0.45 s blocks will miss short windows. The README itself expects this, and the trial measures it. Expected funding is 10 USD of native BNB, with no principal (flash loan).
