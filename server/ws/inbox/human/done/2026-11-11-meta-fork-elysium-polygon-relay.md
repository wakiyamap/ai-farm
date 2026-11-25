# meta 35f952d9 (2026-11-11 08:3xZ): ワークスペース外の2件

## 1. elysium フォーク (9009): reset 直後の eth_call が `Excess blob gas not set.`
- 報告: inbox/meta/2026-11-11-anvil-excess-blob-gas.md (earner 44f81980)。`fork reset elysium <block>` の直後、relay から取得したヘッダに excessBlobGas が無く、anvil (hardfork Bpo1) が eth_call を拒否する。ローカルで1tx採掘すると直る。
- 回避策は TOOLS.md fork 行に記載済み (reset/replay 後に `fork fund-token ... 1`)。
- お願い: fork ツール側で elysium の取得ヘッダに excessBlobGas=0 を補う、または elysium の anvil を blob 前の hardfork で起動する。

## 2. polygon: relay の eth_blockNumber が2つのヘッドを交互に返す
- 報告: inbox/meta/2026-11-11-polygon-getlogs-intermittent-empty.md (earner 19a3e1cf, 06:5x-07:0xZ)。~97116700 と、それより 31,000 ブロック先の 97148117 が交互に返り、同じ時間帯にキャッシュヘッドより下の範囲の eth_getLogs が `[]` を返した。
- meta 08:2xZ の relay-probe では正常 (polygon topic-only 965 件, 最多 emitter 617=617, range 66=66; ヘッド 97119583 で、31k 先のヘッドはもう見えない)。bsc の topic 付き `[]` (06:1xZ 再発) も 08:2xZ は正常 (145 件, 51=51, range 30=30)。
- お願い: 06:5x-07:0xZ の polygon プロバイダログを確認し、ヘッドが大きくずれたノード (別チェーン/異常ノードの可能性) を外す。空の応答をキャッシュしているかも確認してほしい。

これまでの bsc/polygon の空応答は earner に「同じ実行・同じ形・同じ範囲のコントロールが返したときだけゼロを数える」と TOOLS.md で指示済み。
