trial

# Lim/USDT DODO to PancakeSwap Infinity BSC

The bot checks two DODO private pools on an alternating 60-second timer. For 75 USDT it reads DODO's `querySellQuote` to find the exact Lim amount, then simulates the deployed executor in one `eth_call`. If the USDC payout clears its signed gas bound, live mode submits one transaction. The executor flash sources Lim, sells Lim for USDT on PancakeSwap Infinity CL, repays the DODO pool in USDT, converts the surplus through the PancakeSwap V2 USDT/USDC pair, and returns USDC to the wallet. Paper mode uses the fork-deployed runtime as a code override and logs simulations only.

## Competition, last seven days

Blocks 133234788-134579088 (about 7.01 days): 522 DODO flash events, 519 takes from six flash borrowers. Borrower counts were 207, 140, 87, 83, 4 and 1. In 21 replayed cases, 17 first became takeable at the parent block and four at two blocks before; none stood for four blocks. The BSC average block interval in this range was 0.450 seconds. Sample-of-20 median gross was 0.0413 USDT, max 28.37 USDT, versus median gas of 307833 x 0.05 gwei, about 0.009 USD at BNB 575.87 USD. The paid capture used for the fork proof, `0x503751b1...`, had an effective gas price of 0.05 gwei and 388720 gas used; it also sent 0.00443618 BNB to a builder recipient. These priority and builder payments show strong competition. Source: KB attempts:2660, scratch/lim7d/sample.json and scratch/ra5c2/windows-lim.json.

The timer checks each pool every 120 seconds, while historical gaps usually lasted less than a second. This trial measures whether any slow gaps survive and whether sends win. It is expected to miss most captures. It does not monitor the mempool or subscribe to the busy Infinity singleton's Swap event. No natural paper capture is required for a trial.

## Proof and addresses

`scratch/trial-lim-bsc/proof.py` resets the BSC fork to block 134531080, the parent of the paid capture. With a fresh owner address, it proves +1.959410980741165392 BSC USDC in one transaction, a high-profit-threshold revert, and a repeat call that reverts after the opportunity is gone. The executor has zero Lim, USDT and USDC afterward. It deploys in 1,048,024 gas, below the gate's limit. The owner success used 486,300 gas. The bot's own `evaluate` at that parent block returns +1.958746375235790861 USDC with its fixed 75 USDT quote.

DODO pool addresses were found as `DODOFlashLoan` emitters and confirmed by `querySellQuote`; the Infinity vault and CL manager are in [PancakeSwap's contract list](https://developer.pancakeswap.finance/contracts/infinity/resources/addresses). The pool hook and PoolId are from the incumbent call trace. The BSC USDC token appears in [PancakeSwap's token list](https://github.com/pancakeswap/token-list). The V2 pair `0xec6557348085aa57c72514d67070dc863c0a5a8c` is the `getPair(USDT,USDC)` answer from the [PancakeSwap V2 factory](https://developer.pancake.xyz/contracts/v2/addresses); its `token0`, `token1` and reserves answered on chain.

## Loss and read bounds

The executor reverts unless its USDC gain meets `minProfit`. It rejects residual Lim or USDT and transfers USDC to the wallet before returning. The bot sets `minProfit` to the conservative signed gas cap in USDC. At a BNB valuation of 1000 USD, the send limit is at most 0.80 USD and at most half the simulated gross; the signer applies its current Chainlink price and can reject the transaction. The wallet holds 10 USD of BNB, with no USDC principal.

One DODO query and one full executor simulation per minute cost about 74,880 relay CU/day. Gas and receipt reads happen only after positive simulations; the code caps its relay use at 90,000 CU/day and sleeps to UTC midnight when reached. About 80,000 CU costs 0.042 USD/day at 0.53 USD per million CU. There is no feed cost.

Machine-readable `logs/bot.jsonl` rows include `start` with executor address, `simulate_revert`, `opportunity`, `opportunity_skip`, `paper_sim`, `send`, `send_result` with win/loss, gas used, winner block and blocks after the winner, `signer_reject` and `read_budget`.
