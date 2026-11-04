"""The acceptance bar: the REAL Juniper/mist Terraform provider against this server, end to end.

Starts wan-api on high ports with a temp CA and data dir, puts a tiny CONNECT proxy in front (the provider only
accepts the real Mist hostnames, so MIST_PROXY sends `api.mist.com:443` to the test server) and runs the real
`terraform` over a config that covers every resource of docs/SRX-MIST-PLAN.md section 4, with updates, an empty
second plan, drift, import and destroy, then the `http` state backend with locking.

Needs a terraform binary and a plugin dir holding juniper/mist 0.11.0 (a filesystem mirror layout); skips without them.
  WAN_TF_BIN      path to terraform           (default: `terraform` on PATH)
  WAN_TF_MIRROR   mirror/cache directory      (default: ./.tf-mirror, then the author's scratchpad cache)
Run: python3 -B -m unittest test_contract
"""
import http.client
import json
import os
import shutil
import socket
import ssl
import subprocess
import tempfile
import threading
import unittest

import server
import wan_ids

SCRATCH = "/tmp/claude-1000/-home-scott-Development-Topiary/5c0af9cd-4370-4309-8850-654fee77292e/scratchpad"
HERE = os.path.dirname(os.path.abspath(__file__))
USER = "student01"


def find_terraform():
    for cand in (os.environ.get("WAN_TF_BIN"), shutil.which("terraform"), f"{SCRATCH}/bin/terraform"):
        if cand and os.path.isfile(cand):
            return cand
    return None


def find_mirror():
    for cand in (os.environ.get("WAN_TF_MIRROR"), f"{HERE}/.tf-mirror", f"{SCRATCH}/plugin-cache"):
        if cand and os.path.isdir(f"{cand}/registry.terraform.io/juniper/mist"):
            return cand
    return None


TF_BIN, TF_MIRROR = find_terraform(), find_mirror()


class ConnectProxy:
    """Every CONNECT tunnel goes to the test server, whatever host was asked for (api.mist.com:443)."""

    def __init__(self, target_port):
        self.target = ("127.0.0.1", target_port)
        self.sock = socket.socket()
        self.sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.sock.bind(("127.0.0.1", 0))
        self.sock.listen(32)
        self.port = self.sock.getsockname()[1]
        threading.Thread(target=self.accept, daemon=True).start()

    def accept(self):
        while True:
            try:
                conn, _ = self.sock.accept()
            except OSError:
                return
            threading.Thread(target=self.tunnel, args=(conn,), daemon=True).start()

    @staticmethod
    def pipe(a, b):
        try:
            while True:
                data = a.recv(65536)
                if not data:
                    break
                b.sendall(data)
        except OSError:
            pass
        finally:
            for s in (a, b):
                try:
                    s.shutdown(socket.SHUT_RDWR)
                except OSError:
                    pass
                s.close()

    def tunnel(self, conn):
        buf = b""
        while b"\r\n\r\n" not in buf:
            more = conn.recv(4096)
            if not more:
                return
            buf += more
        up = socket.create_connection(self.target)
        conn.sendall(b"HTTP/1.1 200 Connection established\r\n\r\n")
        threading.Thread(target=self.pipe, args=(conn, up), daemon=True).start()
        self.pipe(up, conn)

    def close(self):
        self.sock.close()


MAIN_TF = '''
variable "org_id" { type = string }
variable "rev" { default = 1 }

terraform {
  required_providers {
    mist = { source = "juniper/mist", version = "= 0.11.0" }
  }
}
provider "mist" {}

resource "mist_org_network" "corp" {
  org_id  = var.org_id
  name    = "corp"
  subnet  = "{{site_subnet}}"
  vlan_id = "10"
}
resource "mist_org_network" "guest" {
  org_id  = var.org_id
  name    = "guest"
  subnet  = "10.20.0.0/24"
  vlan_id = "20"
}
resource "mist_org_service" "web" {
  org_id    = var.org_id
  name      = "web"
  type      = "custom"
  addresses = ["0.0.0.0/0"]
  specs     = [{ protocol = "tcp", port_range = "443" }]
}
resource "mist_org_servicepolicy" "corp_to_web" {
  org_id   = var.org_id
  name     = "corp-to-web"
  action   = var.rev == 1 ? "allow" : "deny"
  services = [mist_org_service.web.name]
  tenants  = [mist_org_network.corp.name]
}
resource "mist_org_gatewaytemplate" "branch" {
  org_id      = var.org_id
  name        = "branch-srx"
  type        = "standalone"
  dns_servers = var.rev == 1 ? ["10.10.0.53"] : ["10.10.0.53", "10.10.0.54"]
  port_config = {
    "ge-0/0/0" = { usage = "wan", name = "wan0", wan_type = "broadband",
                   ip_config = { type = "static", ip = "{{wan_ip}}", netmask = "/29", gateway = "{{wan_gw}}" } }
    "ge-0/0/1" = { usage = "lan", networks = [mist_org_network.corp.name] }
  }
  ip_configs = { (mist_org_network.corp.name) = { type = "static", ip = "{{lan_ip}}", netmask = "/24" } }
  service_policies = [{ servicepolicy_id = mist_org_servicepolicy.corp_to_web.id }]
}
resource "mist_org_deviceprofile_gateway" "edge" {
  org_id      = var.org_id
  name        = "edge-profile"
  dns_servers = ["10.10.0.53"]
}
resource "mist_org_sitegroup" "campus" {
  org_id = var.org_id
  name   = var.rev == 1 ? "campus" : "campus-2"
}
resource "mist_org_vpn" "hub" {
  org_id = var.org_id
  name   = "hub-spoke"
  type   = "hub_spoke"
  paths  = { "wan0" = { bfd_profile = var.rev == 1 ? "broadband" : "lte" } }
}

resource "mist_site" "ott" {
  org_id             = var.org_id
  name               = "ottawa-01"
  address            = var.rev == 1 ? "Ottawa, ON, Canada" : "Ottawa, Ontario, Canada"
  country_code       = "CA"
  timezone           = "America/Toronto"
  gatewaytemplate_id = mist_org_gatewaytemplate.branch.id
  sitegroup_ids      = [mist_org_sitegroup.campus.id]
}
resource "mist_site" "tor" {
  org_id             = var.org_id
  name               = "toronto-01"
  address            = "Toronto, ON, Canada"
  country_code       = "CA"
  timezone           = "America/Toronto"
  gatewaytemplate_id = mist_org_gatewaytemplate.branch.id
}
resource "mist_site_setting" "ott" {
  site_id = mist_site.ott.id
  vars = {
    site_subnet = "10.10.0.0/24"
    lan_ip      = "10.10.0.1"
    wan_ip      = "198.51.100.2"
    wan_gw      = "198.51.100.1"
  }
}
resource "mist_site_setting" "tor" {
  site_id = mist_site.tor.id
  vars = {
    site_subnet = "10.11.0.0/24"
    lan_ip      = "10.11.0.1"
    wan_ip      = "198.51.100.10"
    wan_gw      = "198.51.100.9"
  }
}

resource "mist_org_inventory" "inv" {
  org_id = var.org_id
  inventory = {
    "@CODE0@" = { site_id = mist_site.ott.id, unclaim_when_destroyed = true }
    "@CODE1@" = { site_id = mist_site.ott.id, unclaim_when_destroyed = true }
    "@CODE2@" = { site_id = mist_site.tor.id, unclaim_when_destroyed = true }
    "@CODE3@" = { unclaim_when_destroyed = true }
  }
}
resource "mist_org_deviceprofile_assign" "edge" {
  org_id           = var.org_id
  deviceprofile_id = mist_org_deviceprofile_gateway.edge.id
  macs             = [mist_org_inventory.inv.inventory["@CODE2@"].mac]
}
resource "mist_device_gateway" "tor_gw" {
  device_id   = mist_org_inventory.inv.inventory["@CODE2@"].id
  site_id     = mist_site.tor.id
  name        = var.rev == 1 ? "tor-gw-01" : "tor-gw-01a"
  ntp_servers = var.rev == 1 ? ["10.11.0.123"] : ["10.11.0.123", "10.11.0.124"]
  depends_on  = [mist_org_deviceprofile_assign.edge]
}
resource "mist_device_gateway_cluster" "ott_ha" {
  site_id    = mist_site.ott.id
  depends_on = [mist_org_inventory.inv]
  # Literal MACs (from the packing slip): the provider rejects two unknown values as a duplicate list value.
  nodes = [
    { mac = "@MAC0@" },
    { mac = "@MAC1@" },
  ]
}

data "mist_org_networks" "all" {
  org_id     = var.org_id
  depends_on = [mist_org_network.corp, mist_org_network.guest]
}
data "mist_org_services" "all" {
  org_id     = var.org_id
  depends_on = [mist_org_service.web]
}
data "mist_org_servicepolicies" "all" {
  org_id     = var.org_id
  depends_on = [mist_org_servicepolicy.corp_to_web]
}
data "mist_org_gatewaytemplates" "all" {
  org_id     = var.org_id
  depends_on = [mist_org_gatewaytemplate.branch]
}
data "mist_org_deviceprofiles_gateway" "all" {
  org_id     = var.org_id
  depends_on = [mist_org_deviceprofile_gateway.edge]
}
data "mist_org_sitegroups" "all" {
  org_id     = var.org_id
  depends_on = [mist_org_sitegroup.campus]
}
data "mist_org_vpns" "all" {
  org_id     = var.org_id
  depends_on = [mist_org_vpn.hub]
}
data "mist_sites" "all" {
  org_id     = var.org_id
  depends_on = [mist_site.ott, mist_site.tor]
}
data "mist_org_inventory" "all" {
  org_id     = var.org_id
  depends_on = [mist_org_inventory.inv]
}

output "counts" {
  value = {
    networks         = length(data.mist_org_networks.all.org_networks)
    services         = length(data.mist_org_services.all.org_services)
    servicepolicies  = length(data.mist_org_servicepolicies.all.org_servicepolicies)
    gatewaytemplates = length(data.mist_org_gatewaytemplates.all.org_gatewaytemplates)
    profiles         = length(data.mist_org_deviceprofiles_gateway.all.deviceprofiles)
    sitegroups       = length(data.mist_org_sitegroups.all.org_sitegroups)
    vpns             = length(data.mist_org_vpns.all.org_vpns)
    sites            = length(data.mist_sites.all.sites)
    inventory        = length(data.mist_org_inventory.all.org_inventory)
  }
}
'''

BACKEND_TF = '''
terraform {
  required_providers {
    mist = { source = "juniper/mist", version = "= 0.11.0" }
  }
  backend "http" {
    address        = "https://api.mist.com/dojo-state/lab"
    lock_address   = "https://api.mist.com/dojo-state/lab"
    unlock_address = "https://api.mist.com/dojo-state/lab"
    lock_method    = "LOCK"
    unlock_method  = "UNLOCK"
  }
}
provider "mist" {}
variable "org_id" { type = string }
resource "mist_org_network" "shared" {
  org_id  = var.org_id
  name    = "shared"
  subnet  = "10.30.0.0/24"
  vlan_id = "30"
}
'''

RC = '''provider_installation {
  filesystem_mirror {
    path    = "%s"
    include = ["registry.terraform.io/juniper/mist"]
  }
  direct {
    exclude = ["registry.terraform.io/juniper/mist"]
  }
}
'''


@unittest.skipUnless(TF_BIN and TF_MIRROR, "needs a terraform binary and a juniper/mist 0.11.0 mirror (WAN_TF_BIN, WAN_TF_MIRROR)")
class ContractBase(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tmp = tempfile.mkdtemp(prefix="wan-contract-")
        env = {"WAN_DATA_DIR": cls.tmp + "/data", "WAN_SECRETS_DIR": cls.tmp + "/secrets", "WAN_PKI_DIR": cls.tmp + "/pki",
               "WAN_HTTPS_PORT": "0", "WAN_HTTP_PORT": "0", "WAN_BIND": "127.0.0.1", "STUDENT_COUNT": "2",
               "BOT_COUNT": "0", "FACILITATOR_USERNAME": "root", "GATEWAY_TOKEN": "gw-token", "RESET_TOKEN": "reset-token"}
        server.log = lambda msg: None
        cls.app, cls.servers = server.start(env)
        cls.api_port = cls.servers[0].server_address[1]
        cls.portal_port = cls.servers[1].server_address[1]
        cls.proxy = ConnectProxy(cls.api_port)
        cls.token = wan_ids.api_token(cls.app.key, USER)
        cls.org = wan_ids.org_id(cls.app.key, USER)
        cls.codes = [wan_ids.claim_code(cls.app.key, USER, n) for n in range(4)]
        with open(cls.tmp + "/terraformrc", "w") as f:
            f.write(RC % TF_MIRROR)
        cls.env = {**os.environ, "TF_CLI_CONFIG_FILE": cls.tmp + "/terraformrc", "TF_IN_AUTOMATION": "1",
                   "TF_INPUT": "0", "CHECKPOINT_DISABLE": "1", "MIST_HOST": "api.mist.com",
                   "MIST_API_TOKEN": cls.token, "MIST_PROXY": f"http://127.0.0.1:{cls.proxy.port}",
                   "HTTPS_PROXY": f"http://127.0.0.1:{cls.proxy.port}", "https_proxy": f"http://127.0.0.1:{cls.proxy.port}",
                   "NO_PROXY": "", "no_proxy": "", "SSL_CERT_FILE": cls.tmp + "/pki/ca.crt",
                   "TF_VAR_org_id": cls.org, "TF_HTTP_USERNAME": USER, "TF_HTTP_PASSWORD": cls.token}
        cls.env.pop("TF_PLUGIN_CACHE_DIR", None)

    @classmethod
    def tearDownClass(cls):
        for srv in cls.servers:
            srv.shutdown()
            srv.server_close()
        cls.proxy.close()
        shutil.rmtree(cls.tmp, ignore_errors=True)

    # ---- helpers -----------------------------------------------------------------------------------------------
    def tf(self, cwd, *args, expect=(0,)):
        r = subprocess.run([TF_BIN, *args, "-no-color"] if args[0] not in ("output", "state", "version") else [TF_BIN, *args],
                           cwd=cwd, env=self.env, capture_output=True, text=True, timeout=300)
        if r.returncode not in expect:
            self.fail(f"terraform {' '.join(args)} exited {r.returncode} (wanted {expect}):\n{r.stdout[-3000:]}\n{r.stderr[-3000:]}")
        return r

    def api(self, method, path, body=None, token=None, port=None):
        ctx = ssl.create_default_context(cafile=self.tmp + "/pki/ca.crt")
        conn = http.client.HTTPSConnection("localhost", port or self.api_port, context=ctx, timeout=10)
        data = None if body is None else json.dumps(body)
        conn.request(method, path, body=data, headers={"Authorization": "Token " + (token or self.token)})
        r = conn.getresponse()
        raw = r.read()
        conn.close()
        return r.status, (json.loads(raw) if raw[:1] in (b"{", b"[") else raw.decode())

    def workdir(self, name, text):
        d = os.path.join(self.tmp, name)
        os.makedirs(d, exist_ok=True)
        with open(d + "/main.tf", "w") as f:
            f.write(text)
        return d


class TerraformLifecycle(ContractBase):
    def test_full_cycle(self):
        main = MAIN_TF
        for n, code in enumerate(self.codes):
            main = main.replace(f"@CODE{n}@", code)
        for n, slip in enumerate(self.app.store.get(self.org).data["delivery"][:2]):
            main = main.replace(f"@MAC{n}@", slip["mac"])
        d = self.workdir("srx", main)
        org = f"/api/v1/orgs/{self.org}"

        self.tf(d, "init", "-input=false")
        # ---- apply everything: every section-4 resource
        self.tf(d, "apply", "-auto-approve", "-input=false")
        self.tf(d, "plan", "-detailed-exitcode", "-input=false", expect=(0,))          # empty second plan
        # profiles is 0 on purpose: provider 0.11.0's mist_org_deviceprofiles_gateway asks for `?type=ap` (a provider
        # bug), so a server that filters by type answers with no AP profiles. `?type=gateway` finds the profile.
        counts = json.loads(self.tf(d, "output", "-json", "counts").stdout)
        self.assertEqual(counts, {"networks": 2, "services": 1, "servicepolicies": 1, "gatewaytemplates": 1,
                                  "profiles": 0, "sitegroups": 1, "vpns": 1, "sites": 2, "inventory": 4})
        self.assertEqual(len(self.api("GET", f"{org}/deviceprofiles?type=gateway")[1]), 1)
        self.assertEqual(self.api("GET", f"{org}/deviceprofiles?type=ap")[1], [])
        store = self.app.store.get(self.org).snapshot()
        self.assertEqual(len(store["inventory"]), 4)
        self.assertEqual(len(store["clusters"]), 1)
        self.assertEqual(sum(1 for e in store["inventory"] if e["deviceprofile_id"]), 1)
        ott = next(s for s in store["sites"].values() if s["name"] == "ottawa-01")
        self.assertEqual(store["site_settings"][ott["id"]]["vars"]["lan_ip"], "10.10.0.1")
        self.assertTrue(any(e["actor"] == USER for e in store["events"]))

        # ---- the rendered config (other part of the module; 501 only if renderer.py is absent)
        tor_dev = next(e for e in store["inventory"] if e["magic"] == self.codes[2])
        status, text = self.api("GET", f"/api/v1/sites/{tor_dev['site_id']}/devices/{tor_dev['id']}/dojo/config")
        self.assertIn(status, (200, 501))
        if status == 200:
            self.assertIn("198.51.100.10", text)

        # ---- updates: a template, a service policy and a device change in place
        self.tf(d, "apply", "-auto-approve", "-input=false", "-var", "rev=2")
        self.tf(d, "plan", "-detailed-exitcode", "-input=false", "-var", "rev=2", expect=(0,))
        store = self.app.store.get(self.org).snapshot()
        tmpl = next(iter(store["gatewaytemplates"].values()))
        self.assertEqual(tmpl["dns_servers"], ["10.10.0.53", "10.10.0.54"])
        self.assertEqual(next(iter(store["servicepolicies"].values()))["action"], "deny")
        self.assertEqual(next(iter(store["sitegroups"].values()))["name"], "campus-2")
        self.assertEqual(next(iter(store["vpns"].values()))["paths"]["wan0"]["bfd_profile"], "lte")
        self.assertEqual(next(s for s in store["sites"].values() if s["name"] == "ottawa-01")["address"],
                         "Ottawa, Ontario, Canada")
        self.assertEqual(store["devices"][tor_dev["id"]]["name"], "tor-gw-01a")
        self.assertEqual(store["devices"][tor_dev["id"]]["ntp_servers"], ["10.11.0.123", "10.11.0.124"])

        # ---- drift: an out-of-band API edit shows in plan, apply puts it back
        corp = next(n for n in store["networks"].values() if n["name"] == "corp")
        self.assertEqual(self.api("PUT", f"{org}/networks/{corp['id']}", {"vlan_id": "99"})[0], 200)
        self.tf(d, "plan", "-detailed-exitcode", "-input=false", "-var", "rev=2", expect=(2,))
        self.tf(d, "apply", "-auto-approve", "-input=false", "-var", "rev=2")
        self.tf(d, "plan", "-detailed-exitcode", "-input=false", "-var", "rev=2", expect=(0,))
        self.assertEqual(self.api("GET", f"{org}/networks/{corp['id']}")[1]["vlan_id"], "10")

        # ---- drift made by the portal: facilitator only, with the header
        portal = lambda user, hdr: self.portal_post(f"/wan/api/orgs/{self.org}/drift", user, hdr)
        self.assertEqual(portal(USER, {"X-Requested-With": "dojo-admin"}), 403)
        self.assertEqual(portal("root", {}), 403)
        self.assertEqual(portal("root", {"X-Requested-With": "dojo-admin"}), 200)
        self.tf(d, "plan", "-detailed-exitcode", "-input=false", "-var", "rev=2", expect=(2,))
        self.assertEqual(self.app.store.get(self.org).snapshot()["events"][-1]["actor"], "portal:facilitator")
        self.tf(d, "apply", "-auto-approve", "-input=false", "-var", "rev=2")

        # ---- import: a network and a device come back under Terraform with no change
        guest = next(n for n in store["networks"].values() if n["name"] == "guest")
        self.tf(d, "state", "rm", "mist_org_network.guest")
        self.tf(d, "plan", "-detailed-exitcode", "-input=false", "-var", "rev=2", expect=(2,))   # it would create a second
        self.tf(d, "import", "-input=false", "-var", "rev=2", "mist_org_network.guest", f"{self.org}.{guest['id']}")
        self.tf(d, "state", "rm", "mist_device_gateway.tor_gw")
        self.tf(d, "import", "-input=false", "-var", "rev=2", "mist_device_gateway.tor_gw",
                f"{tor_dev['site_id']}.{tor_dev['id']}")
        self.tf(d, "plan", "-detailed-exitcode", "-input=false", "-var", "rev=2", expect=(0,))

        # ---- destroy leaves an empty org (the delivery is still there to claim again)
        self.tf(d, "destroy", "-auto-approve", "-input=false", "-var", "rev=2")
        store = self.app.store.get(self.org).snapshot()
        for name in ("networks", "services", "servicepolicies", "gatewaytemplates", "deviceprofiles", "sitegroups",
                     "vpns", "sites", "site_settings", "devices", "clusters"):
            self.assertEqual(store[name], {}, name)
        self.assertEqual(store["inventory"], [])
        self.assertEqual(len(store["delivery"]), 5)

    def portal_post(self, path, user, extra):
        conn = http.client.HTTPConnection("127.0.0.1", self.portal_port, timeout=10)
        conn.request("POST", path, headers={"X-Gateway-Token": "gw-token", "X-Auth-User": user, **extra})
        r = conn.getresponse()
        r.read()
        conn.close()
        return r.status


class TerraformStateBackend(ContractBase):
    def test_http_backend_with_locking(self):
        d = self.workdir("backend", BACKEND_TF)
        self.tf(d, "init", "-input=false")
        self.tf(d, "apply", "-auto-approve", "-input=false")
        # the state is on the server, not on disk, and the lock was released
        self.assertFalse(os.path.exists(d + "/terraform.tfstate"))
        status, state = self.api("GET", "/dojo-state/lab") if False else self.state_get("lab")
        self.assertEqual(status, 200)
        self.assertEqual(json.loads(state)["resources"][0]["type"], "mist_org_network")
        self.tf(d, "plan", "-detailed-exitcode", "-input=false", expect=(0,))
        # someone else holds the lock: plan refuses, force-unlock clears it
        self.assertEqual(self.state_call("LOCK", "lab", b'{"ID": "held-by-other", "Who": "somebody"}')[0], 200)
        r = self.tf(d, "plan", "-input=false", "-lock-timeout=1s", expect=(1,))
        self.assertIn("held-by-other", r.stdout + r.stderr)
        self.tf(d, "force-unlock", "-force", "held-by-other")
        self.tf(d, "plan", "-detailed-exitcode", "-input=false", expect=(0,))
        self.tf(d, "destroy", "-auto-approve", "-input=false")

    def state_get(self, name):
        return self.state_call("GET", name)

    def state_call(self, method, name, body=b""):
        import base64
        ctx = ssl.create_default_context(cafile=self.tmp + "/pki/ca.crt")
        conn = http.client.HTTPSConnection("localhost", self.api_port, context=ctx, timeout=10)
        auth = base64.b64encode(f"{USER}:{self.token}".encode()).decode()
        conn.request(method, f"/dojo-state/{name}", body=body, headers={"Authorization": "Basic " + auth})
        r = conn.getresponse()
        raw = r.read()
        conn.close()
        return r.status, raw


if __name__ == "__main__":
    unittest.main()
