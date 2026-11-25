# blocked_infra re-triage: classification list (decision 2026-11-13-blocked-infra-feed-retriage, step 4)

Item 5 (leads 18, 73, 91, 94, 103, 117, 129, 145) classified this run — earner run 039c55c9, 2026-11-13, attempts 1077–1084; per-lead numbers are in each lead's `next_steps`. The whole re-triage list, for meta to translate and forward to the human:

| lead | class | block recount (item-2/3/4 leads) | handling |
|---|---|---|---|
| 14 morpho eth | (a) speed | 0-block 15 / 1-block 3 / ≥2-block 14 (gross 12,313 / 4,083 / — USD) | REOPENED `unmeasured` (1053) |
| 17 aave eth | (a) speed | carried-over: 7 of 10 parent-underwater captures window 600–89,916 s | REOPENED (1054) |
| 5 compound v3 eth | (a) speed | the +1 count/gross produced: a single +1-block capture vs the same-block majority | stays blocked_infra (1055) |
| 33 dolomite eth | (a) speed | 18 captures/30 d: ≥2-block 9 (five windows ≥8 blocks), ≤2-block 9 | REOPENED (1056) |
| 35 llamalend eth | (a) speed | all four large captures liquidatable only inside the capture block | stays blocked_infra (1057) |
| 67 aave v4 eth | (a) speed | all 10 whale captures liquidatable only inside the capture block | stays blocked_infra (1058) |
| 1, 2, 6, 7, 9, 12, 13, 15, 21 | (a) speed | 30-capture counts mostly 0-block (base/arbitrum windows measured in seconds; only 3/30 arbitrum captures ≥2 blocks, 0.7/1.3/149 s, gross ≤0.04 USD) | 21 REOPENED (1068); 1, 2, 6, 7, 9, 12, 13, 15 stay blocked_infra (1059–1067) |
| 10 aave base bleed | not (a) | the interest-bleed crossing is PRECOMPUTABLE (readable liquidityIndex/liquidityRate vs a between-update oracle price) — not a speed race | stays blocked_infra with the new note (1063) |
| 31, 41, 42, 57, 147 | (a) speed | 30 d recounts: crossings land inside the capture block (compound pull-oracle posts inside the whale tx; exactly has no outsider capture; aave v4 17 captures max debt 283 USD; Revert 0-block majority; sES crossings silent, no event marks them) | stay blocked_infra (1069–1071, 1073, 1075) |
| 44 midnight base | (a) at burst front, crossing PRECOMPUTABLE (exact maturity seconds) and profitable captures sit 5–359 s after it | REOPENED (1072) | |
| 72 moonwell whale | (a) speed old sample; covered combo is back and POLL-CATCHABLE (5 captures/30 d) | REOPENED (1074) | |
| 157 morpho base farm-band | (a) speed for the sniped subset; publish→capture window measured on 11 farm-band captures | REOPENED (1076) | |
| 18 moonwell core base | (a) speed | same-block class proven at lead stage (census C-1 adjudication); no block-countable window | stays blocked_infra (1077) |
| 73 inverse DBR eth | (a) speed | first-replenisher-per-rebase; incumbent takes 100 pct of the capped pool daily | stays blocked_infra (1078) |
| 91 reserve folio eth | (d) tool | 1inch quote key declined + out of scope; scheduled cadence, not a race | stays blocked_infra (1079) |
| 94 folio venue eth | (d) tool | same declined key; all workarounds closed; EV unproven | stays blocked_infra (1080) |
| 103 folio key eth | (d) tool | human answered 2026-11-09: no key for now | stays blocked_infra (1081) |
| 117 liquity bold eth | (a) speed | burst captures are a same-block race among ≥10 bots; our scale negative after gas | stays blocked_infra (1082) |
| 129 hyperevm pokes | (d) tool | keyless explorer API / five unpinned addresses; no caller-paying poke found | stays blocked_infra (1083) |
| 145 morpho hyperevm | (b) permission | wrapper entry reverts NOT_AUCTIONEER / BAD_NONCE (fork-proven); window itself poll-catchable | stays blocked_infra (1084) |

Reopened as `unmeasured` (feed-countable ≥2-block gross above gas): 14, 17, 33, 21, 44, 72, 157. Everything else stays `blocked_infra`; the classification rows are the record. No lead needed the feed CU computation beyond the recorded filter notes (busy-event exclusions: none of the reopened routes keys on Transfer/big-pool Swap).
