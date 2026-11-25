# fork fund-token の終了コード修正のお願い（meta c10492af）

`/opt/farm/bin/fork fund-token` は、偽装送金がリバートした場合（holder の残高不足）に `FAILED transfer ...` と表示しますが、終了コードは 0 のままです。終了コードだけを見るスクリプトは「資金投入済み」と誤記録します。2026-11-08 の reserve-folio 検証（scratch/rf-venue-proof.json）はこれで無言の失敗になり、earner の数セッション分が無駄になりました（報告: inbox/meta/fork-fund-token-silent-fail.md、run dcd75f6a）。

ツールはワークスペース外にあり meta は変更できません。お願い: 失敗時に非ゼロで終了するようにしてください。それまでは TOOLS.md の fork 行に「funding 後に balanceOf で確認」と注記しました。

費用・リスク上限の変更はありません。
