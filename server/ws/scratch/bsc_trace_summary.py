import json
from pathlib import Path

root = Path(__file__).parent
for name in ("keeper", "trigger"):
    for label in ("original", "stranger"):
        trace = json.loads((root / f"bsc-{name}-{label}-trace.json").read_text())["result"]
        print(name, label, "error", trace.get("error"), "gas", int(trace.get("gasUsed", "0x0"), 16))

        def walk(node, depth=0):
            data = node.get("input", "0x")
            value = int(node.get("value", "0x0"), 16)
            if depth <= 2 or data.startswith(("0xa9059cbb", "0x23b872dd")) or value:
                print(" " * depth, node.get("type"), node.get("from"), node.get("to"), data[:74],
                      "value", value, "error", node.get("error"), "output", node.get("output", "")[:74])
            for child in node.get("calls", []):
                walk(child, depth + 1)

        walk(trace)
