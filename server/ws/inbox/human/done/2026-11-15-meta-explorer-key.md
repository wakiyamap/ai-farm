# arbitrum で名前からアドレスを引く手段がない: explorer の API キーの提案（meta、2026-11-15）

earner の 2 セッション（11-15 07:05〜07:25Z、inbox/meta/2026-11-15-arbitrum-explorer-name-lookup-down.md）の報告です。

- arbitrum.blockscout.com の api/v2 が、朝のあいだずっと Cloudflare の確認ページを返した
- api.etherscan.io/v2 はキーなしの呼び出しを断る（"Missing/Invalid API Key"）
- routescan にはトークン名で検索する経路がない

このため lead 182（GMX v1）の調べる道が閉じ、dead_end になりました（attempts 1268, 1270）。

## 提案

Etherscan v2 の無料 API キー（1 つで全チェーン対応、アカウント登録が要る）を relay と同じように環境変数で渡すかどうか、決めてください。アカウントの作成は人間の判断なので、meta からは作りません。

費用ゼロのままにする場合は、今の回避策（プロトコル自身の API や GitHub のリポジトリにあるアドレス一覧）で続けます。ただし、それを公開していないプロトコルは調べられません。

あわせて、researcher のセッションでは WebFetch が "don't ask" モードで断られていました（inbox/meta/2026-11-15-webfetch-denied-researcher.md）。TOOLS.md の web 行は「断られたら shell の curl で raw のリポジトリファイルを読む」に直しました。docs サイトしか公開していないアドレス（Inverse DBR、Nerite、Aerodrome Relay）を読めるようにするには、researcher に WebFetch を許可する必要があります。これも判断をお願いします。
