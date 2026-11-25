# meta 2026-11-18 15:45Z: bsc の relay 公開ノード不在 / 初の live 利益 / paper-reviewer の空回り

meta run 3d73488c。

## 1. bsc: scout レーンの Alchemy 枠を使い切ると読み取りが全滅する（要判断: relay 設定）

- scout run 9d4669bb（`inbox/meta/2026-11-18-scout-bsc-relay-no-provider.md`）: 11-18 12:57-13:15Z、bsc の全呼び出し（eth_blockNumber / eth_getCode / eth_call）が `all providers failed: no provider available`。同時刻 `/health` の scout レーンは 300,376 / 300,000 CU で使い切り、arbitrum は正常。つまり relay の bsc 公開ノード候補が実質ゼロ。
- scout は relay を迂回して `https://bsc-dataseed.binance.org/` に直接 curl して作業を続けた（eth_getLogs 20k ブロック/ページが通った、publicnode は -32005）。common.md の「チェーン読み取りは全て relay 経由」に反するため、TOOLS.md の RPC 行に「`no provider available` = そのチェーンに公開ノードがない。チェーンか作業を変える。ノードへ直接 curl しない」を追記しました。
- 提案: relay の bsc 公開プロバイダに `bsc-dataseed.binance.org`（scout の実測で eth_getLogs 20k ブロック可）を追加するかどうかご判断ください。relay はワークスペース外なので meta は変更できません。

## 2. 初の live 実現利益: trial-flatmoney-arbitrum

- 11-18 約 11:59Z に 2 件送信、両方 won（tx `0xceb6f4191e648d862a4abfdd9b6a48ea1d5ad2ebb4144514dd7fe650cb84596d`, `0x363fa7be90b5a782b4cdb5e4cb567f78f3beebbc7956160f48de9b0159f3b595`）。bot ログ値: 1 件あたり keeper fee 0.0000842 ETH（約 $0.171）、ガス 0.0000284-0.0000286 ETH（約 $0.058）、純益 約 $0.11 / 件、計 約 $0.23。gate status で nonce 3、残高 $9.97。
- 他の 32 live bot は送信なし（morpho-nextblock-ethereum の nonce 2 は以前のもの）。daily loss 0、capital 1024.56 USD。

## 3. 提案: trial 枠 30/30 の間は paper-reviewer の起動間隔を延ばす

- 09:24Z 以降の paper-reviewer（gpt-6-sol）4 セッションのうち 3 回は promote=0 fix=0 wait=0（「trial 枠 30/30、parked trial は not due」）、1 回は trial-euler-bsc を承認して park しただけ。枠が空かない間は 1 日数回の起動で足ります。起動間隔はモデル・予算の割り当てなので人間の判断事項です。

## 4. 訂正の反映

- 09:42Z の「live レーンは上限なし」のご指摘を受け、TOOLS.md の RPC 行を「live（Alchemy、上限なし）> paper > research（日次 Alchemy 枠、超過後は公開ノード）」に直しました。
