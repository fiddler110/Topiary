# Lab 1: First objects

**Goal:** create your first two org objects, a network and two services, read them back in the portal, and see that a second `plan` is empty. All commands run in `~/lab/srx-terraform`.

> **Starting here?** Run `dojo prep 1`. It forks, clones and runs `terraform init` for you.

```sh
cd ~/lab/srx-terraform
```

---

## 1. Why these two

A Mist org holds objects that every site can share. Two of them are the building blocks of a firewall policy:

| Resource | What it is on the SRX |
| -------- | --------------------- |
| `mist_org_network` | a LAN segment: a name, a VLAN and a subnet. It becomes a zone and an interface unit |
| `mist_org_service` | something you can allow: protocol and port. It becomes an application in a security policy |

Notice the subnet below: `"{{site_subnet}}"`. Double braces are a Mist **site variable**. The org says "there is a corp network"; each site fills in its own subnet (Lab 3). Terraform leaves the braces alone: Mist replaces them later.

## 2. Write the config

Open `main.tf` (VS Code, or `nano main.tf`) and replace its contents:

```hcl
# main.tf
resource "mist_org_network" "corp" {
  org_id  = var.org_id
  name    = "corp"
  vlan_id = "10"
  subnet  = "{{site_subnet}}"
}

resource "mist_org_service" "web" {
  org_id    = var.org_id
  name      = "web"
  type      = "custom"
  addresses = ["0.0.0.0/0"]
  specs     = [{ protocol = "tcp", port_range = "443" }]
}

resource "mist_org_service" "dns" {
  org_id    = var.org_id
  name      = "dns"
  type      = "custom"
  addresses = ["0.0.0.0/0"]
  specs     = [{ protocol = "udp", port_range = "53" }]
}
```

`var.org_id` is the value from `TF_VAR_org_id`. Every org-level resource needs it.

```sh
terraform fmt
terraform validate
```

## 3. Plan, then apply

**Your turn:** before you run it, predict how many resources the plan adds, and which symbol it prints.

```sh
terraform plan
```

<!-- dojo-reveal: Results of plan -->

```text
  # mist_org_network.corp will be created
  + resource "mist_org_network" "corp" {
      + id      = (known after apply)
      + name    = "corp"
      + org_id  = "1f0b3a7e-..."
      + subnet  = "{{site_subnet}}"
      + vlan_id = "10"
    }

  # mist_org_service.dns will be created
  ...
  # mist_org_service.web will be created
  ...
Plan: 3 to add, 0 to change, 0 to destroy.
```

`+` means create. `id` is `(known after apply)` because Mist makes it.

<!-- /dojo-reveal -->

```sh
terraform apply
```

Read the plan, type `yes`.

```text
mist_org_service.dns: Creation complete after 0s [id=...]
mist_org_network.corp: Creation complete after 0s [id=...]
mist_org_service.web: Creation complete after 0s [id=...]

Apply complete! Resources: 3 added, 0 changed, 0 destroyed.
```

## 4. Read it back

Look in the portal (**Dojo WAN**, your org, Networks and Services). Then ask the API directly:

```sh
curl -s -H "Authorization: Token $MIST_API_TOKEN" \
  https://api.mist.com/api/v1/orgs/$MIST_ORG_ID/networks | python3 -m json.tool
dojo wan events
```

The network is there, with the `id` Terraform printed. `dojo wan events` is the change log: it shows your token creating the three objects. Keep that command in mind: Lab 8 uses it to catch someone else's edit.

## 5. Idempotency

**Your turn:** predict what a second `plan` says.

```sh
terraform plan
```

<!-- dojo-reveal: Result -->

```text
No changes. Your infrastructure matches the configuration.
```

Terraform compared the config, its state and the real API, and all three agree. Run `apply` as often as you like: nothing happens until something differs.

## 6. Change one thing

Change the service port in `main.tf` from `443` to `8443`, then `terraform plan`. Read the symbol: `~` means changed **in place**, and the object keeps its `id`. Apply it, then change it back and apply again.

```sh
terraform apply
```

## Check

```sh
dojo check 1
```

<!-- dojo-reveal: What it checks -->

It lists your org's networks and services through the API and expects a `corp` network on VLAN 10 with the subnet `{{site_subnet}}`, and a `web` service on tcp 443. It reads the org, not your files, so it tests the result.

<!-- /dojo-reveal -->

Commit your work on a branch (the next labs add to it):

```sh
git checkout -b estate
git add main.tf .terraform.lock.hcl
git commit -m "Add the corp network and the web and dns services"
```

## Check yourself

1. What does `(known after apply)` mean?
2. You run `apply` twice in a row. What does the second one do?

<!-- dojo-reveal: Show the answer -->

1. The value does not exist until the API creates the object (like `id`).
2. Nothing. It is idempotent: `No changes`.

<!-- /dojo-reveal -->

## Common mistakes

| You see | Cause / fix |
| ------- | ----------- |
| `Error: No value for required variable` for `org_id` | Your shell has no `TF_VAR_org_id`. Open a new terminal tab, or `export TF_VAR_org_id=$MIST_ORG_ID`. |
| `Error: Invalid ... "vlan_id"` or a type error on `vlan_id` | The provider wants a **string**: `vlan_id = "10"`, in quotes. |
| `Unsupported argument; An argument named "port_range" is not expected here` | `port_range` belongs inside `specs`, not on the service itself. |
| `Required plugins are not installed` | Run `terraform init` (and check you are in `~/lab/srx-terraform`). |

**Next:** [lab2.md](lab2.md)
