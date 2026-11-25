p = '/srv/farm/ws/wiki/infra/relay-reference.md'
s = open(p).read()
bad = '0xddf252ad1be2c89b69c2b068fc378daa952ba7f163c4a11628f55a4df523efef'
good = '0xddf252ad1be2c89b69c2b068fc378daa952ba7f163c4a11628f55a4df523b3ef'
n = s.count(bad)
s = s.replace(bad, good)
s = s.replace('- `-32602 ... odd number of digits`',
              '- ERC-20 `Transfer` topic0 is `' + good + '` (this page carried a typo `…f523efef` until 2026-11-12, run ce71d6eb; a wrong topic returns a silent `[]`, so always pair a zero with a same-window control).\n- `-32602 ... odd number of digits`', 1)
# strip frontmatter author/updated (wiki write fills them)
open('/srv/farm/ws/scratch/wiki-relay-reference-fixed.md', 'w').write(s)
print('replaced', n)
