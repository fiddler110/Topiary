"""netlab-ansible pack: each lab milestone fires on a passing `dojo netlab check <lab>` and on no other lab or exit."""
import os
import sys
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
sys.path.insert(0, os.path.join(HERE, "..", "catalog"))
import catalog  # noqa: E402
import ledger as lg  # noqa: E402
import matcher as mt  # noqa: E402

PACK = os.path.join(HERE, "..", "..", "..", "workshops", "netlab-ansible")
SHARED = os.path.join(HERE, "..", "catalog", "shared.json")
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


if __name__ == "__main__":
    unittest.main()
