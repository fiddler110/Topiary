variable "org_id" { type = string }
variable "name" { type = string }
variable "address" { type = string }
variable "country_code" { type = string }
variable "timezone" { type = string }
variable "gatewaytemplate_id" { type = string }
variable "vars" { type = map(string) }

resource "mist_site" "this" {
  org_id             = var.org_id
  name               = var.name
  address            = var.address
  country_code       = var.country_code
  timezone           = var.timezone
  gatewaytemplate_id = var.gatewaytemplate_id
}

resource "mist_site_setting" "this" {
  site_id = mist_site.this.id
  vars    = var.vars
}

output "site_id" {
  value = mist_site.this.id
}
