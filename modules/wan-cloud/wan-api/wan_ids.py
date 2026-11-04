"""Per-user values derived from the signing key: API token, org id, gateway delivery.

The same file is copied to modules/wan-cloud/terminal/ for the credential broker;
modules/wan-cloud/test_parity.py checks the two copies are identical.
"""
import base64
import hashlib
import hmac
import uuid

MODELS = ("SRX300", "SRX300", "SRX345", "SRX345", "SRX1500")   # the delivery: five gateways per org


def _mac(key: bytes, label: str) -> bytes:
    return hmac.new(key, label.encode(), hashlib.sha256).digest()


def api_token(key: bytes, user: str) -> str:
    return _mac(key, "wan/apitoken:" + user).hex()[:40]


def org_id(key: bytes, user: str) -> str:
    return str(uuid.UUID(bytes=_mac(key, "wan/org:" + user)[:16]))


def claim_code(key: bytes, user: str, n: int) -> str:
    """15 characters of [0-9A-Z], as the provider requires: the model, then 9 derived."""
    tail = base64.b32encode(_mac(key, f"wan/claim:{user}:{n}")).decode().rstrip("=")
    return (MODELS[n] + tail)[:15]


def delivery(key: bytes, user: str) -> list:
    """The packing slip: serial, MAC (locally administered, 12 lowercase hex), model, claim code."""
    out = []
    for n, model in enumerate(MODELS):
        d = _mac(key, f"wan/device:{user}:{n}")
        mac = bytes([(d[0] | 0x02) & 0xFE]) + d[1:6]
        out.append({"serial": "CW" + d[6:11].hex().upper()[:10], "mac": mac.hex(), "model": model,
                    "magic": claim_code(key, user, n)})
    return out


def device_id(mac: str) -> str:
    return "00000000-0000-0000-1000-" + mac
