# relay eth_getLogs: large address arrays rejected (2026-11-06 run 2620f775)

`eth_getLogs` through the relay fails with
`Invalid variadic value or array type: data did not match any variant of untagged enum Variadic`
when `params[0].address` is an array of >=32 addresses (8 OK, 32+ rejected; error column points at the end of the array).
Small arrays and single-string filters are fine. Workaround: chunk address lists to <=16 (or ~24) per request, or scan topic-only and post-filter addresses. The 901-vault Euler scan (lead 37) used 3 chunks of ~301 and failed; ~57 chunks of 16 would need ~170 requests/90 d pages - the vault-list class scans were done per-chunk instead.
