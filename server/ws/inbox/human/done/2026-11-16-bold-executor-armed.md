# bold-redeem-tail-ethereum: 起動ログの確認

2026-11-16 18:56 UTC に gate promote が成功し、30 USD の ETH が入金されました。`state/executor.json` の executor `0x809cf62b6f55b00ce9cb0536920dfbc7d3e6f8b0` は live ログの `start.exec` と一致します。

起動ログには `executor armed` 行がありません。別の準備 tx は不要な設計ですが、paper-reviewer の昇格後確認規則に従い報告します。また live ログで signer の wallet address が辞書として返ることが分かり、bot がそのまま JSON-RPC の `from` に渡す不具合も見つかりました。送信前の simulation が失敗するため、緊急連絡を `inbox/live/2026-11-16-bold-live-from-object.md` に残しました。18:57 UTC 時点では機会への送信はありません。
