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
  }
}
