# 引き継ぎ書 15: phase 15g（farmbot_signer の priority fee 0）2026-11-19

本体は `farm/farm-handover.md`。バンドル `farm/phase15g/`（tar sha256 `4902ecaa8fd236da7cb8ab38ffbd8eac46161a1abd7c923bd3a8dfe2c06a4af2`）。状態: **2026-11-19 08:11 JST に人間が適用済み**。

## 変更

- `/opt/farm/lib/farmbot_signer.py`（bot が signer に送るためのライブラリ）の `send()`: priority fee を `max_priority_fee_per_gas or max_fee_per_gas // 10` で決めていたため、明示の 0 が maxFee/10 になっていた（paper-reviewer-claude が trial-bim-harvest-base の審査で発見）。`(max_fee_per_gas // 10 if max_priority_fee_per_gas is None else max_priority_fee_per_gas)` に変える（テキストパッチ 1 箇所、45 行目の `"maxPriorityFeePerGas": hex(int(...))` の中）
- L（1 送信の最悪損失）は変わらない（signer が抑えるのは gas × maxFee）
- **動いている bot は再起動するまで古いコードのまま**。人間の判断で、このために live bot を再起動しない。新しい promote・再起動から効く
- install: 式のテスト 3 件（0 → 0、None → maxFee/10、7 → 7）、パッチ、構文、farmbot で import できることを確認（できなければ戻す）。バックアップ `farmbot_signer.py.bak-15g`。サービスの再起動なし

## 適用時の結果（08:11 JST）

- テスト 3/3、パッチは 1 回だけ一致、farmbot で import ok

| ファイル | 適用前 | 適用後（期待値 = 実物） |
|---|---|---|
| farmbot_signer.py | `4d8220c7d9408948428171e4dbd658356958d7d9970f496430f2654c3a587ccf` | `539c9dac7a5ef0f6eb003e259cc7516a71d3bd4590a51472338d913d1211f3b4` |

## 同じ回の人間の判断（meta の 11-18 22 時台の依頼への答え、メモ `inbox/meta/2026-11-19-phase15g-signer-tip.md`）

- no_report の run の claim をハーネスで自動失効: 今はしない（builder.md の規則で足りる）
- bsc の getLogs（scout レーンの枠が尽きた後）: 現状維持。relay に例外を作らない
- HyperEVM の HYPE: 人間が補充済み（約 38 USD）
- scout が公開ノードに直接 curl した件（2 回）: scout.md の規則を短く明確にし、次の報告で件数を数えるよう meta に依頼

## builder-codex の停止（11-19 05:30 JST）

- journal: `This content was flagged for possible cybersecurity risk ... confirm that the access_programs.cyber parameter is set to the appropriate tier`（OpenAI の内容フィルタ）。同じ頃、人間のスマホの OpenAI も一斉にログアウトされていた
- 次の 08:10 の回は正常に動いた（人間が確認）。一時的な判定と見る。また落ちるなら Daybreak（access_programs.cyber）の設定を確かめる
