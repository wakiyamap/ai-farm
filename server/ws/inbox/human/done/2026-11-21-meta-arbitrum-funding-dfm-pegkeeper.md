# Arbitrum の中間 wallet への入金のお願い（meta 2026-11-21 16:3x UTC）

- 対象 bot: `trial-dfm-pegkeeper-arbitrum`（cheap-chain trial）。paper-reviewer run `2868904f` が fork で guard の revert と利益の出る成功の両方を再現し、技術的には合格としています（`inbox/meta/2026-11-21-trial-dfm-pegkeeper-arbitrum-funding.md`）。
- 止まっている理由: `gate status`（16:2x UTC）で Arbitrum の中間 wallet の native が **2.11 USD**。この bot は `capital_usd: 5`（native）と executor の deploy（約 1.2M gas）が必要で、**約 3 USD 不足**です。`2026-11-20-trial-slots-45.md` に従い、資金が足りない bot は promote しません。
- お願い: Arbitrum の中間 wallet `0x915bd260dCb166f86a499D5fDb3775b5bec70427` に ETH を **10 USD 程度**（この bot の 5 USD + deploy gas + 次の Arbitrum の試行 1 本分の余裕）入れてください。
- 枠: 試行の live 枠は 70 本（`2026-11-21-trial-slots-70.md`）。reviewer の数えでは 14:14 UTC に 68 本でした。
- 総資本: 今 1219 USD / 2000 USD（X）なので、10 USD 足しても余裕があります。
- 不要と判断される場合は返事は要りません。reviewer は paper のまま再審査を続けます。
