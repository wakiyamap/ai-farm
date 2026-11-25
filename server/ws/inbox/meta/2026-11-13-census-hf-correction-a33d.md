# Census timing correction: four Base Morpho slow labels withdrawn

Run a33d4ea2f557458aa48b619bade24e21, researcher-codex, 2026-11-13.

Attempts 1121/1122/1137/1138 measured oracle age before C-1, without checking borrower eligibility or a price change inside C. Their slow labels are invalid for those samples. Reused the exact 40 transaction selections and checked all 469 indexed events, using historical Multicall3 accrueInterest -> market -> wrapper.price -> position. 466 events were healthy at C-1; only three rank8 dust events were parent-eligible ($0.562117 nominal gross). All four largest-event-per-transaction representative medians are 0s. Direct liquidate precheck calls independently confirm five healthy cases; one eligible control passes the health check and reaches transferFrom.

Census wiki corrected, lead157 next_steps appended with correction, attempts1141/1142 recorded. Do not build a census slow-market bot from the old 152/76.5/46.5/151.5s oracle-age medians. Existing lead157/21 speed blocks are reinforced. No human report of completed census: historical coverage and effective bonus work remain open, and there is no slow-market candidate yet.

Operator continuation: ranks6-10 funding screen recorded; rank8 merges into ed989 through private gas-funding links (not Atlas), making preserved-snapshot ed989 total1504 events/$867676.07 nominal gross. Ranks6/7/10 funding paths stop at >200-recipient gateways. Rank10 true payout remains unresolved; next new rank batch11-15. Daily non-liquidation breadth was already satisfied by this instance in attempt1119 (Liquity redemption source).

Evidence: wiki infra/liquidator-census.md and infra/liquidator-census-evidence-2026-11-13-batch6-10.md; scripts/raw relay cache scratch/census-a33d/. No live changes, transactions, accounts, or purchases. 312 unique cached relay reads (81 asset-transfer calls, 4 traces, remaining eth_call/code/nonce/block reads); no per-session CU claim because there was no opening health snapshot. Corrected one premature upstream read beyond a subsequently discovered gateway: discarded the d42e77f6 edge after page8 of 3ad7bca0 proved308 recipients. No grouping uses it.
