"""Tiny client for live bots (any language can do the same: one JSON line over
the Unix socket at $SIGNER_SOCK, one JSON line back).

    from farmbot_signer import send, my_address, limits
    tx = send(chain="base", to="0x..", data="0x..", gas=200000, max_fee_per_gas=50_000_000)
    # -> {"ok": True, "txHash": "0x..", "nonce": 7}  or  {"ok": False, "error": "..."}

The signer decides the nonce and signs with this bot's key; the bot never sees
the key. Rejections are final: do not retry the same request.
"""
import json
import os
import socket

SOCK = os.environ.get("SIGNER_SOCK", "/run/farm/signer.sock")


def _call(req):
    with socket.socket(socket.AF_UNIX, socket.SOCK_STREAM) as s:
        s.settimeout(60)
        s.connect(SOCK)
        s.sendall((json.dumps(req) + "\n").encode())
        buf = b""
        while not buf.endswith(b"\n"):
            chunk = s.recv(65536)
            if not chunk:
                break
            buf += chunk
    return json.loads(buf or b'{"ok": false, "error": "no response"}')


def my_address():
    return _call({"op": "address"})


def limits():
    return _call({"op": "limits"})


def send(chain, to, data="0x", value=0, gas=100_000, max_fee_per_gas=None, max_priority_fee_per_gas=None):
    if max_fee_per_gas is None:
        raise ValueError("max_fee_per_gas is required (wei)")
    return _call({"op": "send", "chain": chain, "to": to, "data": data, "value": hex(int(value)),
                  "gas": hex(int(gas)), "maxFeePerGas": hex(int(max_fee_per_gas)),
                  "maxPriorityFeePerGas": hex(int((max_fee_per_gas // 10 if max_priority_fee_per_gas is None else max_priority_fee_per_gas)))})
