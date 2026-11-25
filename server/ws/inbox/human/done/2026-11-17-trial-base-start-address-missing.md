# Base 試行 bot の起動ログに executor のアドレスがありません

2026-11-17 02:54 UTC の promote 後に確認しました。`trial-morpho-cbbtc-base` の `state/executor.json` は `0x41baa76e2c113b6d07950b2499d5b4dd960599b9`、`trial-aave4-base` は `0xe317f6985d5a4abc1c34b9f910beca6fbd143893` です。両方とも live の `start` 行はありますが、その行に executor アドレスが出ていません。サービスは稼働中です。コードは `EXECUTOR_ADDR` を読む形で、setup tx は不要なので `executor armed` 行の欠落は問題として数えていません。

paper-reviewer.md の promote 後確認規則に従う報告です。次の機会までに live の起動ログで使用中の executor アドレスを確認できるよう、meta にログ項目の修正を依頼してください。今回の promote と入金は完了しています。
