---
type: mechanism
chains: [base, polygon, optimism, arbitrum, avalanche, bsc]
protocols: [superfluid]
---
# Superfluid stream liquidations and the TOGA "PIC" seat: who is paid, and why the farm cannot take it under today's rules

**Conclusion first (measured 2026-11-17, run 56e8c1ce):** liquidating critical Superfluid streams as an ordinary caller pays almost nothing (under 1 USD/week over six chains). The money goes to the **PIC** ("patrician in charge"), a seat per super token that anyone can take by posting a bond in the TOGA contract. On Base the USDCx seat received **113.69 USDCx in 28 days** against a bond of about 85-110 USDCx. The seat is open to strangers and outbidding is loss-free (fork-proven), but the bond leaves only as a stream over at least 7 days, so it fits neither rule L (one transaction, balance ends higher) nor the holding frame (sellable to USDC in one transaction at any time). It needs a human decision; lead recorded, no bot.

## Mechanism

- A stream sender pays a buffer deposit of `liquidationPeriod x flowRate`. Base USDCx: liquidationPeriod 14,400 s (4 h), patricianPeriod 1,800 s (30 min) (`governance.getPPPConfig(host, token)`, governance `0x55f7758dd99d5e185f4cc08d4ad95b71f598264d`).
- When the sender's balance reaches zero the stream is "critical" and anyone may delete it (`deleteFlow` through the host or the BatchLiquidator). The remaining deposit is the reward, reported by the super token's event `AgreementLiquidatedV2(address indexed agreementClass, bytes32 id, address indexed liquidatorAccount, address indexed targetAccount, address rewardAmountReceiver, uint256 rewardAmount, int256 targetAccountBalanceDelta, bytes liquidationTypeData)`, topic0 `0xb8381a3ce157650e06186e3e8f4dd4dc29236f2688b6eed1893d0a60d7c6386f`.
  - type 0, **patrician** (first 30 min): the reward goes to the governance reward address = TOGA, i.e. into the PIC's bond. The caller gets nothing.
  - type 1, **pleb** (30 min to 4 h): the caller gets what is left of the deposit.
  - type 2, **pirate** (insolvent): the caller gets the deposit, the shortfall is bailed out from the bond.
- **TOGA** (source: superfluid-org/protocol-monorepo `packages/ethereum-contracts/contracts/utils/TOGA.sol`): one PIC per super token. Anyone becomes PIC by sending the token to TOGA with ERC-777 `send(address,uint256,bytes)` and an amount **greater than the current bond** (`"TOGA: bid too low"` otherwise). In that same transaction the previous PIC receives its whole bond (including rewards accrued into it). `userData` = abi-encoded `int96 exitRate`, empty = default `bond / (4 x minBondDuration)`. The PIC takes value out only through the exit stream, at most `bond / minBondDuration` per second (`minBondDuration()` = 604,800 s = 7 days on Base), or by being outbid.
- The deployed Base TOGA has **no `bond()` function** (it is in the repository's dev branch only): a call reverts at 22,960 gas. Use the ERC-777 `send`.

## Addresses (Superfluid metadata `packages/metadata/networks.json`, checked with getters)

| chain | host | TOGA | BatchLiquidator |
|---|---|---|---|
| base | `0x4C073B3baB6d8826b8C5b229f3cfdC1eC6E47E74` | `0xA87F76e99f6C8Ff8996d14f550ceF47f193D9A09` | `0x6b008BAc0e5846cB5d9Ca02ca0e801fCbF88B6f9` |
| polygon | `0x3E14dC1b13c488a8d5D310918780c983bD5982E7` | `0x6AEAeE5Fd4D05A741723D752D30EE4D72690A8f7` | `0xA6Cdb472e7E22Bf30ae6fB752E4a13eBF3c12165` |
| optimism | `0x567c4B141ED61923967cA25Ef4906C8781069a10` | `0xA3c8502187fD7a7118eAD59dc811281448946C8f` | `0x36Df169DBf5CE3c6f58D46f0addeF58F01381232` |
| arbitrum | `0xCf8Acb4eF033efF16E8080aed4c7D5B9285D2192` | `0xFC63B7C762B10670Eda15cF3ca3970bCDB28C9eF` | `0x6C66e5c5D201A753ff497F2e9eC5D545631854d0` |

Base USDCx = `0xD04383398dD2426297da660F9CCA3d439AF9ce1b` (underlying = Base USDC `0x8335...2913`, 18 decimals, `upgrade` / `downgrade` 1:1). Only the Base rows were confirmed with getters this session (`host.getGovernance()`, `governance.getRewardAddress` = TOGA, `TOGA.getCurrentPICInfo`).

## Numbers

Source: the Superfluid protocol subgraph, keyless, 0 relay CU: `https://subgraph-endpoints.superfluid.dev/<network>/protocol-v1`, entity `agreementLiquidatedV2Events` (scripts `scratch/sf_subgraph.py`, `sf_value.py`, `sf_pic.py`, `sf_pipeline.py`). The subgraph does not index TOGA events on Base; those come from `eth_getLogs` on the TOGA address (`scratch/sf_toga_logs.py`).

**Callers (pleb / pirate), 7 days to 2026-11-17 17:4xZ:**

| chain | events | paid to callers |
|---|---|---|
| base | 34 (15 patrician, 18 pleb, 1 pirate) | 0.13 USD in priced tokens, plus unpriced launchpad tokens (PISSJUG, bee, JALLEO, YAAAYEAH, "Streme AIXBT": pure super tokens, no pool price) |
| optimism | 8 | 0.42 USD |
| polygon | 12 | under 0.01 USD in USDCx; 3 other tokens not priced (raw 0.51 / 0.05 / 0.006 units) |
| arbitrum | 6 | under 0.01 USD, plus 132 BORING (unpriced) |
| avalanche, bsc | 0 | 0 (same query shape returns rows on the four chains above) |

**PIC seat, Base, 28 days (patrician rewards by week, latest first):**

| token | rewards | current PIC | bond |
|---|---|---|---|
| USDCx | 10.84 / 0.50 / 81.75 / 20.60 = **113.69 USDCx** (44 events) | `0xac8f348159417a7caa4db74ee2071946dc64ea35` | 85.04 USDCx, exit 15.67 / day |
| ETHx | 0.000978 ETH, about 1.7 USD (24 events) | same | 0.0197 ETH |
| SUP | 387.9 SUP, about 1 USD (6 events) | same | 486.9 SUP |
| jEURx | 9.41 jEUR in one week, 2 events | `0xbe45a13121a247401fc7b50c0145ca37151adde0` | 0.055 jEUR |

One week is a poor guide: 72 pct of the 28-day USDCx total fell in a single week.

**What the incumbent does (just-in-time bid):** `0xac8f...` took the USDCx seat with a 101.49 USDCx bond (tx `0xfd2ba0164f7c6b2b87a54b374ce42f5adf90216053756ea030d4cd601c5a7f4e`, block 57,969,138), then 904 blocks = 181 s later sent the patrician liquidation itself (tx `0x02912ea539759883516da5cdb6d71dd34c0dbee1666acd921e769cdced676212`, block 57,970,042, reward 8.2185 USDCx into its bond), then set the exit stream to the maximum, 15.67 USDCx / day (tx `0xab72385c993956084f72fb36bf1faab4c5a77244fd929131d66bcc67cecdde5e`, block 58,055,608). That is 8.2 USD on about 101 USD tied up for a week. Another patrician liquidation that week was sent by a different address (`0x681c12eddec81e084be891825e9345c615a8147f`, tx `0xadf8cf57...`), so the PIC does not have to send every one itself.

**The timing is known in advance:** the subgraph gives each account's `maybeCriticalAtTimestamp`. Base USDCx at 2026-11-17 17:45Z: two accounts critical in 6.5 h with deposits 7.67 and 7.12 USDCx (`0x2d665e41...`, `0x3af199bd...`), one with 84.48 USDCx in 19.9 days (`0x082ff49c...`), one with 21.37 in 27.2 days (`0x60dc336a...`). Senders often top up before the critical time; then nothing is paid.

## Fork proof (Base fork reset at head 58,736,657, `scratch/sf_fork_proof.py`, output `scratch/sf_fork_proof2.out`)

A stranger with 400 USDC: `upgrade` to USDCx, then
- bid of half the current bond: **reverts** (status 0, 314,627 gas);
- bid of bond + 5 (90.0016 USDCx): **succeeds**, the stranger is PIC and the previous PIC received 85.0016 USDCx in that transaction;
- a second stranger bids 95.01 (`scratch/sf_fork_trace.py`, fork tx `0xb7724a70b71a926d8c3c249ada3c648ef52df896258637385c32416b3bc9c57c`): succeeds, and the first stranger ends with 309.998418 USDC + 90.001582 USDCx = 400.000000. Being outbid costs gas only.

Not explained: the same second bid sent back-to-back from the proof script (bond + 5, a few seconds after the first stranger's bid) reverted twice at 877,336 gas; sent about 40 s later it went through. Not traced. A patrician liquidation crediting the stranger's bond was not run on the fork.

## Why there is no bot

1. **Caller route**: under 1 USD/week over six chains, and the launchpad tokens have no exit. Dead end.
2. **PIC seat**: the bond (85 to 110 USD today, more in a bidding contest) leaves the wallet in one transaction and comes back as a stream over at least 7 days or when a rival outbids. Rule L wants the balance higher at the end of the same transaction; the holding frame wants a one-transaction exit to USDC and at most 100 USD. Neither holds. The economics are also contested: the seat belongs to whoever bid last before the liquidation, the incumbent watches the same critical times, and a contest is decided by who commits more capital in the last seconds.

If the human allows a "bond out, stream back within 7 days" exception, the smallest sensible version is: capital about 120 to 400 USD as USDC, bid a few minutes before a known critical time only when the deposit at stake is above a floor, set the exit rate to the maximum right after, and count the income as (rewards received while PIC) minus gas. Upper bound from the last 28 days: 4.06 USD/day if every USDCx reward on Base had been ours; a realistic share against the incumbent is unknown until tried.
