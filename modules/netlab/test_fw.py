import importlib.util
import ipaddress
import os
import re
import sys
import unittest

here = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, here)
import generate  # noqa: E402

spec = importlib.util.spec_from_file_location("netlab_fw", os.path.join(here, "terminal", "netlab_fw.py"))
fw = importlib.util.module_from_spec(spec)
spec.loader.exec_module(fw)


class Roster(unittest.TestCase):
    def test_students_then_bots_numbered_like_account_d(self):
        r = fw.roster({"STUDENT_COUNT": "3", "BOT_COUNT": "2"})
        self.assertEqual(r, [("student01", 1), ("student02", 2), ("student03", 3), ("testuser1", 4), ("testuser2", 5)])

    def test_custom_prefixes_and_defaults(self):
        self.assertEqual(fw.roster({"STUDENT_COUNT": "1", "STUDENT_PREFIX": "s", "BOT_COUNT": "1", "BOT_PREFIX": "bot"}),
                         [("s01", 1), ("bot1", 2)])
        self.assertEqual(len(fw.roster({})), 30)


class Rules(unittest.TestCase):
    def rules(self, mapping):
        return fw.build_rules(mapping).splitlines()

    def test_one_return_per_account_for_its_own_block_only(self):
        lines = self.rules({1001: 1, 1002: 2})
        self.assertIn("-A NETLAB_ISOLATION -d 10.80.1.8/29 -m owner --uid-owner 1001 -j RETURN", lines)
        self.assertIn("-A NETLAB_ISOLATION -d 10.80.1.16/29 -m owner --uid-owner 1002 -j RETURN", lines)
        self.assertEqual(sum("--uid-owner 1001" in l for l in lines), 1)
        self.assertEqual(sum("--uid-owner 1002" in l for l in lines), 1)

    def test_root_first_then_accounts_then_rejects_last(self):
        lines = self.rules({1001: 1})
        self.assertEqual(lines[0:2], ["*filter", ":NETLAB_ISOLATION - [0:0]"])
        self.assertEqual(lines[2], "-A NETLAB_ISOLATION -m owner --uid-owner 0 -j RETURN")
        rejects = [i for i, l in enumerate(lines) if "-j DROP" in l]
        returns = [i for i, l in enumerate(lines) if "-j RETURN" in l]
        self.assertEqual(len(rejects), 1)
        self.assertGreater(min(rejects), max(returns))
        self.assertEqual(lines[rejects[0]], "-A NETLAB_ISOLATION -d 10.80.0.0/22 -j DROP")
        self.assertIn("COMMIT", lines)

    def test_drop_covers_the_whole_management_network_only(self):
        for l in self.rules({1001: 1}):
            if "DROP" in l:
                self.assertIn("-d 10.80.0.0/22", l)
        # nothing allows or rejects other destinations
        self.assertFalse([l for l in self.rules({1001: 1}) if l.startswith("-A") and "-d" not in l and "uid-owner 0" not in l])

    def test_uid_zero_never_gets_a_pod_rule(self):
        lines = self.rules({0: 5})
        self.assertEqual(sum("--uid-owner 0" in l for l in lines), 1)

    def test_no_accounts_still_closes_the_network(self):
        lines = self.rules({})
        self.assertEqual(sum("-j DROP" in l for l in lines), 1)

    def test_every_pod_has_its_own_disjoint_block(self):
        nets = [ipaddress.ip_network(fw.pod_block(p)) for p in range(32)]
        self.assertFalse(any(a.overlaps(b) for i, a in enumerate(nets) for b in nets[i + 1:]))
        mgmt = ipaddress.ip_network(fw.MGMT_CIDR)
        self.assertTrue(all(n.subnet_of(mgmt) for n in nets))
        with self.assertRaises(ValueError):
            fw.pod_block(32)


class AgreesWithGenerate(unittest.TestCase):
    def test_constants_match(self):
        self.assertEqual(fw.MGMT_CIDR, generate.MGMT_CIDR)
        self.assertEqual(".".join(map(str, fw.POD_BASE[:3])) + ".", generate.MGMT_POD_BASE)
        self.assertEqual(fw.POD_SIZE, 8)

    def test_every_node_sits_in_its_own_pods_block_and_addresses_are_unique(self):
        env = {"STUDENT_COUNT": "29", "BOT_COUNT": "2", "NETLAB_MAX_STUDENTS": "40", "STUDENT_PASSWORD_SEED": "s"}
        text = generate.render(env)
        seen = set()
        for name, ip in re.findall(r"^  ([a-z]+-[ma]-\d\d):\n(?:    .*\n)*?        ipv4_address: (\S+)", text, re.M):
            pod = int(name[-2:])
            self.assertIn(ipaddress.ip_address(ip), ipaddress.ip_network(fw.pod_block(pod)), name)
            self.assertNotIn(ip, seen)
            seen.add(ip)
        self.assertEqual(len(seen), 32 * 8)

    def test_flat_pod_and_single_branch_fit_too(self):
        for extra in ({"NETLAB_SWITCH": "0"}, {"NETLAB_MANUAL_BRANCH": "0"}):
            text = generate.render({"STUDENT_COUNT": "15", "STUDENT_PASSWORD_SEED": "s", **extra})
            for name, ip in re.findall(r"^  ([a-z]+-[ma]-\d\d):\n(?:    .*\n)*?        ipv4_address: (\S+)", text, re.M):
                self.assertIn(ipaddress.ip_address(ip), ipaddress.ip_network(fw.pod_block(int(name[-2:]))))

    def test_more_pods_than_the_layout_holds_is_refused(self):
        with self.assertRaisesRegex(generate.ConfigError, "holds 32 pods"):
            generate.render({"STUDENT_COUNT": "32", "NETLAB_MAX_STUDENTS": "40", "STUDENT_PASSWORD_SEED": "s"})


if __name__ == "__main__":
    unittest.main()
