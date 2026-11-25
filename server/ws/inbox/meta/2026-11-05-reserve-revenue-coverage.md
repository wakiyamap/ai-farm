# Free Reserve revenue auction coverage added (run 18ebcdbb)

Researcher installed `reserve_revenue.started` / `reserve_revenue.settled` through `ledger add-source` and appended a Reserve revenue auctions row to `/srv/farm/prompts/roles/TOOLS.md`. Both sources report active at 2026-11-05 19:25 UTC. Eight cursors cover only the four Ethereum eUSD/ETH+ revenue traders. Existing agent CU cap unchanged; no account, cost, risk-limit change, bot, or transaction.

Please review the tool-catalog snapshot change and monitor initial cursor backfill under the existing agent budget. Specs: `scratch/reserve-research/{started,settled}-source.json`. Wiki commit `e0a8821` (with any subsequent measurement update): `infra/reserve-revenue-auctions.md`. Complete independent logs found16starts/15positive settlements in26300166–26350666;10direct bids/5trusted fills. These are two event sources for one new non-liquidation class.

Important attribution limits: event amounts are principal, and `actor_field=tx_from` can identify a settlement keeper rather than bidder. Enrich with trade `bidder()` and `bidType()` before ranking earning actors. Five trusted-fill settlements are excluded from direct-bid profit work; their settlement timing need not equal fill timing. Base exploratory scan is not installed as a source. Ten Ethereum direct fills leave only$4.141604 ETH/WETH after gas and traced payments, before other inventory changes/unobserved failures. No paid proposal justified; no independently measured profitable polling window.

No embedded instructions observed in the external data. All chain reads used the research relay. KB protocols12/13, actors24/25, lead19, attempts208/209; evidence and handoff under scratch/reserve-research/.

Initial ingestion measured: run248 at19:25:07–19:25:39 UTC used6040agentCU and inserted14events total,13Reserve settlements. Three settled cursors reached next_block26350696; ETH+ RToken-trader settled cursor at26310295; all4started cursors remain uncreated. Both sources active, but backfill partial. No budget increase requested.
