import ipaddress
import os
import re
import subprocess
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import generate  # noqa: E402

ENV = {"STUDENT_COUNT": "3", "STUDENT_PASSWORD_SEED": "seed"}


def services(text):
    return re.findall(r"^  ([a-z]+-[ma]-\d\d):$", text, re.M)


class Shape(unittest.TestCase):
    def test_switch_pod_has_eight_nodes_and_six_networks(self):
        text = generate.render(ENV)
        self.assertEqual(len(services(text)), 4 * 8)          # pods 00..03, 8 nodes each
        self.assertEqual(len(re.findall(r"^  netlab_\d\d_[ma]_\w+:$", text, re.M)), 4 * 6)

    def test_flat_pod(self):
        text = generate.render({**ENV, "NETLAB_SWITCH": "0"})
        self.assertEqual(len(services(text)), 4 * 6)
        self.assertNotIn("sw-m-01", text)

    def test_automated_branch_only(self):
        text = generate.render({**ENV, "NETLAB_MANUAL_BRANCH": "0"})
        self.assertEqual(len(services(text)), 4 * 4)
        self.assertEqual({n.split("-")[1] for n in services(text)}, {"a"})

    def test_fifteen_students_is_120_plus_the_facilitators_pod(self):
        text = generate.render({**ENV, "STUDENT_COUNT": "15"})
        self.assertEqual(len(services(text)), 16 * 8)

    def test_names_pods_and_roles(self):
        names = services(generate.render(ENV))
        for want in ("pc-m-00", "sw-a-03", "fw-m-02", "web-a-01"):
            self.assertIn(want, names)


class Limits(unittest.TestCase):
    def test_cap_is_enforced(self):
        with self.assertRaisesRegex(generate.ConfigError, "capped at 15"):
            generate.render({**ENV, "STUDENT_COUNT": "16"})

    def test_cap_can_be_raised(self):
        generate.render({**ENV, "STUDENT_COUNT": "16", "NETLAB_MAX_STUDENTS": "20"})

    def test_needs_a_seed(self):
        with self.assertRaisesRegex(generate.ConfigError, "STUDENT_PASSWORD_SEED"):
            generate.render({"STUDENT_COUNT": "2"})

    def test_bad_number(self):
        with self.assertRaisesRegex(generate.ConfigError, "STUDENT_COUNT"):
            generate.render({**ENV, "STUDENT_COUNT": "lots"})

    def test_range_too_small(self):
        with self.assertRaisesRegex(generate.ConfigError, "no /29 left"):
            generate.render({**ENV, "NETLAB_DATA_NET": "10.81.0.0/26"})

    def test_main_exits_2_with_the_message(self):
        res = subprocess.run([sys.executable, "-B", generate.__file__], capture_output=True, text=True,
                             env={"PATH": os.environ["PATH"], "STUDENT_COUNT": "99", "STUDENT_PASSWORD_SEED": "s"})
        self.assertEqual(res.returncode, 2)
        self.assertIn("capped at 15", res.stderr)
        self.assertEqual(res.stdout, "")


class Isolation(unittest.TestCase):
    def setUp(self):
        self.text = generate.render(ENV)

    def test_every_network_is_internal_with_a_unique_non_overlapping_29(self):
        blocks = re.findall(r"^  (netlab_\d\d_[ma]_\w+):\n    internal: true\n    ipam: \{config: \[\{subnet: ([\d./]+)\}\]\}",
                            self.text, re.M)
        self.assertEqual(len(blocks), 4 * 6)
        nets = [ipaddress.ip_network(c) for _, c in blocks]
        self.assertTrue(all(n.prefixlen == 29 for n in nets))
        for i, a in enumerate(nets):
            for b in nets[i + 1:]:
                self.assertFalse(a.overlaps(b))

    def test_no_published_ports_and_nothing_privileged(self):
        for bad in ("ports:", "privileged", "cap_add: [ALL", "SYS_ADMIN", "NET_RAW", "docker.sock"):
            self.assertNotIn(bad, self.text)
        self.assertEqual(self.text.count("cap_drop: [ALL]"), len(services(self.text)))
        self.assertEqual(self.text.count("no-new-privileges:true"), len(services(self.text)))

    def test_every_node_is_labelled_and_on_mgmt(self):
        n = len(services(self.text))
        self.assertEqual(self.text.count("topiary.module: netlab"), n + 4 * 6)
        self.assertEqual(self.text.count("  - netlab_mgmt\n"), n)

    def test_branches_never_share_a_data_network(self):
        for pod in range(4):
            m = set(re.findall(rf"netlab_{pod:02d}_m_\w+", self.text))
            a = set(re.findall(rf"netlab_{pod:02d}_a_\w+", self.text))
            self.assertFalse(m & a)

    def test_a_node_is_only_on_its_own_pods_networks(self):
        for name, body in re.findall(r"^  (\w+-[ma]-\d\d):\n((?:    .*\n)+)", self.text, re.M):
            _, b, pod = name.split("-")
            for net in re.findall(r"- (netlab_\d\d_\w+)", body):
                if net != "netlab_mgmt":
                    self.assertTrue(net.startswith(f"netlab_{pod}_{b}_"), (name, net))


class Passwords(unittest.TestCase):
    def test_deterministic_and_per_pod(self):
        self.assertEqual(generate.password("s", 1), generate.password("s", 1))
        self.assertNotEqual(generate.password("s", 1), generate.password("s", 2))
        self.assertNotEqual(generate.password("s", 1), generate.password("t", 1))
        self.assertRegex(generate.password("s", 1), r"^[a-z2-7]{24}$")

    def test_same_pod_same_password_both_branches(self):
        text = generate.render(ENV)
        pw = generate.password("seed", 2)
        self.assertEqual(text.count(f"ROOT_PASSWORD={pw}"), 8)

    def test_deterministic_output(self):
        self.assertEqual(generate.render(ENV), generate.render(ENV))


class Wiring(unittest.TestCase):
    def test_switch_ports(self):
        text = generate.render({**ENV, "STUDENT_COUNT": "1"})
        sw = re.search(r"^  sw-m-01:\n((?:    .*\n)+)", text, re.M).group(1)
        ports = re.search(r"NODE_PORTS=(.*)", sw).group(1).split()
        self.assertEqual([p.split("|")[1:3] for p in ports], [["access", "10"], ["access", "20"], ["trunk", "10,20"]])
        self.assertEqual([p.split("|")[5] for p in ports], ["to-pc", "to-web", "to-fw"])

    def test_fw_gets_both_vlans_and_pc_routes_via_it(self):
        text = generate.render({**ENV, "STUDENT_COUNT": "1"})
        self.assertIn("tagged||10=10.10.10.1/24,20=10.10.20.1/24", text)
        self.assertIn("plain||10.10.10.10/24|10.10.10.1", text)

    def test_only_pc_pings_and_only_fw_forwards(self):
        text = generate.render({**ENV, "STUDENT_COUNT": "1"})
        self.assertEqual(text.count("ping_group_range"), 4)    # pc-m/a for pods 00 and 01
        self.assertEqual(text.count("net.ipv4.ip_forward"), 4)


if __name__ == "__main__":
    unittest.main()
