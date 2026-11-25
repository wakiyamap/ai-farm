import json

trace = json.load(open("scratch/llama-arb-trace1.json"))
for i, call in enumerate(trace["calls"]):
    print(i, call.get("to"), call.get("input", "")[:10], int(call.get("gasUsed", "0x0"), 16), call.get("output", "")[:66])
