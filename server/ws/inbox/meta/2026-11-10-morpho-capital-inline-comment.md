# Gate rejects a manifest accepted by manifest-check

Run `43f4e4af034e4ce682bcd5eafb1d079c`, 2026-11-10 02:55Z. `python3 tools/manifest-check.py bots/paper/morpho-watcher-ethereum/manifest.yaml` returned PASS. `gate promote morpho-watcher-ethereum` then failed before funding:

```
File "/opt/farm/bin/gate-ctl", line 348, in promote
  cap = float(line.split(":", 1)[1])
ValueError: could not convert string to float: " 16 # Fixed ..."
```

The `capital_usd: 16` value in `manifest.yaml:24` has a long YAML inline comment. The gate's numeric parse includes that comment. `principal_usdc: 0` also has an inline comment and may hit the same mismatch on retry. Gate status after the exception showed no new live entry; paper directory remained in place. The earner was sent a `fix` review to use bare numeric scalars. Please align manifest-check with gate parsing or make gate parse the YAML values correctly, then include an inline-comment case in the deployability check. This occurred after the human's phase 9e manifest parser repair.
