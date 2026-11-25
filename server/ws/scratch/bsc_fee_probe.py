import json
from pathlib import Path

root = Path(__file__).parent
stranger = "0x1111111111111111111111111111111111111111"
for name in ("keeper", "trigger"):
    tx = json.loads((root / f"bsc-{name}-tx.json").read_text())["result"]
    for label, sender in (("stranger", stranger), ("original", tx["from"])):
        params = [
            {"from": sender, "to": tx["to"], "data": tx["input"], "gas": "0x989680"},
            hex(int(tx["blockNumber"], 16) - 1),
            {"tracer": "callTracer"},
        ]
        (root / f"bsc-{name}-{label}-params.json").write_text(json.dumps(params))
