#!/usr/bin/env python3
"""Dojo WAN credential broker (runs as root inside the terminal container).

A student's shell asks this daemon (over a unix socket) for its Mist API
values. The kernel tells us WHO is asking (SO_PEERCRED gives the caller's real
uid), so a student can only ever obtain their OWN token and org id; the signing
key that derives them is in a root-only file.

Derivations live in wan_ids.py, a byte copy of wan-api/wan_ids.py
(test_parity.py in the module checks that).
"""
import os
import pwd
import json
import socket
import struct
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import wan_ids  # noqa: E402

SOCKET_PATH = "/run/wan-broker/broker.sock"
KEY_PATH = "/run/wan-secrets/signing.key"
READY_MARK = "/run/wan-broker/ca-installed"  # written by start.d/50-wan-cloud.sh once the CA is trusted
MIST_HOST = "api.mist.com"


def roster(env):
    # Same names the engine creates: students are zero-padded (student01), bots are not (testuser1).
    users = []
    for prefix_var, count_var, default_prefix, pad in (("STUDENT_PREFIX", "STUDENT_COUNT", "student", "02d"),
                                                       ("BOT_PREFIX", "BOT_COUNT", "testuser", "d")):
        prefix = env.get(prefix_var, default_prefix)
        try:
            count = int(env.get(count_var, "0") or 0)
        except ValueError:
            count = 0
        users += [f"{prefix}{n:{pad}}" for n in range(1, count + 1)]
    if env.get("FACILITATOR_USERNAME", "root"):
        users.append(env.get("FACILITATOR_USERNAME", "root"))
    return users


def credentials_for(username, key):
    token = wan_ids.api_token(key, username)
    org = wan_ids.org_id(key, username)
    return {
        "MIST_HOST": MIST_HOST,
        "MIST_API_TOKEN": token,
        "MIST_ORG_ID": org,
        "TF_VAR_org_id": org,
        "TF_HTTP_USERNAME": username,
        "TF_HTTP_PASSWORD": token,
    }


def serve():
    users = set(roster(os.environ))
    key = None
    while key is None:  # wan-api creates the key; the rest of the lab works without it
        try:
            with open(KEY_PATH, "rb") as f:
                key = f.read().strip() or None
        except OSError:
            key = None
        if key is None:
            time.sleep(2)

    os.makedirs(os.path.dirname(SOCKET_PATH), mode=0o755, exist_ok=True)
    if os.path.exists(SOCKET_PATH):
        os.remove(SOCKET_PATH)
    srv = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
    srv.bind(SOCKET_PATH)
    os.chmod(SOCKET_PATH, 0o666)
    srv.listen(64)
    while True:
        conn, _ = srv.accept()
        try:
            conn.settimeout(3)
            _pid, uid, _gid = struct.unpack("3i", conn.getsockopt(socket.SOL_SOCKET, socket.SO_PEERCRED,
                                                                 struct.calcsize("3i")))
            try:
                name = pwd.getpwuid(uid).pw_name
            except KeyError:
                name = ""
            # Nothing until the CA is trusted: a shell with a token but no way to trust the API is worse
            # than a shell without one (open a new tab).
            ready = name in users and os.path.exists(READY_MARK)
            payload = credentials_for(name, key) if ready else {}
            conn.sendall(json.dumps(payload).encode())
        except OSError:
            pass
        finally:
            conn.close()


if __name__ == "__main__":
    sys.exit(serve())
