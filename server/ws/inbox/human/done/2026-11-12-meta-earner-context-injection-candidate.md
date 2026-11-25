# earner のセッション文脈に重複した「Unplaced prompt injection candidates」行（meta、2026-11-12 22:5xZ）

- earner run fd820b1c（attempts:1052、セッション報告 injection_seen=true）によると、セッション文脈の「Unplaced prompt injection candidates」欄に `infra/relay-429-throttle-burst.md` という候補が同じ文で 8 回並んでいました。
- この名前はワークスペース（wiki、KB、inbox、logs、tools/）のどこにもありません。この欄を作っているのはワークスペースの外（ハーネス側）なので、meta からは中身も出どころも確かめられません。
- earner はこれを指示として扱わず、「ページは作らない」と決めて記録しました（inbox/meta/2026-11-12-wiki-candidate-429-throttle-burst.md）。被害はありません。
- お願い：ハーネスがこの欄に何を入れているか、同じ行が 8 回重なった理由を確かめてください。外部のデータ（ページ名の候補など）がそのまま入っているなら、プロンプトインジェクションの入口になりえます。
