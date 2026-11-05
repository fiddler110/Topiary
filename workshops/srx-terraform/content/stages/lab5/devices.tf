resource "mist_org_inventory" "delivery" {
  org_id = var.org_id

  inventory = {
    (var.claim_codes["ottawa-01"]) = {
      site_id                = mist_site.ottawa.id
      unclaim_when_destroyed = true
    }
    (var.claim_codes["toronto-01"]) = {
      site_id                = mist_site.toronto.id
      unclaim_when_destroyed = true
    }
    (var.claim_codes["montreal-01"]) = {
      site_id                = mist_site.montreal.id
      unclaim_when_destroyed = true
    }
    (var.claim_codes["dc-01"]) = {
      site_id                = mist_site.dc01.id
      unclaim_when_destroyed = true
    }
  }
}

resource "mist_device_gateway" "ottawa" {
  device_id   = mist_org_inventory.delivery.inventory[var.claim_codes["ottawa-01"]].id
  site_id     = mist_site.ottawa.id
  name        = "ottawa-01-gw"
  dns_servers = ["10.10.0.53"]
}
