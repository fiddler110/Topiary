# Lab 8: Drift and import

**Goal:** notice a change made outside Terraform, decide whether to revert or adopt it, and bring an object that was made by hand under Terraform's control with `import`. All commands run in `~/lab/srx-terraform`.

> **Starting here?** Run `dojo prep 8`.

---

## 1. Drift

**Drift** is when the real estate stops matching the code: someone fixed something in the Mist portal at 2 a.m. and went home. Terraform can't stop that. It can tell you the next time you run `plan`.

Your facilitator may press the **Drift** button in the Dojo WAN admin tab, which makes a canned edit in your org. If they haven't, make the same kind of edit yourself, "portal style": an API call that bypasses Terraform and changes the `corp` network's VLAN from 10 to 99.

```sh
NET=$(curl -s -H "Authorization: Token $MIST_API_TOKEN" \
  https://api.mist.com/api/v1/orgs/$MIST_ORG_ID/networks \
  | python3 -c 'import json,sys; print([n["id"] for n in json.load(sys.stdin) if n["name"]=="corp"][0])')
curl -s -X PUT -H "Authorization: Token $MIST_API_TOKEN" -H 'Content-Type: application/json' \
  -d '{"vlan_id": "99"}' https://api.mist.com/api/v1/orgs/$MIST_ORG_ID/networks/$NET | python3 -m json.tool | grep vlan
```

## 2. Find out who changed what

The org keeps a change log. Terraform's own changes appear there too, so you can tell them apart by the **actor**:

```sh
dojo wan events
```

<!-- dojo-reveal: Result -->

```text
1730...  studentNN        PUT  /api/v1/orgs/.../networks/...
```

Lines from your own `apply` and from the portal look alike here: the actor names the login. If the facilitator pressed the button, the actor is `portal:facilitator`.

<!-- /dojo-reveal -->

## 3. `plan` shows it

**Your turn:** predict what `plan` says. Which side is "right", the code or the world?

```sh
terraform plan
```

<!-- dojo-reveal: Result -->

```text
  # mist_org_network.corp will be updated in-place
  ~ resource "mist_org_network" "corp" {
        id      = "..."
        name    = "corp"
      ~ vlan_id = "99" -> "10"
        # (4 unchanged attributes hidden)
    }

Plan: 0 to add, 1 to change, 0 to destroy.
```

Terraform refreshed its view of the real object (`vlan_id = "99"`), compared it with your code (`"10"`), and proposes to put it back. The code is the source of truth; the plan is a to-do list for making the world match.

<!-- /dojo-reveal -->

Look at what the drift did to a gateway:

```sh
dojo wan config ottawa-01-gw | grep 'interfaces ge-0/0/1 unit'
```

The LAN interface is on unit 99 now, a different VLAN from the switch it plugs into. That is why drift matters.

## 4. Revert or adopt

Two honest answers:

| Choice | When | How |
| ------ | ---- | --- |
| **Revert** | the portal change was a mistake or a hack | `terraform apply`: the world goes back to the code |
| **Adopt** | the portal change was right (an emergency fix) | change the code to match, and `plan` shows nothing |

Adopt first, to see it work: edit `main.tf`, set `vlan_id = "99"`, and run `terraform plan`.

```text
No changes. Your infrastructure matches the configuration.
```

The code now says what the world says. Nothing was applied. In the real estate this is a pull request: the fix gets reviewed after the fact. VLAN 99 is wrong here, so put the code back to `"10"` and **revert**:

```sh
terraform apply
dojo wan config ottawa-01-gw | grep 'interfaces ge-0/0/1 unit'
```

## 5. An object made by hand

Drift is a change to something Terraform knows. The other case is an object Terraform has never heard of. Someone built a guest network in the portal:

```sh
curl -s -X POST -H "Authorization: Token $MIST_API_TOKEN" -H 'Content-Type: application/json' \
  -d '{"name": "guest", "vlan_id": "20", "subnet": "172.16.20.0/24"}' \
  https://api.mist.com/api/v1/orgs/$MIST_ORG_ID/networks | python3 -m json.tool
```

`plan` is silent about it, because it isn't in your code or your state. If you just wrote a `guest` resource and applied, Terraform would try to create a second one. The right move is **import**: tell Terraform that this resource block is that existing object.

Write the block first. It must match what exists, or the next `plan` shows a change. Create `imported.tf`:

```hcl
# imported.tf
resource "mist_org_network" "guest" {
  org_id  = var.org_id
  name    = "guest"
  vlan_id = "20"
  subnet  = "172.16.20.0/24"
}
```

An import needs the object's **id**. For an org network it is `<org_id>.<network_id>`:

```sh
GUEST=$(curl -s -H "Authorization: Token $MIST_API_TOKEN" \
  https://api.mist.com/api/v1/orgs/$MIST_ORG_ID/networks \
  | python3 -c 'import json,sys; print([n["id"] for n in json.load(sys.stdin) if n["name"]=="guest"][0])')
terraform import mist_org_network.guest "$MIST_ORG_ID.$GUEST"
terraform plan
```

<!-- dojo-reveal: Result -->

```text
mist_org_network.guest: Importing from ID "1f0b....-..."...
mist_org_network.guest: Import prepared!
...
Import successful!

No changes. Your infrastructure matches the configuration.
```

If `plan` shows `~` changes, your block doesn't match the object. Fix the block (not the object) until the plan is empty, or decide the object is the thing that's wrong.

<!-- /dojo-reveal -->

(Terraform can also import declaratively, with an `import { to = ..., id = "..." }` block that goes through a normal plan and review. Use it when the import itself should be reviewed.)

## 6. Import a device

A gateway override has a different id format: `<site_id>.<device_id>`. Practise it by letting Terraform forget the Toronto gateway's override, then adopting it back. Forgetting changes nothing in Mist: `state rm` only edits the state.

```sh
SITE=$(terraform state show 'module.site["toronto-01"].mist_site.this' | awk '/^ *id /{print $3}' | tr -d '"')
DEV=$(terraform state show 'module.gateway["toronto-01"].mist_device_gateway.this' | awk '/^ *device_id /{print $3}' | tr -d '"')
terraform state rm 'module.gateway["toronto-01"].mist_device_gateway.this'
terraform plan
```

`plan` now wants to create the gateway override again (`Plan: 1 to add`): Terraform has lost track of it. Import it back:

```sh
terraform import 'module.gateway["toronto-01"].mist_device_gateway.this' "$SITE.$DEV"
terraform plan
```

The plan should be empty again.

## Check

```sh
dojo check 8
```

<!-- dojo-reveal: What it checks -->

Through the API: `corp` is on VLAN 10 again, there is exactly one `guest` network, `terraform plan` is clean (exit code 0), and `guest` is in your state.

<!-- /dojo-reveal -->

```sh
git checkout -b adopt-guest-network
git add imported.tf
git commit -m "Adopt the guest network that was made in the portal"
```

## Check yourself

1. `plan` shows `~ vlan_id = "99" -> "10"`. Did the VLAN change in your code, or in the world?
2. You write a resource for something that already exists and run `apply` without importing. What happens?
3. How do you stop drift from happening at all?

<!-- dojo-reveal: Show the answer -->

1. In the world. The `-> "10"` is where Terraform wants to take it.
2. At best an error for a duplicate name; at worst a second object. Import first.
3. You can't stop it entirely: make portal access read-only for most people, and run `plan` on a schedule so drift is found in hours, not months.

<!-- /dojo-reveal -->

## Common mistakes

| You see | Cause / fix |
| ------- | ----------- |
| `Error: Cannot import non-existent remote object` | The id is wrong. A network id is `<org_id>.<network_id>`; a device id is `<site_id>.<device_id>`. |
| `Resource already managed by Terraform` | It is already in state. `terraform state list` to see. |
| After import, `plan` wants to change things | Your block doesn't match the real object. Compare with `terraform state show` and fix the block. |
| `Error: Invalid import id` | Quote the module address with single quotes in the shell: `'module.gateway["toronto-01"]...'`. |
| `No such resource instance` on `state rm` | Spelled the module key wrong. `terraform state list`. |

**Next:** [lab9.md](lab9.md)
