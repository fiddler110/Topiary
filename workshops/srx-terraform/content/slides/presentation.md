---
marp: true
theme: default
paginate: true
size: 16:9
html: true
style: |
    @import url('assets/themes/presentation.css');
    .mermaid { text-align: center; margin: 8px 0; }
    .mermaid:not([data-processed]) { visibility: hidden; }
    .mermaid svg { max-height: 400px; }
    .mermaid foreignObject p, .mermaid foreignObject div { margin: 0 !important; line-height: 1.35 !important; }
footer: "[&larr; Hub](index.md) &nbsp;|&nbsp; SRX with Terraform and Mist | Technology"
---

<!-- _class: lead -->
<!-- _paginate: false -->
<!-- _footer: "[&larr; Hub](index.md)" -->

# SRX with Terraform and Mist

## Build and run a branch firewall estate from code

Builds on OpenTofu Basics: the same plan and apply loop, now aimed at a real product

**Talk ~30 min · Labs 0-9 ~130 min · about 2¾ hours total**

<!--
Timing. Labs 0 to 9 add up to 130 minutes from the lab README (10, 12, 12, 12, 12, 12, 15, 15, 15, 15). The talk is my estimate from the slide count, not a measured run. Add about 5 minutes for the recap and questions.

By part: Part 1 ~5 min, Part 2 ~8, Part 3 ~6, Part 4 ~6, Part 5 ~5.

Everyone should have used Terraform or OpenTofu once (init, plan, apply). If the room has not, run OpenTofu Basics first. If you are short on time, the talk can shrink to Parts 2 and 4 and the labs carry the rest.

Say early: nothing here touches a real Mist organization or a real SRX. Students work against a practice cloud that answers at api.mist.com. The provider, the resource names and the API calls are the real ones.
-->

---

## Today

1. **Part 1:** Why Mist and Terraform
2. **Part 2:** The model: org, template, profile, site, device
3. **Part 3:** Variables and the claim flow
4. **Part 4:** State and the team workflow
5. **Part 5:** Drift and import
6. **Labs 0-9:** build the estate, one step at a time

> You are training for one real job: a greenfield SRX estate, managed from Mist, run from git.

<!--
About 1 minute. The point of the day is the job, not the tool. By the end they will have built the layout, the change process and the habits they will keep on the real estate.
-->

---

<!-- _class: section-title -->

# Part 1

## Why Mist and Terraform

---

## A greenfield estate

<div class="two-column">

- Many branch offices, each with an SRX
- The same design at every site, apart from addresses
- Boxes arrive from the supplier and are claimed into **Mist**, a cloud that manages them
- Mist pushes the config to each device

- Changes come from a team, not one person
- A mistake at one site should not need a truck roll to fix

</div>

> The question is not "how do I configure one SRX". It is "how do I keep fifty of them the same, and know why they differ".

<!--
About 2 minutes. Ask who has configured a branch firewall by pasting set commands. Then ask how they knew two branches matched. The answer is usually "we did not". That is the problem to solve.
-->

---

## What Mist gives you, and what it does not

| Mist does | Mist does not |
| --------- | ------------- |
| Holds the config objects and pushes them to devices | Say who changed what, in your words |
| Merges a template, a profile and the device's own settings | Review a change before it lands |
| Takes a claim code and enrols a box with no one logging in | Stop someone clicking in the portal |
| Has a full REST API | Keep a copy you can diff |

**Terraform** fills the right-hand column: the config lives in git, a change is a pull request, and `plan` shows the effect before anything moves.

<!--
About 2 minutes. Be even-handed about the portal. It is good for looking and for emergencies. The rule is that the portal can show you the estate, and git decides what it should be.
-->

---

## The real provider

```hcl
terraform {
  required_providers {
    mist = {
      source  = "juniper/mist"
      version = "0.11.0"
    }
  }
}

provider "mist" {}   # host and token come from MIST_HOST and MIST_API_TOKEN
```

- `juniper/mist` is the vendor's provider, built from the Mist API spec
- No host or token in the file: the environment supplies them
- Today it talks to **Dojo WAN**, a practice cloud that answers as `api.mist.com`

<!--
About 1 minute. The provider only accepts the real Mist cloud hostnames, so the practice cloud answers to api.mist.com inside the lab. Nothing in the lab can reach the real one. The HCL they write is exactly the HCL they will write at work.
-->

---

<!-- _class: section-title -->

# Part 2

## The model

---

## Roles: spoke, hub, one box

<div class="mermaid">
flowchart TD
  o["Org objects<br/>networks, services, policies"] --> t["Spoke: gateway template<br/>assigned to branch sites"]
  o --> p["Hub: hub profile<br/>on a gateway at a hub site"]
  t --> j["Final config on the SRX"]
  p --> j
  d["Device override<br/>one box, last resort"] --> j
</div>

- **Site variables** fill the blanks; a device's own `vars` win
- Template or profile **DNS/NTP** only apply with `dns_override` / `ntp_override`
- Mist documents one or the other on a gateway, never both

<!--
About 3 minutes. This is the slide to come back to all day. Lab 5 shows it: the dc-01 hub takes its DNS from a hub profile (and loses it if dns_override is removed), branches take theirs from the template, Ottawa's NTP comes from the device. Say plainly that Mist does not document a template and a profile on the same gateway, so we do not do it.
-->

---

## Which role? The house rule

| The setting is... | Put it in |
| ----------------- | --------- |
| the same everywhere | org objects |
| the same for every branch | the **template** |
| the same for a hub | a **hub profile** |
| different per site | a **site variable** |
| true for exactly one box | a **device override** (last resort) |

> Every override is a box that no longer looks like its neighbours.

<!--
About 2 minutes. Spend time on the last row. Ask for an example of a setting that really is per box (a name, a local clock). Most of the things people want to override are really per site, which is a variable.
-->

---

## The resources, in build order

| Layer | Terraform resource |
| ----- | ------------------ |
| Org | `mist_org_network`, `mist_org_service`, `mist_org_servicepolicy` |
| Template and profile | `mist_org_gatewaytemplate`, `mist_org_deviceprofile_gateway`, `mist_org_deviceprofile_assign` |
| Site | `mist_site`, `mist_site_setting` |
| Device | `mist_org_inventory`, `mist_device_gateway` |

Terraform works out the order from references, as it did in OpenTofu Basics.

<!--
About 2 minutes. Do not read the table out. Point at the four rows and say the labs go top to bottom, one row at a time, except that the inventory (claiming boxes) waits until sites exist.
-->

---

## A gateway template

```hcl
resource "mist_org_gatewaytemplate" "branch" {
  org_id = var.org_id
  name   = "branch-srx"
  type   = "standalone"

  port_config = {
    "ge-0/0/0" = { usage = "wan", name = "wan0", wan_type = "broadband",
                   ip_config = { type = "static", ip = "{{wan_ip}}",
                                 netmask = "/29", gateway = "{{wan_gw}}" } }
    "ge-0/0/1" = { usage = "lan", networks = [mist_org_network.corp.name] }
  }
}
```

- Ports, networks and policies: the same at every branch
- `{{wan_ip}}` is **not** Terraform syntax. It is a Mist variable, filled in per site

<!--
About 2 minutes. The braces are the one place students get confused: Terraform leaves the string alone, and Mist replaces it. If you want a mental image, it is a mail merge.
-->

---

<!-- _class: section-title -->

# Part 3

## Variables and the claim flow

---

## Site variables: one design, many sites

<div class="mermaid">
flowchart LR
  t["Template<br/>ip = {{wan_ip}}"] --> a["ottawa-01<br/>wan_ip = 198.51.100.2"]
  t --> b["toronto-01<br/>wan_ip = 203.0.113.2"]
  t --> c["montreal-01<br/>wan_ip = 192.0.2.2"]
</div>

- Variables live in `mist_site_setting.vars`
- A name nobody defines stays as `{{name}}` in the config: a typo you can see

<!--
About 2 minutes. This is how a branch is described in one place: a handful of values in a map. Lab 6 turns that map into the single place you edit to open a branch.
-->

---

## The claim flow

<div class="mermaid">
flowchart LR
  s["Supplier ships<br/>the box"] --> k["Claim code<br/>on the packing slip"]
  k --> i["Claim into the org<br/>inventory"]
  i --> g["Assign to a site"]
  g --> c["Template and variables<br/>apply"]
  c --> z["Device configures itself"]
</div>

- `mist_org_inventory` takes a map from claim code to site
- The claim code is exactly 15 characters of `0-9A-Z`
- Nobody logs in to the SRX

<!--
About 2 minutes. This is zero touch provisioning. In the lab the delivery is five boxes with claim codes; dojo wan delivery prints them. Mention unclaim_when_destroyed: without it a destroy leaves the box claimed and a rebuild fails.
-->

---

## What the box actually gets

```text
set system host-name ottawa-01-gw
set system name-server 10.10.0.53
set system ntp server 192.0.2.123
set interfaces ge-0/0/0 unit 0 family inet address 198.51.100.2/29
set interfaces ge-0/0/1 unit 10 family inet address 10.10.0.1/24
set routing-options static route 0.0.0.0/0 next-hop 198.51.100.1
```

- `dojo wan config <device>` shows the rendered Junos `set` lines
- The check for most labs is simple: **read the config the device would get**
- It is a preview, not a real commit

<!--
About 1 minute. Be clear about what the preview is. It is built from the parts the team can confirm on a real SRX, and it is labelled as a preview. Someone on the team should compare it with a real device before the first class.
-->

---

<!-- _class: section-title -->

# Part 4

## State and the team workflow

---

## Structure that survives growth

```hcl
module "site" {
  source   = "./modules/site"
  for_each = var.sites
  name     = each.key
}
moved {
  from = mist_site.ottawa
  to   = module.site["ottawa-01"].mist_site.this
}
```

- One map entry per site
- Renaming a resource looks like **delete and create** to Terraform
- `moved` says "same object, new address"

<!--
About 2 minutes. Show the destroy count in the plan before the moved blocks. Read the destroy count is the habit to build: every plan, every time. Lab 6 makes them see 7 to destroy, then 0.
-->

---

## State: shared, and locked

<div class="two-column">

**On your laptop**

- One person's memory
- A teammate sees an empty estate
- Two applies can overwrite each other

**On a backend**

- One shared copy
- A **lock** so one run changes it at a time
- Never in git: state can hold secrets

</div>

```hcl
backend "http" {
  address = "https://api.mist.com/dojo-state/srx-estate"
}
```

<!--
About 2 minutes. The lab uses the HTTP backend Dojo WAN serves. A real team would use an object store or a hosted service. The idea is identical. Mention that the login for the backend comes from the environment, so the file has no secret.
-->

---

## The change process

<div class="mermaid">
flowchart LR
  b["Branch"] --> p["terraform plan"]
  p --> pr["Pull request<br/>with the plan"]
  pr --> r["Review"]
  r --> m["Merge"]
  m --> a["Apply from main"]
</div>

- Nobody applies from a branch
- The reviewer reads the **plan**, starting with the destroy count
- The token is never in the repo

<!--
About 2 minutes. On the real estate a runner posts the plan on the pull request. In the lab they paste it. Ask the room what a reviewer can learn from the plan that they cannot learn from the code diff. The answer is the effect.
-->

---

<!-- _class: section-title -->

# Part 5

## Drift and import

---

## Drift: the portal changed it

<div class="mermaid">
flowchart LR
  g["Git and state<br/>vlan_id = 10"] --> p["terraform plan"]
  w["Mist today<br/>vlan_id = 99"] --> p
  p -->|"different"| d["~ vlan_id 99 to 10"]
  d --> r["Revert<br/>apply"]
  d --> ad["Adopt<br/>edit the code"]
</div>

- `plan` refreshes first, so it finds changes made outside Terraform
- Decide: was the portal change a mistake (revert) or right (adopt in a pull request)?

<!--
About 2 minutes. In the lab the facilitator may press a Drift button, or students make a portal-style change with curl. dojo wan events shows who did it. A good question for the room: how often would you run plan on a schedule so that drift is found in hours.
-->

---

## Import: bring in what was made by hand

```sh
terraform import mist_org_network.guest "$MIST_ORG_ID.$GUEST_ID"
terraform import 'module.gateway["toronto-01"].mist_device_gateway.this' "$SITE_ID.$DEVICE_ID"
```

1. Write the resource block to match what exists
2. Import: tell Terraform the block **is** that object
3. `plan` shows nothing

- Without it, `apply` would try to create a second one

<!--
About 1 minute. The id formats are the part people cannot guess, so they are on the cheat sheet: org.id for an org object, site.device for a device.
-->

---

## What the labs cover

| Lab | You will |
| --- | -------- |
| **0-1** | tour, then create your first objects |
| **2-3** | the gateway template, three sites with variables |
| **4-5** | claim the delivery; roles: hub profile and override |
| **6** | modules, `for_each`, `moved` |
| **7** | shared state, lock, pull request with the plan |
| **8** | drift and import |
| **9** | capstone: a new branch from a ticket |

<!--
About 1 minute. Keep the order. Each lab builds on the one before and nothing is destroyed along the way. dojo prep N catches anyone up.
-->

---

## Recap

- **Mist holds the config, git decides it**: the portal shows, Terraform changes
- **Roles**: spoke template, hub profile, device override. Template/profile DNS and NTP need the override flags; put each setting at the **broadest** place that fits
- **Claim and assign** from a delivery: no one logs in to the box
- **State is shared and locked**; the token is never in the repo
- **Pull request with the plan**, read the destroy count, apply from `main`
- **Drift** is found by `plan`; **import** adopts what was made by hand

**Next steps:** a secrets manager for the token, a runner that plans on every pull request, scheduled drift checks, and a real device to compare the preview with.

<!--
About 3 minutes. Ask each table what surprised them. Common answers: how much of the config is variables, how loud a destroy count is, drift on a network you did not touch.
-->

---

<!-- _class: lead -->
<!-- _paginate: false -->
<!-- _footer: "[&larr; Hub](index.md)" -->

# Let's go

## Next: [labs.md](labs.md) for what each lab covers, then your terminal

Keep [cheat-sheet.md](cheat-sheet.md) open in another tab. Ask for help any time. This is a lab, not a test.
