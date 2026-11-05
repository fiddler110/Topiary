# Lab 6: Structure

**Goal:** replace three copy-pasted sites with a module and a loop over a map, without destroying anything. All commands run in `~/lab/srx-terraform`.

> **Starting here?** Run `dojo prep 6`.

---

## 1. Why refactor

`sites.tf` repeats the same two blocks three times. A fourth site means a fourth copy, and a typo in one of them is easy to miss. The goal is **one map entry per site**. But Terraform keys every object in state by its address, `mist_site.ottawa`. Rename or move the resource, and Terraform sees a resource that is gone and a new one: it plans to **destroy the real site and create another**. Here, that means a site, its variables and its gateway assignment are rebuilt. Wrong on a live network.

The `moved` block is the tool: it tells Terraform "the object at the old address is the same object, now at this new address".

## 2. Write down what exists

Save the ids of your sites. You will compare them at the end:

```sh
curl -s -H "Authorization: Token $MIST_API_TOKEN" \
  https://api.mist.com/api/v1/orgs/$MIST_ORG_ID/sites \
  | python3 -c 'import json,sys; [print(s["name"], s["id"]) for s in json.load(sys.stdin)]' \
  | tee ~/lab/site-ids.before
terraform state list
```

## 3. Two modules

A **module** is a folder of `.tf` files with inputs (variables) and outputs. Each module needs its own `required_providers`, or Terraform looks for a provider called `hashicorp/mist`.

```hcl
# modules/site/versions.tf
terraform {
  required_providers {
    mist = {
      source = "juniper/mist"
    }
  }
}
```

```hcl
# modules/site/main.tf
variable "org_id" { type = string }
variable "name" { type = string }
variable "address" { type = string }
variable "country_code" { type = string }
variable "timezone" { type = string }
variable "gatewaytemplate_id" { type = string }
variable "vars" { type = map(string) }

resource "mist_site" "this" {
  org_id             = var.org_id
  name               = var.name
  address            = var.address
  country_code       = var.country_code
  timezone           = var.timezone
  gatewaytemplate_id = var.gatewaytemplate_id
}

resource "mist_site_setting" "this" {
  site_id = mist_site.this.id
  vars    = var.vars
}

output "site_id" {
  value = mist_site.this.id
}
```

```hcl
# modules/gateway/versions.tf
terraform {
  required_providers {
    mist = {
      source = "juniper/mist"
    }
  }
}
```

```hcl
# modules/gateway/main.tf
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
```

`default = null` means "leave this setting alone", so a site that doesn't need a local DNS server doesn't send one.

## 4. One map for all sites

Replace `variables.tf`:

```hcl
# variables.tf
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
```

Keep the `dc-01` hub **out** of this map: it is not a branch (it has no template), and `hub.tf` stays as it is. Its claim code moves from the old `claim_codes` map to its own variable. Add it to `variables.tf`:

```hcl
# variables.tf (add)
variable "hub_claim_code" {
  description = "Claim code of the dc-01 hub gateway (not one of the branch sites)"
  type        = string
}
```

Replace `terraform.tfvars` (your claim codes go in `claim_code`; the placeholders are the same ones as in Lab 4):

```hcl
# terraform.tfvars
hub_claim_code = "SRX1500ZZZZZZZZ"

sites = {
  "ottawa-01" = {
    address      = "Ottawa, ON, Canada"
    country_code = "CA"
    timezone     = "America/Toronto"
    claim_code   = "SRX300XXXXXXXXX"
    wan_ip       = "198.51.100.2"
    wan_gw       = "198.51.100.1"
    lan_subnet   = "10.10.0.0/24"
    lan_ip       = "10.10.0.1"
    dns_servers  = ["10.10.0.53"]
  }
  "toronto-01" = {
    address      = "Toronto, ON, Canada"
    country_code = "CA"
    timezone     = "America/Toronto"
    claim_code   = "SRX300YYYYYYYYY"
    wan_ip       = "203.0.113.2"
    wan_gw       = "203.0.113.1"
    lan_subnet   = "10.20.0.0/24"
    lan_ip       = "10.20.0.1"
  }
  "montreal-01" = {
    address      = "Montreal, QC, Canada"
    country_code = "CA"
    timezone     = "America/Toronto"
    claim_code   = "SRX345XXXXXXXXX"
    wan_ip       = "192.0.2.2"
    wan_gw       = "192.0.2.1"
    lan_subnet   = "10.30.0.0/24"
    lan_ip       = "10.30.0.1"
  }
}
```

Replace `sites.tf` and `devices.tf` with loops over that map:

```hcl
# sites.tf
module "site" {
  source   = "./modules/site"
  for_each = var.sites

  org_id             = var.org_id
  name               = each.key
  address            = each.value.address
  country_code       = each.value.country_code
  timezone           = each.value.timezone
  gatewaytemplate_id = mist_org_gatewaytemplate.branch.id

  vars = {
    site_subnet = each.value.lan_subnet
    lan_ip      = each.value.lan_ip
    wan_ip      = each.value.wan_ip
    wan_gw      = each.value.wan_gw
  }
}
```

```hcl
# devices.tf
resource "mist_org_inventory" "delivery" {
  org_id = var.org_id

  inventory = merge(
    {
      for name, s in var.sites : s.claim_code => {
        site_id                = module.site[name].site_id
        unclaim_when_destroyed = true
      }
    },
    {
      (var.hub_claim_code) = {
        site_id                = mist_site.dc01.id
        unclaim_when_destroyed = true
      }
    },
  )
}

module "gateway" {
  source   = "./modules/gateway"
  for_each = var.sites

  site_id     = module.site[each.key].site_id
  device_id   = mist_org_inventory.delivery.inventory[each.value.claim_code].id
  name        = "${each.key}-gw"
  dns_servers = each.value.dns_servers
}
```

In `profile.tf`, change the assignment to read the hub's claim code from the new variable, `macs = [mist_org_inventory.delivery.inventory[var.hub_claim_code].mac]`: edit the line, or run this.

```sh
sed -i 's/var.claim_codes\["dc-01"\]/var.hub_claim_code/' profile.tf
```

Every branch gateway now gets a name and the Ottawa one keeps its local DNS server, from the map.

```sh
terraform fmt -recursive
terraform init
terraform validate
```

(`init` again, because there are modules now.)

## 5. Plan it first WITHOUT `moved`

**Your turn:** predict what happens to the sites. Then read the plan carefully. **Do not apply it.**

```sh
terraform plan
```

<!-- dojo-reveal: Result -->

```text
  # mist_site.ottawa will be destroyed
  # (because mist_site.ottawa is not in configuration)
  ...
  # module.site["ottawa-01"].mist_site.this will be created
  ...
Plan: 9 to add, 2 to change, 7 to destroy.
```

Terraform sees seven objects with no home (three sites, their three settings, the Ottawa gateway override) and nine with no history. Applying this would delete three live sites and their settings. Your counts may differ by one or two; the destroys are the point. Always read the destroy count.

<!-- /dojo-reveal -->

## 6. Add the `moved` blocks

```hcl
# moved.tf
moved {
  from = mist_site.ottawa
  to   = module.site["ottawa-01"].mist_site.this
}
moved {
  from = mist_site_setting.ottawa
  to   = module.site["ottawa-01"].mist_site_setting.this
}
moved {
  from = mist_site.toronto
  to   = module.site["toronto-01"].mist_site.this
}
moved {
  from = mist_site_setting.toronto
  to   = module.site["toronto-01"].mist_site_setting.this
}
moved {
  from = mist_site.montreal
  to   = module.site["montreal-01"].mist_site.this
}
moved {
  from = mist_site_setting.montreal
  to   = module.site["montreal-01"].mist_site_setting.this
}
moved {
  from = mist_device_gateway.ottawa
  to   = module.gateway["ottawa-01"].mist_device_gateway.this
}
```

```sh
terraform validate
terraform plan
```

<!-- dojo-reveal: Result -->

```text
  # mist_site.ottawa has moved to module.site["ottawa-01"].mist_site.this
  ...
Plan: 2 to add, 0 to change, 0 to destroy.
```

Seven objects moved, nothing destroyed. The two additions are the Toronto and Montreal gateway overrides, which now exist for every site.

<!-- /dojo-reveal -->

```sh
terraform apply
```

Compare the site ids with the ones you saved. They must not change:

```sh
curl -s -H "Authorization: Token $MIST_API_TOKEN" \
  https://api.mist.com/api/v1/orgs/$MIST_ORG_ID/sites \
  | python3 -c 'import json,sys; [print(s["name"], s["id"]) for s in json.load(sys.stdin)]' \
  | diff - ~/lab/site-ids.before && echo "same ids"
terraform state list
```

Keep `moved.tf` in the repo until everyone who uses this state has applied. After that it can go.

## Check

```sh
dojo check 6
```

<!-- dojo-reveal: What it checks -->

Through the API: the three branches and the `dc-01` hub, with the same ids as `~/lab/site-ids.before`, all three gateways named `<site>-gw`, and Terraform's state lists modules (`module.site["ottawa-01"]` and so on). A site that was destroyed and recreated would have a new id.

<!-- /dojo-reveal -->

```sh
git add -A modules sites.tf devices.tf profile.tf moved.tf variables.tf terraform.tfvars
git commit -m "Move sites and gateways into modules driven by one sites map"
```

## Check yourself

1. A resource moves into a module with no `moved` block. What does `plan` say, and what would `apply` do?
2. How do you add a fourth site now?

<!-- dojo-reveal: Show the answer -->

1. It plans to destroy the old object and create a new one. `apply` would delete the real thing.
2. One new entry in the `sites` map, with its own claim code. No other file changes.

<!-- /dojo-reveal -->

## Common mistakes

| You see | Cause / fix |
| ------- | ----------- |
| `Could not load plugin` / `provider hashicorp/mist` | A module is missing its `versions.tf` with `source = "juniper/mist"`. |
| `Module not installed` | Run `terraform init` after adding modules. |
| `Plan: 9 to add, 2 to change, 7 to destroy.` | The `moved` blocks are missing or their addresses are spelled wrong. Compare with `terraform state list`. Do not apply. |
| `Invalid value for input variable` on `sites` | A field is missing or the wrong type in `terraform.tfvars`. `dns_servers` is optional; everything else is required. |
| `Cycle` | Something in `sites.tf` points back at itself. The site module must not reference `mist_org_inventory`. |

**Next:** [lab7.md](lab7.md)
