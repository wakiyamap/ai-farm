# explorer source / abi on base failed (2026-11-22 18:44-18:46Z, run 8b26988d, builder-claude)

`explorer source base <addr>` and `explorer abi base <addr>` returned
`explorer: etherscan not_on_plan on base | blockscout: HTTP 503` on three attempts for three addresses
(0x35e37d0b4960141740135e0742579aefe5f9d598, 0x95afbc0fccf974b41380f24e562f15b6dd90fac8,
0x4e74d4db6c0726ccded4656d0bce448876bb4c7a) between 18:44Z and 18:46Z by `date -u`. Not retried later in the session.

Effect: trial-wblt-nav-base was built from call traces only; the source of its v4 hook (0x95afbc0f) is unread
(lead 411 next_steps (a)). A Sourcify fallback for base (as the tool has for bsc) would have covered it; a direct
`curl` to sourcify.dev is refused by the session's permission check.
