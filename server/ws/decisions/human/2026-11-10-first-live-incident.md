# 2026-11-10 最初の live 2 本と、promote 時の不具合（記録と指示）

## 経緯（2026-11-09 17:20〜17:50Z）

1. paper-reviewer が franken-dutch-ethereum と gearbox-v3-watcher-ethereum を promote した。gate は bot に gas 代を送った直後、その送金がブロックに入る前に executor を配備しようとして、「残高 0」で失敗した。bot は live に移り、資金は入ったが executor がない状態で止まった（reviewer は正しく報告して promote を止めた）。
2. 人間が phase 9f（送金のレシートを待つ。途中で止まった promote を `gate-ctl deploy <id>` で再開できる）を入れ、2 本を deploy した。
3. watchdog は、配備のトランザクション（bot の鍵で gate が送ったもの）を signer の記録の中に見つけられず、「鍵の漏洩の可能性」として全体を halt し、bot を sweep した。**これは誤検知で、漏洩はない**（そのトランザクションは gate.log の deploy_executor そのもの）。
4. 人間が phase 9g（gate が配備と sweep を nonce 付きで記録し、watchdog がそれを既知のトランザクションとして扱う。watchdog の緊急停止で archive が失敗していた問題も修正）を入れた。そのうえで halt を解除し、franken に 100 USD を再度 fund した。

現在: live 2 本（franken-dutch-ethereum 約 100 USD、gearbox-v3-watcher-ethereum 約 96 USD）が active。frozen=false、halted=false。日次の損失 1.78 USD は配備の gas 代。

## 指示

- **live-operator**: inbox/live の `20261109T174418Z-watchdog.md` と `2026-11-09-franken-partial-promotion.md` は、上の経緯で解決済み（漏洩ではなかった。2 本とも executor を配備し、資金を入れた）。2 本は止めずに監視を続けること。累積損失 30 USD で停止する処理と、想定外の送信がないかを毎日確認すること。
- **paper-reviewer**: gate の promote は phase 9e〜9g で直った（manifest の読み取り、executor_args、送金を待ってから配備、watchdog の誤検知）。基準を満たしている bot（reserve-dutch-ethereum など）は、もう一度 promote してよい。中間ウォレットの ETH が足りないと gate が拒否したら、必要額を書いて inbox/human に出すこと。
- **meta**: inbox/meta の `2026-11-09-franken-gate-allowed-contracts.md` と `2026-11-09-franken-deploy-zero-balance.md` を解決済みとして RESOLVED.md に入れること。次回の報告から、live bot ごとの送信数・成功数・損益を数えること。
- 今後、gate が bot の鍵で送るトランザクションを追加する場合は、送った直後に nonce 付きで gate.log に記録すること（人間側の開発ルール）。
