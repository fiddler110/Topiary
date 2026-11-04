"""The 8080 side: portal files, /wan/api JSON, drift, reset, readiness. Run: python3 -B -m unittest test_portal"""
import json
import unittest

from wan_testlib import FAC, OTHER, STUDENT, LabCase

ADMIN = {"X-Requested-With": "dojo-admin"}


class PortalFiles(LabCase):
    def test_static_files_and_headers(self):
        for path, ctype in (("/wan/", "text/html"), ("/wan", None), ("/wan/app.js", "text/javascript"),
                            ("/wan/app.css", "text/css"), ("/wan/favicon.svg", "image/svg+xml")):
            status, _, headers = self.lab.portal("GET", path)
            if ctype is None:
                self.assertEqual((status, headers["Location"]), (301, "/wan/"))
                continue
            self.assertEqual(status, 200, path)
            self.assertTrue(headers["Content-Type"].startswith(ctype), path)
            self.assertIn("default-src 'self'", headers["Content-Security-Policy"])
            self.assertNotIn("unsafe-inline", headers["Content-Security-Policy"])
            self.assertEqual(headers["X-Content-Type-Options"], "nosniff")

    def test_only_flat_files_are_served(self):
        for path in ("/wan/../server.py", "/wan/%2e%2e/server.py", "/wan/.hidden", "/wan/a/b", "/wan/nothing.js"):
            self.assertEqual(self.lab.portal("GET", path)[0], 404, path)
        self.assertEqual(self.lab.portal("POST", "/wan/app.js")[0], 405)

    def test_readyz_and_unknown(self):
        self.assertEqual(self.lab.portal("GET", "/readyz")[:2], (200, {"ready": True}))
        self.assertEqual(self.lab.portal("GET", "/elsewhere")[0], 404)
        self.assertEqual(self.lab.portal("GET", "/api/v1/self")[0], 404)       # the Mist API is not on this port


class PortalApi(LabCase):
    def test_identity_needs_the_gateway_token(self):
        self.assertEqual(self.lab.portal("GET", "/wan/api/me")[0], 401)
        self.assertEqual(self.lab.portal("GET", "/wan/api/me", user=STUDENT, token="wrong")[0], 401)
        self.assertEqual(self.lab.portal("GET", "/wan/api/me", user=STUDENT, token="")[0], 401)
        self.assertEqual(self.lab.portal("GET", "/wan/api/me", user="stranger")[0], 403)
        self.assertEqual(self.lab.portal("GET", "/wan/api/me", user=STUDENT, headers={"X-Auth-User": "root"},
                                         token="wrong")[0], 401)       # a spoofed header alone gets nothing

    def test_unset_gateway_token_fails_closed(self):
        from wan_testlib import Lab
        lab = Lab(GATEWAY_TOKEN="")
        try:
            self.assertEqual(lab.portal("GET", "/wan/api/me", user=STUDENT, token="")[0], 503)
        finally:
            lab.close()

    def test_me(self):
        me = self.lab.portal("GET", "/wan/api/me", user=STUDENT)[1]
        self.assertEqual(me, {"user": STUDENT, "facilitator": False,
                              "orgs": [{"id": self.org, "name": "Dojo Org student01", "user": STUDENT}]})
        fac = self.lab.portal("GET", "/wan/api/me", user=FAC)[1]
        self.assertTrue(fac["facilitator"])
        self.assertEqual({o["user"] for o in fac["orgs"]}, {"student01", "student02", "testuser1", "root"})

    def test_org_store_own_org_only(self):
        net = self.make("networks", name="corp", subnet="10.0.0.0/24")
        status, store, _ = self.lab.portal("GET", f"/wan/api/orgs/{self.org}", user=STUDENT)
        self.assertEqual(status, 200)
        self.assertIn(net["id"], store["networks"])
        self.assertEqual(len(store["delivery"]), 4)
        self.assertEqual(store["events"][-1]["actor"], STUDENT)
        self.assertEqual(self.lab.portal("GET", f"/wan/api/orgs/{self.lab.org(OTHER)}", user=STUDENT)[0], 403)
        self.assertEqual(self.lab.portal("GET", f"/wan/api/orgs/{self.org}", user=FAC)[0], 200)
        self.assertEqual(self.lab.portal("POST", f"/wan/api/orgs/{self.org}", user=STUDENT)[0], 405)

    def test_org_store_shows_the_newest_200_events(self):
        net = self.make("networks", name="n", subnet="10.0.0.0/24")
        for i in range(210):
            self.ok("PUT", f"{self.base}/networks/{net['id']}", {"vlan_id": str(i)})
        store = self.lab.portal("GET", f"/wan/api/orgs/{self.org}", user=STUDENT)[1]
        self.assertEqual(len(store["events"]), 200)

    def test_device_config(self):
        dev = self.ok("POST", f"{self.base}/inventory", [self.lab.code(STUDENT, 0)])["inventory_added"][0]
        did = "00000000-0000-0000-1000-" + dev["mac"]
        status, text, headers = self.lab.portal("GET", f"/wan/api/orgs/{self.org}/devices/{did}/config", user=STUDENT)
        self.assertIn(status, (200, 501))
        if status == 200:
            self.assertTrue(headers["Content-Type"].startswith("text/plain"))
            self.assertIn("set system host-name", text)
        self.assertEqual(self.lab.portal("GET", f"/wan/api/orgs/{self.org}/devices/{'0' * 36}/config", user=STUDENT)[0], 404)
        self.assertEqual(self.lab.portal("GET", f"/wan/api/orgs/{self.lab.org(OTHER)}/devices/{did}/config",
                                         user=STUDENT)[0], 403)

    def test_missing_renderer_is_501(self):
        import sys
        dev = self.ok("POST", f"{self.base}/inventory", [self.lab.code(STUDENT, 0)])["inventory_added"][0]
        saved = sys.modules.get("renderer")
        sys.modules["renderer"] = None            # makes `import renderer` raise ImportError
        try:
            status = self.lab.portal("GET", f"/wan/api/orgs/{self.org}/devices/00000000-0000-0000-1000-{dev['mac']}/config",
                                     user=STUDENT)[0]
        finally:
            if saved is None:
                sys.modules.pop("renderer", None)
            else:
                sys.modules["renderer"] = saved
        self.assertEqual(status, 501)

    def test_unknown_routes(self):
        for path in ("/wan/api", "/wan/api/nothing", f"/wan/api/orgs/{self.org}/nothing"):
            self.assertEqual(self.lab.portal("GET", path, user=STUDENT)[0], 404, path)


class Drift(LabCase):
    path = property(lambda self: f"/wan/api/orgs/{self.org}/drift")

    def test_only_the_facilitator_with_the_header(self):
        self.assertEqual(self.lab.portal("POST", self.path)[0], 401)
        self.assertEqual(self.lab.portal("POST", self.path, user=STUDENT, headers=ADMIN)[0], 403)
        self.assertEqual(self.lab.portal("POST", self.path, user=FAC)[0], 403)                      # no header
        self.assertEqual(self.lab.portal("POST", self.path, user=FAC, headers={"X-Requested-With": "x"})[0], 403)
        self.assertEqual(self.lab.portal("GET", self.path, user=FAC, headers=ADMIN)[0], 405)
        self.assertEqual(self.lab.portal("POST", f"/wan/api/orgs/{'0' * 36}/drift", user=FAC, headers=ADMIN)[0], 404)
        self.assertEqual(self.ok("GET", f"{self.base}/dojo/events"), [])

    def test_changes_a_network_vlan(self):
        net = self.make("networks", name="corp", subnet="10.0.0.0/24", vlan_id="10")
        self.make("networks", name="later", subnet="10.1.0.0/24", vlan_id="11")
        status, change, _ = self.lab.portal("POST", self.path, user=FAC, headers=ADMIN)
        self.assertEqual((status, change["changed"], change["from"], change["to"]), (200, "network", "10", "999"))
        self.assertEqual(self.ok("GET", f"{self.base}/networks/{net['id']}")["vlan_id"], "999")
        event = self.ok("GET", f"{self.base}/dojo/events")[-1]
        self.assertEqual(event["actor"], "portal:facilitator")
        self.assertIn("vlan_id 10 -> 999", event["action"])
        self.lab.portal("POST", self.path, user=FAC, headers=ADMIN)                  # again: still a change
        self.assertEqual(self.ok("GET", f"{self.base}/networks/{net['id']}")["vlan_id"], "998")

    def test_with_no_network_it_adds_a_policy(self):
        change = self.lab.portal("POST", self.path, user=FAC, headers=ADMIN)[1]
        self.assertEqual(change["changed"], "servicepolicy")
        pols = self.ok("GET", f"{self.base}/servicepolicies")
        self.assertEqual([(p["name"], p["action"]) for p in pols], [("drift-allow-all", "allow")])


class Reset(LabCase):
    def reset(self, user, phase="teardown", token="reset-token", method="POST"):
        import http.client
        conn = http.client.HTTPConnection("127.0.0.1", self.lab.portal_port, timeout=10)
        hdrs = {"X-Dojo-Reset-Token": token} if token is not None else {}
        conn.request(method, f"/_dojo/reset/{user}?phase={phase}", headers=hdrs)
        r = conn.getresponse()
        out = (r.status, json.loads(r.read() or b"{}"))
        conn.close()
        return out

    def test_token_required(self):
        for kw in ({"token": None}, {"token": "wrong"}, {"token": ""}, {"method": "GET"}):
            self.assertEqual(self.reset(STUDENT, **kw)[0], 403, kw)

    def test_unknown_user_or_phase(self):
        self.assertEqual(self.reset("nobody")[0], 404)
        self.assertEqual(self.reset(STUDENT, "explode")[0], 404)
        self.assertEqual(self.reset("../x")[0], 404)

    def test_teardown_restores_the_seed_and_leaves_others_alone(self):
        self.make("networks", name="mine", subnet="10.0.0.0/24")
        self.ok("POST", f"{self.base}/inventory", [self.lab.code(STUDENT, 0)])
        self.make("sites", name="s")
        self.lab.state("POST", "infra", body=b"{}")
        theirs = self.ok("POST", f"/api/v1/orgs/{self.lab.org(OTHER)}/networks", {"name": "x", "subnet": "10.0.0.0/24"}, user=OTHER)
        status, out = self.reset(STUDENT)
        self.assertEqual((status, out["ok"]), (200, True))
        self.assertIn("1 state", out["detail"])
        self.assertEqual(self.ok("GET", f"{self.base}/networks"), [])
        self.assertEqual(self.ok("GET", f"{self.base}/inventory"), [])
        self.assertEqual(self.ok("GET", f"{self.base}/sites"), [])
        self.assertEqual(self.ok("GET", f"{self.base}/dojo/events"), [])
        self.assertEqual(len(self.ok("GET", f"{self.base}/dojo/delivery")), 4)
        self.assertEqual(self.lab.state("GET", "infra")[0], 404)
        self.assertEqual(self.ok("GET", f"/api/v1/orgs/{self.lab.org(OTHER)}/networks/{theirs['id']}", user=OTHER)["name"], "x")
        self.assertEqual(self.lab.call(STUDENT, "GET", f"/api/v1/sites/{'0' * 8}-0000-0000-0000-{'0' * 12}")[0], 404)

    def test_the_same_claim_codes_work_again_after_reset(self):
        code = self.lab.code(STUDENT, 0)
        self.assertEqual(self.ok("POST", f"{self.base}/inventory", [code])["added"], [code])
        self.reset(STUDENT)
        self.assertEqual(self.ok("POST", f"{self.base}/inventory", [code])["added"], [code])

    def test_provision_does_nothing(self):
        self.make("networks", name="mine", subnet="10.0.0.0/24")
        self.assertEqual(self.reset(STUDENT, "provision")[1]["detail"], "nothing to do")
        self.assertEqual(len(self.ok("GET", f"{self.base}/networks")), 1)

    def test_no_reset_token_configured_means_no_reset(self):
        from wan_testlib import Lab
        lab = Lab(RESET_TOKEN="")
        try:
            import http.client
            conn = http.client.HTTPConnection("127.0.0.1", lab.portal_port, timeout=10)
            conn.request("POST", f"/_dojo/reset/{STUDENT}?phase=teardown", headers={"X-Dojo-Reset-Token": ""})
            self.assertEqual(conn.getresponse().status, 403)
        finally:
            lab.close()


if __name__ == "__main__":
    unittest.main()
