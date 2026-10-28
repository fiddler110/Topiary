#!/usr/bin/env python3
"""netlab-checker: POST /check {user, key, lab} -> the lab's assertions run against that student's pod.

Trust: the key is HMAC-SHA256(STUDENT_PASSWORD_SEED, "netlab-check:<user>") in the same encoding as the pod
password, written to ~/.config/dojo/netlab-check-key by the terminal. A caller can only name itself. Nothing the
caller sends reaches a shell: the pod number comes from the validated user name, the lab from a fixed table.
Nodes are reached with `sshpass -e ssh root@<role>-<branch>-<NN>` on netlab_mgmt; the password goes in SSHPASS.
"""
import base64
import concurrent.futures
import hashlib
import hmac
import json
import os
import re
import subprocess
import sys
import threading
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

PC_TO_WEB = "10.10.20.10"
SCAN_PORTS = (22, 23, 25, 80, 443, 8080, 8443)
WIDE_SCAN = (21, 22, 23, 25, 53, 110, 111, 139, 143, 445, 3306, 3389, 5432, 6379, 8000, 8080, 8443, 9090)
SSH_TIMEOUT = 25


def derive(seed, label):
    """Same encoding as generate.password(): base32 of the HMAC, first 24, lowercase."""
    mac = hmac.new(seed.encode(), label.encode(), hashlib.sha256).digest()
    return base64.b32encode(mac).decode()[:24].lower()


def pod_password(seed, pod):
    return derive(seed, f"netlab:{pod:02d}")


def check_key(seed, user):
    return derive(seed, f"netlab-check:{user}")


def view_token(seed):
    """What netlab-view sends (X-Netlab-View-Token) to read GET /last; students never see it."""
    return derive(seed, "netlab-view")


def clean(text, limit=200):
    """Text safe to log or show: printable ASCII only, bounded."""
    return re.sub(r"[^\x20-\x7e]", "?", str(text))[:limit]


class Config:
    def __init__(self, env=None):
        env = os.environ if env is None else env
        self.seed = env.get("STUDENT_PASSWORD_SEED", "")
        self.prefix = env.get("STUDENT_PREFIX", "student") or "student"
        self.count = int(env.get("STUDENT_COUNT", "30") or 30)
        self.facilitator = env.get("FACILITATOR_USERNAME", "root") or "root"
        self.manual = env.get("NETLAB_MANUAL_BRANCH", "1") != "0"
        self.switch = env.get("NETLAB_SWITCH", "1") != "0"
        self.rate_max = int(env.get("NETLAB_CHECK_RATE_MAX", "6"))
        self.rate_window = float(env.get("NETLAB_CHECK_RATE_WINDOW", "60"))

    def pod_of(self, user):
        """Pod number for a user name, or None."""
        if not isinstance(user, str):
            return None
        if user == self.facilitator:
            return 0
        m = re.fullmatch(re.escape(self.prefix) + r"(\d{1,4})", user)
        if not m:
            return None
        n = int(m.group(1))
        if user != f"{self.prefix}{n:02d}" or not 1 <= n <= self.count:
            return None
        return n

    def branches(self):
        return ("m", "a") if self.manual else ("a",)


# --- assertions --------------------------------------------------------------------------------------------
# An assertion: name, refs [(branch, role, command)], test(results) -> (ok, detail); results = [(rc, out)] per ref.
# Commands are constants. Output of a command is only ever shown after clean().

class A:
    def __init__(self, name, refs, test):
        self.name, self.refs, self.test = name, refs, test


def one(test):
    return lambda rs: test(*rs[0])


def http_code(port, scheme="http", path="/"):
    return f"curl -ks -o /dev/null -m 3 -w %{{http_code}} {scheme}://{PC_TO_WEB}:{port}{path}"


def scan(ports):
    # In parallel: dropped ports each cost the full -w2, and a wide scan must finish inside SSH_TIMEOUT.
    return ("for p in " + " ".join(str(p) for p in ports) +
            f"; do (nc -z -w2 {PC_TO_WEB} $p && echo open $p) & done; wait; true")


def open_ports(out):
    return {int(m) for m in re.findall(r"^open (\d+)$", out, re.M)}


def a_http(b, port, scheme, name, want):
    def test(rc, out):
        code = out.strip()
        return (code in want if want else code.startswith(("2", "3"))), f"HTTP {clean(code, 8) or 'no answer'}"
    return A(name, [(b, "pc", http_code(port, scheme))], one(test))


def a_blocked(b, ports, label=None):
    def test(rc, out):
        op = open_ports(out) & set(ports)
        return not op, ("blocked" if not op else "reachable: " + ", ".join(map(str, sorted(op))))
    return A(label or f"ports {', '.join(map(str, ports))} blocked from pc", [(b, "pc", scan(SCAN_PORTS))], one(test))


def a_open(b, ports):
    def test(rc, out):
        miss = set(ports) - open_ports(out)
        return not miss, ("reachable" if not miss else "not reachable: " + ", ".join(map(str, sorted(miss))))
    return A(f"ports {', '.join(map(str, ports))} reachable from pc", [(b, "pc", scan(SCAN_PORTS))], one(test))


def a_cmd(b, role, cmd, name, test):
    return A(name, [(b, role, cmd)], one(test))


def t_rc0(ok_text, bad_text):
    return lambda rc, out: (rc == 0, ok_text if rc == 0 else bad_text)


def a_ping_blocked(b):
    return a_cmd(b, "pc", f"ping -c1 -W2 {PC_TO_WEB} >/dev/null 2>&1", "ping from pc to web is blocked",
                 lambda rc, out: (rc != 0, "blocked" if rc != 0 else "ping works"))


def a_ping_works(b):
    return a_cmd(b, "pc", f"ping -c1 -W2 {PC_TO_WEB} >/dev/null 2>&1", "pc can ping web",
                 t_rc0("ping works", "ping fails"))


def lab1(b):
    def test(rc, out):
        if rc != 0:
            return False, "no index.html"
        return "nginx default page" not in out, "page changed" if "nginx default page" not in out else "still the default page"
    return [a_cmd(b, "web", "cat /var/www/html/index.html", "web index.html is no longer the default page", test)]


def lab2(b):
    return [a_http(b, 80, "http", "HTTP (80) answers from pc", None),
            a_blocked(b, (22, 8080), "ports 22 and 8080 blocked from pc"),
            a_cmd(b, "fw", "iptables -S LAB", "fw LAB chain has a dport 443 rule",
                  lambda rc, out: ("--dport 443" in out, "rule present" if "--dport 443" in out else "no dport 443 rule"))]


def lab3(b):
    return [a_http(b, 443, "https", "HTTPS (443) returns 200 from pc", {"200"}),
            a_cmd(b, "web", "test -f /etc/nginx/tls/web.crt", "web has /etc/nginx/tls/web.crt",
                  t_rc0("present", "missing"))]


def lab4(b):
    want = {"maxauthtries": "3", "logingracetime": "20", "x11forwarding": "no"}

    def test(rc, out):
        got = {}
        for line in out.splitlines():
            k, _, v = line.partition(" ")
            got[k.lower()] = v.strip().lower()
        bad = [f"{k} is {got.get(k, '?')}, want {v}" for k, v in want.items() if got.get(k) != v]
        return not bad, "; ".join(bad) or "maxauthtries 3, logingracetime 20, x11forwarding no"
    return [a_cmd(b, "web", "sshd -T", "sshd on web: MaxAuthTries 3, LoginGraceTime 20, X11Forwarding no", test)]


def lab6(b):
    return [a_open(b, (80, 443)),
            a_blocked(b, (22, 23, 25, 8080, 8443)),
            a_ping_blocked(b)]


def vlan_ports(out):
    """{ifname: {vlan: set(flags)}} from `bridge -j vlan show`."""
    res = {}
    try:
        data = json.loads(out)
    except ValueError:
        return res
    for e in data if isinstance(data, list) else []:
        res[e.get("ifname")] = {v.get("vlan"): {str(f).lower() for f in v.get("flags", [])} for v in e.get("vlans", [])}
    return res


def s1(b):
    def test(rc, out):
        p = vlan_ports(out)
        bad = []
        for port, vlan in (("to-pc", 10), ("to-web", 20)):
            f = p.get(port, {}).get(vlan)
            if f is None or "pvid" not in f or "egress untagged" not in f:
                bad.append(f"{port} needs VLAN {vlan} as pvid untagged")
        return not bad, "; ".join(bad) or "to-pc 10 and to-web 20 are untagged access ports"
    return [a_cmd(b, "sw", "bridge -j vlan show", "switch access ports: to-pc pvid 10, to-web pvid 20, untagged", test)]


def s2(b):
    def test(rc, out):
        p = vlan_ports(out).get("to-fw", {})
        bad = [f"to-fw needs VLAN {v} tagged" for v in (10, 20) if v not in p or "egress untagged" in p[v]]
        return not bad, "; ".join(bad) or "to-fw carries 10 and 20 tagged"
    return [a_cmd(b, "sw", "bridge -j vlan show", "switch trunk: to-fw carries VLANs 10 and 20 tagged", test),
            a_ping_works(b)]


def s3(b):
    def test(rc, out):
        extra = open_ports(out) - {80, 443}
        return not extra, ("nothing else open" if not extra else "open: " + ", ".join(map(str, sorted(extra))))
    # 443 needs a listener (lab 3) to be reachable, and the S labs start from a baseline web server: judge it by the rule.
    return [a_open(b, (80,)),
            a_cmd(b, "fw", "iptables -S LAB", "fw LAB chain has a dport 443 rule",
                  lambda rc, out: ("--dport 443" in out, "rule present" if "--dport 443" in out else "no dport 443 rule")),
            a_blocked(b, (22,), "SSH (22) blocked from pc"),
            A("attacker view: nothing but 80 and 443 is open", [(b, "pc", scan(WIDE_SCAN))], one(test))]


def lab0(b, cfg):
    roles = ("pc", "sw", "fw", "web") if cfg.switch else ("pc", "fw", "web")
    return [A(f"{r} node reachable over SSH", [(b, r, "true")], one(t_rc0("reachable", "no answer"))) for r in roles]


def norm(text):
    return "\n".join(sorted(l.strip() for l in text.splitlines() if l.strip() and l[0] not in "#:"))


def match_assertions():
    def cmp(what):
        def test(rs):
            (rc1, o1), (rc2, o2) = rs
            if rc1 != 0 or rc2 != 0:
                return False, "could not read one of the branches"
            if norm(o1) == norm(o2):
                return True, "same"
            a, b = set(norm(o1).splitlines()), set(norm(o2).splitlines())
            diff = [f"only in M: {clean(l, 80)}" for l in sorted(a - b)[:3]] + \
                   [f"only in A: {clean(l, 80)}" for l in sorted(b - a)[:3]]
            return False, "; ".join(diff) or "different order or duplicates"
        return test
    return [A("branches match: fw rules (iptables-save)", [("m", "fw", "iptables-save"), ("a", "fw", "iptables-save")], cmp("fw")),
            A("branches match: web nginx config", [("m", "web", "cat /etc/nginx/http.d/*.conf"),
                                                   ("a", "web", "cat /etc/nginx/http.d/*.conf")], cmp("web"))]


def info_only(text):
    return lambda b, cfg: [A(text, [], lambda rs: (True, "check by running compare.yml"))]


# lab -> (builder(branch, cfg) -> [A], needs_switch, compare branches). Add a lab by adding a line.
LABS = {
    "0": (lab0, False, False),
    "1": (lambda b, c: lab1(b), False, True),
    "2": (lambda b, c: lab2(b), False, True),
    "3": (lambda b, c: lab3(b), False, True),
    "4": (lambda b, c: lab4(b), False, True),
    "5": (lambda b, c: [a_cmd(b, "pc", http_code(80, "http", "/admin"), "/admin returns 401 without credentials",
                              lambda rc, out: (out.strip() == "401", f"HTTP {clean(out.strip(), 8) or 'no answer'}"))],
          False, True),
    "6": (lambda b, c: lab6(b), False, True),
    "7": (info_only("roles/ directory exists in ~/netlab"), False, False),
    "S1": (lambda b, c: s1(b), True, True),
    "S2": (lambda b, c: s2(b), True, True),
    "S3": (lambda b, c: s3(b), True, True),
}
LAB8 = (lab2, lab3, lab4, lab6)


def build(lab, cfg):
    """[(label or None, A)] for a lab, or None for an unknown lab / one the config cannot run."""
    out = []
    if lab == "8":
        out += [("A", a) for f in LAB8 for a in f("a")]
        if cfg.manual:
            out += [(None, a) for a in match_assertions()]
        return out
    if lab not in LABS:
        return None
    builder, needs_switch, compare = LABS[lab]
    if needs_switch and not cfg.switch:
        return None
    if lab == "7":
        return [(None, a) for a in builder("a", cfg)]
    for b in cfg.branches():
        out += [(b.upper(), a) for a in builder(b, cfg)]
    if compare and cfg.manual and not needs_switch:
        out += [(None, a) for a in match_assertions()]
    return out


# --- running ------------------------------------------------------------------------------------------------

def ssh(cfg, pod, branch, role, cmd):
    """(rc, output) of CMD on root@<role>-<branch>-<NN>. rc 255 = could not connect."""
    host = f"{role}-{branch}-{pod:02d}"
    env = {"SSHPASS": pod_password(cfg.seed, pod), "PATH": os.environ.get("PATH", "/usr/bin:/bin")}
    argv = ["sshpass", "-e", "ssh", "-o", "StrictHostKeyChecking=no", "-o", "UserKnownHostsFile=/dev/null",
            "-o", "LogLevel=ERROR", "-o", "ConnectTimeout=5", "-o", "PreferredAuthentications=password",
            "-o", "PubkeyAuthentication=no", f"root@{host}", cmd]
    try:
        p = subprocess.run(argv, env=env, capture_output=True, timeout=SSH_TIMEOUT, stdin=subprocess.DEVNULL)
    except (subprocess.TimeoutExpired, OSError):
        return 255, ""
    return p.returncode, p.stdout.decode("utf-8", "replace")


def run_check(cfg, pod, lab, runner=ssh):
    plan = build(lab, cfg)
    if plan is None:
        return None
    refs = {r for _, a in plan for r in a.refs}
    with concurrent.futures.ThreadPoolExecutor(max_workers=8) as pool:
        futs = {r: pool.submit(runner, cfg, pod, *r) for r in refs}
        res = {r: f.result() for r, f in futs.items()}
    items = []
    for label, a in plan:
        rs = [res[r] for r in a.refs]
        name = f"[{label}] {a.name}" if label else a.name
        if any(rc == 255 for rc, _ in rs):
            ok, detail = False, "node unreachable"
        else:
            ok, detail = a.test(rs)
        items.append({"name": name, "ok": bool(ok), "detail": clean(detail)})
    return {"lab": lab, "ok": all(i["ok"] for i in items), "assertions": items}


class RateLimit:
    def __init__(self, maximum, window, clock=time.monotonic):
        self.max, self.window, self.clock, self.hits, self.lock = maximum, window, clock, {}, threading.Lock()

    def allow(self, user):
        now = self.clock()
        with self.lock:
            recent = [t for t in self.hits.get(user, []) if now - t < self.window]
            if len(recent) >= self.max:
                self.hits[user] = recent
                return False
            recent.append(now)
            self.hits[user] = recent
            return True


# pod -> {lab: {"ok", "passed", "total", "time"}}: the latest verdict per lab, read by netlab-view.
LAST = {}


def remember(pod, result, store=None, now=time.time):
    store = LAST if store is None else store
    items = result["assertions"]
    store.setdefault(pod, {})[result["lab"]] = {"ok": result["ok"], "passed": sum(1 for i in items if i["ok"]),
                                                "total": len(items), "time": int(now())}


def handle(cfg, limiter, body, runner=ssh):
    """(status, reply dict) for a decoded /check body."""
    if not isinstance(body, dict):
        return 400, {"error": "bad request"}
    user, key, lab = body.get("user"), body.get("key"), body.get("lab")
    pod = cfg.pod_of(user)
    if pod is None or not isinstance(key, str) or not cfg.seed:
        return 403, {"error": "not allowed"}
    if not hmac.compare_digest(key.encode("utf-8", "replace"), check_key(cfg.seed, user).encode()):
        return 403, {"error": "not allowed"}
    if not isinstance(lab, str) or lab.upper() not in {k.upper() for k in (*LABS, "8")}:
        return 400, {"error": "unknown lab"}
    if not limiter.allow(user):
        return 429, {"error": "slow down: too many checks, try again in a minute"}
    result = run_check(cfg, pod, lab.upper() if lab.upper().startswith("S") else lab, runner)
    if result is None:
        return 400, {"error": "that lab needs the switch, which this run does not have"}
    remember(pod, result)
    return 200, result


def make_handler(cfg, limiter, gate=threading.BoundedSemaphore(4)):
    class H(BaseHTTPRequestHandler):
        def log_message(self, fmt, *args):
            sys.stderr.write("netlab-checker: %s\n" % clean(fmt % args))

        def _send(self, status, obj):
            data = json.dumps(obj).encode()
            self.send_response(status)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(data)))
            self.send_header("Cache-Control", "no-store")
            self.send_header("X-Content-Type-Options", "nosniff")
            self.end_headers()
            self.wfile.write(data)

        def do_GET(self):
            if self.path == "/healthz":
                return self._send(200, {"ok": True})
            m = re.fullmatch(r"/last/(\d{1,4})", self.path)
            if m:
                given = self.headers.get("X-Netlab-View-Token") or ""
                if not cfg.seed or not hmac.compare_digest(given.encode(), view_token(cfg.seed).encode()):
                    return self._send(403, {"error": "not allowed"})
                return self._send(200, {"labs": LAST.get(int(m.group(1)), {})})
            self._send(404, {"error": "not found"})

        def do_POST(self):
            if self.path != "/check":
                return self._send(404, {"error": "not found"})
            try:
                n = int(self.headers.get("Content-Length", "0"))
                if not 0 < n <= 2048:
                    return self._send(400, {"error": "bad request"})
                body = json.loads(self.rfile.read(n))
            except (ValueError, UnicodeDecodeError):
                return self._send(400, {"error": "bad request"})
            if not gate.acquire(timeout=30):
                return self._send(429, {"error": "busy, try again"})
            try:
                status, reply = handle(cfg, limiter, body)
            finally:
                gate.release()
            self._send(status, reply)
    return H


def main():
    cfg = Config()
    if not cfg.seed:
        print("netlab-checker: STUDENT_PASSWORD_SEED is empty; every check will be refused", file=sys.stderr)
    srv = ThreadingHTTPServer(("0.0.0.0", 8080), make_handler(cfg, RateLimit(cfg.rate_max, cfg.rate_window)))
    srv.serve_forever()


if __name__ == "__main__":
    main()
