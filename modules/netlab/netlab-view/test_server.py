import io
import json
import os
import sys
import threading
import unittest
import urllib.error
import urllib.request
from http.server import ThreadingHTTPServer

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import server  # noqa: E402
checker = server.checker

SEED = "seed"
TOKEN = "tok"
ENV = {"STUDENT_PASSWORD_SEED": SEED, "STUDENT_COUNT": "3"}
IPJ = json.dumps([
    {"ifname": "lo", "operstate": "UNKNOWN", "addr_info": [{"family": "inet", "local": "127.0.0.1", "prefixlen": 8}]},
    {"ifname": "eth0", "operstate": "UP", "addr_info": [{"family": "inet", "local": "10.80.0.5", "prefixlen": 24}]},
    {"ifname": "eth1", "operstate": "UP", "addr_info": [{"family": "inet", "local": "10.10.10.10", "prefixlen": 24}]},
    {"ifname": "eth2", "operstate": "DOWN", "addr_info": []}])
VLAN = json.dumps([{"ifname": "to-pc", "vlans": [{"vlan": 10, "flags": ["PVID", "Egress Untagged"]}]},
                   {"ifname": "to-fw", "vlans": [{"vlan": 10, "flags": []}, {"vlan": 20, "flags": []}]}])


def fake(cfg, pod, branch, role, cmd):
    if branch == "m" and role == "web":
        return 255, ""
    extra = {"pc": "ping ok\nhttp 200\nhttps 000\n", "sw": VLAN, "fw": "-A LAB -p tcp --dport 80 -j ACCEPT\n-P x\n",
             "web": ""}[role]
    return 0, f"{IPJ}\n{server.MARK}\n{extra}"


class Parse(unittest.TestCase):
    def test_ifaces_hide_lo_and_management(self):
        got = server.parse_ifaces(IPJ)
        self.assertEqual([i["name"] for i in got], ["eth1", "eth2"])
        self.assertEqual(got[1]["state"], "down")
        self.assertEqual(got[0]["addrs"], ["10.10.10.10/24"])

    def test_bad_json(self):
        self.assertEqual(server.parse_ifaces("nope"), [])
        self.assertEqual(server.parse_vlans("nope"), [])

    def test_vlans(self):
        v = {p["port"]: p["vlans"] for p in server.parse_vlans(VLAN)}
        self.assertEqual(v["to-pc"], [{"id": 10, "pvid": True, "untagged": True}])
        self.assertEqual([x["untagged"] for x in v["to-fw"]], [False, False])

    def test_rules_only_lab_chain_and_cleaned(self):
        self.assertEqual(server.parse_rules("-P INPUT ACCEPT\n-A LAB -j ACCEPT‮\n"), ["-A LAB -j ACCEPT?"])
        self.assertEqual(len(server.parse_rules("-A LAB -j DROP\n" * 99)), server.RULE_LIMIT)

    def test_probes(self):
        self.assertEqual(server.parse_probes("ping fail\nhttp 200\nhttps 000\n"),
                         {"ping": "blocked", "http": "200", "https": "blocked"})
        self.assertEqual(server.parse_probes("http <script>")["http"], "blocked")

    def test_commands_are_constants(self):
        for r in server.ROLES:
            self.assertTrue(server.command(r).startswith("ip -j addr;"))


class Collect(unittest.TestCase):
    def test_collect_marks_down_nodes_and_probes(self):
        cfg = checker.Config(ENV)
        doc = server.collect(cfg, 2, fake)
        self.assertEqual(doc["user"], "student02")
        m, a = doc["branches"]
        self.assertFalse(m["nodes"][-1]["up"])
        self.assertTrue(a["nodes"][-1]["up"])
        self.assertEqual(a["probes"]["http"], "200")
        self.assertEqual([n["role"] for n in a["nodes"]], ["pc", "sw", "fw", "web"])
        self.assertEqual(a["nodes"][2]["rules"], ["-A LAB -p tcp --dport 80 -j ACCEPT"])

    def test_no_switch_no_manual(self):
        cfg = checker.Config({**ENV, "NETLAB_SWITCH": "0", "NETLAB_MANUAL_BRANCH": "0"})
        doc = server.collect(cfg, 1, fake)
        self.assertEqual(len(doc["branches"]), 1)
        self.assertEqual([n["role"] for n in doc["branches"][0]["nodes"]], ["pc", "fw", "web"])

    def test_cache_collects_once_per_ttl(self):
        calls = []
        now = [0.0]
        cache = server.Cache(checker.Config(ENV), ttl=4, runner=lambda *a: calls.append(a) or fake(*a),
                             last=lambda pod: {"2": {"ok": True}}, clock=lambda: now[0])
        d1 = cache.get(1)
        n = len(calls)
        self.assertIs(cache.get(1), d1)
        self.assertEqual(len(calls), n)
        self.assertEqual(d1["checks"], {"2": {"ok": True}})
        now[0] = 5
        cache.get(1)
        self.assertGreater(len(calls), n)


class Http(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.cfg = checker.Config(ENV)
        cls.srv = ThreadingHTTPServer(("127.0.0.1", 0), server.make_handler(cls.cfg, server.Cache(cls.cfg, runner=fake), TOKEN))
        threading.Thread(target=cls.srv.serve_forever, daemon=True).start()
        cls.base = f"http://127.0.0.1:{cls.srv.server_port}"

    @classmethod
    def tearDownClass(cls):
        cls.srv.shutdown()

    def get(self, path, user=None, token=TOKEN):
        h = {}
        if user:
            h["X-Auth-User"] = user
        if token:
            h["X-Gateway-Token"] = token
        try:
            r = urllib.request.urlopen(urllib.request.Request(self.base + path, headers=h))
            return r.status, r.read(), r.headers
        except urllib.error.HTTPError as e:
            return e.code, e.read(), e.headers

    def test_no_or_wrong_token_is_no_identity(self):
        self.assertEqual(self.get("/api/pod/1", "student01", token=None)[0], 401)
        self.assertEqual(self.get("/api/pod/1", "student01", token="bad")[0], 401)
        self.assertEqual(self.get("/", "student01", token="bad")[0], 401)

    def test_student_sees_only_own_pod(self):
        self.assertEqual(self.get("/api/pod/1", "student01")[0], 200)
        self.assertEqual(self.get("/api/pod/2", "student01")[0], 403)
        self.assertEqual(self.get("/api/pod/0", "student01")[0], 403)
        me = json.loads(self.get("/api/me", "student03")[1])
        self.assertEqual(me, {"user": "student03", "facilitator": False, "pods": [3]})

    def test_facilitator_sees_all(self):
        for n in range(0, 4):
            self.assertEqual(self.get(f"/api/pod/{n}", "root")[0], 200)
        self.assertEqual(self.get("/api/pod/4", "root")[0], 404)
        self.assertEqual(json.loads(self.get("/api/me", "root")[1])["pods"], [0, 1, 2, 3])

    def test_unknown_user_and_bad_paths(self):
        self.assertEqual(self.get("/api/pod/1", "mallory")[0], 403)
        self.assertEqual(self.get("/api/pod/1x", "student01")[0], 404)
        self.assertEqual(self.get("/api/pod/01", "student01")[0], 200)  # same pod, int-parsed

    def test_page_headers_and_health(self):
        status, body, h = self.get("/", "student01")
        self.assertEqual(status, 200)
        self.assertIn("script-src 'self'", h["Content-Security-Policy"])
        self.assertEqual(self.get("/healthz", token=None)[0], 200)
        self.assertEqual(self.get("/readyz", token=None)[0], 200)
        self.assertEqual(self.get("/", "root")[0], 200)


class Static(unittest.TestCase):
    def test_no_inline_script_style_or_innerhtml(self):
        d = os.path.join(os.path.dirname(os.path.abspath(__file__)), "static")
        with open(os.path.join(d, "index.html")) as f, open(os.path.join(d, "app.js")) as j:
            html, js = f.read(), j.read()
        self.assertNotIn("<style", html)
        self.assertNotIn("style=", html)
        self.assertNotRegex(html, r"<script(?![^>]*\bsrc=)")
        self.assertNotIn("innerHTML", js)


class Authorize(unittest.TestCase):
    def test_authorize(self):
        cfg = checker.Config(ENV)
        self.assertEqual(server.authorize(cfg, "student01", 1)[0], 200)
        self.assertEqual(server.authorize(cfg, "student01", 2)[0], 403)
        self.assertEqual(server.authorize(cfg, "student09", 9)[0], 403)


if __name__ == "__main__":
    unittest.main()
