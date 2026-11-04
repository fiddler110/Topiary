# Lab 4: Claim and assign

**Goal:** claim the gateways from your delivery, assign each to its site, and read the Junos configuration each one receives. All commands run in `~/lab/srx-terraform`.

> **Starting here?** Run `dojo prep 4`.

---

## 1. The delivery

On a real greenfield build, a box arrives with a **claim code** (the `magic`). Claiming it adds the box to your org's inventory; assigning it puts it in a site, where it picks up the site's template. This is zero-touch provisioning: nobody logs in to the SRX.

```sh
dojo wan delivery
```

You have four boxes. Use three now and keep one for the capstone:

| Box | Site |
| --- | ---- |
| first `SRX300` | `ottawa-01` |
| second `SRX300` | `toronto-01` |
| first `SRX345` | `montreal-01` |
| second `SRX345` | kept for Lab 9 |

A claim code is 15 characters of `0-9A-Z`, such as `SRX300ABC123XYZ`. The provider checks the format before it calls the API.

## 2. Put the codes in a variable, not in the resource

Claim codes are inputs, so they go in a variable and a `terraform.tfvars` file (`terraform.tfvars` is loaded automatically). Change `variables.tf`:

```hcl
# variables.tf
variable "org_id" {
  description = "Mist organization id"
  type        = string
}

variable "claim_codes" {
  description = "Claim code of the gateway for each site"
  type        = map(string)
}
```

Create `terraform.tfvars` with **your** codes from `dojo wan delivery` (the ones below are placeholders):

```hcl
# terraform.tfvars
claim_codes = {
  "ottawa-01"   = "SRX300XXXXXXXXX"
  "toronto-01"  = "SRX300YYYYYYYYY"
  "montreal-01" = "SRX345XXXXXXXXX"
}
```

## 3. Claim and assign

`mist_org_inventory` takes a map. The key is a claim code, and the value says where the device goes. Create `devices.tf`:

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
```

`unclaim_when_destroyed = true` hands the box back to the delivery if you `destroy`. Without it, a destroyed config leaves the box claimed and a rebuild fails.

```sh
terraform fmt
terraform validate
terraform plan
```

<!-- dojo-reveal: Result of plan -->

```text
  # mist_org_inventory.delivery will be created
  + resource "mist_org_inventory" "delivery" {
      + inventory = {
          + "SRX300XXXXXXXXX" = {
              + site_id                = (known after apply)
              + unclaim_when_destroyed = true
              ...
Plan: 1 to add, 0 to change, 0 to destroy.
```

Only one resource: the inventory is one object holding all three devices.

<!-- /dojo-reveal -->

```sh
terraform apply
```

## 4. Read the configuration the gateway gets

The gateway now sits in a site with the `branch-srx` template. Ask for its Junos config by MAC address (a serial or a name works too):

```sh
dojo wan delivery
dojo wan config <mac of your first SRX300>
```

<!-- dojo-reveal: Result -->

```text
# Rendered by Dojo WAN (preview, not a real device)
# site: ottawa-01
# template: branch-srx
# profile: (none)

# system
set system host-name <the serial number>
set system name-server 192.0.2.53
set system ntp server 192.0.2.123

# interfaces
set interfaces ge-0/0/0 description "wan0"
set interfaces ge-0/0/0 unit 0 family inet address 198.51.100.2/29
set interfaces ge-0/0/1 vlan-tagging
set interfaces ge-0/0/1 unit 10 vlan-id 10
set interfaces ge-0/0/1 unit 10 family inet address 10.10.0.1/24
...
set routing-options static route 0.0.0.0/0 next-hop 198.51.100.1
```

Your variables are filled in: `{{wan_ip}}` became `198.51.100.2`. The host name is just the serial number: a device has no name until you give it one (Lab 5). If a line still shows `{{something}}`, a variable is missing or misspelled in `sites.tf`; the config ends with a warning that names it.

<!-- /dojo-reveal -->

Try the other two boxes. One template, three configurations.

## Check

```sh
dojo check 4
```

<!-- dojo-reveal: What it checks -->

Through the API: three gateways are in your inventory, each in the right site, and each one's rendered configuration holds that site's WAN address and no unreplaced `{{variable}}`.

<!-- /dojo-reveal -->

```sh
git add variables.tf terraform.tfvars devices.tf
git commit -m "Claim the delivered gateways and assign them to their sites"
```

## Check yourself

1. What is the key in the `inventory` map?
2. The Ottawa gateway lands in `ottawa-01`. Where does it get its template from?

<!-- dojo-reveal: Show the answer -->

1. The claim code (or the MAC of a device already in the org).
2. From the site: `mist_site.ottawa.gatewaytemplate_id`.

<!-- /dojo-reveal -->

## Common mistakes

| You see | Cause / fix |
| ------- | ----------- |
| `claim code ... is not valid` / format error before any call | Claim codes are exactly 15 characters of `0-9A-Z`. Copy the `magic` column, with no spaces. |
| The API says the code is already claimed, or `duplicated` | The code is claimed by an earlier run or a typo points at a box that is not yours. Compare with `dojo wan delivery`. |
| `Invalid for_each` or `Invalid key` on `var.claim_codes["..."]` | The key in `terraform.tfvars` must match the site name exactly (`ottawa-01`). |
| `dojo wan config` says no device found | Not claimed yet, or you used the wrong MAC. `dojo wan delivery` prints the `mac` column. |

**Next:** [lab5.md](lab5.md)
