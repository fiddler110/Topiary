terraform {
  required_version = ">= 1.17"

  required_providers {
    mist = {
      source  = "juniper/mist"
      version = "0.11.0"
    }
  }
}
