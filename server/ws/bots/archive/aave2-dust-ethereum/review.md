Decision: fix
Reviewed at: 2026-11-06T17:16:16Z
Reviewer: paper-reviewer / gpt-6-sol
Run: 3cb48d637a024dd38ec0944ea93f240d
next_review_at: null (resubmit after an atomic USDC sale/profit path, a working paper simulation, correct live executor resolution and funding, and independent fork success plus revert)
Code SHA256: 5007e37a8d816f89a99c84b5ff2ce493f0483bcfaf2660445df15c635d3588c5
Manifest SHA256: df9ac3610cf023a2855eb5c4d2fea305d3972989fb31e625d84dc3c53ef4ae2d
Executor source SHA256: 017250204f00d3eb791b04ec5ca586c8e91dd5ae6008dd6b24c0156a00e469fe

The new executor is based on an incorrect Aave v2 API assumption. The verified Ethereum LendingPool implementation 0x02d84abd89ee9db409572f19b6e1596c301f3c81 names the fifth liquidationCall argument `receiveAToken` and states that true delivers collateral aTokens, while false delivers the underlying collateral. Aave does not pay the liquidation premium in USDC through this flag. AaveDustBatch.sol:81 passes true, repays USDC, and never sells the resulting aStETH. Its USDC balance-increase check at :89 will revert an ordinary liquidation; there is no completed atomic USDC-profit path. Source: https://etherscan.io/address/0x02d84abd89ee9db409572f19b6e1596c301f3c81#code . The manifest's fork_evidence explicitly says the revised source has no successful fork proof, so no success/revert reproduction was attempted or trusted.

The paper and live simulations use `SIM_FROM=0x000...000` (bot.py:24, :122, :129), but the executor requires `msg.sender == owner` at AaveDustBatch.sol:67 and its constructor sets owner to the deployer. These eth_calls cannot prove a profitable owner call. In live mode bot.py reads `EXECUTOR`, whose default is the old fork address (bot.py:21), while the gate provides the deployed address as `EXECUTOR_ADDR`; the live path has no verified binding to its deployed contract. The gate funds principal USDC to the bot wallet, but the executor must hold USDC for pool transferFrom and neither its constructor nor bot.py transfers principal into it. A separate USDC transfer would also leave the one-transaction loss guarantee unproven until an atomic funding/action route exists. The live send specifies gas=13,000,000 but no fixed fee ceiling; the manifest's claimed 2.3 USD at 1 gwei is arithmetically wrong: 13M x 1 gwei = 0.013 ETH, about 30 USD near 2300 USD/ETH. Verify the signed fee against the manifest's 31 USD limit at signing.

Event decoding now takes topics[3] and the first data word, correcting the prior indexing errors. Paper logs through head 26357232 show pending=0 and no natural successful capture. Direct relay eth_getLogs on the Aave v2 pool LiquidationCall topic found zero new events in blocks 26353156-26357248, after the manifest last sweep block 26353155. Public liquidation is permitted under S; no bot code was edited and no mainnet transaction was sent. KB attempts:310-311 (311 corrects a mistaken Compound ledger reference in 310).

--- Previous review ---

Decision: fix
Reviewed at: 2026-11-06T15:42:00Z
Reviewer: paper-reviewer / gpt-6-sol
Run: 71396b4d6be44a9a960fa1a4985be474
next_review_at: null (resubmit after an atomic USDC profit guard, correct event decoding and a complete live send path)

The submitted executor repays USDC at AaveDustBatch.sol:76, receives stETH, then checks only that stETH increased at :83-84. It leaves the USDC outflow unpaid and explicitly plans to sell stETH in a later bulk transaction (source :27-28; manifest legal_note). This does not enforce an end-balance profit or complete repay/seize/sale in one transaction. The $100 USDC principal is exposed to collateral price and execution risk between transactions, so L fails regardless of the stated 13M gas limit. Do not promote. A fork success or NO_PROFIT revert cannot establish the missing guard, so no fork lease was taken.

The paper bot cannot establish detection or execution evidence yet. bot.py:81 reads topics[4] for the user, although Aave v2 LiquidationCall has only three indexed fields (collateral, debt, user), so the event has topics[0..3]. It also converts the entire multiword data field to debtToCover instead of its first 32-byte word. Once an event arrives, these errors raise an index error or produce an invalid repayment. Its simulated call at :103 uses from 0x...f0c3 while the executor restricts calls to the deploying owner (:64). The paper simulation reads a mutable shared fork at a past state, not current chain state. There is no live signer/send branch anywhere in bot.py. Current logs through 15:38Z show only heartbeats and pending=0; no natural profitable capture. These are concrete fixes, not merely an event wait.

capital_usd=120 includes principal_usdc=100. The stated 31 USD gas exposure is within the current 50 USD ceiling if the actual signed fee is limited to 1 gwei and 13M gas, but the bot contains no live transaction with those fields. Public Aave liquidation is within S. No bot code was edited and no mainnet transaction was sent.
