# Build-time only: lists the providers to mirror into /opt/terraform-providers.
# Keep this pin identical to the one in the workshop's versions.tf files.
terraform {
  required_providers {
    mist = {
      source  = "juniper/mist"
      version = "0.11.0"
    }
  }
}
