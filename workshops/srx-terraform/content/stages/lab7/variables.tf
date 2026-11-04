variable "org_id" {
  description = "Mist organization id"
  type        = string
}

variable "sites" {
  description = "Every branch office, by site name"
  type = map(object({
    address      = string
    country_code = string
    timezone     = string
    claim_code   = string
    wan_ip       = string
    wan_gw       = string
    lan_subnet   = string
    lan_ip       = string
    ntp_servers  = optional(list(string))
  }))
}
