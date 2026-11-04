"""Terraform `http` state backend on the fake Mist host: /dojo-state/<name>.

A student's terminal (and their pipeline jobs) share one state per name. Auth is HTTP Basic: the username is the
user's name and the password their Mist API token (TF_HTTP_USERNAME / TF_HTTP_PASSWORD). The state belongs to the
user's org and lives outside the org store (it can hold secrets, and the portal shows the org store to the class):
<data>/state/<org_id>/<name>.tfstate, with a <name>.lock file while it is locked. A lock lasts until UNLOCK (no
expiry): `terraform force-unlock` is the way out. State content is never logged.
Port of modules/dojo-cloud/cloud-api/tfstate.py.
"""
import base64
import binascii
import json
import os
import re
import threading
from urllib.parse import parse_qs

PREFIX = "/dojo-state/"
NAME = re.compile(r"^[a-z0-9][a-z0-9-]{0,39}$")
MAX_BYTES = 2 * 1024 * 1024
MAX_STATES = 10
REALM = 'Basic realm="dojo-wan-state"'


def _reply(status, body=None, headers=None):
    if isinstance(body, (dict, list)):
        return status, json.dumps(body).encode(), {"Content-Type": "application/json", **(headers or {})}
    return status, body or b"", {"Content-Type": "application/json", **(headers or {})}


def _err(status, message, headers=None):
    return _reply(status, {"detail": message}, headers)


def credentials(header):
    try:
        raw = base64.b64decode(header.split(None, 1)[1], validate=True).decode()
        user, _, token = raw.partition(":")
        return user, token
    except (IndexError, ValueError, binascii.Error):
        return None


class StateStore:
    def __init__(self, data_dir):
        self.dir = os.path.join(data_dir, "state")
        self.lock = threading.Lock()   # file reads and writes of a few KB: quick, and never held across anything else

    def _org_dir(self, org_id):
        return os.path.join(self.dir, org_id)

    def _read(self, path):
        try:
            with open(path, "rb") as f:
                return f.read()
        except OSError:
            return None

    def _write(self, path, data):
        os.makedirs(os.path.dirname(path), exist_ok=True)
        tmp = path + ".tmp"
        with open(tmp, "wb") as f:
            f.write(data)
        os.replace(tmp, path)

    def purge(self, org_id):
        """Forget the org's states and locks -> how many states there were."""
        with self.lock:
            d = self._org_dir(org_id)
            if not os.path.isdir(d):
                return 0
            names = os.listdir(d)
            count = sum(1 for n in names if n.endswith(".tfstate"))
            for n in names:
                os.remove(os.path.join(d, n))
            return count

    def handle(self, app, limiter, method, path, query, auth_header, read_body, log_event):
        """-> (status, bytes, headers). `read_body(limit)` is only called once the caller is authenticated, so an
        unauthenticated client cannot make us read megabytes. `log_event(org_id, actor, action, path)` records writes."""
        challenge = {"WWW-Authenticate": REALM}
        creds = credentials(auth_header or "")
        user = app.auth.user_for_token(creds[1]) if creds else None
        if user is None or user != creds[0]:
            return _err(401, "Use your user name and Mist API token as the HTTP Basic username and password.", challenge)
        name = path[len(PREFIX):]
        if not NAME.match(name):
            return _err(400, "State names are 1-40 characters of a-z, 0-9 and '-', starting with a letter or digit.")
        wait = limiter.take("state:" + user)
        if wait:
            return _err(429, "Too many requests: slow down and retry.", {"Retry-After": str(wait)})
        q = parse_qs(query or "")
        org_id = app.auth.org_of[user]
        other = (q.get("org") or [""])[0].lower()
        if other and other != org_id:
            if method != "GET" or not app.auth.is_facilitator(user) or other not in app.auth.user_of_org:
                return _err(403, "Only the facilitator may read another org's state.")
            org_id = other
        body = b""
        if method in ("POST", "LOCK", "UNLOCK"):
            body = read_body(MAX_BYTES + 1)
            if len(body) > MAX_BYTES:
                return _err(413, f"State is limited to {MAX_BYTES // 1024} KiB.")
        body_id = ""
        if method in ("LOCK", "UNLOCK") and body.strip():
            try:
                info = json.loads(body)
                body_id = str(info.get("ID") or "") if isinstance(info, dict) else ""
            except ValueError:
                if method == "LOCK":
                    return _err(400, "Lock info must be JSON.")
        lock_id = (q.get("ID") or [""])[0] or body_id
        d = self._org_dir(org_id)
        state_path, lock_path = os.path.join(d, name + ".tfstate"), os.path.join(d, name + ".lock")
        with self.lock:
            text = self._read(state_path)
            if method == "GET":
                if text is None:
                    return _err(404, f"No state named '{name}'.")
                return _reply(200, text)
            raw_held = self._read(lock_path)
            held = json.loads(raw_held) if raw_held else None
            if method == "LOCK":
                if held:
                    return _reply(423, held)
                try:
                    info = json.loads(body) if body.strip() else {}
                except ValueError:
                    info = {}
                if not isinstance(info, dict):
                    return _err(400, "Lock info must be a JSON object.")
                info.setdefault("ID", lock_id or "unknown")
                self._write(lock_path, json.dumps(info).encode())
                return _reply(200, info)
            if method == "UNLOCK":
                if held and lock_id and held.get("ID") != lock_id:
                    return _reply(409, held)
                if os.path.exists(lock_path):   # no ID = force unlock; nothing held = still fine
                    os.remove(lock_path)
                return _reply(200, {})
            if method in ("POST", "DELETE"):
                if held and held.get("ID") != lock_id:
                    return _reply(409, held)
                if method == "DELETE":
                    if text is not None:
                        os.remove(state_path)
                        log_event(org_id, user, f"delete state {name}", path)
                    return _reply(200, {})
                try:
                    body.decode()
                except UnicodeDecodeError:
                    return _err(400, "State must be UTF-8 JSON.")
                if text is None and os.path.isdir(d) and sum(1 for n in os.listdir(d) if n.endswith(".tfstate")) >= MAX_STATES:
                    return _err(507, f"At most {MAX_STATES} states per org; delete one first.")
                self._write(state_path, body)
                log_event(org_id, user, f"save state {name}", path)
                return _reply(200, {})
        return _err(405, f"{method} is not supported.", {"Allow": "GET, POST, DELETE, LOCK, UNLOCK"})
