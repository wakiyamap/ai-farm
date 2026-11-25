# セッション報告の欠落と meta の実行権限について（meta, run 425c8d40, 2026-11-04）

## 1. 11/4 のセッション報告がほとんど残っていません
- 11/4 00:08Z〜09:23Z に KB の attempts を書いた run は 18 件ありますが、`logs/sessions/2026-11-04.jsonl` に行があるのは 2 件だけです。欠けている 16 件の内訳は earner 10 件、paper-reviewer 6 件です。
- このファイルは 08:20:11Z に新しく作られています（stat の birth、所有者は earner）。それより前の報告が最初から書かれなかったのか、Write ツールでファイルごと置き換えられて消えたのかは、ログからは区別できません。11/3 のファイルも 21:41Z に別の inode で作り直されています。
- 対策として `tools/session-report.py` を追加しました。O_APPEND で追記するだけで既存の行は書き換えず、フィールドと outcome を検証し、同じ run_id の重複は拒否します。TOOLS.md と earner.md / paper-reviewer.md にそれぞれ1行ずつ案内を足しました。次回の meta で、報告が残った run の割合を測ります（目標は 80% 以上）。
- お願い：可能であれば `logs/sessions/` を追記専用にしてください（例：chattr +a）。または harness 側でセッション終了時に報告行を自動で追記していただけると、より確実です。

## 2. meta から python と git を実行できません
- don't-ask モードでは、`python3 /srv/farm/ws/tools/*.py` も `git log` も拒否されます。そのため、今回追加したツールを meta 自身で試せていません。また、レビューすべきコミット一覧も得られていません。
- お願い：meta の許可リストに `python3 /srv/farm/ws/tools/*` と `git -C /srv/farm/ws log` を追加してください。

## 参考
- live bot は 0 件、gate の資金は $74.11 です。昨日からの promote も 0 件です（paper 3 bot は fix の往復が続いています）。
