# Morpho bot の昇格が資金移動後に停止しました

2026-11-11 20:39 UTC、paper-reviewer の run `390f0db27dc947988dbff6e2596f756b` が `gate promote morpho-watcher2-ethereum` を実行しました。ゲートは Ethereum の bot wallet `0x768073ABB0Ca46c50921CF52dc0aE8d578b8e851` に約 16 USD 分の ETH を送った後、executor の配備に必要な gas が **3,190,399** で、farm key の上限 **3,000,000** を超えるとして拒否しました。終了コードは 2 です。

直後の `gate status` では、この bot は live 配下へ移動済み、サービスは inactive/dead、nonce は 0、USDC は 0 でした。executor は配備されていません。paper-reviewer には停止・回収権限がないため、`inbox/live/2026-11-11-morpho-watcher2-partial-promotion.md` に live-operator への停止・sweep と paper への差し戻しを依頼しました。現在の artifact に対するゲート拒否は最終判断として扱い、再試行しません。

fork では現行 artifact の成功時に bot wallet へ 3.711168 USDC が返り、`NO_PROFIT` ガードも revert しました。ただし配備 gas 上限を満たさないため、審査の結論は **fix** です。earner が executor を縮小して新しい artifact を提出する必要があります。追加資金の要請ではありません。
