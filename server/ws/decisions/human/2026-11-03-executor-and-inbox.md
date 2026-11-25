# 回答（2026-11-03）

## signer でコントラクトをデプロイできるか
対応済み。manifest の `executor:` に forge の artifact を書くと、gate が promote 時に bot 自身の鍵でデプロイし、signer がそのアドレスを許可先に加える。手順は earner.md 3b と TOOLS.md（fork / forge）を参照。

## inbox/meta の権限
対応済み。inbox / scratch / logs / claims にデフォルト ACL（group:farm 読み書き）を設定した。
