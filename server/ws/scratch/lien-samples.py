import collections
import json
import subprocess

logs = json.load(open("/srv/farm/ws/scratch/lien-dividend-logs.json"))
logs = logs.get("result", logs)
counts = collections.Counter(log["transactionHash"] for log in logs)
for txhash, n in counts.items():
    p = subprocess.run(
        ["python3", "/srv/farm/ws/tools/rpc.py", "ethereum", "eth_getTransactionByHash", json.dumps([txhash])],
        check=True,
        capture_output=True,
        text=True,
    )
    tx = json.loads(p.stdout)["result"]
    receipts = subprocess.run(
        ["python3", "/srv/farm/ws/tools/rpc.py", "ethereum", "eth_getTransactionReceipt", json.dumps([txhash])],
        check=True,
        capture_output=True,
        text=True,
    )
    receipt = json.loads(receipts.stdout)["result"]
    recipients = [log["topics"][2][-40:] for log in logs if log["transactionHash"] == txhash]
    eth = sum(int(log["data"], 16) for log in logs if log["transactionHash"] == txhash) / 1e18
    print(json.dumps({
        "tx": txhash,
        "caller": tx["from"],
        "recipient_count": n,
        "caller_recipient": tx["from"].lower()[2:] in recipients,
        "payout_eth": eth,
        "gas_used": int(receipt["gasUsed"], 16),
        "effective_gas_price_wei": int(receipt["effectiveGasPrice"], 16),
    }))
