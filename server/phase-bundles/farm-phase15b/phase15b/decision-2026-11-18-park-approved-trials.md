# 審査済みで live の枠だけを待つ試行の bot は、paper を止めて並ばせる（人間の判断 2026-11-18）

2026-11-18 05:28 JST の時点で paper は 12/12 が埋まり、そのうち 11 本は審査を通って live の試行の枠（10 本）が空くのを待っているだけだった。このため builder が作った新しい bot が `paper start` を断られ、次の審査にも進めない。次のとおりにする。

1. **対象**: 試行の bot（`2026-11-17-cheap-chain-trials.md`）のうち、技術審査を通っていて、待っている理由が live の試行の枠だけのもの。ほかの理由（修正待ち、paper での確認待ちなど）で wait にしている bot は対象外で、今までどおり paper で動かす。
2. **paper-reviewer がすること**: 対象の bot の判定を `wait (parked: approved, waiting for a live trial slot)` と書き、`paper stop <id>` で paper のサービスを止める。ディレクトリと review.md はそのまま残す（archive しない）。止めた bot は paper の 12 枠に数えない。`next_review_at` は今までどおり書き、そのときに枠を確かめる。
3. **promote**: `gate promote` は止まっている paper bot からでもできる（gate は paper のサービスの状態を見ない）。live の試行の枠が空いたら、並んでいる bot から promote する。順番は審査を通った時刻の古い順。人間が順番を指定したときはそれに従う。
4. **並んでいる bot は paper で動かし直さない**（builder も meta も）。コードや manifest を変えた bot は審査し直す。そのとき paper での実行が要るなら、空いている枠で `paper start` してよい。
5. 試行の bot では自然キャプチャは要らない（11-17 の判断のまま）。並んでいるあいだの paper の記録がないことを、promote を止める理由にしない。
6. trial-euler-base はすでに審査を通っていて、live の枠を待っている。paper を始めなくても、並んでいる bot として扱う。
7. 空いた paper の枠は、builder が作った新しい bot に使う。
8. meta: paper-reviewer.md（Capacity）、builder.md、TOOLS.md（paper-reviewer は `paper stop` も使う）に反映すること。paper-reviewer-claude の Bash の許可には、phase 15b で `paper stop` を足した（codex の reviewer はこの許可の一覧を使わない）。
