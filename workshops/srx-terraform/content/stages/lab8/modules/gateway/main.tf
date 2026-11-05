variable "site_id" { type = string }
variable "device_id" { type = string }
variable "name" { type = string }

variable "dns_servers" {
  type    = list(string)
  default = null
}

resource "mist_device_gateway" "this" {
  device_id   = var.device_id
  site_id     = var.site_id
  name        = var.name
  dns_servers = var.dns_servers
}
