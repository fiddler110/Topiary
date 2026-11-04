# Lab 2: The gateway template

**Goal:** describe what every branch SRX looks like once, in a `mist_org_gatewaytemplate`, and read the Junos configuration it produces. All commands run in `~/lab/srx-terraform`.

> **Starting here?** Run `dojo prep 2` to catch up with Lab 1.

---

## 1. A template is the shared part of a config

You will have many branch offices. They should not each be hand-built. The **gateway template** holds what is the same everywhere: which port is the WAN, which is the LAN, which networks live where, and which service policies apply. Anything that differs per site is a `{{variable}}`.

| Piece | In this lab |
| ----- | ----------- |
| `port_config` | `ge-0/0/0` is the WAN (static address from variables), `ge-0/0/1` is the LAN carrying `corp` |
| `ip_configs` | the gateway's own address on each network, keyed by network **name** |
| `service_policies` | which policies apply (here: `corp-to-web`) |
| `dns_servers`, `ntp_servers` | the branch DNS and time servers. They only replace what the site would otherwise inherit because `dns_override` and `ntp_override` are `true` (Lab 5) |

## 2. Write a policy and the template

A **service policy** says which tenants (networks) may use which services. Create `gateway.tf`:

```hcl
# gateway.tf
resource "mist_org_servicepolicy" "corp_to_web" {
  org_id   = var.org_id
  name     = "corp-to-web"
  action   = "allow"
  services = [mist_org_service.web.name, mist_org_service.dns.name]
  tenants  = [mist_org_network.corp.name]
}

resource "mist_org_gatewaytemplate" "branch" {
  org_id = var.org_id
  name   = "branch-srx"
  type   = "standalone"

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
  dns_servers  = ["192.0.2.53"]
  ntp_override = true
  ntp_servers  = ["192.0.2.123"]
}
```

Two things to notice:

- `mist_org_network.corp.name` is a **reference**. Terraform sees it, so it creates the network before the policy and the policy before the template. You never write an order.
- The map key `(mist_org_network.corp.name)` is in parentheses because a key that is an expression needs them.
- Without `dns_override = true` Mist ignores the template's `dns_servers` and the gateway keeps the site's inherited DNS. The same goes for `ntp_override` and NTP.

```sh
terraform fmt
terraform validate
```

## 3. Plan and apply

**Your turn:** before you run it, predict how many resources are added.

```sh
terraform plan
terraform apply
```

<!-- dojo-reveal: Results -->

```text
Plan: 2 to add, 0 to change, 0 to destroy.
...
Apply complete! Resources: 2 added, 0 changed, 0 destroyed.
```

The earlier three are untouched; Terraform only plans the difference.

<!-- /dojo-reveal -->

## 4. Where is the Junos config?

A template alone is not on any box. It starts to matter when a site uses it (Lab 3) and a device lands in that site (Lab 4). Until then, open the portal's **Templates** page and look at what you stored. Next lab, `dojo wan config <gateway>` shows the Junos `set` commands a gateway receives, with the variables filled in.

Remember the preview rule: the Dojo WAN configuration is a **preview**, built from the parts you can confirm on a real SRX (interfaces, zones, policies, NAT). It is not a real Junos commit.

## Check

```sh
dojo check 2
```

<!-- dojo-reveal: What it checks -->

It reads your org through the API and expects a `corp-to-web` policy that allows, and a `branch-srx` template whose `ge-0/0/0` is a WAN, `ge-0/0/1` is a LAN carrying `corp`, and which uses the policy.

<!-- /dojo-reveal -->

```sh
git add gateway.tf
git commit -m "Add the corp-to-web policy and the branch-srx gateway template"
```

## Check yourself

1. Why does the template say `{{wan_ip}}` instead of an address?
2. In `ip_configs`, what is the key?

<!-- dojo-reveal: Show the answer -->

1. The template is shared by every site. Each site supplies its own address through a site variable.
2. The network **name** (`corp`), not its id.

<!-- /dojo-reveal -->

## Common mistakes

| You see | Cause / fix |
| ------- | ----------- |
| `Invalid object key` / `Ambiguous attribute key` on the `ip_configs` map | An expression used as a key needs parentheses: `(mist_org_network.corp.name) = {...}`. |
| `Unsupported argument; An argument named "ip" is not expected here` | `ip` belongs inside `ip_config { ... }` on the port, not next to `usage`. |
| `Inconsistent result after apply` | The API stored something different from what you sent. Usually a mistyped enum (`usage = "wan"`, `wan_type = "broadband"`); read the value in the portal. |
| The policy lists a service that doesn't exist | `services` takes service **names**. Use the references (`mist_org_service.web.name`). |

**Next:** [lab3.md](lab3.md)
