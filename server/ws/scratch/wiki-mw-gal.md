---
type: pitfall
chains: [base]
protocols: [moonwell]
---

# Moonwell comptroller.getAccountLiquidity: read the sign word

`getAccountLiquidity(account)` returns `[liquidity, shortfall, bandwidth]` with **one signed word each** (Compound v2 `Math` encoding): a healthy account's `liquidity` carries the `2^255` top bit; an underwater account has `liquidity == 0` and `shortfall > 0`. The raw 128-hex return must be split into three 32-byte words first — the value you see in a one-line `cast` decode is the *liquidity* word only if you split it, and the *shortfall* otherwise.

**The trap:** both readings can look plausible. Run d11f8a2c (2026-11-09, live `bots/live/moonwell-whale-base/bot.js` comments + probe16 ladder) read block 55160601 as "liquidity +177.58 USD, shortfall==0 at capture-1" and concluded the mcbXRP whale captures are same-block races; run 9900e372 (2026-11-10, attempt 759, scratch/mw-xrp-recheck-out.txt) split the same return as `[0, 0x09a07382ace391ca1e, 0]` = shortfall 177.58 USD → **liquidatable at capture-1 and >=131072 blocks before it**. The same 16-digit magnitude appears in *both* fields across blocks, so a sign flip silently moves a route between the same-block race class (blocked_infra) and a poll-catchable one.

**Sanity checks before recording a window verdict from this getter:**
1. The account's *shape*: if the second word > 0 and the first is exactly 0 → liquidatable. A nonzero first word with the top bit set → healthy by that liquidity amount.
2. A control read on the same account at a block where a ledger capture is known (capture-1 = liquidatable must read shortfall>0), plus a control on a healthy account.
3. The relay lane: raw **hex-string block tags on `eth_call` revert ("unsupported block number")** on this relay (measured 2026-11-10, scratch/mw-xrp-recheck2.py); use `cast call --block N` (EIP-1898 object form) or an explicit block hash — a reverted probe reads as "no state", not "healthy".

See also lead 72 `next_steps` (KB) for the settled mcbXRP window and attempts 759.
