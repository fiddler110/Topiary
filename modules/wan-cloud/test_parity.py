"""Guards the logic duplicated across two images: the terminal broker
(terminal/wan-broker.py) and the control plane (wan-api/wan_ids.py) must derive
identical tokens and org ids, and the files copied from tofu-basics must not
drift. Run from this directory:
    python3 -B -m unittest test_parity
"""
import filecmp
import importlib.machinery
import importlib.util
import os
import sys
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
TERMINAL = os.path.join(HERE, "terminal")
TOFU = os.path.join(HERE, "..", "..", "workshops", "tofu-basics", "compose", "terminal")
sys.path.insert(0, os.path.join(HERE, "wan-api"))
import wan_ids  # noqa: E402  (the wan-api copy)


def load(name, path):
    spec = importlib.util.spec_from_loader(name, importlib.machinery.SourceFileLoader(name, path))
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


broker = load("wan_broker", os.path.join(TERMINAL, "wan-broker.py"))
KEY = b"0123456789abcdef" * 2


class Parity(unittest.TestCase):
    def test_wan_ids_copies_identical(self):
        self.assertTrue(filecmp.cmp(os.path.join(HERE, "wan-api", "wan_ids.py"),
                                    os.path.join(TERMINAL, "wan_ids.py"), shallow=False))

    def test_broker_uses_the_same_derivations(self):
        for user in ("student01", "testuser3", "admin"):
            creds = broker.credentials_for(user, KEY)
            self.assertEqual(creds["MIST_API_TOKEN"], wan_ids.api_token(KEY, user))
            self.assertEqual(creds["MIST_ORG_ID"], wan_ids.org_id(KEY, user))
            self.assertEqual(creds["TF_VAR_org_id"], wan_ids.org_id(KEY, user))
            self.assertEqual(creds["TF_HTTP_USERNAME"], user)
            self.assertEqual(creds["TF_HTTP_PASSWORD"], wan_ids.api_token(KEY, user))
            self.assertEqual(creds["MIST_HOST"], "api.mist.com")

    def test_users_get_different_values(self):
        a, b = broker.credentials_for("student01", KEY), broker.credentials_for("student02", KEY)
        self.assertNotEqual(a["MIST_API_TOKEN"], b["MIST_API_TOKEN"])
        self.assertNotEqual(a["MIST_ORG_ID"], b["MIST_ORG_ID"])

    def test_roster(self):
        env = {"STUDENT_PREFIX": "s", "STUDENT_COUNT": "3", "BOT_PREFIX": "b", "BOT_COUNT": "11",
               "FACILITATOR_USERNAME": "fac"}
        users = broker.roster(env)
        self.assertEqual(users[:3], ["s01", "s02", "s03"])  # students: padded
        self.assertEqual(users[3:-1], [f"b{n}" for n in range(1, 12)])  # bots: not padded
        self.assertEqual(users[-1], "fac")

    def test_files_copied_from_tofu_basics(self):
        for name in ("unpack-mirror.py", "disable-tofu-ls.py"):
            src = os.path.join(TOFU, name)
            if not os.path.exists(src):
                self.skipTest("tofu-basics not next to this module")
            self.assertTrue(filecmp.cmp(src, os.path.join(TERMINAL, name), shallow=False), name)


if __name__ == "__main__":
    unittest.main()
