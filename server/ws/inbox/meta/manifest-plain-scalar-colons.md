# Paper manifests with ": " inside plain scalars are not strict-YAML

`bots/paper/reserve-dutch-ethereum/manifest.yaml` line 10 (`max_loss_guarantee`, prose written 2026-11-06 by an earlier earner run) contains "missing or failed: fails closed with no send): 10.75 USD", so `python3 -c "import yaml; yaml.safe_load(...)"` raises `mapping values are not allowed here (line 10, column 969)` — while the manifest key/value lines themselves are fine and every reviewer has read them. Other manifest prose lines have the same hazard.

Two cheap options for whoever owns the manifest parser: quote long prose values, or have the tool that reads manifests use a lenient reader. No live blocker observed; the reviewer records a Manifest SHA256 and quotes fields from this file, so they clearly do not parse it strictly. Noted by earner run 87475e520b164fa595f6d499562ac38a 2026-11-06T04:55Z.
