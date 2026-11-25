"""Keys for the farm: BIP-39 mnemonic + BIP-44 derivation (m/44'/60'/0'/0/i).

Account 0 is the intermediate wallet; each live bot gets the next free index,
recorded in /var/lib/farmgate/accounts.json. The same mnemonic restores every
address in any standard wallet (Rabby, MetaMask, hardware wallets).

Only farmgate processes (signer, gate) import this. Nothing here logs a key.
"""
import hashlib
import hmac
import json
import os
import unicodedata

import coincurve
import rlp
from Crypto.Hash import keccak

MNEMONIC_PATH = "/var/lib/farmgate/mnemonic"
ACCOUNTS_PATH = "/var/lib/farmgate/accounts.json"
WORDLIST_PATH = os.environ.get("FARM_WORDLIST", "/opt/farm/lib/bip39-english.txt")
SECP256K1_N = 0xFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFEBAAEDCE6AF48A03BBFD25E8CD0364141
HARD = 0x80000000


def keccak256(data: bytes) -> bytes:
    h = keccak.new(digest_bits=256)
    h.update(data)
    return h.digest()


# --- BIP-39 -------------------------------------------------------------
def wordlist():
    with open(WORDLIST_PATH, encoding="utf-8") as f:
        words = [w.strip() for w in f if w.strip()]
    if len(words) != 2048:
        raise ValueError("bad wordlist")
    return words


def entropy_to_mnemonic(entropy: bytes) -> str:
    words = wordlist()
    cs_bits = len(entropy) * 8 // 32
    h = hashlib.sha256(entropy).digest()
    bits = bin(int.from_bytes(entropy, "big"))[2:].zfill(len(entropy) * 8) + bin(h[0])[2:].zfill(8)[:cs_bits]
    return " ".join(words[int(bits[i:i + 11], 2)] for i in range(0, len(bits), 11))


def validate_mnemonic(phrase: str) -> None:
    words = wordlist()
    ws = unicodedata.normalize("NFKD", phrase).strip().split()
    if len(ws) not in (12, 15, 18, 21, 24):
        raise ValueError("mnemonic must have 12/15/18/21/24 words")
    try:
        bits = "".join(bin(words.index(w))[2:].zfill(11) for w in ws)
    except ValueError as exc:
        raise ValueError(f"word not in BIP-39 list: {exc}") from None
    ent_len = len(bits) * 32 // 33
    entropy = int(bits[:ent_len], 2).to_bytes(ent_len // 8, "big")
    cs = bin(hashlib.sha256(entropy).digest()[0])[2:].zfill(8)[:len(bits) - ent_len]
    if bits[ent_len:] != cs:
        raise ValueError("mnemonic checksum is wrong (a word is mistyped)")


def mnemonic_to_seed(phrase: str, passphrase: str = "") -> bytes:
    m = unicodedata.normalize("NFKD", " ".join(phrase.split()))
    salt = unicodedata.normalize("NFKD", "mnemonic" + passphrase)
    return hashlib.pbkdf2_hmac("sha512", m.encode(), salt.encode(), 2048)


# --- BIP-32 -------------------------------------------------------------
def _ckd_priv(k: bytes, c: bytes, i: int):
    if i >= HARD:
        data = b"\x00" + k + i.to_bytes(4, "big")
    else:
        data = coincurve.PrivateKey(k).public_key.format(compressed=True) + i.to_bytes(4, "big")
    I = hmac.new(c, data, hashlib.sha512).digest()
    il, ir = int.from_bytes(I[:32], "big"), I[32:]
    child = (il + int.from_bytes(k, "big")) % SECP256K1_N
    if il >= SECP256K1_N or child == 0:
        raise ValueError("invalid child key; use another index")
    return child.to_bytes(32, "big"), ir


def derive_path(seed: bytes, path: str) -> bytes:
    I = hmac.new(b"Bitcoin seed", seed, hashlib.sha512).digest()
    k, c = I[:32], I[32:]
    for part in path.split("/")[1:]:
        hardened = part.endswith("'") or part.endswith("h")
        idx = int(part.rstrip("'h")) + (HARD if hardened else 0)
        k, c = _ckd_priv(k, c, idx)
    return k


def account_key(seed: bytes, index: int) -> bytes:
    return derive_path(seed, f"m/44'/60'/0'/0/{index}")


# --- farm-level helpers ---------------------------------------------------
def load_master(path=MNEMONIC_PATH) -> bytes:
    """Returns the BIP-39 seed (64 bytes) for the farm mnemonic."""
    with open(path, encoding="utf-8") as f:
        phrase = f.read()
    validate_mnemonic(phrase)
    return mnemonic_to_seed(phrase)


def _accounts():
    try:
        with open(ACCOUNTS_PATH, encoding="utf-8") as f:
            return json.load(f)
    except (OSError, ValueError):
        return {"intermediate": 0, "bots": {}}


def _save_accounts(acc):
    tmp = ACCOUNTS_PATH + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(acc, f, indent=1)
    os.replace(tmp, ACCOUNTS_PATH)


def account_index(label: str, create: bool = False) -> int:
    """'intermediate' -> 0; 'bot:<id>' -> its index (allocated on first use when create=True)."""
    if label == "intermediate":
        return 0
    if not label.startswith("bot:"):
        raise ValueError("label must be 'intermediate' or 'bot:<id>'")
    bot = label[4:]
    acc = _accounts()
    if bot in acc["bots"]:
        return acc["bots"][bot]
    if not create:
        raise KeyError(f"no account allocated for {bot}")
    idx = 1 + max([0] + list(acc["bots"].values()))
    acc["bots"][bot] = idx
    _save_accounts(acc)
    return idx


def derive_private_key(seed: bytes, label: str, create: bool = False) -> bytes:
    return account_key(seed, account_index(label, create))


def address_of(priv: bytes) -> str:
    pub = coincurve.PrivateKey(priv).public_key.format(compressed=False)[1:]
    return "0x" + keccak256(pub)[-20:].hex()


def checksum(addr: str) -> str:
    a = addr.lower().replace("0x", "")
    h = keccak256(a.encode()).hex()
    return "0x" + "".join(c.upper() if int(h[i], 16) >= 8 else c for i, c in enumerate(a))


# --- transactions -----------------------------------------------------------
def sign_eip1559(priv: bytes, tx: dict) -> bytes:
    def i(v):
        return int(v, 16) if isinstance(v, str) else int(v)

    to = bytes.fromhex(tx["to"][2:]) if tx.get("to") else b""
    data = bytes.fromhex(tx.get("data", "0x")[2:]) if tx.get("data") else b""
    fields = [i(tx["chainId"]), i(tx["nonce"]), i(tx["maxPriorityFeePerGas"]), i(tx["maxFeePerGas"]),
              i(tx["gas"]), to, i(tx.get("value", 0)), data, []]
    digest = keccak256(b"\x02" + rlp.encode(fields))
    sig = coincurve.PrivateKey(priv).sign_recoverable(digest, hasher=None)
    r, s, v = int.from_bytes(sig[:32], "big"), int.from_bytes(sig[32:64], "big"), sig[64]
    return b"\x02" + rlp.encode(fields + [v, r, s])


def tx_hash(raw: bytes) -> str:
    return "0x" + keccak256(raw).hex()


def selector(signature: str) -> str:
    return "0x" + keccak256(signature.encode())[:4].hex()


def encode_call(signature: str, *args) -> str:
    out = bytes.fromhex(selector(signature)[2:])
    for a in args:
        if isinstance(a, str) and a.startswith("0x"):
            out += bytes(12) + bytes.fromhex(a[2:].rjust(40, "0"))
        else:
            out += int(a).to_bytes(32, "big")
    return "0x" + out.hex()


if __name__ == "__main__":
    # Known vectors: the canonical test mnemonic derives these addresses at m/44'/60'/0'/0/{0,1}
    phrase = "abandon abandon abandon abandon abandon abandon abandon abandon abandon abandon abandon about"
    validate_mnemonic(phrase)
    seed = mnemonic_to_seed(phrase)
    assert seed.hex().startswith("5eb00bbddcf069084889a8ab9155568165f5c453ccb85e70811aaed6f6da5fc1"), seed.hex()
    a0 = checksum(address_of(account_key(seed, 0)))
    a1 = checksum(address_of(account_key(seed, 1)))
    assert a0 == "0x9858EfFD232B4033E47d90003D41EC34EcaEda94", a0
    assert a1 == "0x6Fac4D18c912343BF86fa7049364Dd4E424Ab9C0", a1
    assert selector("transfer(address,uint256)") == "0xa9059cbb"
    assert entropy_to_mnemonic(bytes(16)) == phrase
    print(json.dumps({"ok": True, "account0": a0}))
