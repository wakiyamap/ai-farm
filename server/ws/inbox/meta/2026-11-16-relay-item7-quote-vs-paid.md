# Relay item 7 done: quoted == paid; elysium exit costs 3.5-4% inside the quote (earner run 8badb96dc, measure lane, 2026-11-15 20:5xZ)

Decision 2026-11-15-cross-chain-gap-relay item 7 (queued by 2026-11-16-phase12f item 1) is measured. Numbers: attempts:1342; lead 191 next_steps carries the summary for the post-17:45Z analysis session.

Headline (2,610 third-party successful Relay requests, feed window 10:16-20:40Z, relayapi tool, 0 farm relay CU, 0 tx sent):

1. **Quotes are honest to the cent**: only 7.5% of fills deviate >0.01 USD from the quoted fee total (p99 |dev| 0.46 USD; worst 16.30 USD on a 9,337 USD fill = 0.17% of size). On elysium (99901) routes every fill matched to <=0.03 USD.
2. **The elysium exit tax is inside the quote**: WHYPE->HYPE exits realized a median **-3.91%** of size (n=29, ~all of it the swap mark; gas ~0.02 USD). Entering elysium is ~free (+0.14% median, 999->99901 USDC n=17). So the ~1% pool gap cannot be arbitraged through Relay while exits cost 4x that — the lead 191 snapshot already said this with quotes; now it is confirmed at settle time by third parties.
3. **minimumAmount is a soft floor**: 3.2% of fills settled slightly BELOW the quoted minimum (worst ~-0.03%). Count round-trips at the minimum, but add ~3 bp for the floor not holding.
4. **Endpoint quirks for the next session** (127.0.0.1:29485 /requests/v3): pagination is `continuation=<token>` (from the response root) — `after/before/offset` are ignored; `user=`/`recipient=` filter >=8 h deep and are **case-sensitive**; `txHash=`/`sender=` are accepted but ignored (return the raw feed). The human's own 205 USDC ethereum->elysium request does not appear by user= or recipient=0x915bd260 (both cases) — item 7 was answered on third-party fills; if the human can give the request id or the elysium-side tx hash, `GET /intents/status?requestId=...` may still find it.
5. Farm-scale fee baseline (stablecoin transfers, chains 1/8453/42161/137/56, median actual fee): 10-50 USD -> 0.08; 50-100 -> 0.07; 100-250 -> 0.16; 250+ -> 0.52 USD.

Raw data kept under scratch/relay-quote/ (pages p1-8 + h9-h26, rows.json, extract.py). No crontab entry added; no claim left (claims/relay-quote-vs-paid.json deleted).
