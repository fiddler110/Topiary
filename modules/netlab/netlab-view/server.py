"""netlab-view: read-only page of a pod's topology and each node's live state.

GET /                 the page          GET /api/me        {user, facilitator, pods}
GET /api/pod/<n>      one pod's state   GET /healthz /readyz
Trust: the route is gate `identity`; X-Auth-User counts only with the right X-Gateway-Token (dojo_http). A student
may read only their own pod; the facilitator may read every pod. Pod numbers are validated integers, and every
command sent to a node is a constant, so nothing a caller sends reaches a shell.
State is read over SSH with netlab-checker/checker.py (copied next to this file in the image). One collection per pod
is shared by every request for TTL seconds, so the class polling costs a bounded number of SSH sessions.
"""
import concurrent.futures
import json
import os
import re
import sys
import threading
import time
import urllib.request
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

HERE = os.path.dirname(os.path.abspath(__file__))
# checker: ../netlab-checker in the source tree, next to this file in the image. dojo_http: modules/_shared/ or ./_shared/.
sys.path[:0] = [os.path.join(HERE, "..", "netlab-checker"), os.path.join(HERE, "..", "..", "_shared"),
                os.path.join(HERE, "_shared"), HERE]
import checker  # noqa: E402
import dojo_http  # noqa: E402

STATIC_DIR = os.environ.get("STATIC_DIR", os.path.join(HERE, "static"))
FILES = {
    "/": ("index.html", "text/html; charset=utf-8"),
    "/static/app.css": ("app.css", "text/css; charset=utf-8"),
    "/static/app.js": ("app.js", "text/javascript; charset=utf-8"),
    "/static/favicon.svg": ("favicon.svg", "image/svg+xml"),
}
MARK = "@@@@"
MGMT_PREFIX = "10.80.0."
RULE_LIMIT = 40
ROLES = ("pc", "sw", "fw", "web")
IP = checker.PC_TO_WEB

# Constant commands: node state, then (after MARK) the role's extra. Output is parsed, cleaned and bounded below.
PROBES = (f"(ping -c1 -W2 {IP} >/dev/null 2>&1 && echo ping ok || echo ping fail) & "
          f"(echo http $(curl -ks -o /dev/null -m 2 -w %{{http_code}} http://{IP}/)) & "
          f"(echo https $(curl -ks -o /dev/null -m 2 -w %{{http_code}} https://{IP}/)) & wait; true")
EXTRA = {"pc": PROBES, "sw": "bridge -j vlan show", "fw": "iptables -S LAB", "web": "true"}


def command(role):
    return f"ip -j addr; echo {MARK}; {EXTRA[role]}"


def parse_ifaces(text):
    """[{name, state, addrs}] for the data interfaces (no lo, no management interface)."""
    try:
        data = json.loads(text)
    except ValueError:
        return []
    out = []
    for e in data if isinstance(data, list) else []:
        name = e.get("ifname")
        addrs = [f"{a.get('local')}/{a.get('prefixlen')}" for a in e.get("addr_info", []) if a.get("family") == "inet"]
        if not name or name == "lo" or any(a.startswith(MGMT_PREFIX) for a in addrs):
            continue
        state = str(e.get("operstate", "UNKNOWN")).lower()
        out.append({"name": checker.clean(name, 32), "state": "up" if state in ("up", "unknown") else "down",
                    "addrs": [checker.clean(a, 32) for a in addrs]})
    return sorted(out, key=lambda i: i["name"])


def parse_vlans(text):
    ports = checker.vlan_ports(text)
    return [{"port": checker.clean(p, 32),
             "vlans": [{"id": v, "pvid": "pvid" in f, "untagged": "egress untagged" in f}
                       for v, f in sorted(vl.items(), key=lambda kv: (kv[0] is None, kv[0]))]}
            for p, vl in sorted(ports.items(), key=lambda kv: str(kv[0])) if isinstance(p, str)]


def parse_rules(text):
    rules = [checker.clean(l.strip(), 160) for l in text.splitlines() if l.startswith("-A LAB ")]
    return rules[:RULE_LIMIT]


def parse_probes(text):
    got = dict(l.split(" ", 1) for l in text.splitlines() if " " in l)
    http = {}
    for k in ("http", "https"):
        code = got.get(k, "").strip()
        http[k] = code if re.fullmatch(r"\d{3}", code) and code != "000" else "blocked"
    return {"ping": "ok" if got.get("ping", "").strip() == "ok" else "blocked", **http}


def node_state(role, name, rc, out):
    """One node's document from its SSH result."""
    if rc == 255:
        return {"name": name, "role": role, "up": False}, None
    base, _, extra = out.partition(MARK)
    node = {"name": name, "role": role, "up": True, "ifaces": parse_ifaces(base)}
    if role == "sw":
        node["vlans"] = parse_vlans(extra)
    elif role == "fw":
        node["rules"] = parse_rules(extra)
    return node, parse_probes(extra) if role == "pc" else None


def collect(cfg, pod, runner=checker.ssh):
    """The pod's state: per branch the nodes and the pc's probes of the web node."""
    roles = [r for r in ROLES if r != "sw" or cfg.switch]
    refs = [(b, r) for b in cfg.branches() for r in roles]
    with concurrent.futures.ThreadPoolExecutor(max_workers=8) as pool:
        futs = {ref: pool.submit(runner, cfg, pod, ref[0], ref[1], command(ref[1])) for ref in refs}
        res = {ref: f.result() for ref, f in futs.items()}
    branches = []
    for b in cfg.branches():
        nodes, probes = [], None
        for r in roles:
            name = f"{r}-{b}-{pod:02d}"
            rc, out = res[(b, r)]
            got, p = node_state(r, name, rc, out)
            probes = p if p is not None else probes
            nodes.append(got)
        branches.append({"branch": b, "label": "Manual" if b == "m" else "Automated", "nodes": nodes,
                         "probes": probes})
    return {"pod": pod, "user": cfg.user_of(pod), "branches": branches}


class Cache:
    """One collection per pod per TTL, however many requests ask; at most LIMIT collections at once."""

    def __init__(self, cfg, ttl=4.0, limit=3, runner=checker.ssh, last=None, clock=time.monotonic):
        self.cfg, self.ttl, self.runner, self.last, self.clock = cfg, ttl, runner, last, clock
        self.sem = threading.BoundedSemaphore(limit)
        self.locks, self.data, self.guard = {}, {}, threading.Lock()

    def get(self, pod):
        with self.guard:
            lock = self.locks.setdefault(pod, threading.Lock())
        with lock:
            hit = self.data.get(pod)
            if hit and self.clock() - hit[0] < self.ttl:
                return hit[1]
            with self.sem:
                doc = collect(self.cfg, pod, self.runner)
            doc["checks"] = self.last(pod) if self.last else {}
            doc["updated"] = int(time.time())
            self.data[pod] = (self.clock(), doc)
            return doc


def fetch_last(cfg, url):
    """pod -> {lab: {ok, passed, total, time}} from netlab-checker's GET /last/<pod>; {} when it does not answer."""
    def get(pod):
        req = urllib.request.Request(f"{url}/last/{pod}", headers={"X-Netlab-View-Token": checker.view_token(cfg.seed)})
        try:
            with urllib.request.urlopen(req, timeout=3) as r:
                labs = json.load(r).get("labs", {})
        except (OSError, ValueError):
            return {}
        return {str(k): {f: v.get(f) for f in ("ok", "passed", "total", "time")}
                for k, v in labs.items() if isinstance(v, dict)} if isinstance(labs, dict) else {}
    return get


def authorize(cfg, user, pod):
    """(status, reason) for USER reading POD: students only their own, the facilitator any."""
    own = cfg.pod_of(user)
    if own is None:
        return 403, "not allowed"
    if user == cfg.facilitator:
        return (200, "") if 0 <= pod <= cfg.count else (404, "no such pod")
    return (200, "") if pod == own else (403, "not your pod")


def make_handler(cfg, cache, token):
    class H(BaseHTTPRequestHandler):
        server_version = "netlab-view"
        sys_version = ""

        def log_message(self, fmt, *args):
            pass

        def _json(self, status, obj):
            dojo_http.send_json(self, status, obj)

        def do_HEAD(self):
            self.do_GET()

        def do_GET(self):
            path = self.path.split("?", 1)[0] or "/"
            if path == "/healthz":
                return self._json(200, {"ok": True})
            if path == "/readyz":
                ok = bool(cfg.seed and token)
                return self._json(200 if ok else 503, {"ready": ok})
            user = dojo_http.gateway_user(self.headers, token)
            if not user:
                return self._json(401, {"error": "not signed in"})
            if path == "/api/me":
                own = cfg.pod_of(user)
                if own is None:
                    return self._json(403, {"error": "not allowed"})
                fac = user == cfg.facilitator
                return self._json(200, {"user": user, "facilitator": fac,
                                        "pods": list(range(0, cfg.count + 1)) if fac else [own]})
            m = re.fullmatch(r"/api/pod/(\d{1,4})", path)
            if m:
                pod = int(m.group(1))
                status, why = authorize(cfg, user, pod)
                if status != 200:
                    return self._json(status, {"error": why})
                return self._json(200, cache.get(pod))
            if path in FILES:
                name, ctype = FILES[path]
                if cfg.pod_of(user) is None:
                    return self._json(403, {"error": "not allowed"})
                try:
                    with open(os.path.join(STATIC_DIR, name), "rb") as f:
                        body = f.read()
                except OSError:
                    return self._json(404, {"error": "not found"})
                return dojo_http.send(self, 200, body, ctype)
            self._json(404, {"error": "not found"})
    return H


def main():
    cfg = checker.Config()
    token = os.environ.get("GATEWAY_TOKEN", "")
    if not cfg.seed or not token:
        print("netlab-view: STUDENT_PASSWORD_SEED or GATEWAY_TOKEN is empty; every request will be refused", file=sys.stderr)
    last = fetch_last(cfg, os.environ.get("NETLAB_CHECKER_URL", "http://netlab-checker:8080")) if cfg.seed else None
    cache = Cache(cfg, last=last)
    ThreadingHTTPServer(("0.0.0.0", int(os.environ.get("PORT", "8080"))), make_handler(cfg, cache, token)).serve_forever()


if __name__ == "__main__":
    main()
