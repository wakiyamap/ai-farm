# Paper review file blocked by bot directory ACL

Run `03c8763a7fc145fd89c67c660e037ae0` archived `moonwell-whale3-base` as a closed route (lead 72 `dead_end`, `attempts:1110` after `paper_placed` 1108). The reason is in `bots/archive/moonwell-whale3-base/ARCHIVE.md` and `attempts:1112`.

I could not create the required `bots/paper/moonwell-whale3-base/review.md` before archiving: the directory was owned by `earner:farm` with ACL `mask::r-x`, so group write was ineffective. `apply_patch` failed. The archive is read-only. Please have the paper placement path grant reviewer write permission for `review.md` or create it with a writable ACL at placement. No bot code was changed.
