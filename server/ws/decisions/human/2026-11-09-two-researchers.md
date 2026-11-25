# 2026-11-09 researcher を 2 つ並走させる（phase 9）

- researcher を 2 インスタンスにした。役割ファイル（researcher.md）は共通。
  - `researcher`: codex（gpt-6.1-sol）。毎日 04:00 JST ごろ。
  - `researcher-claude`: claude（opus）。毎日 16:10 JST。
- 目的は、清算以外の稼得クラスを見つけること（2026-11-08-beyond-liquidations）と、どちらのモデルが良い lead を出すかを比べること。
- 重複を避けるため、両方とも作業の最初に、直近 2 日の KB `leads` / `attempts` と ledger の add-source を確認すること。もう一方が手を付けた対象には、その続き（次のステップ）からだけ入ること。同じ対象を最初から測り直さない。
- claude 版の権限: kb / wiki / ledger / websearch / fork / forge / cast / curl、`tools/` の編集と `python3 tools/*`、scratch と inbox への書き込み。gate と paper の操作はできない（必要ない）。拒否されたコマンドがあれば、そのコマンド行をそのまま inbox/human に書くこと。
- meta: 毎回の報告で、インスタンスごと（session report の model 欄で区別できる）に次を数えること: 追加した lead の数、そのうち清算以外の数、earner が測って dead_end でなかった数、paper まで進んだ数。2 週間たったら、続けるか、どちらかに絞るかを提案すること。
