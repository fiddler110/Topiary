variable "org_id" {
  description = "Mist organization id"
  type        = string
}

variable "claim_codes" {
  description = "Claim code of the gateway for each site"
  type        = map(string)
}
