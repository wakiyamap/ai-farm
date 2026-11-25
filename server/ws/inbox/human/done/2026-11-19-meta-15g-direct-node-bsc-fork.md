# meta 0facbcb2 (2026-11-19 03:3x-04:0xZ): 15g 反映、ノード直読みルール、bsc フォークの非アーカイブ上流

## 1. phase 15g(signer tip 0)への対応 — 完了
- TOOLS.md の signer 行から「tip 0 は maxFee/10、1 を渡せ」を削除(TOOLS.md 16959 → 16881 B)。
- wiki `pitfalls/signer-zero-priority-fee.md` を「修正済み(11-18 ~23:10Z)」に更新。それ以前に起動した live bot は再起動まで旧挙動、と明記。

## 2. ノード直読み — scout.md を明文化、違反数
- scout.md(読み取り手段の行)に1文追加:「チェーン読み取りはすべて `rpc.py` 経由。`curl` やスクリプトでノード(`bsc-dataseed`、`publicnode` 等の公開 RPC 含む)を叩かない。relay に provider が無ければ verdict は `unclear` で次へ」。
- builder.md にも同趣旨の1文を追加(理由: scout だけでなくビルダーのスクリプトにも公開ノード直書きがあった)。
- 11-18 の違反(scratch のスクリプトとご指摘から数えた下限):
  - `scratch/avalon-bsc/scan2-4.py`(15:45-15:52Z、bsc-rpc.publicnode.com / bsc-dataseed.binance.org)
  - `scratch/fluid_scan.py`, `fluid_probe.py`, `fluid_backprobe.py`, `probe1.py`(19:55-20:06Z、polygon publicnode / llamarpc / drpc。lead 280 関連のビルダー作業)
  - ご指摘の scout 2件(bsc-dataseed、~21Z bsc publicnode。1件目は上記 avalon-bsc と同一の可能性あり)
  - → 11-18 は少なくとも 3 セッション。次回の meta で、本日 04:00Z 以降に作られた scratch ファイル中の公開ノード URL を同じ方法で数えて報告します(目標 0)。
- プロンプトサイズ: scout 39460、builder 51543、earner 55908、paper-reviewer 53102(すべて ≤56000)。

## 3. お願い(ワークスペース外): bsc フォークレーンの上流
- builder-claude c6a6f716(11-19 00:00Z): 4日前のブロックに reset した bsc フォークで、fork レーンが新しい日(111k CU)なのに `missing trie node` が出たり出なかったりし、同じ呼び出しが数秒後に成功。fork が一度 `bsc down` に。research レーンは同じスロットを正常に返した。
- fork レーンの bsc 上流のどれかが非アーカイブノードと思われます。**フォーク用の bsc provider から非アーカイブのものを外していただけますか。** 回避策(RPC エラー時に1回リトライ、エラーを revert と数えない)は wiki `pitfalls/fork-past-state-public-nodes.md` に追記済み。

## 4. 参考
- base の Blockscout タイムアウト(11-18 ~22Z、scout 32ead678)は一時的でした。11-19 03:4xZ に `explorer txs base` は即応答。wiki `infra/explorer.md` にリトライと relay での代替を追記。なお同 scout は base.blockscout.com を User-Agent 付きで直接叩いていました(既存ルールで禁止済み、wiki に再掲)。
- gate: live 34、本日損失 0、capital 1025.78 USD、14日間無動作の bot なし(最古の live は 11-12 頃)。
