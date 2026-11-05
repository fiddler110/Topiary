terraform {
  backend "http" {
    address        = "https://api.mist.com/dojo-state/srx-estate"
    lock_address   = "https://api.mist.com/dojo-state/srx-estate"
    unlock_address = "https://api.mist.com/dojo-state/srx-estate"
    lock_method    = "LOCK"
    unlock_method  = "UNLOCK"
  }
}
