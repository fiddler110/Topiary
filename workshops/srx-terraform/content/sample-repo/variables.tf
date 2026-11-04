# Your organization's id. Your terminal sets TF_VAR_org_id, so Terraform fills this in by itself.
variable "org_id" {
  description = "Mist organization id"
  type        = string
}
