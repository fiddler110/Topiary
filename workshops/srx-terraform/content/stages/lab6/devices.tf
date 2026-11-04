resource "mist_org_inventory" "delivery" {
  org_id = var.org_id

  inventory = merge(
    {
      for name, s in var.sites : s.claim_code => {
        site_id                = module.site[name].site_id
        unclaim_when_destroyed = true
      }
    },
    {
      (var.hub_claim_code) = {
        site_id                = mist_site.dc01.id
        unclaim_when_destroyed = true
      }
    },
  )
}

module "gateway" {
  source   = "./modules/gateway"
  for_each = var.sites

  site_id     = module.site[each.key].site_id
  device_id   = mist_org_inventory.delivery.inventory[each.value.claim_code].id
  name        = "${each.key}-gw"
  ntp_servers = each.value.ntp_servers
}
