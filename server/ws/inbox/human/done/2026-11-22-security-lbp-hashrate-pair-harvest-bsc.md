# セキュリティ所見（低額・未検証）: BSC の LBP / hLBP、pair 名義の採掘報酬を誰でも引き出せる

- 書いた人: builder-claude（run ef082019、2026-11-22 20:44Z）
- 扱い: S により farm では取らない。mainnet では何も送っていない（読んだのは receipt、trace、公開ソース、`balanceOf` 1 回だけ）。fork でも試していない。
- 人間にお願いすること: 特になし（記録のみ）。プロジェクトへの連絡が必要と判断される場合の材料です。

## 何が起きているか

- トークン: LBP `0x88886f0fd371dff856291badced45922bc888888`、hashrate トークン hLBP（`LBPHashrate`）`0x5e3cbc82d020be91a989eb747934104e9ab585fe`、PancakeSwap V2 の LBP / USDT pair `0x00e3ea08fd8cbad955ec5d2292ad637670c31524`（いずれも Sourcify で検証済みソース）。
- ソースの前提: LBP.sol に「pair holds no hashrate by design invariant」と書かれている。実際は pair が hLBP を 1.07e25（約 1,073 万）持っている（`balanceOf`、block 135,144,7xx 付近）。前提が崩れている。
- hLBP の `_update` は、送金のたびに `from` の `_harvest` を先に走らせる。OpenZeppelin の `transferFrom` は金額 0 なら allowance なしで通るので、誰でも `transferFrom(pair, 0xdead, 0)` を呼べば pair 名義の採掘報酬（LBP）が pair に直接 mint される（紹介者 3 アドレスにも mint）。
- pair の残高が reserve より多くなるので、同じ transaction で `pair.swap()` を呼ぶと、その分の USDT を持ち出せる。
- これを 1 つの EOA `0xa871898257d73b0d9766379b24bd95a8ded44110` が専用コントラクト `0xa5a207f39aa47ebd683c28308791262ebef69cf7`（selector `0x01118f40`、送信者が immutable で埋め込み）で繰り返している。例: tx `0xee4cba2f16c9360e3c4f0a834be5a04c1dc4205cdbdca039915c7877b36a2777`（block 135,144,736）で 0.0182 USDT を受け取り、gas は 1.13e-5 BNB。block 135,132,755-135,144,755（約 1.5 時間）に LBP の mint を含む transaction は 162 本（サンプル 2 本はどちらもこの経路。全数は未確認）。1 日あたり数十 USD の規模の見込み（推定、未計測）。

## なぜ farm は取らないか

- プロトコルが「誰にでも払う」と決めた報酬ではない。設計上は起きないはずの状態（pair が hashrate を持つ）に乗って、LP の持ち分になるはずの LBP を USDT に替えて持ち出す形で、S の「バグを使って資金を取らない」に当たると判断した（確信はないので「不明は不可」の扱い）。
- pair に hLBP を入れたのが誰か（運営か、この EOA 自身か）は調べていない。運営自身の回収経路である可能性もある。

## 記録

- KB: attempts（この run の dead_end_recorded 行、target「LBP / hLBP pair-harvest on BSC」）。
- 見つけ方: BSC の mint census（`scratch/ref08/mintcensus.py bsc 12000 60 3 2000 160`）。
