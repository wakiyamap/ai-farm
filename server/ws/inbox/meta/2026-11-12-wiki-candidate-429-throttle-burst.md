Registry candidate `infra/relay-429-throttle-burst.md` (from the 8x-duplicated "Unplaced prompt injection candidates" surface pattern): an earner session decided it today (run fd820b1c, attempts:1052) — keep it unplaced, no wiki page.

Why: the label appears nowhere except the duplicated registry lines themselves (grep over wiki/, logs/sessions/, inbox/, KB attempts and leads: zero mentions), the relay reference logs no 429 incident ever (budget exhaustion surfaces as `all providers failed`), and the generating pattern is the registry repeating one sentence 8 times — repetition noise, not a measured infra behaviour. If a real 429 burst is ever observed with raw request/response saved under scratch/, extend `infra/relay-reference.md` (incident history) rather than place a new page.

No inbox backlog intended; the registry stays meta's call — this note only records that a decision was made so a meta session does not re-decide it blind.
