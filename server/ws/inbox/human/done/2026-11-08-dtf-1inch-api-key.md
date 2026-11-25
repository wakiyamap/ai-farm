# reserve-folio-dtf-ethereum: 1inch APIキーのお願い (2026-11-08)

DTF リバランスオークションの bid 経路は、落札者が使う 1inch Fusion 経由の swap 脚（スワッパー 0x6131b5fae19ea4f9d964eac0408e4408b66337b5）をそのまま使います。その脚（calldata）と見積りは 1inch のオフチェーン API（https://api.1inch.com/v1.1/1/fusion-v1/swap）からのみ取得できますが、キーなしだと 401 が返ります（試測: scratch/dtf96-401.txt、2026-11-08）。

- お願い: 1inch の開発者 API キー（無料枠）を 1 本発行し、`bots/paper/reserve-folio-dtf-ethereum/state/fusion_key.json` に `{"key": "..."}` で置いてください（live 昇格時は gate が同じ場所に置く想定）。
- キーがあるまで bot は fail-closed（見積りなし → send なし）で、paper ログに sim 記録が出ません（審査 2026-11-08T19:05Z blocker 3 の理由）。キー入手後、real venue 脚の fork 証明と paper capture 審査が続きます。
- 費用: 無料枠で足りる見込み（1 日あたり数リクエスト〜数十）。無料枠で不足したらその時に有料プランの相談をします。
