# trial-morpho-eth-base の Base ガス資金

2026-11-17 02:55 UTC、paper-reviewer の審査では cheap-chain trial の条件を満たしました。fork で利益のある成功（bot wallet に +0.604823 USDC）と、利益不足時に全体が revert することを再現しました。`gate promote trial-morpho-eth-base` は資金を動かす前に exit 2 で「intermediate wallet on base has less than 18.00 USD + gas; deposit first」と拒否しました。直前の `gate status` では Base のネイティブ残高は約 11.63 USD です。

必要なのは少なくとも 6.37 USD と executor 配備用ガスの余裕です。入金は人間の判断です。bot は paper のままで、`review.md` の再確認時刻を 2026-11-17 05:00 UTC にしました。今回の拒否では bot への入金も executor の配備もありません。
