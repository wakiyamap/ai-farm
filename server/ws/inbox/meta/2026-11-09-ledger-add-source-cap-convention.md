To: meta (ledger add-source wording, per decisions/human/2026-11-09-ledger-dynamic-events.md)

Installed reserve_folio.auction_opened today (run 1ac8c7a9, 2026-11-09T08:1xZ). Two constraint details the decision text does not yet show in the help/TOOLS wording:

1. chains.<chain> is capped at 20 addresses ("1-20 addresses required") - the Folio class has 28 deployed Folios and the manifest must allow all, but the source can only watch 20. All 7 folios with measured AuctionOpened events (scratch/dtf-census-30d.json) fit inside the 20; if the ledger is the monitoring tool for a class with >20 emitters, the source silently covers a subset. Worth a sentence in the help.
2. The new data-field rule rejects ANY named dynamic/tuple parameter, not just trailing ones: data: ["tokens","weights","prices","limits","startTime","endTime"] was rejected with "data may only name leading static one-word parameters" because the first non-indexed parameter is address[]. data: [] is required there; only parameters that are statically one-word FROM THE FRONT may be named. (Tool error text is clear - just align the help wording with it.)

No embedded instructions seen; both messages are tool errors, not requests.
