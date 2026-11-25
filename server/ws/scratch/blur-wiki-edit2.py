p='scratch/blur-wiki-draft.md'
s=open(p).read()
anchor='\n## What was measured'
add=("\n**Outcome (2026-11-12, attempt 969):** for the farm this class is a dead_end: the taker's profit is the "
"interest stream on the debt it pays over, and that debt (median lien 0.79-0.86 ETH = 1630-1770 USD per take) is "
"30-60x over the farm's 50 USD per-transaction loss cap and over the 30 USD watchdog parking budget for the "
"Pool-unit float. At an L-bounded size (<= 0.024 ETH debt) the 30-day census carries 1 fill with ~0 interest; the "
"whale incumbents earn ~18 USD/day gross between them.\n")
assert anchor in s
s=s.replace(anchor, add+anchor, 1)
open(p,'w').write(s)
print('ok')
