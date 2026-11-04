"""The Terraform http state backend (tfstate.py) against a real server. Run: python3 -B -m unittest test_tfstate"""
import json
import unittest

from wan_testlib import FAC, OTHER, STUDENT, LabCase


class State(LabCase):
    def test_auth_failures(self):
        for kw in ({"password": "wrong"}, {"username": OTHER}, {"password": ""}, {"username": "nobody"}):
            status, _, headers = self.lab.state("GET", "s", **kw)
            self.assertEqual(status, 401, kw)
            self.assertIn("Basic realm", headers["WWW-Authenticate"])
        self.assertEqual(self.lab.state("GET", "s", username=STUDENT, password=self.lab.token(OTHER))[0], 401)

    def test_bad_name(self):
        self.assertEqual(self.lab.state("GET", "Bad_Name")[0], 400)
        self.assertEqual(self.lab.state("GET", "a" * 41)[0], 400)

    def test_get_post_delete(self):
        self.assertEqual(self.lab.state("GET", "infra")[0], 404)
        self.assertEqual(self.lab.state("POST", "infra", body=b'{"v":1}')[0], 200)
        self.assertEqual(self.lab.state("GET", "infra")[:2], (200, b'{"v":1}'))
        self.assertEqual(self.lab.state("POST", "infra", body=b'{"v":2}')[0], 200)
        self.assertEqual(self.lab.state("GET", "infra")[1], b'{"v":2}')
        self.assertEqual(self.lab.state("DELETE", "infra")[0], 200)
        self.assertEqual(self.lab.state("GET", "infra")[0], 404)
        events = json.dumps(self.lab.app.store.get(self.org).data["events"])
        self.assertIn("save state infra", events)
        self.assertNotIn('"v"', events)        # content is never logged

    def test_state_is_kept_out_of_the_org_store(self):
        self.lab.state("POST", "infra", body=b'{"secret": "hunter2"}')
        self.assertNotIn("hunter2", json.dumps(self.lab.app.store.get(self.org).snapshot()))
        status, data, _ = self.lab.portal("GET", f"/wan/api/orgs/{self.org}", user=STUDENT)
        self.assertEqual(status, 200)
        self.assertNotIn("hunter2", json.dumps(data))

    def test_lock_cycle(self):
        info = json.dumps({"ID": "L1", "Who": "me"}).encode()
        self.assertEqual(self.lab.state("LOCK", "infra", body=info)[0], 200)
        status, body, _ = self.lab.state("LOCK", "infra", body=json.dumps({"ID": "L2"}).encode())
        self.assertEqual((status, json.loads(body)["ID"]), (423, "L1"))
        self.assertEqual(self.lab.state("POST", "infra", body=b"{}")[0], 409)                 # no lock id
        self.assertEqual(self.lab.state("POST", "infra", body=b"{}", query="?ID=nope")[0], 409)
        self.assertEqual(self.lab.state("DELETE", "infra")[0], 409)
        self.assertEqual(self.lab.state("POST", "infra", body=b'{"v":3}', query="?ID=L1")[0], 200)
        self.assertEqual(self.lab.state("UNLOCK", "infra", body=json.dumps({"ID": "L2"}).encode())[0], 409)
        self.assertEqual(self.lab.state("UNLOCK", "infra", body=json.dumps({"ID": "L1"}).encode())[0], 200)
        self.assertEqual(self.lab.state("LOCK", "infra", body=info)[0], 200)                  # free again
        self.assertEqual(self.lab.state("UNLOCK", "infra")[0], 200)                           # force unlock: no id
        self.assertEqual(self.lab.state("POST", "infra", body=b"{}")[0], 200)

    def test_lock_survives_a_restart_of_the_store_object(self):
        self.lab.state("LOCK", "infra", body=b'{"ID": "L1"}')
        again = type(self.lab.app.states)(self.lab.app.data_dir)     # a new StateStore reads the same files
        self.assertTrue(again._read(again._org_dir(self.org) + "/infra.lock"))

    def test_states_are_per_org(self):
        self.lab.state("POST", "infra", body=b'{"mine": 1}')
        self.assertEqual(self.lab.state("GET", "infra", user=OTHER)[0], 404)
        self.assertEqual(self.lab.state("GET", "infra", user=STUDENT, query=f"?org={self.lab.org(OTHER)}")[0], 403)
        self.assertEqual(self.lab.state("GET", "infra", user=FAC, query=f"?org={self.org}")[:2], (200, b'{"mine": 1}'))
        self.assertEqual(self.lab.state("POST", "infra", user=FAC, body=b"{}", query=f"?org={self.org}")[0], 403)
        self.assertEqual(self.lab.state("GET", "infra", user=FAC, query="?org=nonsense")[0], 403)

    def test_size_and_count_limits(self):
        import tfstate
        self.assertEqual(self.lab.state("POST", "big", body=b"x" * (tfstate.MAX_BYTES + 1))[0], 413)
        for n in range(tfstate.MAX_STATES):
            self.assertEqual(self.lab.state("POST", f"s{n}", body=b"{}")[0], 200)
        self.assertEqual(self.lab.state("POST", "one-too-many", body=b"{}")[0], 507)
        self.assertEqual(self.lab.state("POST", "s0", body=b'{"again": 1}')[0], 200)         # replacing is fine


if __name__ == "__main__":
    unittest.main()
