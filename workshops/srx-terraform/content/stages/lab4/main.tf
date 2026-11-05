resource "mist_org_network" "corp" {
  org_id  = var.org_id
  name    = "corp"
  vlan_id = "10"
  subnet  = "{{site_subnet}}"
}

resource "mist_org_service" "web" {
  org_id    = var.org_id
  name      = "web"
  type      = "custom"
  addresses = ["0.0.0.0/0"]
  specs     = [{ protocol = "tcp", port_range = "443" }]
}

resource "mist_org_service" "dns" {
  org_id    = var.org_id
  name      = "dns"
  type      = "custom"
  addresses = ["0.0.0.0/0"]
  specs     = [{ protocol = "udp", port_range = "53" }]
}
