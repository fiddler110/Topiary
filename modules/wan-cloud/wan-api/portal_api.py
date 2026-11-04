"""The Dojo WAN portal on port 8080: static files at /wan/ and a small JSON API at /wan/api/.

Trust: identity is taken from X-Auth-User ONLY when the request also carries X-Gateway-Token equal to $GATEWAY_TOKEN
(students can curl wan-api directly on workshop_lab, so a missing or wrong token means no identity at all; an unset
token fails closed). Only Caddy sets both headers.

  GET  /wan/api/me                              {"user", "facilitator", "orgs": [{"id", "name", "user"}]}
  GET  /wan/api/orgs/{org}                      the org store (events: newest 200); own org, or any for the facilitator
  GET  /wan/api/orgs/{org}/devices/{id}/config  the rendered Junos `set` preview, text/plain
  POST /wan/api/orgs/{org}/drift                facilitator only, with X-Requested-With: dojo-admin: one canned
                                                out-of-band change, logged as actor "portal:facilitator"
"""
import hmac
import json
import mimetypes
import os
import re

from mist_api import ApiError, MistApi

CSP = ("default-src 'self'; script-src 'self'; style-src 'self'; img-src 'self' data:; connect-src 'self'; "
       "base-uri 'none'; form-action 'none'; frame-ancestors 'self'")
SECURITY_HEADERS = {
    "Content-Security-Policy": CSP,
    "X-Frame-Options": "SAMEORIGIN",   # only the /admin workspace (same origin) frames this page
    "X-Content-Type-Options": "nosniff",
    "Referrer-Policy": "no-referrer",
    "Cache-Control": "no-store",
}
# Content types we state ourselves; mimetypes would depend on the machine's tables.
TYPES = {".html": "text/html; charset=utf-8", ".js": "text/javascript; charset=utf-8",
         ".css": "text/css; charset=utf-8", ".svg": "image/svg+xml", ".json": "application/json",
         ".png": "image/png", ".ico": "image/x-icon", ".txt": "text/plain; charset=utf-8"}
FILE_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]*$")   # one flat file name: no slashes, no dotfiles
DRIFT_ACTOR = "portal:facilitator"


def _headers(extra=None):
    out = dict(SECURITY_HEADERS)
    out.update(extra or {})
    return out


def _json(status, obj, headers=None):
    return status, _headers({"Content-Type": "application/json; charset=utf-8", **(headers or {})}), json.dumps(obj).encode()


def _err(status, detail):
    return _json(status, {"detail": detail})


class Portal:
    def __init__(self, app, env):
        self.app = app
        self.env = env
        self.dir = env.get("PORTAL_DIR", os.path.join(os.path.dirname(os.path.abspath(__file__)), "portal"))

    def dispatch(self, method, path, headers, read_body=None):
        """-> (status, headers, bytes) for anything under /wan."""
        low = path.rstrip("/") or "/"
        if path == "/wan":
            return 301, _headers({"Location": "/wan/"}), b""
        if low.startswith("/wan/api/") or low == "/wan/api":
            return self.api(method, [p for p in path.split("/") if p][2:], headers)
        if method not in ("GET", "HEAD"):
            return _err(405, "method not allowed")
        return self.static(path[len("/wan/"):] or "index.html")

    def static(self, name):
        if not FILE_RE.match(name):
            return _err(404, "not found")
        ctype = TYPES.get(os.path.splitext(name)[1].lower()) or mimetypes.guess_type(name)[0] or "application/octet-stream"
        try:
            with open(os.path.join(self.dir, name), "rb") as f:
                data = f.read()
        except OSError:
            return _err(404, "not found")
        return 200, _headers({"Content-Type": ctype, "Cache-Control": "no-cache"}), data

    # ---- identity ----------------------------------------------------------------------------------------------
    def identity(self, headers):
        """-> (user, None) or (None, error response)."""
        expected = self.env.get("GATEWAY_TOKEN") or ""
        if not expected:
            return None, _err(503, "The portal is not configured (GATEWAY_TOKEN is unset).")
        given = headers.get("X-Gateway-Token") or ""
        user = headers.get("X-Auth-User") or ""
        if not user or not hmac.compare_digest(given.encode(), expected.encode()):
            return None, _err(401, "Sign in through the gateway.")
        if user not in self.app.auth.org_of:
            return None, _err(403, "You are not part of this workshop.")
        return user, None

    def api(self, method, segs, headers):
        user, err = self.identity(headers)
        if err:
            return err
        auth = self.app.auth
        try:
            if segs == ["me"]:
                return self.only(method, "GET") or _json(200, {"user": user, "facilitator": auth.is_facilitator(user),
                                                               "orgs": auth.orgs_for(user)})
            if len(segs) >= 2 and segs[0] == "orgs":
                org = self.app.mist.org_for(user, segs[1])
                if len(segs) == 2:
                    return self.only(method, "GET") or _json(200, org.snapshot(events=200))
                if len(segs) == 5 and segs[2] == "devices" and segs[4] == "config":
                    return self.only(method, "GET") or self.config(org, segs[3])
                if len(segs) == 3 and segs[2] == "drift":
                    return self.only(method, "POST") or self.drift(org, user, headers)
        except ApiError as exc:
            return _err(exc.status, exc.detail)
        return _err(404, "not found")

    @staticmethod
    def only(method, *allowed):
        return None if method in allowed else _err(405, "method not allowed")

    def config(self, org, dev_id):
        with org.lock:
            if not any(e["id"] == dev_id for e in org.data["inventory"]):
                raise ApiError(404, "device not found")
        status, text, hdrs = self.app.mist.render_text(org, dev_id)
        return status, _headers(hdrs), text.encode()

    def drift(self, org, user, headers):
        """One canned change made 'by hand' in the portal, for plan to find. Needs the facilitator and a custom
        header (a form on another site cannot set it): the usual CSRF guard for a POST."""
        if not self.app.auth.is_facilitator(user):
            return _err(403, "Only the facilitator can make drift.")
        if headers.get("X-Requested-With") != "dojo-admin":
            return _err(403, "Missing X-Requested-With: dojo-admin.")
        change = make_drift(org)
        return _json(200, change)


def make_drift(org):
    """The canned change: the first network's VLAN id moves (to 999, or 998 if it already is 999). With no network
    yet, a service policy that allows everything appears instead. -> a short description of what changed."""
    import time
    import uuid
    path = f"/api/v1/orgs/{org.data['org']['id']}"
    with org.lock:
        nets = list(org.data["networks"].values())      # oldest first: the dict keeps creation order
        if nets:
            net = nets[0]
            old = net.get("vlan_id")
            net["vlan_id"] = "998" if str(old) == "999" else "999"
            net["modified_time"] = int(time.time())
            org.event(DRIFT_ACTOR, f"update network '{net.get('name', '')}' vlan_id {old} -> {net['vlan_id']}",
                      f"{path}/networks/{net['id']}")
            change = {"changed": "network", "id": net["id"], "name": net.get("name"), "field": "vlan_id",
                      "from": old, "to": net["vlan_id"]}
        else:
            t = int(time.time())
            pid = str(uuid.uuid4())
            org.data["servicepolicies"][pid] = {"id": pid, "org_id": org.data["org"]["id"], "name": "drift-allow-all",
                                                "action": "allow", "services": ["any"], "tenants": ["any"],
                                                "created_time": t, "modified_time": t}
            org.event(DRIFT_ACTOR, "create service policy 'drift-allow-all'", f"{path}/servicepolicies/{pid}")
            change = {"changed": "servicepolicy", "id": pid, "name": "drift-allow-all"}
        org.save()
    return change
