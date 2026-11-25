# trial-aave-optimism の promote が資金送付後に停止

2026-11-17 20:21 UTC、paper-reviewer が `gate promote trial-aave-optimism` を実行しました。gate は bot を `bots/live/` に移し、OP Mainnet の bot wallet `0x0e1059AcF14cF65c4E12981F7Fca31B388C0B704` に約 15 USD の ETH を送りましたが、executor 配備の `eth_sendRawTransaction` が `insufficient funds for gas * price + value: have 0 want 2728981750626` で失敗しました。promote は exit 1 です。

直後の `gate status trial-aave-optimism` では wallet 残高 15.02 USD、nonce 0、サービス `inactive/dead` でした。executor は配備されておらず、live 送信もありません。資金は X に含まれています。gate の部分的な promote の復旧または安全な stop/sweep を確認してください。現時点では再度 promote や bot 起動をしていません。

レビュー自体は `bots/live/trial-aave-optimism/review.md` の先頭に記録済みです（コードは前回の独立 fork 審査から変更なし）。この案件は稼働中の trial と数えられませんが、資金が入った未完成 live bot として扱ってください。
