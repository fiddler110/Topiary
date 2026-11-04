resource "mist_site" "ottawa" {
  org_id             = var.org_id
  name               = "ottawa-01"
  address            = "Ottawa, ON, Canada"
  country_code       = "CA"
  timezone           = "America/Toronto"
  gatewaytemplate_id = mist_org_gatewaytemplate.branch.id
}

resource "mist_site_setting" "ottawa" {
  site_id = mist_site.ottawa.id
  vars = {
    site_subnet = "10.10.0.0/24"
    lan_ip      = "10.10.0.1"
    wan_ip      = "198.51.100.2"
    wan_gw      = "198.51.100.1"
  }
}

resource "mist_site" "toronto" {
  org_id             = var.org_id
  name               = "toronto-01"
  address            = "Toronto, ON, Canada"
  country_code       = "CA"
  timezone           = "America/Toronto"
  gatewaytemplate_id = mist_org_gatewaytemplate.branch.id
}

resource "mist_site_setting" "toronto" {
  site_id = mist_site.toronto.id
  vars = {
    site_subnet = "10.20.0.0/24"
    lan_ip      = "10.20.0.1"
    wan_ip      = "203.0.113.2"
    wan_gw      = "203.0.113.1"
  }
}

resource "mist_site" "montreal" {
  org_id             = var.org_id
  name               = "montreal-01"
  address            = "Montreal, QC, Canada"
  country_code       = "CA"
  timezone           = "America/Toronto"
  gatewaytemplate_id = mist_org_gatewaytemplate.branch.id
}

resource "mist_site_setting" "montreal" {
  site_id = mist_site.montreal.id
  vars = {
    site_subnet = "10.30.0.0/24"
    lan_ip      = "10.30.0.1"
    wan_ip      = "192.0.2.2"
    wan_gw      = "192.0.2.1"
  }
}
