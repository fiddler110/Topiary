"""Roster, tokens, signing key, CA, rate limit and request plumbing. Run: python3 -B -m unittest test_server"""
import http.client
import os
import ssl
import stat
import subprocess
import tempfile
import unittest

import auth
import pki
import server
import wan_ids
from wan_testlib import Lab, LabCase, STUDENT

KEY = b"x" * 64


class Roster(unittest.TestCase):
    def test_names_match_the_engine_and_the_broker(self):
        users = auth.roster({"STUDENT_PREFIX": "student", "STUDENT_COUNT": "3", "BOT_PREFIX": "testuser",
                             "BOT_COUNT": "2", "FACILITATOR_USERNAME": "root"})
        self.assertEqual(users, ["student01", "student02", "student03", "testuser1", "testuser2", "root"])
        self.assertEqual(auth.roster({}), ["root"])
        self.assertEqual(auth.roster({"STUDENT_COUNT": "x", "FACILITATOR_USERNAME": ""}), [])

    def test_tokens_and_orgs_are_derived_and_distinct(self):
        a = auth.Auth(KEY, ["student01", "student02"], "root")
        self.assertEqual(a.user_for_token(wan_ids.api_token(KEY, "student02")), "student02")
        self.assertIsNone(a.user_for_token("x" * 40))
        self.assertIsNone(a.user_for_token(""))
        self.assertEqual(len({a.org_of["student01"], a.org_of["student02"]}), 2)
        self.assertTrue(a.can_access_org("student01", a.org_of["student01"]))
        self.assertFalse(a.can_access_org("student01", a.org_of["student02"]))
        self.assertFalse(a.is_facilitator("student01"))

    def test_the_broker_agrees(self):
        """The terminal's broker builds its own roster; the two lists must be the same."""
        import importlib.util
        path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "terminal", "wan-broker.py")
        if not os.path.exists(path):
            self.skipTest("terminal/wan-broker.py not present")
        spec = importlib.util.spec_from_file_location("wan_broker", path)
        broker = importlib.util.module_from_spec(spec)
        import sys
        sys.path.insert(0, os.path.dirname(path))
        try:
            spec.loader.exec_module(broker)
        finally:
            sys.path.remove(os.path.dirname(path))
            sys.modules.pop("wan_ids_terminal", None)
        env = {"STUDENT_PREFIX": "pupil", "STUDENT_COUNT": "12", "BOT_PREFIX": "bot", "BOT_COUNT": "11",
               "FACILITATOR_USERNAME": "sensei"}
        self.assertEqual(broker.roster(env), auth.roster(env))
        self.assertEqual(broker.roster({}), auth.roster({}))


class Startup(unittest.TestCase):
    def test_signing_key_and_ca_files(self):
        tmp = tempfile.mkdtemp()
        key = server.load_signing_key(tmp + "/sec")
        path = tmp + "/sec/signing.key"
        self.assertEqual(len(bytes.fromhex(key.decode())), 32)
        self.assertEqual(stat.S_IMODE(os.stat(path).st_mode), 0o600)
        self.assertEqual(server.load_signing_key(tmp + "/sec"), key)          # kept on the next start

    def test_pki_is_idempotent_and_keeps_keys_private(self):
        tmp = tempfile.mkdtemp()
        crt, key = pki.ensure(tmp + "/private", tmp + "/shared")
        self.assertEqual(os.listdir(tmp + "/shared"), ["ca.crt"])               # only the certificate is shared
        self.assertEqual(stat.S_IMODE(os.stat(tmp + "/private/ca.key").st_mode), 0o600)
        before = open(crt, "rb").read()
        self.assertEqual(pki.ensure(tmp + "/private", tmp + "/shared"), (crt, key))
        self.assertEqual(open(crt, "rb").read(), before)
        text = subprocess.run(["openssl", "x509", "-in", crt, "-noout", "-ext", "subjectAltName"], capture_output=True,
                              text=True).stdout
        self.assertIn("DNS:api.mist.com", text)
        self.assertIn("DNS:wan-api", text)

    def test_app_start_is_idempotent(self):
        lab = Lab()
        try:
            org = lab.app.store.get(lab.org(STUDENT))
            with org.lock:
                org.data["networks"]["keep"] = {"id": "keep"}
                org.save()
            again = server.App(lab.env)                                       # a restart: same key, same stores
            self.assertEqual(again.key, lab.app.key)
            self.assertIn("keep", again.store.get(lab.org(STUDENT)).data["networks"])
        finally:
            lab.close()


class Plumbing(LabCase):
    def test_tls_verifies_against_the_lab_names(self):
        conn = http.client.HTTPSConnection("localhost", self.lab.api_port, context=self.lab.ctx, timeout=5)
        conn.request("GET", "/api/v1/self", headers={"Authorization": "Token " + self.lab.token(STUDENT)})
        self.assertEqual(conn.getresponse().status, 200)
        bare = ssl.create_default_context()
        with self.assertRaises(ssl.SSLError):                                  # the CA is not a public one
            c = http.client.HTTPSConnection("localhost", self.lab.api_port, context=bare, timeout=5)
            c.request("GET", "/")
            c.getresponse()

    def test_keep_alive_survives_an_unread_looking_body(self):
        conn = http.client.HTTPSConnection("localhost", self.lab.api_port, context=self.lab.ctx, timeout=5)
        hdrs = {"Authorization": "Token " + self.lab.token(STUDENT), "Content-Type": "application/json"}
        conn.request("POST", f"{self.base}/nothing", body=b'{"a": 1}', headers=hdrs)        # 404 with a body
        r = conn.getresponse()
        r.read()
        self.assertEqual(r.status, 404)
        conn.request("GET", "/api/v1/self", headers=hdrs)                                     # same connection
        r = conn.getresponse()
        r.read()
        self.assertEqual(r.status, 200)

    def test_oversized_body_is_refused(self):
        conn = http.client.HTTPSConnection("localhost", self.lab.api_port, context=self.lab.ctx, timeout=5)
        conn.putrequest("POST", f"{self.base}/networks")
        conn.putheader("Authorization", "Token " + self.lab.token(STUDENT))
        conn.putheader("Content-Length", str(server.BODY_LIMIT + 1))
        conn.endheaders()
        r = conn.getresponse()
        self.assertEqual(r.status, 413)

    def test_every_error_is_json_with_detail(self):
        status, data, headers = self.lab.call(STUDENT, "GET", f"{self.base}/networks/nope")
        self.assertEqual((status, data), (404, {"detail": "Not found"}))
        self.assertTrue(headers["Content-Type"].startswith("application/json"))


class RateLimit(unittest.TestCase):
    def setUp(self):
        self.now = 0.0
        self.lim = server.RateLimit(3, 1, clock=lambda: self.now)

    def test_burst_then_refused_with_retry_after(self):
        self.assertEqual([self.lim.take("a") for _ in range(3)], [0, 0, 0])
        self.assertGreaterEqual(self.lim.take("a"), 1)

    def test_identities_are_separate_and_refill(self):
        for _ in range(3):
            self.lim.take("a")
        self.assertEqual(self.lim.take("b"), 0)
        self.now += 2
        self.assertEqual(self.lim.take("a"), 0)

    def test_zero_is_off(self):
        off = server.RateLimit(0, 0)
        self.assertEqual([off.take("a") for _ in range(1000)], [0] * 1000)

    def test_the_api_answers_429_when_the_tripwire_trips(self):
        lab = Lab(WAN_API_RATE_BURST="3", WAN_API_RATE_PER_SEC="0.001")
        try:
            codes = [lab.call(STUDENT, "GET", "/api/v1/self")[0] for _ in range(5)]
            self.assertEqual(codes, [200, 200, 200, 429, 429])
            status, data, headers = lab.call(STUDENT, "GET", "/api/v1/self")
            self.assertIn("Retry-After", headers)
            self.assertEqual(lab.call("student02", "GET", "/api/v1/self")[0], 200)     # another identity is not affected
        finally:
            lab.close()


if __name__ == "__main__":
    unittest.main()
