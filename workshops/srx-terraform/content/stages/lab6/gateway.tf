resource "mist_org_servicepolicy" "corp_to_web" {
  org_id   = var.org_id
  name     = "corp-to-web"
  action   = "allow"
  services = [mist_org_service.web.name, mist_org_service.dns.name]
  tenants  = [mist_org_network.corp.name]
}

resource "mist_org_gatewaytemplate" "branch" {
  org_id = var.org_id
  name   = "branch-srx"
  type   = "standalone"

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
  dns_servers  = ["192.0.2.53"]
  ntp_override = true
  ntp_servers  = ["192.0.2.123"]
}
