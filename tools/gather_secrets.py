#!/usr/bin/env python3
"""Collect the real secret values on this host into a list, one per line.

Run as root: python3 -I gather_secrets.py <out-file>
             python3 -I gather_secrets.py --check   (derivation check only; prints addresses)
The list is only used by sanitize.py for exact-match redaction and checking;
collect.sh deletes it afterwards. Nothing is printed except counts.

Besides API keys and the seed phrase, the private keys derived from the seed
(m/44'/60'/0'/0/<i>, i = 0..DERIVE_COUNT-1) are added in hex, so a key that was
ever written to a log or a file is caught by exact match. The derivation is
checked against the addresses from `gate-ctl accounts`.
"""
import glob
import hashlib
import hmac
import json
import os
import re
import sys
import unicodedata

ALCHEMY_SEG = re.compile(r"alchemy\.com/v2/([A-Za-z0-9_-]{8,})")
SECRETY_NAME = re.compile(r"(?i)key|token|secret|pass|auth|cred|bearer|cookie|session")
URL_WITH_CRED = re.compile(r"(?i)https?://[^\s\"']*(?:alchemy|infura|quiknode|ankr|blast|drpc)[^\s\"']*")
DERIVE_COUNT = int(os.environ.get("DERIVE_COUNT", "300"))

# --- secp256k1 / BIP-32, pure Python (one point multiplication per run) ---
P = 0xFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFEFFFFFC2F
N = 0xFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFEBAAEDCE6AF48A03BBFD25E8CD0364141
G = (0x79BE667EF9DCBBAC55A06295CE870B07029BFCDB2DCE28D959F2815B16F81798,
     0x483ADA7726A3C4655DA4FBFC0E1108A8FD17B448A68554199C47D08FFB10D4B8)


def _add(a, b):
    if a is None:
        return b
    if b is None:
        return a
    if a[0] == b[0] and (a[1] + b[1]) % P == 0:
        return None
    if a == b:
        lam = 3 * a[0] * a[0] * pow(2 * a[1], -1, P) % P
    else:
        lam = (b[1] - a[1]) * pow(b[0] - a[0], -1, P) % P
    x = (lam * lam - a[0] - b[0]) % P
    return (x, (lam * (a[0] - x) - a[1]) % P)


def _mul(k, pt=G):
    r = None
    while k:
        if k & 1:
            r = _add(r, pt)
        pt = _add(pt, pt)
        k >>= 1
    return r


def _ser_pub(pt):
    return bytes([2 + (pt[1] & 1)]) + pt[0].to_bytes(32, "big")


def _ckd(k, c, i):
    if i & 0x80000000:
        data = b"\x00" + k.to_bytes(32, "big") + i.to_bytes(4, "big")
    else:
        data = _ser_pub(_mul(k)) + i.to_bytes(4, "big")
    h = hmac.new(c, data, hashlib.sha512).digest()
    return (int.from_bytes(h[:32], "big") + k) % N, h[32:]


def derive_keys(words, count):
    mnemonic = unicodedata.normalize("NFKD", " ".join(words))
    seed = hashlib.pbkdf2_hmac("sha512", mnemonic.encode(), b"mnemonic", 2048)
    h = hmac.new(b"Bitcoin seed", seed, hashlib.sha512).digest()
    k, c = int.from_bytes(h[:32], "big"), h[32:]
    for i in (44 | 0x80000000, 60 | 0x80000000, 0x80000000, 0):
        k, c = _ckd(k, c, i)
    # Children are non-hardened: reuse the parent public key for every index.
    pub = _ser_pub(_mul(k))
    out = []
    for i in range(count):
        hh = hmac.new(c, pub + i.to_bytes(4, "big"), hashlib.sha512).digest()
        out.append((int.from_bytes(hh[:32], "big") + k) % N)
    return out


_RC = [0x0000000000000001, 0x0000000000008082, 0x800000000000808A, 0x8000000080008000,
       0x000000000000808B, 0x0000000080000001, 0x8000000080008081, 0x8000000000008009,
       0x000000000000008A, 0x0000000000000088, 0x0000000080008009, 0x000000008000000A,
       0x000000008000808B, 0x800000000000008B, 0x8000000000008089, 0x8000000000008003,
       0x8000000000008002, 0x8000000000000080, 0x000000000000800A, 0x800000008000000A,
       0x8000000080008081, 0x8000000000008080, 0x0000000080000001, 0x8000000080008008]
_ROT = [[0, 36, 3, 41, 18], [1, 44, 10, 45, 2], [62, 6, 43, 15, 61],
        [28, 55, 25, 21, 56], [27, 20, 39, 8, 14]]
_M64 = (1 << 64) - 1


def keccak256(data):
    """Ethereum's Keccak-256 (not SHA3-256), pure Python."""
    rate = 136
    msg = bytearray(data) + b"\x01"
    msg += b"\x00" * (-len(msg) % rate)
    msg[-1] |= 0x80
    st = [[0] * 5 for _ in range(5)]
    for off in range(0, len(msg), rate):
        for i in range(rate // 8):
            st[i % 5][i // 5] ^= int.from_bytes(msg[off + 8 * i: off + 8 * i + 8], "little")
        for rc in _RC:
            c = [st[x][0] ^ st[x][1] ^ st[x][2] ^ st[x][3] ^ st[x][4] for x in range(5)]
            d = [c[(x - 1) % 5] ^ (((c[(x + 1) % 5] << 1) | (c[(x + 1) % 5] >> 63)) & _M64) for x in range(5)]
            st = [[st[x][y] ^ d[x] for y in range(5)] for x in range(5)]
            b = [[0] * 5 for _ in range(5)]
            for x in range(5):
                for y in range(5):
                    r = _ROT[x][y]
                    v = st[x][y]
                    b[y][(2 * x + 3 * y) % 5] = ((v << r) | (v >> (64 - r))) & _M64 if r else v
            st = [[b[x][y] ^ ((~b[(x + 1) % 5][y]) & b[(x + 2) % 5][y]) for y in range(5)] for x in range(5)]
            st[0][0] ^= rc
    return b"".join(st[i % 5][i // 5].to_bytes(8, "little") for i in range(4))


def known_addresses():
    """Addresses the gate actually used: accounts.json (if it lists any) and `gate-ctl accounts`."""
    import subprocess
    found = ""
    try:
        with open("/var/lib/farmgate/accounts.json", encoding="utf-8") as f:
            found += f.read()
    except OSError:
        pass
    try:
        found += subprocess.run(["sudo", "-u", "farmgate", "/opt/farm/bin/gate-ctl", "accounts"],
                                capture_output=True, text=True, timeout=120).stdout
    except (OSError, subprocess.SubprocessError):
        pass
    return {a.lower() for a in re.findall(r"0x[0-9a-fA-F]{40}", found)}


def eth_address(priv):
    x, y = _mul(priv)
    return "0x" + keccak256(x.to_bytes(32, "big") + y.to_bytes(32, "big")).hex()[-40:]


def add(out, v):
    if not isinstance(v, str):
        return
    v = v.strip()
    if len(v) < 12:
        return
    out.add(v)
    for m in ALCHEMY_SEG.finditer(v):
        out.add(m.group(1))


def walk_json(obj, out, name="", all_strings=False):
    if isinstance(obj, dict):
        for k, v in obj.items():
            walk_json(v, out, str(k), all_strings)
    elif isinstance(obj, list):
        for v in obj:
            walk_json(v, out, name, all_strings)
    elif isinstance(obj, str):
        if all_strings or SECRETY_NAME.search(name) or URL_WITH_CRED.search(obj):
            add(out, obj)


def check_only():
    """Derive keys and compare their addresses with accounts.json. Prints addresses only."""
    with open("/var/lib/farmgate/mnemonic", encoding="utf-8") as f:
        words = f.read().split()
    known = known_addresses()
    addrs = [eth_address(k) for k in derive_keys(words, DERIVE_COUNT)]
    matched = [i for i, a in enumerate(addrs) if a in known]
    print(f"words in seed: {len(words)}; addresses known to the gate: {len(known)}")
    print(f"derived index 0: {addrs[0]}")
    print(f"matching indices: {matched[:20]}{' ...' if len(matched) > 20 else ''} ({len(matched)} of {len(known)})")


def main():
    if sys.argv[1] == "--check":
        check_only()
        return
    out_path = sys.argv[1]
    secrets = set()
    phrases = set()
    derived = set()
    sources = 0

    # Key files kept by the operator (Alchemy, Etherscan, Relay, Hermes, Blockscout ...).
    for p in glob.glob("/etc/farm/*.key") + glob.glob("/etc/farm/**/*.key", recursive=True):
        with open(p, encoding="utf-8", errors="replace") as f:
            for line in f:
                add(secrets, line)
        sources += 1

    # JSON configs: values under secret-looking names, and RPC URLs.
    for p in glob.glob("/etc/farm/*.json"):
        try:
            with open(p, encoding="utf-8") as f:
                walk_json(json.load(f), secrets)
            sources += 1
        except (OSError, ValueError):
            pass

    # env files: NAME=VALUE.
    for p in glob.glob("/etc/farm/*.env") + glob.glob("/etc/farm/*.env.*") + glob.glob("/etc/systemd/system/**/*.conf", recursive=True):
        try:
            with open(p, encoding="utf-8", errors="replace") as f:
                for line in f:
                    m = re.match(r"\s*(?:Environment=)?\"?([A-Za-z_][A-Za-z0-9_]*)=(.*?)\"?\s*$", line)
                    if not m:
                        continue
                    name, val = m.group(1), m.group(2).strip().strip("'\"")
                    if SECRETY_NAME.search(name) or URL_WITH_CRED.search(val):
                        add(secrets, val)
            sources += 1
        except OSError:
            pass

    # Agent harness credentials (codex / claude / dsh), wherever the homes are.
    patterns = [
        "/home/*/.codex/auth.json", "/var/lib/*/.codex/auth.json", "/srv/*/.codex/auth.json",
        "/home/*/.claude/.credentials.json", "/var/lib/*/.claude/.credentials.json",
        "/home/*/.dsh/**/*.json", "/var/lib/*/.dsh/**/*.json", "/root/.codex/auth.json",
        "/root/.claude/.credentials.json",
    ]
    for pat in patterns:
        for p in glob.glob(pat, recursive=True):
            try:
                with open(p, encoding="utf-8") as f:
                    data = json.load(f)
                walk_json(data, secrets, all_strings=p.endswith(("auth.json", ".credentials.json")))
                sources += 1
            except (OSError, ValueError):
                pass

    # The seed phrase itself (and its 6-word windows, so a partial paste is caught),
    # and the private keys derived from it.
    mn = "/var/lib/farmgate/mnemonic"
    if os.path.exists(mn):
        with open(mn, encoding="utf-8") as f:
            words = f.read().split()
        if words:
            phrases.add(" ".join(words))
            for i in range(0, len(words) - 5):
                phrases.add(" ".join(words[i:i + 6]))
            secrets |= phrases
            keys = derive_keys(words, DERIVE_COUNT)
            for k in keys:
                hx = f"{k:064x}"
                derived |= {hx, "0x" + hx, hx.upper(), "0x" + hx.upper()}
            # Check the derivation against the addresses the gate actually used.
            known = known_addresses()
            if not known:
                print("warning: no addresses from accounts.json or gate-ctl accounts; derived keys not checked")
            else:
                matched = sum(1 for k in keys if eth_address(k) in known)
                print(f"derived keys: {len(keys)} (addresses matching the gate's accounts: {matched} of {len(known)})")
                if matched == 0:
                    print("derived keys do not match the gate's accounts; refusing to continue", file=sys.stderr)
                    sys.exit(1)
        sources += 1

    # Keep only values that look like credentials, so that config identifiers
    # (source names, chain names, public addresses) are not blanked everywhere.
    def looks_secret(s):
        if s in phrases:
            return True
        if re.fullmatch(r"0x[0-9a-fA-F]{40}", s):
            return False
        if URL_WITH_CRED.search(s) and ALCHEMY_SEG.search(s):
            return True
        return (len(s) >= 16 and " " not in s and re.search(r"\d", s)
                and re.search(r"[A-Za-z]", s) and not re.fullmatch(r"[a-z0-9_.:/-]+\.(?:json|py|md|sh)", s))

    secrets = {s for s in secrets if looks_secret(s)} | derived

    fd = os.open(out_path, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600)
    with os.fdopen(fd, "w", encoding="utf-8") as f:
        for s in sorted(secrets):
            f.write(s + "\n")
    print(f"secret values collected: {len(secrets)} from {sources} sources")


if __name__ == "__main__":
    main()
