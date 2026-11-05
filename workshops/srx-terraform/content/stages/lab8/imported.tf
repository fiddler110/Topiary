resource "mist_org_network" "guest" {
  org_id  = var.org_id
  name    = "guest"
  vlan_id = "20"
  subnet  = "172.16.20.0/24"
}
