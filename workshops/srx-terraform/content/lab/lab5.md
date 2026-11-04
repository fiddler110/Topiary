# Lab 5: Layers

**Goal:** learn the layers a gateway's configuration is built from, see which one wins, and decide where each kind of setting belongs. All commands run in `~/lab/srx-terraform`.

> **Starting here?** Run `dojo prep 5`.

---

## 1. Who gets the last word

A gateway's final configuration is merged from layers. Each layer overrides the one before it, setting by setting:

```text
org objects      networks, services, service policies   (shared by everything)
   |
gateway template   the branch design                    (all sites that use it)
   |  + site variables ({{wan_ip}} ...)                  (per site, fills the blanks)
device profile     a role: "edge", "lab", "hub"         (every device assigned to it)
   |
device override    this one box                         (one device)
```

Dojo WAN renders the config in exactly this order: **template, then profile, then device**. The last layer that sets a value wins. A layer that does not mention a setting leaves the earlier one alone.

You will set `dns_servers` and `ntp_servers` at three layers and watch the result change.

## 2. See what you have

The template (Lab 2) says DNS `192.0.2.53` and NTP `192.0.2.123`. Look at a gateway:

```sh
dojo wan config <mac of your Toronto gateway> | grep -E 'name-server|ntp'
```

```text
set system name-server 192.0.2.53
set system ntp server 192.0.2.123
```

## 3. A device profile

A **device profile** is a role. Create `profile.tf`:

```hcl
# profile.tf
resource "mist_org_deviceprofile_gateway" "edge" {
  org_id      = var.org_id
  name        = "edge-profile"
  dns_servers = ["10.99.0.53"]
}

resource "mist_org_deviceprofile_assign" "edge" {
  org_id           = var.org_id
  deviceprofile_id = mist_org_deviceprofile_gateway.edge.id
  macs             = [for d in mist_org_inventory.delivery.inventory : d.mac]
}
```

The `macs` list is built from the inventory you already manage: every device you claimed gets the profile. (`type` on the profile is set by Mist; you do not write it.)

**Your turn:** before you apply, predict what the Toronto gateway's `name-server` line says afterwards, and its `ntp` line.

```sh
terraform fmt
terraform validate
terraform apply
dojo wan config <mac of your Toronto gateway> | grep -E 'name-server|ntp'
```

<!-- dojo-reveal: Results -->

```text
set system name-server 10.99.0.53
set system ntp server 192.0.2.123
```

The profile sets DNS, so it beats the template. The profile says nothing about NTP, so the template's value stays.

<!-- /dojo-reveal -->

## 4. A device override

One site needs its own time server: Ottawa has a local clock. The right layer for "this one box" is the device. `mist_device_gateway` configures a single claimed gateway. Add to `devices.tf` (the whole file is shown; the inventory block is unchanged):

```hcl
# devices.tf
resource "mist_org_inventory" "delivery" {
  org_id = var.org_id

  inventory = {
    (var.claim_codes["ottawa-01"]) = {
      site_id                = mist_site.ottawa.id
      unclaim_when_destroyed = true
    }
    (var.claim_codes["toronto-01"]) = {
      site_id                = mist_site.toronto.id
      unclaim_when_destroyed = true
    }
    (var.claim_codes["montreal-01"]) = {
      site_id                = mist_site.montreal.id
      unclaim_when_destroyed = true
    }
  }
}

resource "mist_device_gateway" "ottawa" {
  device_id   = mist_org_inventory.delivery.inventory[var.claim_codes["ottawa-01"]].id
  site_id     = mist_site.ottawa.id
  name        = "ottawa-01-gw"
  ntp_servers = ["10.10.0.123"]
}
```

`device_id` and the site come from the inventory entry, so the override waits for the claim. `name` becomes the Junos host name.

```sh
terraform fmt
terraform validate
terraform plan
terraform apply
dojo wan config ottawa-01-gw | grep -E 'host-name|name-server|ntp'
```

<!-- dojo-reveal: Result -->

```text
set system host-name ottawa-01-gw
set system name-server 10.99.0.53
set system ntp server 10.10.0.123
```

Three layers in one answer: the **name** and **NTP** come from the device, the **DNS** from the profile.

<!-- /dojo-reveal -->

## 5. The house rule

| Setting is... | Put it in... | Example |
| ------------- | ------------ | ------- |
| the same everywhere | org objects or the **template** | the corp network, the WAN/LAN port layout |
| different per site, and fills a blank | a **site variable** | `{{wan_ip}}`, `{{site_subnet}}` |
| the same for a role | a **device profile** | DNS servers for edge gateways |
| true for exactly one box | a **device override** | its name, a local NTP server |

The device layer is the last resort. Every override is a box that no longer looks like its neighbours, and a reviewer has to remember it exists. Prefer a variable; then a profile; then, rarely, an override.

## Check

```sh
dojo check 5
```

<!-- dojo-reveal: What it checks -->

Through the API: an `edge-profile` is assigned to all three gateways; the Toronto and Montreal configs show the profile's DNS and the template's NTP; the Ottawa gateway is named `ottawa-01-gw` and shows the device's NTP.

<!-- /dojo-reveal -->

```sh
git add profile.tf devices.tf
git commit -m "Add the edge profile and a local NTP override for Ottawa"
```

## Check yourself

1. The template says NTP `192.0.2.123` and the device says `10.10.0.123`. Which ends up on the box?
2. Montreal's gateway needs its own DNS server. Which layer do you reach for first?

<!-- dojo-reveal: Show the answer -->

1. `10.10.0.123`: the device layer is applied last.
2. A **site variable** if the template can use one. Only then a device override. A new profile fits if several sites share the need.

<!-- /dojo-reveal -->

## Common mistakes

| You see | Cause / fix |
| ------- | ----------- |
| The Ottawa gateway still shows the template's NTP | You put `ntp_servers` on the **profile** (which applies to all three) instead of the device. Move it. |
| `Missing required argument "site_id"` | `mist_device_gateway` needs both `device_id` and `site_id`. |
| `Invalid index` on `inventory[...]` | The claim code in `terraform.tfvars` doesn't match the one in the inventory map. |
| A setting is overridden in two places and you can't tell which | Read the rendered config, not the files: `dojo wan config <device>`. |
| `type` is rejected on the profile | `type` is read-only on `mist_org_deviceprofile_gateway`. Remove the line. |

**Next:** [lab6.md](lab6.md)
