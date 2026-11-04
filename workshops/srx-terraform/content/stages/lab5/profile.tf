resource "mist_org_deviceprofile_gateway" "hub" {
  org_id = var.org_id
  name   = "hub-profile"

  port_config = {
    "ge-0/0/0" = {
      usage    = "wan"
      name     = "wan0"
      wan_type = "broadband"
      ip_config = {
        type    = "static"
        ip      = "{{wan_ip}}"
        netmask = "/29"
        gateway = "{{wan_gw}}"
      }
    }
    "ge-0/0/1" = {
      usage    = "lan"
      networks = [mist_org_network.corp.name]
    }
  }

  ip_configs = {
    (mist_org_network.corp.name) = {
      type    = "static"
      ip      = "{{lan_ip}}"
      netmask = "/24"
    }
  }

  service_policies = [{ servicepolicy_id = mist_org_servicepolicy.corp_to_web.id }]

  dns_override = true
  dns_servers  = ["10.99.0.53"]
}

resource "mist_org_deviceprofile_assign" "hub" {
  org_id           = var.org_id
  deviceprofile_id = mist_org_deviceprofile_gateway.hub.id
  macs             = [mist_org_inventory.delivery.inventory[var.claim_codes["dc-01"]].mac]
}
