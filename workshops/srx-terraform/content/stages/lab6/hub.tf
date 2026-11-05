# The hub site has no gateway template: its gateway takes a hub profile (profile.tf).
resource "mist_site" "dc01" {
  org_id       = var.org_id
  name         = "dc-01"
  address      = "Mississauga, ON, Canada"
  country_code = "CA"
  timezone     = "America/Toronto"
}

resource "mist_site_setting" "dc01" {
  site_id = mist_site.dc01.id
  vars = {
    site_subnet = "10.99.0.0/24"
    lan_ip      = "10.99.0.1"
    wan_ip      = "198.18.0.2"
    wan_gw      = "198.18.0.1"
  }
}
