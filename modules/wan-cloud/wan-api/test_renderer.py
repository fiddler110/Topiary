import copy
import unittest

import renderer

DEV = "00000000-0000-0000-1000-aabbccddeeff"


def store():
    return {
        "org": {"id": "o1", "name": "Dojo Org x"},
        "networks": {"n1": {"name": "corp", "subnet": "{{site_subnet}}", "vlan_id": "10"},
                     "n2": {"name": "dmz", "subnet": "10.20.0.0/24", "vlan_id": 20}},
        "services": {
            "s1": {"name": "web", "type": "custom", "addresses": ["0.0.0.0/0"],
                   "specs": [{"protocol": "tcp", "port_range": "443"}]},
            "s2": {"name": "mail", "type": "custom", "addresses": ["10.20.0.25/32"],
                   "specs": [{"protocol": "tcp", "port_range": "25,587"}]},
            "s3": {"name": "ident", "type": "apps", "app_name": "youtube"},
        },
        "servicepolicies": {
            "p1": {"name": "corp-to-web", "action": "allow", "services": ["web"], "tenants": ["corp"]},
            "p2": {"name": "corp-to-dmz", "action": "allow", "services": ["mail", "ident"], "tenants": ["corp"]},
        },
        "gatewaytemplates": {"t1": {
            "name": "branch-srx", "ntp_servers": ["10.0.0.1"], "dns_servers": ["9.9.9.9"],
            "port_config": {
                "ge-0/0/0": {"usage": "wan", "name": "wan0",
                             "ip_config": {"type": "static", "ip": "{{wan_ip}}", "netmask": "/29", "gateway": "{{wan_gw}}"}},
                "ge-0/0/1": {"usage": "lan", "networks": ["corp", "dmz"]}},
            "ip_configs": {"corp": {"type": "static", "ip": "{{lan_ip}}", "netmask": "/24"},
                           "dmz": {"type": "static", "ip": "10.20.0.1", "netmask": "255.255.255.0"}},
            "service_policies": [{"servicepolicy_id": "p1"}, {"servicepolicy_id": "p2"}],
            "dhcpd_config": {"enabled": True, "config": {"corp": {"type": "local", "ip_start": "10.10.0.10", "ip_end": "10.10.0.99", "dns_servers": ["10.10.0.53"]}}},
        }},
        "deviceprofiles": {"d1": {"name": "edge-profile", "dnsOverride": True, "dns_servers": ["10.10.0.53"],
                                  "ntpOverride": True, "ntp_servers": ["10.0.0.2"]}},
        "sites": {"site1": {"name": "ottawa-01", "gatewaytemplate_id": "t1"}},
        "site_settings": {"site1": {"vars": {"site_subnet": "10.10.0.0/24", "lan_ip": "10.10.0.1",
                                             "wan_ip": "198.51.100.2", "wan_gw": "198.51.100.1"}}},
        "inventory": [{"id": DEV, "serial": "S1", "mac": "aabbccddeeff", "model": "SRX300", "type": "gateway",
                       "site_id": "site1", "deviceprofile_id": "d1"}],
        "devices": {DEV: {"name": "ott-gw-01", "ntp_servers": ["10.10.0.123"],
                          "additional_config_cmds": ["set system services ssh"]}},
        "events": [],
    }


class Overrides(unittest.TestCase):
    def render(self, st):
        return renderer.render(st, DEV).splitlines()

    def test_without_flag_site_values_are_inherited(self):
        st = store()
        del st["deviceprofiles"]["d1"]["dnsOverride"]
        st["site_settings"]["site1"]["dns_servers"] = ["192.0.2.53"]
        lines = self.render(st)
        self.assertIn("set system name-server 192.0.2.53", lines)
        self.assertNotIn("set system name-server 10.10.0.53", lines)
        self.assertNotIn("set system name-server 9.9.9.9", lines)    # template has no flag either
        self.assertIn("# note: profile dns_servers not applied (dnsOverride is not true)", lines)
        self.assertIn("# note: template dns_servers not applied (dnsOverride is not true)", lines)

    def test_template_flag_applies_template_dns(self):
        st = store()
        st["deviceprofiles"] = {}
        st["inventory"][0]["deviceprofile_id"] = None
        st["gatewaytemplates"]["t1"]["dnsOverride"] = True
        lines = self.render(st)
        self.assertIn("set system name-server 9.9.9.9", lines)
        self.assertFalse(any("both apply" in x for x in lines))

    def test_template_and_profile_together_are_noted(self):
        self.assertTrue(any("a template and a profile both apply" in x for x in self.render(store())))

    def test_device_vars_override_site_vars(self):
        st = store()
        st["devices"][DEV]["vars"] = {"wan_ip": "203.0.113.9"}
        lines = self.render(st)
        self.assertIn("set interfaces ge-0/0/0 unit 0 family inet address 203.0.113.9/29", lines)
        self.assertIn("set routing-options static route 0.0.0.0/0 next-hop 198.51.100.1", lines)   # other site vars kept


class T(unittest.TestCase):
    def setUp(self):
        self.out = renderer.render(store(), DEV)
        self.lines = self.out.splitlines()

    def has(self, line):
        self.assertIn(line, self.lines, self.out)

    def test_header(self):
        self.assertEqual(self.lines[0], "# Rendered by Dojo WAN (preview, not a real device)")
        for s in ("# site: ottawa-01", "# template: branch-srx", "# profile: edge-profile"):
            self.has(s)

    def test_precedence(self):
        self.has("set system ntp server 10.10.0.123")       # device wins over profile and template
        self.assertNotIn("set system ntp server 10.0.0.2", self.lines)
        self.assertNotIn("set system ntp server 10.0.0.1", self.lines)
        self.has("set system name-server 10.10.0.53")       # profile (dnsOverride) wins over template
        self.assertNotIn("set system name-server 9.9.9.9", self.lines)
        self.has("set system host-name ott-gw-01")

    def test_map_merge(self):
        s = store()
        s["devices"][DEV]["port_config"] = {"ge-0/0/2": {"usage": "lan", "networks": ["dmz"]}}
        out = renderer.render(s, DEV)
        self.assertIn("set interfaces ge-0/0/0 unit 0 family inet address 198.51.100.2/29", out)  # kept
        self.assertIn("ge-0/0/2 unit 20 vlan-id 20", out)                                       # added

    def test_variables(self):
        self.has("set interfaces ge-0/0/0 unit 0 family inet address 198.51.100.2/29")
        self.has("set routing-options static route 0.0.0.0/0 next-hop 198.51.100.1")
        self.has("set interfaces ge-0/0/1 unit 10 family inet address 10.10.0.1/24")
        self.has("set interfaces ge-0/0/1 unit 20 family inet address 10.20.0.1/24")
        self.assertNotIn("WARNING", self.out)

    def test_unknown_variable(self):
        s = store()
        del s["site_settings"]["site1"]["vars"]["wan_gw"]
        out = renderer.render(s, DEV)
        self.assertIn("# WARNING: unknown variable {{wan_gw}}", out)
        self.assertIn("next-hop {{wan_gw}}", out)

    def test_zones_nat(self):
        self.has("set security zones security-zone untrust interfaces ge-0/0/0.0")
        self.has("set security zones security-zone corp interfaces ge-0/0/1.10")
        self.has("set security zones security-zone dmz interfaces ge-0/0/1.20")
        self.has("set security zones security-zone corp interfaces ge-0/0/1.10 host-inbound-traffic system-services ping")
        self.has("set security nat source rule-set snat-corp from zone corp")
        self.has("set security nat source rule-set snat-corp to zone untrust")
        self.has("set security nat source rule-set snat-corp rule all then source-nat interface")

    def test_policies(self):
        self.has("set applications application web term t1 protocol tcp")
        self.has("set applications application web term t1 destination-port 443")
        self.has("set applications application mail term t2 destination-port 587")
        self.has("set security policies from-zone corp to-zone untrust policy corp-to-web match application web")
        self.has("set security policies from-zone corp to-zone untrust policy corp-to-web then permit")
        # mail's address is inside the dmz subnet -> to-zone dmz
        self.has("set security policies from-zone corp to-zone dmz policy corp-to-dmz match destination-address mail-1")
        self.has("set security address-book global address mail-1 10.20.0.25/32")
        self.assertTrue(any("ident: application-identified" in l for l in self.lines))
        self.assertNotIn("match application ident", self.out)

    def test_dhcp_and_extra(self):
        self.has("set access address-assignment pool corp family inet network 10.10.0.0/24")
        self.has("set access address-assignment pool corp family inet range r1 low 10.10.0.10 high 10.10.0.99")
        self.has("set system services dhcp-local-server group corp interface ge-0/0/1.10")
        self.assertEqual(self.lines[-1], "set system services ssh")

    def test_dhcp_wan_and_deny(self):
        s = store()
        s["gatewaytemplates"]["t1"]["port_config"]["ge-0/0/0"]["ip_config"] = {"type": "dhcp"}
        s["servicepolicies"]["p1"]["action"] = "deny"
        out = renderer.render(s, DEV)
        self.assertIn("ge-0/0/0 unit 0 family inet dhcp", out)
        self.assertIn("policy corp-to-web then deny", out)
        self.assertNotIn("next-hop", out)

    def test_robustness(self):
        for st in ({}, None, [], "x", {"inventory": "x"}, {"inventory": [{"id": DEV}], "devices": []}):
            out = renderer.render(st, DEV)
            self.assertTrue(out.startswith("# Rendered by Dojo WAN"))
        junk = store()
        junk["gatewaytemplates"]["t1"].update({
            "port_config": {"ge-0/0/1-3": {"usage": "lan"}, 5: None, "ge-0/0/9": {"usage": "lan", "networks": ["nope", 7]},
                            "ge-0/0/8": {"usage": "wan", "ip_config": {"type": "static", "ip": "bad"}}},
            "ip_configs": [], "service_policies": [None, {"servicepolicy_id": "zzz"}, {"servicepolicy_id": "p1", "action": "weird"}],
            "dhcpd_config": "yes", "additional_config_cmds": [1, None, "set x"]})
        out = renderer.render(junk, DEV)
        self.assertIn("# skipped:", out)
        self.assertTrue(renderer.render(store(), "no-such-device").count("# skipped: device not found"))

    def test_untagged_network_beside_tagged_is_skipped(self):
        # Junos refuses unit 0 without a vlan-id on a port with vlan-tagging.
        st = store()
        st["networks"]["n3"] = {"name": "flat", "subnet": "10.30.0.0/24"}
        st["gatewaytemplates"]["t1"]["port_config"]["ge-0/0/1"]["networks"].append("flat")
        out = renderer.render(st, DEV)
        self.assertIn("# skipped: untagged network 'flat' on ge-0/0/1, a port with tagged VLANs", out)
        self.assertNotIn("set interfaces ge-0/0/1 unit 0", out)

    def test_determinism(self):
        a = renderer.render(store(), DEV)
        s = store()
        s["networks"] = dict(reversed(list(s["networks"].items())))
        b = renderer.render(s, DEV)
        self.assertEqual(a, b)
        self.assertEqual(a, renderer.render(copy.deepcopy(store()), DEV))


if __name__ == "__main__":
    unittest.main()
