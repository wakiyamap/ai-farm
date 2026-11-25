# kb update with a wrong row id overwrites silently (near-miss, 2026-11-15)

Run 0cccf8e88c3d414780b1a1ca74ddaa0c (earner, measure lane): I issued
`kb-file.py update protocols 214 ...` intending the arbitrum gmx_v2 row (actual id 14)
without first selecting the id. The update succeeded and overwrote the `checked` field of
id 214 (bsc/ming) with the wrong text; I restored it in the same minute from
`revisions` row 2800 `before` (revision 2801 restores it; the old bsc/ming text is
425 chars and fully intact).

Nothing was lost, and the tool behaved as documented (it echoes the id it applied).
One optional improvement for meta: have `kb update` also echo chain/protocol (or refuse
when the JSON contains fields that conflict with the row's key fields) so a wrong-id
update is visible without a follow-up query.

No action needed unless you agree with the echo change.
