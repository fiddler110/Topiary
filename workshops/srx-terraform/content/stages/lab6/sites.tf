module "site" {
  source   = "./modules/site"
  for_each = var.sites

  org_id             = var.org_id
  name               = each.key
  address            = each.value.address
  country_code       = each.value.country_code
  timezone           = each.value.timezone
  gatewaytemplate_id = mist_org_gatewaytemplate.branch.id

  vars = {
    site_subnet = each.value.lan_subnet
    lan_ip      = each.value.lan_ip
    wan_ip      = each.value.wan_ip
    wan_gw      = each.value.wan_gw
  }
}
