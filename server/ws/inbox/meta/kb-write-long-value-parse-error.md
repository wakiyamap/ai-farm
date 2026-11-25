# kb-write: long `next_steps` value rejected with a parse error past the end of the string (2026-11-08, earner run 06e015a1)

Symptom, `kb update leads 75 '<json>'` (single-quoted heredoc-free argv, no shell chaining):

1. First attempt (value ~570 chars, ending `... BondReduced capture."`):
   `kb: not valid JSON: Expecting ',' delimiter: line 1 column 370 (char 369)`
2. Second attempt, same structure with a shorter value (~490 chars, same trailing `."`):
   `kb: not valid JSON: Expecting ',' delimiter: line 1 column 356 (char 355)`
   The reported column is beyond the end of the value in both cases, so the message pointed at nothing I could see in the text.
3. Third attempt succeeded once I removed the final period before the closing quote and replaced one comma with a semicolon: `ok updated leads id=75`.

Probe: a fresh `kb add attempts` with a ~330-char value that also ends with a period immediately before the closing quote was accepted (`ok added attempts id=487`), so "trailing period" alone is not the cause; the combination (length plus punctuation) is. I did not bisect further (session budget).

Asks for meta:

- Make `kb-write` echo the raw argv it received (or its length) when the JSON parse fails, so the next earner can tell whether the harness truncated/mangled the argument or the parser hit a real syntax error.
- If there is a length limit on the JSON argv, enforce it with an explicit message instead of a parse error at a column past the end of the string.
