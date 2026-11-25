# 2026-11-06 ethereum の中間ウォレットに入金した（paper-reviewer / earner / meta へ）

- ethereum の中間ウォレットに USDC 400 とガス用 ETH を入れた。`gate status` の `intermediate_balances_usd` の `ethereum` / `ethereum:usdc` で確認できる。
- これで `gate promote` の「intermediate wallet on ethereum has less than … deposit first」は出なくなる。cv3-buy-watcher-ethereum など `principal_usdc` を使う bot の promote 条件は、資金以外のブロッカー（自然発生した機会の実捕捉、独立再現）だけになった。
- 初回の promote は decisions/human/2026-11-05-phase7-usdc.md の手順どおり小額（principal_usdc 50 程度）で、`gate status <id>` → 1 回の動作 → `gate stop <id>` で USDC とネイティブが中間ウォレットに戻り PnL が記録されることまで確認してから、本来の額で promote し直すこと。
- Base / Arbitrum の中間ウォレットは従来どおり（ガス用 ETH のみ）。
