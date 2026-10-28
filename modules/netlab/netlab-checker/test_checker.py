import json
import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(__file__))
import checker  # noqa: E402

SEED = "test-seed"
ENV = {"STUDENT_PASSWORD_SEED": SEED, "STUDENT_COUNT": "3", "FACILITATOR_USERNAME": "root"}
VLAN_OK = json.dumps([
    {"ifname": "to-pc", "vlans": [{"vlan": 10, "flags": ["PVID", "Egress Untagged"]}]},
    {"ifname": "to-web", "vlans": [{"vlan": 20, "flags": ["PVID", "Egress Untagged"]}]},
    {"ifname": "to-fw", "vlans": [{"vlan": 10}, {"vlan": 20}]}])


def cfg(**kw):
    return checker.Config(dict(ENV, **kw))


def fake(table):
    """Runner: table maps (role, substring of command) -> (rc, out); default (0, '')."""
    def run(c, pod, branch, role, cmd):
        for (r, sub), v in table.items():
            if r == role and sub in cmd:
                return v(branch) if callable(v) else v
        return 0, ""
    return run


class Keys(unittest.TestCase):
    def test_match_generate_password(self):
        sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
        import generate
        self.assertEqual(checker.pod_password(SEED, 7), generate.password(SEED, 7))

    def test_key_shape(self):
        k = checker.check_key(SEED, "student01")
        self.assertEqual(len(k), 24)
        self.assertNotEqual(k, checker.check_key(SEED, "student02"))

    def test_pods(self):
        c = cfg()
        self.assertEqual(c.pod_of("student02"), 2)
        self.assertEqual(c.pod_of("root"), 0)
        for bad in ("student04", "student00", "student2", "student002", "x", "", None, "student01;id"):
            self.assertIsNone(c.pod_of(bad), bad)


class Handle(unittest.TestCase):
    def body(self, user="student01", lab="1", key=None):
        return {"user": user, "key": checker.check_key(SEED, user) if key is None else key, "lab": lab}

    def test_wrong_key_and_other_user(self):
        c, lim = cfg(), checker.RateLimit(5, 60)
        self.assertEqual(checker.handle(c, lim, self.body(key="nope"))[0], 403)
        other = self.body(user="student01", key=checker.check_key(SEED, "student02"))
        self.assertEqual(checker.handle(c, lim, other)[0], 403)
        self.assertEqual(checker.handle(c, lim, "x")[0], 400)

    def test_unknown_lab(self):
        self.assertEqual(checker.handle(cfg(), checker.RateLimit(5, 60), self.body(lab="99"))[0], 400)

    def test_rate_limit_per_user(self):
        now = [0.0]
        lim = checker.RateLimit(2, 60, clock=lambda: now[0])
        c, run = cfg(), fake({})
        self.assertEqual(checker.handle(c, lim, self.body(), run)[0], 200)
        self.assertEqual(checker.handle(c, lim, self.body(), run)[0], 200)
        self.assertEqual(checker.handle(c, lim, self.body(), run)[0], 429)
        self.assertEqual(checker.handle(c, lim, self.body(user="student02"), run)[0], 200)
        now[0] = 61
        self.assertEqual(checker.handle(c, lim, self.body(), run)[0], 200)

    def test_facilitator(self):
        st, r = checker.handle(cfg(), checker.RateLimit(5, 60), self.body(user="root", lab="0"), fake({}))
        self.assertEqual(st, 200)
        self.assertTrue(r["ok"])


class Labs(unittest.TestCase):
    def run_lab(self, lab, table, **kw):
        return checker.run_check(cfg(**kw), 1, lab, fake(table))

    def failed(self, r):
        return [a["name"] for a in r["assertions"] if not a["ok"]]

    def test_lab0_unreachable(self):
        r = self.run_lab("0", {("sw", "true"): (255, "")})
        self.assertFalse(r["ok"])
        self.assertTrue(all("sw node" in n for n in self.failed(r)))
        self.assertEqual(len(self.failed(r)), 2)  # sw-m, sw-a

    def test_lab1(self):
        r = self.run_lab("1", {("web", "index.html"): (0, "<p>nginx default page.</p>")})
        self.assertFalse(r["ok"])
        r = self.run_lab("1", {("web", "index.html"): (0, "<h1>mine</h1>")})
        self.assertTrue(r["ok"], r)

    def test_lab2_open_too_much(self):
        table = {("pc", "for p in"): (0, "open 80\nopen 22\n"), ("pc", "curl"): (0, "200"),
                 ("fw", "iptables -S"): (0, "-A LAB -p tcp --dport 443 -j ACCEPT")}
        r = self.run_lab("2", table, NETLAB_MANUAL_BRANCH="0")
        self.assertEqual(self.failed(r), ["[A] ports 22 and 8080 blocked from pc"])
        self.assertIn("22", r["assertions"][1]["detail"])

    def test_lab2_pass_with_match(self):
        table = {("pc", "for p in"): (0, "open 80\n"), ("pc", "curl"): (0, "200"),
                 ("fw", "iptables -S"): (0, "--dport 443"), ("fw", "iptables-save"): (0, "-A LAB -j X\n# c\n:LAB - [0:0]")}
        r = self.run_lab("2", table)
        self.assertTrue(r["ok"], self.failed(r))
        self.assertTrue(any(a["name"].startswith("branches match") for a in r["assertions"]))
        self.assertTrue(any(a["name"].startswith("[M]") for a in r["assertions"]))

    def test_branches_differ(self):
        table = {("pc", "for p in"): (0, "open 80\n"), ("pc", "curl"): (0, "200"), ("fw", "iptables -S"): (0, "--dport 443"),
                 ("fw", "iptables-save"): lambda b: (0, "-A LAB -j " + ("ACCEPT" if b == "a" else "DROP"))}
        r = self.run_lab("2", table)
        self.assertEqual(self.failed(r), ["branches match: fw rules (iptables-save)"])
        self.assertIn("only in M", r["assertions"][-2]["detail"])

    def test_normalise(self):
        self.assertEqual(checker.norm("# x\n:INPUT ACCEPT [1:2]\n-A a\n"), checker.norm("-A a"))

    def test_lab3(self):
        r = self.run_lab("3", {("pc", "curl"): (0, "000"), ("web", "test -f"): (1, "")}, NETLAB_MANUAL_BRANCH="0")
        self.assertEqual(len(self.failed(r)), 2)

    def test_lab4(self):
        good = "maxauthtries 3\nlogingracetime 20\nx11forwarding no\n"
        self.assertTrue(self.run_lab("4", {("web", "sshd -T"): (0, good)}, NETLAB_MANUAL_BRANCH="0")["ok"])
        r = self.run_lab("4", {("web", "sshd -T"): (0, good.replace("3", "6"))}, NETLAB_MANUAL_BRANCH="0")
        self.assertIn("maxauthtries is 6", r["assertions"][0]["detail"])

    def test_lab5(self):
        self.assertTrue(self.run_lab("5", {("pc", "curl"): (0, "401")}, NETLAB_MANUAL_BRANCH="0")["ok"])
        self.assertFalse(self.run_lab("5", {("pc", "curl"): (0, "200")}, NETLAB_MANUAL_BRANCH="0")["ok"])

    def test_lab6(self):
        scan = (0, "open 80\nopen 443\n")
        ok = self.run_lab("6", {("pc", "for p in"): scan, ("pc", "ping"): (1, "")}, NETLAB_MANUAL_BRANCH="0")
        self.assertTrue(ok["ok"], ok)
        bad = self.run_lab("6", {("pc", "for p in"): (0, "open 80\nopen 8080\n"), ("pc", "ping"): (0, "")},
                           NETLAB_MANUAL_BRANCH="0")
        self.assertEqual(len(self.failed(bad)), 3)

    def test_lab7(self):
        r = self.run_lab("7", {})
        self.assertTrue(r["ok"])
        self.assertEqual(r["assertions"][0]["detail"], "check by running compare.yml")

    def test_lab8(self):
        table = {("pc", "for p in"): (0, "open 80\nopen 443\n"), ("pc", "curl"): (0, "200"),
                 ("pc", "ping"): (1, ""), ("fw", "iptables -S"): (0, "--dport 443"),
                 ("fw", "iptables-save"): (0, "x"), ("web", "sshd -T"): (0, "maxauthtries 3\nlogingracetime 20\nx11forwarding no"),
                 ("web", "test -f"): (0, ""), ("web", "cat /etc"): (0, "server {}")}
        r = self.run_lab("8", table)
        self.assertTrue(r["ok"], self.failed(r))
        self.assertFalse(any(a["name"].startswith("[M]") for a in r["assertions"]))
        self.assertEqual(sum(a["name"].startswith("branches") for a in r["assertions"]), 2)

    def test_switch_labs(self):
        table = {("sw", "bridge"): (0, VLAN_OK), ("pc", "ping"): (0, ""), ("pc", "for p in"): (0, "open 80\nopen 443\n")}
        for lab in ("S1", "S2"):
            self.assertTrue(self.run_lab(lab, table, NETLAB_MANUAL_BRANCH="0")["ok"], lab)
        bad = json.dumps([{"ifname": "to-pc", "vlans": [{"vlan": 10, "flags": ["PVID"]}]}])
        self.assertFalse(self.run_lab("S1", {("sw", "bridge"): (0, bad)}, NETLAB_MANUAL_BRANCH="0")["ok"])
        self.assertFalse(self.run_lab("S2", {("sw", "bridge"): (0, bad)}, NETLAB_MANUAL_BRANCH="0")["ok"])

    def test_s3_attacker_view(self):
        t = {("pc", "for p in"): (0, "open 80\nopen 443\nopen 3306\n"), ("fw", "iptables -S"): (0, "--dport 443")}
        r = self.run_lab("S3", t, NETLAB_MANUAL_BRANCH="0")
        self.assertIn("attacker view", self.failed(r)[-1])
        self.assertIn("3306", r["assertions"][-1]["detail"])

    def test_s_needs_switch(self):
        self.assertIsNone(self.run_lab("S1", {}, NETLAB_SWITCH="0"))

    def test_output_is_cleaned(self):
        r = self.run_lab("5", {("pc", "curl"): (0, "4\x1b[31m\nxx" + "A" * 500)}, NETLAB_MANUAL_BRANCH="0")
        d = r["assertions"][0]["detail"]
        self.assertNotIn("\x1b", d)
        self.assertLess(len(d), 40)

    def test_ssh_argv_has_no_password(self):
        seen = {}
        orig = checker.subprocess.run

        def fake_run(argv, **kw):
            seen.update(argv=argv, env=kw["env"])
            class P: returncode, stdout = 0, b"ok"
            return P
        checker.subprocess.run = fake_run
        try:
            checker.ssh(cfg(), 3, "a", "pc", "true")
        finally:
            checker.subprocess.run = orig
        self.assertNotIn(checker.pod_password(SEED, 3), " ".join(seen["argv"]))
        self.assertEqual(seen["env"]["SSHPASS"], checker.pod_password(SEED, 3))
        self.assertIn("root@pc-a-03", seen["argv"])
        self.assertIn("ConnectTimeout=5", seen["argv"])

    def test_remember_keeps_latest_verdict_per_pod_and_lab(self):
        store = {}
        res = {"lab": "2", "ok": False, "assertions": [{"ok": True}, {"ok": False}]}
        checker.remember(3, res, store, now=lambda: 100)
        self.assertEqual(store[3]["2"], {"ok": False, "passed": 1, "total": 2, "time": 100})
        checker.remember(3, {"lab": "2", "ok": True, "assertions": [{"ok": True}]}, store, now=lambda: 200)
        self.assertEqual(store[3]["2"]["time"], 200)
        self.assertNotIn(4, store)

    def test_view_token_differs_from_check_keys(self):
        self.assertNotEqual(checker.view_token(SEED), checker.check_key(SEED, "student01"))


if __name__ == "__main__":
    unittest.main()
