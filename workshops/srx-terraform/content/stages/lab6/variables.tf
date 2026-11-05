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
    dns_servers  = optional(list(string))
  }))
}

variable "hub_claim_code" {
  description = "Claim code of the dc-01 hub gateway (not one of the branch sites)"
  type        = string
}
