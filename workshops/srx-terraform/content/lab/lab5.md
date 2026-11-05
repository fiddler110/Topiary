# Lab 5: Roles

**Goal:** learn the roles Mist builds a gateway's configuration from (spoke template, hub profile, device override), and decide where each kind of setting belongs. All commands run in `~/lab/srx-terraform`.

> **Starting here?** Run `dojo prep 5`.

---

## 1. The model: roles, not a stack

A gateway gets its configuration from one of these, by role:

```text
spoke   a branch site        gateway TEMPLATE, assigned to the site        (every branch that uses it)
hub     a hub/DC gateway     HUB PROFILE (a device profile), assigned      (the hub gateways you assign it to)
                             to the device, at a site with no template
one box a single device      DEVICE OVERRIDE (mist_device_gateway)         (that device: the last resort)
```

Three more pieces:

- **Site variables** (`{{wan_ip}}` ...) fill the blanks in whichever of the above applies. A device's own `vars` override the site's, key by key.
- **DNS and NTP** set in a template or a profile only apply when `dns_override = true` / `ntp_override = true` is set next to them. Without the flag the gateway inherits the site's values.
- A device override always applies to its box (Mist lets a device override only DNS and the application policy).

Mist does not document putting a template **and** a profile on the same gateway, so we don't. Branches get the template; the hub gets a profile and sits at a site with no template. (Dojo WAN will render both if you try, and leave a `# note:` in the config to tell you.)

## 2. See what you have

The template (Lab 2) says DNS `192.0.2.53` and NTP `192.0.2.123`, and both set the override flags. Look at a branch gateway:

```sh
dojo wan config <mac of your Toronto gateway> | grep -E 'name-server|ntp'
```

```text
set system name-server 192.0.2.53
set system ntp server 192.0.2.123
```

## 3. A hub profile and a hub site

Your delivery has a fifth box, an `SRX1500`. It goes to a hub: a data-centre site, `dc-01`. A hub is not a copy of a branch, so it gets a **hub profile** (the Mist UI calls them *Hub Profiles*) instead of the template. Three new files.

The site has **no** `gatewaytemplate_id`. Create `hub.tf` (the hub's addresses are variables, like any site's; pick values that do not clash with the branches):

```hcl
# hub.tf
resource "mist_site" "dc01" {
  org_id       = var.org_id
  name         = "dc-01"
  address      = "Mississauga, ON, Canada"
  country_code = "CA"
  timezone     = "America/Toronto"
}

resource "mist_site_setting" "dc01" {
  site_id = mist_site.dc01.id
  vars = {
    site_subnet = "10.99.0.0/24"
    lan_ip      = "10.99.0.1"
    wan_ip      = "198.18.0.2"
    wan_gw      = "198.18.0.1"
  }
}
```

The profile carries its own ports (a profile with no template has nothing else to take them from), its own DNS, and the override flag. Create `profile.tf`:

```hcl
# profile.tf
resource "mist_org_deviceprofile_gateway" "hub" {
  org_id = var.org_id
  name   = "hub-profile"

  port_config = {
    "ge-0/0/0" = {
      usage    = "wan"
      name     = "wan0"
      wan_type = "broadband"
      ip_config = {
        type    = "static"
        ip      = "{{wan_ip}}"
        netmask = "/29"
        gateway = "{{wan_gw}}"
      }
    }
    "ge-0/0/1" = {
      usage    = "lan"
      networks = [mist_org_network.corp.name]
    }
  }

  ip_configs = {
    (mist_org_network.corp.name) = {
      type    = "static"
      ip      = "{{lan_ip}}"
      netmask = "/24"
    }
  }

  service_policies = [{ servicepolicy_id = mist_org_servicepolicy.corp_to_web.id }]

  dns_override = true
  dns_servers  = ["10.99.0.53"]
}

resource "mist_org_deviceprofile_assign" "hub" {
  org_id           = var.org_id
  deviceprofile_id = mist_org_deviceprofile_gateway.hub.id
  macs             = [mist_org_inventory.delivery.inventory[var.claim_codes["dc-01"]].mac]
}
```

The assignment names one MAC: the hub gateway. The branches are not on the profile. (`type` on the profile is set by Mist; you do not write it.)

Claim the `SRX1500` into `dc-01`. Add its claim code (`dojo wan delivery`) to `terraform.tfvars`, and its entry to the inventory in `devices.tf`. The profile reads that inventory entry, so both files change before you apply.

```hcl
# terraform.tfvars
claim_codes = {
  "ottawa-01"   = "SRX300XXXXXXXXX"
  "toronto-01"  = "SRX300YYYYYYYYY"
  "montreal-01" = "SRX345XXXXXXXXX"
  "dc-01"       = "SRX1500ZZZZZZZZ"
}
```

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
    (var.claim_codes["dc-01"]) = {
      site_id                = mist_site.dc01.id
      unclaim_when_destroyed = true
    }
  }
}
```

**Your turn:** before you apply, predict the hub's `name-server` line, and whether the Toronto gateway changes.

```sh
terraform fmt
terraform validate
terraform apply
dojo wan config <mac of your SRX1500> | grep -E 'profile|note|name-server'
```

<!-- dojo-reveal: Results -->

```text
# profile: hub-profile
set system name-server 10.99.0.53
```

The hub's DNS comes from its profile, because the flag is on. Toronto does not change: it is a spoke and never saw the profile. There is no `# note:` line, because the hub has no template.

<!-- /dojo-reveal -->

**Your turn, the flag:** remove the `dns_override = true` line from `profile.tf`, plan and apply, then read the hub's config again. Predict first.

<!-- dojo-reveal: Results -->

```text
# note: profile dns_servers not applied (dns_override is not true)
```

The `name-server` line is gone. Without the flag the profile's DNS is ignored and the gateway inherits the site's and org's (this lab sets none). Put the line back and apply again.

<!-- /dojo-reveal -->

## 4. A device override

One site needs its own time server: Ottawa has a local clock. The right layer for "this one box" is the device. `mist_device_gateway` configures a single claimed gateway. Add the device to `devices.tf` (the whole file is shown; the Ottawa block at the end is the new one):

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
    (var.claim_codes["dc-01"]) = {
      site_id                = mist_site.dc01.id
      unclaim_when_destroyed = true
    }
  }
}

resource "mist_device_gateway" "ottawa" {
  device_id   = mist_org_inventory.delivery.inventory[var.claim_codes["ottawa-01"]].id
  site_id     = mist_site.ottawa.id
  name        = "ottawa-01-gw"
  dns_servers = ["10.10.0.53"]
}
```

`device_id` and the site come from the inventory entry, so the override waits for the claim. `name` becomes the Junos host name. In Terraform and the API, setting the field on the device is the override; in the Mist portal it is the device's "Override Template Settings" checkbox. Mist lets a device override only DNS and the application policy, not NTP or the ports.

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
set system name-server 10.10.0.53
set system ntp server 192.0.2.123
```

The **name** and **DNS** come from the device, the **NTP** from the template.

<!-- /dojo-reveal -->

## 5. The house rule

| Setting is... | Put it in... | Example |
| ------------- | ------------ | ------- |
| the same everywhere | org objects | the corp network, services, service policies |
| the same for every branch | the **template** (spoke) | the WAN/LAN port layout, branch DNS/NTP (with the override flags) |
| the same for a hub | a **hub profile**, on a site with no template | the hub's own ports and DNS (with `dns_override`) |
| different per site, and fills a blank | a **site variable** | `{{wan_ip}}`, `{{site_subnet}}` |
| true for exactly one box | a **device override** | its name, its own DNS server |

Never both a template and a profile on one gateway. The device override is the last resort. Every override is a box that no longer looks like its neighbours, and a reviewer has to remember it exists. Prefer a variable; then the template or profile for the role; then, rarely, an override.

## Check

```sh
dojo check 5
```

<!-- dojo-reveal: What it checks -->

Through the API: `hub-profile` is assigned only to the `dc-01` gateway, whose site has no template, and its config shows the profile's DNS and no "both apply" note. Toronto and Montreal show the template's DNS and NTP. The Ottawa gateway is named `ottawa-01-gw` and shows the device's own DNS (not the template's) and the template's NTP.

<!-- /dojo-reveal -->

```sh
git add hub.tf profile.tf devices.tf
git commit -m "Add the dc-01 hub with a hub profile, and a local DNS override for Ottawa"
```

## Check yourself

1. The template says DNS `192.0.2.53` and the device says `10.10.0.53`. Which ends up on the box?
2. You put `dns_servers` in a profile and the config shows no such line. What did you forget?
3. Montreal's gateway needs its own DNS server. Which do you reach for first?

<!-- dojo-reveal: Show the answer -->

1. `10.10.0.53`: a device's own DNS setting always applies.
2. `dns_override = true` (and `ntp_override = true` for NTP). Without the flag the profile's value is ignored.
3. A **site variable** if the template can use one. Only then a device override. Never a profile on a spoke.

<!-- /dojo-reveal -->

## Common mistakes

| You see | Cause / fix |
| ------- | ----------- |
| The hub has no `name-server` line, and a `# note: ... not applied` | `dns_override = true` is missing from the profile. |
| `# note: a template and a profile both apply` | The hub site has a `gatewaytemplate_id`. Remove it: in this lab a hub takes a profile only, because Mist doesn't document how the two combine on one gateway. |
| Ottawa still shows `name-server 192.0.2.53` (the template's) | `dns_servers` is missing from `mist_device_gateway.ottawa`, maybe because it went on the template or a profile instead. Only the device's own value overrides the template for one gateway. |
| `Missing required argument "site_id"` | `mist_device_gateway` needs both `device_id` and `site_id`. |
| `Invalid index` on `inventory[...]` | The claim code in `terraform.tfvars` doesn't match the one in the inventory map (is `dc-01` in both?). |
| A setting is overridden in two places and you can't tell which | Read the rendered config, not the files: `dojo wan config <device>`. |
| `type` is rejected on the profile | `type` is read-only on `mist_org_deviceprofile_gateway`. Remove the line. |

**Next:** [lab6.md](lab6.md)
