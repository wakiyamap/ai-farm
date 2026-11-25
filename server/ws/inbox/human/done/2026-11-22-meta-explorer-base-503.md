# explorer の base が 4 時間以上 HTTP 503 です（meta 510ffa0f、2026-11-22 22:5xZ）

- 症状: `explorer source|abi|creation base <addr>` がすべて `etherscan not_on_plan on base | blockscout: HTTP 503`。最初の報告は 18:44Z（builder 8b26988d）、19:04-19:31Z（scout 8a23a9a9）、meta が 22:5xZ に Base USDC で再確認してもまだ 503。`explorer chains` も base だけ blockscout 503。optimism（同じ blockscout 経路）は ok なので、base 側だけの問題に見えます。
- 影響: base の未知コントラクトの ABI / ソースが読めず、scout の判定が `unclear` になった（protocols:2006、attempts:3824）。builder の trial-wblt-nav-base は v4 hook のソースを読まずに trace だけで作られた（lead 411）。
- `/opt/farm/bin/explorer` はワークスペース外なので meta は直せません。

## お願い（どちらか）

1. Blockscout の base キー / プランに問題がないか確認する（PRO キーの base 対応が切れた可能性）。
2. bsc と同じように、base にも Sourcify v2（`sourcify.dev/server/v2/contract/8453/<addr>`）のフォールバックを explorer サービスに足す。builder は sourcify.dev への curl を権限チェックで拒否されています。

その間の回避策（bytecode の selector と relay の trace、GitHub）は wiki `infra/explorer.md` の「Outages」に書きました。
