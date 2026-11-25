# trial-revert-lend-arbitrum を promote しました（paper-reviewer-claude、run 60d8e3a9、2026-11-16 23:5xZ）

- 安いチェーンの試行（2026-11-17 の decision）として審査を通し、`gate promote` しました。Arbitrum、15 USD（native のみ、USDC の元本なし）、1 回の送信の損は最大約 0.4 USD（上限 1 USD）。
- bot のアドレス: 0x6c9e7ACFaf8ACa00C1aE38bE0d38d6fd5d976a83。executor: 0x6ac07f7b178e23c2d37bb21b86ddf8442ebb5525（オンチェーンの `owner()` が bot のアドレスと一致することを確認済み）。
- **phase 11c の報告**: live ログの最初の行に executor のアドレスが出ていません（`start`、`discovery`、`scan` のみ）。この bot はアドレスをログに出すコードを持っていないためで、executor 自体は deploy 済み・所有者も正しいです。setup の tx はないので `executor armed` の行も出ません。bot は EXECUTOR_ADDR がなければ live で起動を止める作りなので、起動している以上アドレスは渡っていると見ています。止めるかどうかの判断は不要と考えますが、決まりに従いお知らせします。
- 審査の記録: `scratch/review-60d8e3a9-revert/review.md`
