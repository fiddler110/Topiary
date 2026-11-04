# Lab 3: Sites and variables

**Goal:** make three sites that share one template, and give each its own addresses through site variables. All commands run in `~/lab/srx-terraform`.

> **Starting here?** Run `dojo prep 3`.

---

## 1. A site is a place, plus its variables

A `mist_site` is a branch office: a name, an address, a country and a time zone. Pointing it at a gateway template (`gatewaytemplate_id`) means every gateway that lands in the site gets that template.

The values that differ per site live in **site variables**, in `mist_site_setting.vars`. This is where `{{wan_ip}}` and friends get their values.

| Site | WAN | LAN |
| ---- | --- | --- |
| `ottawa-01` | 198.51.100.2/29, gateway .1 | 10.10.0.0/24, gateway at 10.10.0.1 |
| `toronto-01` | 203.0.113.2/29, gateway .1 | 10.20.0.0/24, gateway at 10.20.0.1 |
| `montreal-01` | 192.0.2.2/29, gateway .1 | 10.30.0.0/24, gateway at 10.30.0.1 |

## 2. Write the sites

Create `sites.tf`. The first site is here in full; **you** add Toronto and Montreal by copying it and changing the names and values from the table. (Look for the pattern: that is what Lab 6 will tidy up.)

```hcl
# sites.tf
resource "mist_site" "ottawa" {
  org_id             = var.org_id
  name               = "ottawa-01"
  address            = "Ottawa, ON, Canada"
  country_code       = "CA"
  timezone           = "America/Toronto"
  gatewaytemplate_id = mist_org_gatewaytemplate.branch.id
}

resource "mist_site_setting" "ottawa" {
  site_id = mist_site.ottawa.id
  vars = {
    site_subnet = "10.10.0.0/24"
    lan_ip      = "10.10.0.1"
    wan_ip      = "198.51.100.2"
    wan_gw      = "198.51.100.1"
  }
}

resource "mist_site" "toronto" {
  org_id             = var.org_id
  name               = "toronto-01"
  address            = "Toronto, ON, Canada"
  country_code       = "CA"
  timezone           = "America/Toronto"
  gatewaytemplate_id = mist_org_gatewaytemplate.branch.id
}

resource "mist_site_setting" "toronto" {
  site_id = mist_site.toronto.id
  vars = {
    site_subnet = "10.20.0.0/24"
    lan_ip      = "10.20.0.1"
    wan_ip      = "203.0.113.2"
    wan_gw      = "203.0.113.1"
  }
}

resource "mist_site" "montreal" {
  org_id             = var.org_id
  name               = "montreal-01"
  address            = "Montreal, QC, Canada"
  country_code       = "CA"
  timezone           = "America/Toronto"
  gatewaytemplate_id = mist_org_gatewaytemplate.branch.id
}

resource "mist_site_setting" "montreal" {
  site_id = mist_site.montreal.id
  vars = {
    site_subnet = "10.30.0.0/24"
    lan_ip      = "10.30.0.1"
    wan_ip      = "192.0.2.2"
    wan_gw      = "192.0.2.1"
  }
}
```

Notice `site_id = mist_site.ottawa.id`: the setting belongs to a site, so it points at it. That reference is also why the site is made first.

```sh
terraform fmt
terraform validate
terraform plan
```

**Your turn:** predict the count. Three sites and three settings.

<!-- dojo-reveal: Result of plan -->

```text
Plan: 6 to add, 0 to change, 0 to destroy.
```

<!-- /dojo-reveal -->

```sh
terraform apply
```

In the portal, **Sites** now lists three. They are empty: no gateway has arrived yet.

## 3. Where do the variables go?

The org network `corp` has the subnet `{{site_subnet}}`. Open **Networks** in the portal, then a site's settings. One network definition, three subnets:

```sh
SITE=$(terraform state show mist_site.ottawa | awk '/^ *id /{print $3}' | tr -d '"')
curl -s -H "Authorization: Token $MIST_API_TOKEN" \
  https://api.mist.com/api/v1/sites/$SITE/setting | python3 -m json.tool | head -20
```

## Check

```sh
dojo check 3
```

<!-- dojo-reveal: What it checks -->

Through the API: three sites named `ottawa-01`, `toronto-01` and `montreal-01`, each using the `branch-srx` template, and each with the four variables `site_subnet`, `lan_ip`, `wan_ip` and `wan_gw`.

<!-- /dojo-reveal -->

```sh
git add sites.tf
git commit -m "Add the three branch sites and their variables"
```

## Check yourself

1. Where does a value that differs per site go: the template, or the site?
2. What happens to a `{{variable}}` that no site setting defines?

<!-- dojo-reveal: Show the answer -->

1. The site: in `mist_site_setting.vars`.
2. It stays as literal text in the config. Mist (and Dojo WAN's preview) flag it as an unknown variable. Lab 4 shows where.

<!-- /dojo-reveal -->

## Common mistakes

| You see | Cause / fix |
| ------- | ----------- |
| `Error: Reference to undeclared resource` | A typo in `mist_site.ottawa`. The resource name is the second label. |
| `Missing required argument "address"` | A `mist_site` needs `address` as well as `name`. |
| `a variable name has a typo` (for example `{{wan_ipp}}`) | Terraform can't see it; it is a string. The unknown variable shows up in Lab 4's rendered config. Fix the spelling in the settings. |
| Three near-identical blocks | That is expected for now. Lab 6 replaces them with one loop. |

**Next:** [lab4.md](lab4.md)
