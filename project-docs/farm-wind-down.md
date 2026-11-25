# Farm をたたむ手順（2026-11-24 16:54 JST 人間の判断）

> 状態: 1〜5 は実施済み（5 のサービス停止は 11-25 01:08 に残りを止めて完了、`farm/ops/2026-11-25-0108.md`）。6・7 は人間。

## 判断

- 卒業の候補 4 本がすべてだめ（flatmoney / peapods / ethos / ryeth）。繰り返し取れる稼ぎは 1 日 1 USD 未満、運用費は約 15 USD/日。人間が「たたむ方向」と決めた（11-24 16:54）

## 順番（前の段が済んでから次へ）

1. **エージェントを止める**（新しい bot を作らせない・promote させない）
   - `sudo systemctl disable --now farm-builder-claude.timer farm-builder-opus.timer farm-meta.timer farm-paper-reviewer.timer farm-scout-enum.timer farm-scout@1.timer farm-scout@2.timer farm-scout@3.timer farm-scout@4.timer`
   - 走っている回があれば `sudo systemctl stop 'agent@*.service'`
2. **paper の bot を閉じる**: `sudo -u harness env PATH=/opt/farm/bin:$PATH paper archive vortex-auction-bsc --reason "wind-down 2026-11-24"`
3. **live の bot を全部止めて中間ウォレットに戻す**（signer・relay・watchdog はまだ動かしておく）
   - `for b in $(sudo ls /srv/farm/ws/bots/live); do sudo -u farmgate /opt/farm/bin/gate-ctl stop "$b"; done`
   - 終了コード 3（sweep が終わっていない）の bot はもう一度 `gate-ctl stop <id>`
   - 確認: `sudo -u harness /opt/farm/bin/gate status` で live 0、各 bot の残高 0
4. **中間ウォレットから自分のウォレットへ出金**（人間。11-16 の elysium と同じく本人の操作）。残高は `sudo -u harness /opt/farm/bin/gate intermediate`
5. **サービスを止める**（出金が済んでから）: watchdog、feed、relay、signer、dash、search、explorer、relayapi、hermes、fork@*、ledger-ingest、それに farm-nft と farm-acl-fix.timer。`stop` ではなく `disable --now`（再起動で戻らないように）。fork@* は `disable` がワイルドカードを受け付けないので `$(systemctl list-units --no-legend --plain 'fork@*' | awk '{print $1}')` で名前を渡す
   - 確認: `systemctl list-units --state=active --no-legend 'farm-*' 'bot@*' 'agent@*' 'paper@*' 'fork@*' 'rpc-relay*' 'ledger*'` と `systemctl list-unit-files --state=enabled --no-legend`（同じ並び）がどちらも空。active には waiting のタイマーと exited の oneshot も含まれる（`collect.sh` の稼働チェックも同じ数え方）
6. **外部の契約・鍵**（人間）
   - Blockscout Builder（月 49 USD）: 12-18 ごろの更新の前に解約
   - Alchemy: 使用が止まれば課金は増えない。鍵は失効させてもよい
   - Relay の API キー、Pyth Hermes の試用（12-01 ごろ自然に切れる）、Etherscan の鍵
   - Claude の使用クレジット（2027-05-17 まで残る）。月の上限はそのまま
7. **記録を残す**（任意）: `/srv/farm/ws` の kb/knowledge.db・wiki/・ledger/ledger.db・bots/archive を tar で手元に保存

## 残すかもしれないもの（人間が決める）

- trial-dfm-weekly-optimism（11-29 12:00 UTC の窓）、trial-flatmoney-arbitrum（12-01 ごろ鍵切れまで）。既定では全部止める（11-24 16:57 人間: 例外なく全部止める）
- qwen-server は Farm の外（16e で外した）。触らない
