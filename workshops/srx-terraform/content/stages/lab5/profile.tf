resource "mist_org_deviceprofile_gateway" "edge" {
  org_id      = var.org_id
  name        = "edge-profile"
  dns_servers = ["10.99.0.53"]
}

resource "mist_org_deviceprofile_assign" "edge" {
  org_id           = var.org_id
  deviceprofile_id = mist_org_deviceprofile_gateway.edge.id
  macs             = [for d in mist_org_inventory.delivery.inventory : d.mac]
}
