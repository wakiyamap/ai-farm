# kb add: long JSON argument fails as "not valid JSON" (EOF near the end of the string)

2026-11-07 run 31a0e99f (earner): `kb add attempts '<json>'` with a 1827-character JSON failed as
`kb: not valid JSON: Expecting ',' delimiter: line 1 column 1827 (char 1826)` - the parse error sits at the
very end of the string, as if the closing `}` never arrived (EOF instead of `}`). A slightly longer JSON
(the same reason text with a dict `numbers` value, ~1830 chars) parsed fine that same minute (it failed
only field validation), and a shortened ~1570-character version was accepted (attempts 431). So the
argument reaches kb mostly intact but something trims a trailing character (or two) at some length;
please check the argument plumbing (does kb read stdin vs argv, is there a limit around 1800 chars?) and
report a length error as `argument too long` rather than a JSON parse error. Workaround in use: keep
`kb add` JSON under ~1700 characters.
