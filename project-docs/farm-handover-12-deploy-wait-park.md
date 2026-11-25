# 引き継ぎ書 12: phase 15b（executor 配備の待ち、審査済みの試行を paper から外す）2026-11-18

本体は `farm/farm-handover.md`。この文書は 15b の変更だけ。バンドルは `farm/phase15b/`。**2026-11-18 05:40 JST に適用済み。**

## gate-ctl: `send_deploy()`（executor の配備）

- きっかけ: 11-17 20:21Z、trial-aave-optimism の promote。送金のレシートは見えた（9f）のに、配備の送信を受けたノードが古い残高を読んで `insufficient funds ... have 0` を返した。資金だけ入って executor のない live bot になり、`gate-ctl deploy` で復旧した
- 変更: `deploy_executor()` の送信を `send_deploy()` に通す（promote と deploy の両方）
  - bot の wallet が配備の最悪ガス（gas×1.2×maxFee）以上を読むまで待つ
  - ノードが "insufficient funds" を返す間は、同じ署名済みのバイト列を送り直す（受け付けられていないので nonce は使われていない）
  - ほかの送信エラーは今までどおりそのまま上げる
  - 3 秒おき 20 回（1 分）で諦める。bot の鍵からは何も送らず、gate.log に `deploy_executor_not_sent`、終了コード 2。今までどおりの部分 promote として `gate-ctl deploy <id>` で再開する
- watchdog の変更は要らない（送っていない tx に nonce はない）

## run-role

- paper-reviewer-claude の Bash の許可に `Bash(paper stop *)` を足した（`Bash(paper archive *)` の後ろ）。codex の reviewer はこの一覧を使わない

## decision: 審査済みで live の枠だけを待つ試行の bot は paper を止めて並ばせる

- `decisions/human/2026-11-18-park-approved-trials.md`
- reviewer は判定を `wait (parked: approved, waiting for a live trial slot)` と書いて `paper stop`。ディレクトリと review.md は残し、paper の 12 枠に数えない
- `gate promote` は止まった paper bot からでもできる（gate は paper のサービスの状態を見ない）。枠が空いたら、審査を通った時刻の古い順に promote する
- 並んでいる bot は paper で動かし直さない。trial-euler-base はすでに並んでいる扱い
- meta に paper-reviewer.md・builder.md・TOOLS.md への反映を依頼（`inbox/meta/2026-11-18-phase15b-deploy-wait-park.md`）

## 確かめ方

- install.sh: 12d 後の gate-ctl・14d 後の run-role の sha256 を参考値として表示する。適用するかどうかはテキストパッチで決める（どれも 1 回だけ一致すること）。オフラインのテスト 6 件（適用前は 0/6）。`gate status` が失敗したら元に戻す。サービスの再起動はない
- テストの途中に出る `gate: executor deployment ... was not sent after 60 s` は「諦める」ケースのテストの出力で、異常ではない

## sha256

| ファイル | 適用前（期待値 / 実物） | 適用後（期待値 / 実物） |
|---|---|---|
| gate-ctl | dc0d8d5a…9430828（12d）/ 一致 | b8fded9fd31c403aad5209af9e3bf0b9d562dc98a90ea72cac43e7b88f11e7d8 / 一致 |
| run-role | 6229fed4…22c663ac（14d）/ 一致 | acc2ccd5112fe7b86401bf04e3ab74376ded042f67c2f9c0baebd2e1303db0ad / 一致 |
| バックアップ | `/opt/farm/bin/.gate-ctl.bak-15b`、`.run-role.bak-15b` | |
