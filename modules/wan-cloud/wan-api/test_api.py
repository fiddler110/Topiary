"""Auth, tenancy, the 9.1 rules and the inventory flow, against a real server. Run: python3 -B -m unittest test_api"""
import unittest

from wan_testlib import FAC, OTHER, STUDENT, LabCase


class Auth(LabCase):
    def test_token_required(self):
        for hdrs in ({}, {"Authorization": "Token nope"}, {"Authorization": "Bearer " + "x" * 40}):
            status, data, _ = self.lab.call(None, "GET", "/api/v1/self", headers=hdrs)
            self.assertEqual(status, 401)
            self.assertIn("detail", data)

    def test_self_lists_the_callers_org(self):
        me = self.ok("GET", "/api/v1/self")
        self.assertEqual([p["org_id"] for p in me["privileges"]], [self.org])
        self.assertEqual(me["privileges"][0]["name"], "Dojo Org student01")

    def test_facilitator_sees_every_org(self):
        me = self.ok("GET", "/api/v1/self", user=FAC)
        ids = {p["org_id"] for p in me["privileges"]}
        self.assertEqual(ids, {self.lab.org(u) for u in ("student01", "student02", "testuser1", FAC)})

    def test_other_orgs_are_denied(self):
        theirs = self.lab.org(OTHER)
        other_net = self.ok("POST", f"/api/v1/orgs/{theirs}/networks", {"name": "n", "subnet": "10.0.0.0/24"}, user=OTHER)
        for method, path, body in (("GET", f"/api/v1/orgs/{theirs}/networks", None),
                                   ("POST", f"/api/v1/orgs/{theirs}/networks", {"name": "x", "subnet": "10.0.0.0/24"}),
                                   ("GET", f"/api/v1/orgs/{theirs}/networks/{other_net['id']}", None),
                                   ("DELETE", f"/api/v1/orgs/{theirs}/networks/{other_net['id']}", None),
                                   ("GET", f"/api/v1/orgs/{theirs}/inventory", None),
                                   ("GET", f"/api/v1/orgs/{theirs}/dojo/delivery", None),
                                   ("GET", f"/api/v1/orgs/{theirs}/dojo/events", None)):
            self.assertEqual(self.lab.call(STUDENT, method, path, body)[0], 403, path)
        self.assertEqual(self.ok("GET", f"/api/v1/orgs/{theirs}/networks/{other_net['id']}", user=OTHER)["name"], "n")

    def test_other_orgs_sites_look_missing(self):
        site = self.ok("POST", f"/api/v1/orgs/{self.lab.org(OTHER)}/sites", {"name": "theirs"}, user=OTHER)
        for method, tail in (("GET", ""), ("PUT", ""), ("DELETE", ""), ("GET", "/setting"), ("PUT", "/setting"),
                             ("GET", "/devices")):
            self.assertEqual(self.lab.call(STUDENT, method, f"/api/v1/sites/{site['id']}{tail}", {})[0], 404, tail)
        self.assertEqual(self.ok("GET", f"/api/v1/sites/{site['id']}", user=OTHER)["name"], "theirs")

    def test_facilitator_may_use_any_org(self):
        net = self.make("networks", name="n", subnet="10.0.0.0/24")
        self.assertEqual(self.ok("GET", f"{self.base}/networks/{net['id']}", user=FAC)["name"], "n")
        self.ok("DELETE", f"{self.base}/networks/{net['id']}", user=FAC)
        self.assertEqual(self.ok("GET", f"{self.base}/dojo/events")[-1]["actor"], FAC)

    def test_unknown_org_and_paths(self):
        self.assertEqual(self.lab.call(FAC, "GET", "/api/v1/orgs/00000000-0000-0000-0000-000000000000/networks")[0], 404)
        self.assertEqual(self.lab.call(STUDENT, "GET", "/api/v1/orgs/not-a-uuid/networks")[0], 403)
        self.assertEqual(self.lab.call(STUDENT, "GET", "/api/v1/nothing")[0], 404)
        self.assertEqual(self.lab.call(STUDENT, "GET", "/elsewhere")[0], 404)
        self.assertEqual(self.lab.call(STUDENT, "PATCH", f"{self.base}/networks")[0], 405)


class Rules(LabCase):
    """docs/SRX-MIST-PLAN.md 9.1, one test per rule."""

    def test_r1_chunked_body(self):
        status, data, _ = self.lab.call(STUDENT, "POST", f"{self.base}/networks",
                                        {"name": "chunky", "subnet": "10.1.0.0/24"}, chunked=True)
        self.assertEqual((status, data["name"]), (200, "chunky"))

    def test_r2_scope_ids(self):
        site = self.make("sites", name="s")
        self.assertEqual(site["org_id"], self.org)
        setting = self.ok("GET", f"/api/v1/sites/{site['id']}/setting")
        self.assertEqual((setting["site_id"], setting["org_id"]), (site["id"], self.org))   # even before any PUT
        put = self.ok("PUT", f"/api/v1/sites/{site['id']}/setting", {"vars": {"a": "1"}})
        self.assertEqual((put["site_id"], put["org_id"], put["vars"]), (site["id"], self.org, {"a": "1"}))
        self.assertEqual(self.make("networks", name="n", subnet="10.0.0.0/24")["org_id"], self.org)

    def test_r3_paging_headers_on_every_list(self):
        self.make("networks", name="n", subnet="10.0.0.0/24")
        site = self.make("sites", name="s")
        for path in ("networks", "services", "servicepolicies", "gatewaytemplates", "deviceprofiles", "sitegroups",
                     "vpns", "sites", "inventory", "dojo/delivery", "dojo/events"):
            status, data, headers = self.lab.call(STUDENT, "GET", f"{self.base}/{path}")
            self.assertEqual(status, 200, path)
            self.assertIsInstance(data, list)
            self.assertEqual(headers["X-Page-Total"], str(len(data)), path)
            self.assertIn("X-Page-Limit", headers)
            self.assertIn("X-Page-Page", headers)
        status, data, headers = self.lab.call(STUDENT, "GET", f"/api/v1/sites/{site['id']}/devices")
        self.assertEqual((status, data, headers["X-Page-Total"]), (200, [], "0"))

    def test_r3_paging_slices(self):
        for i in range(5):
            self.make("networks", name=f"n{i}", subnet=f"10.{i}.0.0/24")
        status, data, headers = self.lab.call(STUDENT, "GET", f"{self.base}/networks?limit=2&page=3")
        self.assertEqual((len(data), headers["X-Page-Total"], headers["X-Page-Limit"], headers["X-Page-Page"]),
                         (1, "5", "2", "3"))
        self.assertEqual(self.lab.call(STUDENT, "GET", f"{self.base}/networks?limit=abc")[0], 400)

    def test_r4_put_semantics(self):
        net = self.make("networks", name="n", subnet="10.0.0.0/24", vlan_id="10", gateway="10.0.0.1")
        put = self.ok("PUT", f"{self.base}/networks/{net['id']}",
                      {"-gateway": "", "vlan_id": "11", "id": "evil", "org_id": "evil", "created_time": 1})
        self.assertEqual((put["vlan_id"], put["id"], put["org_id"], put["created_time"]),
                         ("11", net["id"], self.org, net["created_time"]))
        self.assertNotIn("gateway", put)
        self.assertEqual(put["subnet"], "10.0.0.0/24")          # untouched keys are kept
        self.assertEqual(self.ok("GET", f"{self.base}/networks/{net['id']}"), put)

    def test_r4_create_drops_minus_keys_and_owned_fields(self):
        net = self.make("networks", name="n", subnet="10.0.0.0/24", **{"-isolation": "", "id": "mine", "org_id": "x"})
        self.assertNotIn("-isolation", net)
        self.assertNotEqual(net["id"], "mine")
        self.assertEqual(net["org_id"], self.org)

    def test_r5_echo_in_the_same_shape(self):
        body = {"name": "web", "type": "custom", "addresses": ["0.0.0.0/0"],
                "specs": [{"protocol": "tcp", "port_range": "443"}]}
        svc = self.make("services", **body)
        for key, value in body.items():
            self.assertEqual(svc[key], value)
        tmpl = self.make("gatewaytemplates", name="t", type="standalone",
                         port_config={"ge-0/0/0": {"usage": "wan", "ip_config": {"type": "dhcp"}}},
                         ip_configs={"corp": {"type": "static", "ip": "{{lan_ip}}", "netmask": "/24"}})
        self.assertEqual(tmpl["port_config"]["ge-0/0/0"]["ip_config"], {"type": "dhcp"})
        self.assertEqual(tmpl["type"], "standalone")
        self.assertEqual(tmpl["ip_configs"]["corp"]["ip"], "{{lan_ip}}")

    def test_r6_inventory_and_profile_assign(self):
        mac = self.claim(0)["mac"]
        prof = self.make("deviceprofiles", name="p", type="gateway")
        site = self.make("sites", name="s")
        self.ok("PUT", f"{self.base}/inventory", {"op": "assign", "macs": [mac], "site_id": site["id"]})
        out = self.ok("POST", f"{self.base}/deviceprofiles/{prof['id']}/assign", {"macs": [mac]})
        self.assertEqual(out["success"], [mac])
        dev = self.ok("GET", f"{self.base}/inventory")[0]
        self.assertEqual((dev["site_id"], dev["deviceprofile_id"]), (site["id"], prof["id"]))
        self.ok("POST", f"{self.base}/deviceprofiles/{prof['id']}/unassign", {"macs": [mac]})
        self.assertIsNone(self.ok("GET", f"{self.base}/inventory")[0]["deviceprofile_id"])

    def test_r7_empty_is_a_list_missing_is_404(self):
        self.assertEqual(self.ok("GET", f"{self.base}/vpns"), [])
        missing = "/00000000-0000-0000-0000-000000000099"
        for path in (f"{self.base}/vpns{missing}", f"/api/v1/sites{missing}", f"{self.base}/networks/not-an-id"):
            self.assertEqual(self.lab.call(STUDENT, "GET", path)[0], 404, path)
        net = self.make("networks", name="n", subnet="10.0.0.0/24")
        self.ok("DELETE", f"{self.base}/networks/{net['id']}")
        self.assertEqual(self.lab.call(STUDENT, "GET", f"{self.base}/networks/{net['id']}")[0], 404)
        self.assertEqual(self.lab.call(STUDENT, "DELETE", f"{self.base}/networks/{net['id']}")[0], 404)

    def claim(self, n):
        out = self.ok("POST", f"{self.base}/inventory", [self.lab.code(STUDENT, n)])
        return out["inventory_added"][0]


class Validation(LabCase):
    def test_required_fields(self):
        for kind, body in (("networks", {"name": "n"}), ("networks", {"subnet": "10.0.0.0/24"}), ("services", {}),
                           ("servicepolicies", {"name": ""}), ("gatewaytemplates", {}), ("deviceprofiles", {}),
                           ("sitegroups", {}), ("vpns", {}), ("sites", {})):
            status, data, _ = self.lab.call(STUDENT, "POST", f"{self.base}/{kind}", body)
            self.assertEqual(status, 400, (kind, body))
            self.assertIn("detail", data)

    def test_types_and_enums(self):
        for kind, body in (("networks", {"name": 5, "subnet": "10.0.0.0/24"}),
                           ("networks", {"name": "n", "subnet": ["x"]}),
                           ("services", {"name": "s", "addresses": "0.0.0.0/0"}),
                           ("servicepolicies", {"name": "p", "action": "maybe"}),
                           ("gatewaytemplates", {"name": "t", "port_config": []}),
                           ("sites", {"name": "s", "timezone": 3})):
            self.assertEqual(self.lab.call(STUDENT, "POST", f"{self.base}/{kind}", body)[0], 400, (kind, body))
        self.assertEqual(self.lab.call(STUDENT, "POST", f"{self.base}/networks", b"{nope")[0], 400)
        self.assertEqual(self.lab.call(STUDENT, "POST", f"{self.base}/networks", [1])[0], 400)

    def test_put_validates_what_it_gets(self):
        net = self.make("networks", name="n", subnet="10.0.0.0/24")
        self.assertEqual(self.lab.call(STUDENT, "PUT", f"{self.base}/networks/{net['id']}", {"name": ""})[0], 400)
        self.assertEqual(self.lab.call(STUDENT, "PUT", f"{self.base}/networks/{net['id']}", {"subnet": 4})[0], 400)
        self.assertEqual(self.ok("PUT", f"{self.base}/networks/{net['id']}", {"vlan_id": 20})["vlan_id"], 20)

    def test_every_collection_round_trips(self):
        bodies = {"networks": {"name": "n", "subnet": "10.0.0.0/24"}, "services": {"name": "s"},
                  "servicepolicies": {"name": "p", "action": "allow"}, "gatewaytemplates": {"name": "t"},
                  "deviceprofiles": {"name": "d"}, "sitegroups": {"name": "g"}, "vpns": {"name": "v", "paths": {}},
                  "idpprofiles": {"name": "i"}, "avprofiles": {"name": "a"}}
        for kind, body in bodies.items():
            obj = self.make(kind, **body)
            self.assertEqual(self.ok("GET", f"{self.base}/{kind}/{obj['id']}"), obj)
            self.assertEqual([o["id"] for o in self.ok("GET", f"{self.base}/{kind}")], [obj["id"]])
            upd = self.ok("PUT", f"{self.base}/{kind}/{obj['id']}", {"name": "renamed"})
            self.assertEqual(upd["name"], "renamed")
            self.ok("DELETE", f"{self.base}/{kind}/{obj['id']}")
            self.assertEqual(self.ok("GET", f"{self.base}/{kind}"), [])
        self.assertEqual(self.make("deviceprofiles", name="x")["type"], "gateway")

    def test_events_record_writes_by_actor(self):
        net = self.make("networks", name="corp", subnet="10.0.0.0/24")
        self.ok("PUT", f"{self.base}/networks/{net['id']}", {"vlan_id": "5"})
        self.ok("DELETE", f"{self.base}/networks/{net['id']}")
        events = self.ok("GET", f"{self.base}/dojo/events")
        self.assertEqual([e["action"] for e in events],
                         ["create network 'corp'", "update network 'corp'", "delete network 'corp'"])
        self.assertEqual({e["actor"] for e in events}, {STUDENT})
        self.assertTrue(all(isinstance(e["ts"], int) and e["path"] for e in events))


class Inventory(LabCase):
    def claim(self, *codes):
        return self.ok("POST", f"{self.base}/inventory", list(codes))

    def test_claim_flow(self):
        codes = [self.lab.code(STUDENT, n) for n in range(4)]
        self.assertEqual(self.ok("GET", f"{self.base}/inventory"), [])      # unclaimed devices are not listed
        slip = self.ok("GET", f"{self.base}/dojo/delivery")
        self.assertEqual([s["magic"] for s in slip], codes)
        self.assertFalse(any(s["claimed"] for s in slip))
        out = self.claim(codes[0], codes[1], "SRX300NOTACODE00")
        self.assertEqual((out["added"], out["error"], out["reason"]), (codes[:2], ["SRX300NOTACODE00"], ["invalid claim code"]))
        self.assertEqual({i["magic"] for i in out["inventory_added"]}, set(codes[:2]))
        again = self.claim(codes[0])
        self.assertEqual((again["added"], again["duplicated"]), ([], [codes[0]]))
        self.assertEqual(again["inventory_duplicated"][0]["serial"], out["inventory_added"][0]["serial"])
        inv = self.ok("GET", f"{self.base}/inventory")
        self.assertEqual(len(inv), 2)
        self.assertTrue(all(i["id"] == "00000000-0000-0000-1000-" + i["mac"] for i in inv))
        self.assertEqual([s["claimed"] for s in self.ok("GET", f"{self.base}/dojo/delivery")], [True, True, False, False])

    def test_other_orgs_codes_do_not_claim(self):
        out = self.claim(self.lab.code(OTHER, 0))
        self.assertEqual((out["added"], len(out["error"])), ([], 1))

    def test_assign_unassign_delete(self):
        a, b = (self.claim(self.lab.code(STUDENT, n))["inventory_added"][0] for n in (0, 1))
        site = self.make("sites", name="s")
        out = self.ok("PUT", f"{self.base}/inventory", {"op": "assign", "macs": [a["mac"], b["mac"]], "site_id": site["id"]})
        self.assertEqual(out["success"], [a["mac"], b["mac"]])
        self.assertEqual({i["site_id"] for i in self.ok("GET", f"{self.base}/inventory")}, {site["id"]})
        site_devs = self.ok("GET", f"/api/v1/sites/{site['id']}/devices")
        self.assertEqual({d["mac"] for d in site_devs}, {a["mac"], b["mac"]})
        self.assertEqual(len(self.ok("GET", f"{self.base}/inventory?unassigned=true")), 0)
        self.ok("PUT", f"{self.base}/inventory", {"op": "unassign", "macs": [a["mac"]]})
        self.assertEqual([i["mac"] for i in self.ok("GET", f"{self.base}/inventory?unassigned=true")], [a["mac"]])
        self.assertEqual(len(self.ok("GET", f"{self.base}/inventory?mac={b['mac']}")), 1)
        self.ok("PUT", f"{self.base}/inventory", {"op": "delete", "macs": [a["mac"], b["mac"]]})
        self.assertEqual(self.ok("GET", f"{self.base}/inventory"), [])
        self.assertEqual(self.claim(a["magic"])["added"], [a["magic"]])      # can be claimed again

    def test_errors_keep_error_and_reason_in_step(self):
        status, data, _ = self.lab.call(STUDENT, "PUT", f"{self.base}/inventory",
                                        {"op": "unassign", "macs": ["aaaaaaaaaaaa", "bbbbbbbbbbbb"]})
        self.assertEqual(status, 400)
        self.assertEqual(len(data["error"]), len(data["reason"]))    # the provider indexes reason by error position
        self.assertEqual(self.lab.call(STUDENT, "PUT", f"{self.base}/inventory", {"op": "assign", "macs": []})[0], 400)
        self.assertEqual(self.lab.call(STUDENT, "PUT", f"{self.base}/inventory", {"op": "explode"})[0], 400)
        gone = self.ok("PUT", f"{self.base}/inventory", {"op": "delete", "macs": ["aaaaaaaaaaaa"]})
        self.assertEqual((gone["success"], len(gone["error"])), ([], 1))   # deleting what is gone does not fail a destroy
        self.assertEqual(self.lab.call(STUDENT, "POST", f"{self.base}/inventory", {"a": 1})[0], 400)

    def test_site_delete_returns_devices_to_the_inventory(self):
        dev = self.claim(self.lab.code(STUDENT, 0))["inventory_added"][0]
        site = self.make("sites", name="s")
        self.ok("PUT", f"{self.base}/inventory", {"op": "assign", "macs": [dev["mac"]], "site_id": site["id"]})
        self.ok("PUT", f"/api/v1/sites/{site['id']}/devices/00000000-0000-0000-1000-{dev['mac']}", {"name": "gw"})
        self.ok("DELETE", f"/api/v1/sites/{site['id']}")
        inv = self.ok("GET", f"{self.base}/inventory")
        self.assertEqual((inv[0]["site_id"], inv[0].get("name")), (None, None))
        self.assertEqual(self.lab.call(STUDENT, "GET", f"/api/v1/sites/{site['id']}")[0], 404)

    def test_assign_to_a_missing_site_fails(self):
        dev = self.claim(self.lab.code(STUDENT, 0))["inventory_added"][0]
        status, _, _ = self.lab.call(STUDENT, "PUT", f"{self.base}/inventory",
                                     {"op": "assign", "macs": [dev["mac"]], "site_id": "00000000-0000-0000-0000-000000000001"})
        self.assertEqual(status, 400)


class Devices(LabCase):
    def setUp(self):
        super().setUp()
        self.dev = self.ok("POST", f"{self.base}/inventory", [self.lab.code(STUDENT, 0)])["inventory_added"][0]
        self.site = self.make("sites", name="s")
        self.ok("PUT", f"{self.base}/inventory", {"op": "assign", "macs": [self.dev["mac"]], "site_id": self.site["id"]})
        self.path = f"/api/v1/sites/{self.site['id']}/devices/00000000-0000-0000-1000-{self.dev['mac']}"

    def test_device_put_never_takes_identity_from_the_request(self):
        got = self.ok("PUT", self.path, {"name": "gw", "type": "", "mac": "ffffffffffff", "serial": "X", "model": "Y",
                                         "site_id": "z", "ntp_servers": ["10.0.0.1"]})
        self.assertEqual((got["name"], got["type"], got["mac"], got["model"], got["site_id"]),
                         ("gw", "gateway", self.dev["mac"], self.dev["model"], self.site["id"]))
        self.assertEqual(got["serial"], self.dev["serial"])
        self.assertEqual(got["org_id"], self.org)
        gone = self.ok("PUT", self.path, {"-ntp_servers": "", "-name": ""})
        self.assertNotIn("name", gone)
        self.assertNotIn("ntp_servers", gone)
        self.assertEqual(gone["mac"], self.dev["mac"])
        self.assertEqual(self.ok("GET", self.path), gone)

    def test_device_must_be_at_the_site(self):
        other = self.make("sites", name="elsewhere")
        wrong = f"/api/v1/sites/{other['id']}/devices/00000000-0000-0000-1000-{self.dev['mac']}"
        self.assertEqual(self.lab.call(STUDENT, "GET", wrong)[0], 404)
        self.assertEqual(self.lab.call(STUDENT, "PUT", wrong, {"name": "x"})[0], 404)
        self.assertEqual(self.lab.call(STUDENT, "PUT", self.path, {"ntp_servers": "no"})[0], 400)

    def test_site_setting_put_and_delete(self):
        base = f"/api/v1/sites/{self.site['id']}/setting"
        self.ok("PUT", base, {"vars": {"a": "1"}, "persist_config_on_device": True})
        self.assertEqual(self.ok("PUT", base, {"-persist_config_on_device": ""}).get("persist_config_on_device"), None)
        self.assertEqual(self.ok("GET", base)["vars"], {"a": "1"})
        self.assertEqual(self.lab.call(STUDENT, "PUT", base, {"vars": []})[0], 400)

    def test_cluster(self):
        b = self.ok("POST", f"{self.base}/inventory", [self.lab.code(STUDENT, 1)])["inventory_added"][0]
        self.ok("PUT", f"{self.base}/inventory", {"op": "assign", "macs": [b["mac"]], "site_id": self.site["id"]})
        cluster = f"/api/v1/sites/{self.site['id']}/devices/00000000-0000-0000-1000-{self.dev['mac']}/ha"
        self.assertEqual(self.lab.call(STUDENT, "GET", cluster)[0], 404)
        body = {"nodes": [{"mac": self.dev["mac"]}, {"mac": b["mac"]}]}
        self.assertEqual(self.ok("POST", cluster, body), body)
        self.assertEqual(self.ok("GET", cluster), body)
        status, data, _ = self.lab.call(STUDENT, "POST", cluster, body)
        self.assertEqual(status, 400)
        self.assertIn("already belong to a ha cluster", data["detail"])    # the provider matches this text
        self.ok("DELETE", cluster)
        self.assertEqual(self.lab.call(STUDENT, "GET", cluster)[0], 404)
        self.assertEqual(self.lab.call(STUDENT, "POST", cluster, {"nodes": [{"mac": self.dev["mac"]}]})[0], 400)
        self.assertEqual(self.lab.call(STUDENT, "POST", cluster, {"nodes": [{"mac": self.dev["mac"]},
                                                                              {"mac": "aaaaaaaaaaaa"}]})[0], 400)

    def test_rendered_config(self):
        status, text, headers = self.lab.call(STUDENT, "GET", self.path + "/dojo/config")
        self.assertIn(status, (200, 501))
        if status == 200:
            self.assertTrue(headers["Content-Type"].startswith("text/plain"))
            self.assertIn("set system host-name", text)


if __name__ == "__main__":
    unittest.main()
