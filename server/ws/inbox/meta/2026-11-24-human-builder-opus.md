# Reduced operation: builder-claude every 12 h, new builder-opus (human, 2026-11-24)

- builder-claude (Mythos) now runs at 00:40 and 12:40 JST only (was every 4 h).
- builder-opus is a second instance of the same role `builder` on Claude Opus, at 06:40 and 18:40 JST.
  The two never overlap (75-minute sessions, 6 hours apart). Bots it builds name `builder/opus` as author;
  paper-reviewer (codex) reviews them like any other bot.
- builder.md says "one builder": keep that meaning (one builder at a time), and mention that the instance
  alternates between Mythos and Opus.
- In your reports, show builder runs per instance (sessions, outcome, bots placed in paper) so the human can
  compare Opus with Mythos.
