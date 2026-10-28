"""netlab-ansible pack: each lab milestone fires on a passing `dojo netlab check <lab>` and on no other lab or exit;
the capstone is proven by the netlab checker (plugins/netlab `netlab_labs_passed`), asked over HTTP with its own token."""
import json
import os
import sys
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
sys.path.insert(0, os.path.join(HERE, "..", "catalog"))
import catalog  # noqa: E402
import ledger as lg  # noqa: E402
import challenges  # noqa: E402
import matcher as mt  # noqa: E402

PACK = os.path.join(HERE, "..", "..", "..", "workshops", "netlab-ansible")
SHARED = os.path.join(HERE, "..", "catalog", "shared.json")
NETLAB = os.path.join(HERE, "..", "plugins", "netlab")
CORE = os.path.join(HERE, "..", "achievements")
LABS = {"0": "n0-lay-of-land", "1": "n1-first-play", "2": "n2-open-ports", "3": "n3-changed-zero",
        "4": "n4-validated", "5": "n5-vaulted", "6": "n6-rollback", "7": "n7-roles", "8": "n8-capstone",
        "S1": "ns1-vlans", "S2": "ns2-trunk", "S3": "ns3-segment"}


def sh(cmd, exit=0, **kw):
    c = catalog.load(PACK, SHARED)[0]
    return mt.Matcher(lg.Ledger(c, lg.Config()).index).match(mt.shell_event(dict(cmd=cmd, exit=exit, **kw)))


class NetlabPack(unittest.TestCase):
    def test_each_lab_fires_only_for_itself(self):
        for lab, ident in LABS.items():
            got = sh(f"dojo netlab check {lab}")
            self.assertEqual([i for i in got if i in LABS.values()], [ident], lab)

    def test_failed_or_other_commands_do_not_fire(self):
        self.assertEqual([i for i in sh("dojo netlab check 2", 1) if i in LABS.values()], [])
        self.assertIn("f-redcell", sh("dojo netlab check 2", 1))
        self.assertEqual([i for i in sh("dojo check 2") if i in LABS.values()], [])
        self.assertEqual([i for i in sh("echo dojo netlab check 2") if i in LABS.values()], [])
        self.assertNotIn("n1-first-play", sh("dojo netlab check 10"))

    def test_chained_lines_need_the_checks_own_exit(self):
        labs = lambda cmd, code=0: [i for i in sh(cmd, code) if i in LABS.values()]
        self.assertEqual(labs("dojo netlab check 3; echo rc=$?"), [])
        self.assertEqual(labs("dojo netlab check 3 | cat"), [])
        self.assertEqual(labs("dojo netlab check 3 || true"), [])
        self.assertEqual(labs("true; dojo netlab check 3"), ["n3-changed-zero"])
        self.assertEqual(labs("cd ~/netlab && dojo netlab check 3"), ["n3-changed-zero"])
        self.assertEqual(labs("dojo netlab check 3 && echo ok"), ["n3-changed-zero"])

    def test_core_set(self):
        c = catalog.load(PACK, SHARED)[0]
        core = {m["id"] for m in catalog.core_milestones(c)}
        self.assertEqual(core, {LABS[k] for k in "0123468"})

    def test_funny(self):
        self.assertIn("f-reset", sh("ansible-playbook reset_fw.yml -e branch=a"))
        self.assertNotIn("f-reset", sh("ansible-playbook reset_fw.yml", 2))
        self.assertIn("f-drycheck", sh("ansible-playbook labs/2/site.yml --check --diff"))
        self.assertNotIn("f-drycheck", sh("ansible-playbook labs/2/site.yml"))
        self.assertIn("f-unreachable", sh("ansible all -m ping", 4, out="fw-a-07 | UNREACHABLE! => {}"))


class Capstone(unittest.TestCase):
    """The capstone passes only when the checker says every core lab last passed on the asking student's own pod."""

    def setUp(self):
        self.cat = catalog.load(PACK, SHARED)[0]
        self.runner = challenges.Runner(challenges.load_plugins([CORE, NETLAB]), os.path.join(PACK, "achievements", "seeds"),
                                        None, lambda: 0)
        self.mod = self.runner.verbs["netlab_labs_passed"][1]
        self.sent, self.reply = [], {"passed": True, "missing": []}
        self.orig = self.mod._ask
        self.mod._ask = lambda user, labs: self.sent.append((user, labs)) or self.reply
        self.addCleanup(setattr, self.mod, "_ask", self.orig)

    def test_capstone_is_on_and_uses_a_known_verb(self):
        cap = self.cat["capstone"]
        self.assertNotEqual(cap.get("enabled"), False)
        self.assertEqual(self.runner.unknown_verbs(self.cat), [])
        self.assertEqual(cap["verify"][0]["labs"], ["0", "1", "2", "3", "4", "6", "8"])

    def test_asks_for_the_core_labs_of_the_checking_student_only(self):
        self.assertTrue(self.runner.verify(self.cat["capstone"], "student03")["passed"])
        self.assertEqual(self.sent, [("student03", ["0", "1", "2", "3", "4", "6", "8"])])

    def test_missing_labs_are_named(self):
        self.reply = {"passed": False, "missing": ["3", "8"]}
        got = self.runner.verify(self.cat["capstone"], "student03")
        self.assertFalse(got["passed"])
        self.assertIn("3, 8", got["message"])

    def test_cannot_name_another_pod(self):
        ch = dict(self.cat["capstone"], verify=[{"verb": "netlab_labs_passed", "user": "student04", "labs": ["0"]}])
        self.assertFalse(self.runner.verify(ch, "student03")["passed"])
        self.assertEqual(self.sent, [])

    def test_a_malformed_reply_is_not_a_pass(self):
        for reply in ({}, {"passed": "yes"}, {"passed": 1, "missing": []}, {"missing": []}):
            self.reply = reply
            self.assertFalse(self.runner.verify(self.cat["capstone"], "student03")["passed"], reply)

    def test_checker_down_is_try_again_not_a_wrong_answer(self):
        self.mod._ask = self.orig
        env = dict(os.environ)
        self.addCleanup(lambda: (os.environ.clear(), os.environ.update(env)))
        os.environ.pop("NETLAB_PROOF_TOKEN", None)
        os.environ.pop("NETLAB_CHECKER_URL", None)
        with self.assertRaises(self.mod.Unavailable):
            self.runner.verify(self.cat["capstone"], "student03")
        self.assertIn(self.mod.Unavailable, self.runner.errors())

    def test_request_carries_the_token_and_the_user(self):
        self.mod._ask = self.orig
        seen = []

        class R:
            def __enter__(s): return s
            def __exit__(s, *x): return False
            def read(s): return b'{"passed": true, "missing": []}'

        orig, env = self.mod.urllib.request.urlopen, dict(os.environ)
        self.mod.urllib.request.urlopen = lambda req, timeout: seen.append(req) or R()
        os.environ.update(NETLAB_CHECKER_URL="http://netlab-checker:8080/", NETLAB_PROOF_TOKEN="tok")
        try:
            self.mod._ask("student03", ["0"])
        finally:
            self.mod.urllib.request.urlopen = orig
            os.environ.clear()
            os.environ.update(env)
        req = seen[0]
        self.assertEqual(req.full_url, "http://netlab-checker:8080/proof")
        self.assertEqual(req.get_header("X-netlab-proof-token"), "tok")
        self.assertEqual(json.loads(req.data), {"user": "student03", "labs": ["0"]})


if __name__ == "__main__":
    unittest.main()
