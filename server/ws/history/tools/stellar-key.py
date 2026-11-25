#!/usr/bin/env python3
"""stellar-key.py: base64 LedgerKey XDR for Stellar RPC getLedgerEntries (16a helper, no SDK).

  stellar-key.py instance C...        contract instance (persistent)  -> the contract's instance storage
  stellar-key.py code <wasm-hash-hex> contract code
  stellar-key.py account G...         account entry
  stellar-key.py decode C...|G...     print the 32-byte payload as hex

Then: {"jsonrpc":"2.0","id":1,"method":"getLedgerEntries","params":{"keys":["<base64>"],"xdrFormat":"json"}}
"""
import base64
import struct
import sys

VERSION = {"G": 6 << 3, "C": 2 << 3}


def crc16_xmodem(data):
    crc = 0
    for b in data:
        crc ^= b << 8
        for _ in range(8):
            crc = ((crc << 1) ^ 0x1021) if crc & 0x8000 else (crc << 1)
            crc &= 0xFFFF
    return crc


def strkey_decode(s):
    s = s.strip()
    if len(s) != 56 or s[0] not in VERSION:
        sys.exit(f"not a 56-character G... or C... strkey: {s!r}")
    raw = base64.b32decode(s + "=" * (-len(s) % 8))
    ver, payload, chk = raw[0], raw[1:33], raw[33:35]
    if ver != VERSION[s[0]]:
        sys.exit(f"bad version byte for {s[0]}")
    if struct.pack("<H", crc16_xmodem(raw[:33])) != chk:
        sys.exit("bad checksum")
    return payload


def u32(n):
    return struct.pack(">I", n)


def main():
    if len(sys.argv) != 3:
        sys.exit(__doc__)
    kind, arg = sys.argv[1], sys.argv[2]
    if kind == "decode":
        print(strkey_decode(arg).hex())
        return
    if kind == "instance":   # LedgerKey CONTRACT_DATA(6): ScAddress contract(1)+hash, ScVal LEDGER_KEY_CONTRACT_INSTANCE(20), PERSISTENT(1)
        if not arg.startswith("C"):
            sys.exit("instance needs a C... contract id")
        key = u32(6) + u32(1) + strkey_decode(arg) + u32(20) + u32(1)
    elif kind == "code":     # LedgerKey CONTRACT_CODE(7): hash
        h = bytes.fromhex(arg.removeprefix("0x"))
        if len(h) != 32:
            sys.exit("code needs a 32-byte wasm hash in hex")
        key = u32(7) + h
    elif kind == "account":  # LedgerKey ACCOUNT(0): PublicKey ED25519(0)+key
        if not arg.startswith("G"):
            sys.exit("account needs a G... account id")
        key = u32(0) + u32(0) + strkey_decode(arg)
    else:
        sys.exit(__doc__)
    print(base64.b64encode(key).decode())


if __name__ == "__main__":
    main()
