# phase 15g and answers to your note of 2026-11-18 22:xx (run 096358ac) (human, 2026-11-19)

1. **Signer priority fee 0**: fixed in `/opt/farm/lib/farmbot_signer.py` (phase 15g). An explicit `max_priority_fee_per_gas=0` now stays 0; only a missing value (None) gets maxFee/10. A running bot keeps the old code until it is restarted, so it takes effect for bots started after 2026-11-19 ~08:10 JST (new promotions, restarts). The human does not restart the live bots for this. You may drop the "pass 1, not 0" line from TOOLS.md and mark the wiki pitfall as fixed.
2. **Auto-expiring claims of no_report runs in the harness**: not now. Your builder.md rule (a claim of a run with a logs/sessions line is void) is enough until the 11-24 decision.
3. **bsc getLogs after the scout lane is spent**: status quo (c). Most bsc protocols are dead_end; no relay exception. Judge bsc candidates by state getters, as in the wiki.
4. **HyperEVM HYPE**: sent; the hyperevm intermediate wallet holds about 38 USD.

Also: scouts have now twice read a public bsc node directly (curl to bsc-dataseed.binance.org on 11-18, to bsc-rpc.publicnode.com on 11-18 ~21Z). Please make the rule in scout.md explicit and short (all chain reads through the relay; when the relay has no provider, record `unclear` and move on) and count violations in your next report.
