# Lab 9: Capstone: a new branch office from a ticket

**Goal:** open a new branch the way the team will on the real estate: read a ticket, make a one-entry change, put the plan in a pull request, get it reviewed, apply from `main`, and check the gateway's configuration. All commands run in `~/lab/srx-terraform`.

> **Starting here?** Run `dojo prep 9`. It also leaves you on `main`, up to date.

There are fewer steps this time. You have done every part of this before.

---

## The ticket

```text
NET-142   Open the Halifax branch

Site name    halifax-01
Address      Halifax, NS, Canada   (time zone America/Halifax)
Gateway      the second SRX345 from our delivery (see `dojo wan delivery`)
WAN          198.51.100.10/29, next hop 198.51.100.9
LAN          10.40.0.0/24, the gateway is 10.40.0.1
Design       the standard branch design: the template, no profile, no local overrides
Done when    the gateway has the Halifax addresses, the standard DNS and NTP
             servers from the template, and `terraform plan` is empty.
```

## 1. Branch and add one entry

```sh
git checkout main
git pull origin main
git checkout -b open-halifax-01
```

You already have the pieces. Add one entry to the `sites` map in `terraform.tfvars`, with the claim code of your second `SRX345`:

```hcl
  "halifax-01" = {
    address      = "Halifax, NS, Canada"
    country_code = "CA"
    timezone     = "America/Halifax"
    claim_code   = "SRX345YYYYYYYYY"
    wan_ip       = "198.51.100.10"
    wan_gw       = "198.51.100.9"
    lan_subnet   = "10.40.0.0/24"
    lan_ip       = "10.40.0.1"
  }
```

Paste it inside the closing `}` of `sites = { ... }`, after the Montreal entry. No other file changes.

```sh
terraform fmt
terraform validate
terraform plan -no-color | tee plan.txt
```

**Your turn:** before you look, predict the summary line.

<!-- dojo-reveal: Result -->

```text
Plan: 3 to add, 5 to change, 0 to destroy.
```

Three to add: the site, its settings, the gateway. Five to change: the inventory (one more device), and the four things that read an id out of it, the hub's profile assignment and the three branch gateways. Open any of them: the only change is `device_id = "..." -> (known after apply)`, because the inventory is changing and Terraform cannot know its ids until it has. Nothing real moves. **Zero destroy** is the number to read: if your plan shows any destroy, stop, something else changed.

<!-- /dojo-reveal -->

## 2. Pull request, review, merge

Commit and push the branch, then open a pull request in your fork with the plan in its description, exactly as in Lab 7:

```sh
git add terraform.tfvars
git commit -m "Open halifax-01 (NET-142)"
git push -u origin open-halifax-01
```

Open the pull request with the same `pr.json` block as Lab 7 (section 5), changing only the branch, the title and the first line of the description:

```sh
python3 - <<'PY' > pr.json
import json
fence = chr(96) * 3
plan = open("plan.txt").read()
print(json.dumps({"head": "open-halifax-01", "base": "main",
  "title": "Open halifax-01 (NET-142)",
  "body": "New branch site from ticket NET-142, on the standard design.\n\n" + fence + "text\n" + plan + "\n" + fence}))
PY
curl -s --netrc -H 'Content-Type: application/json' -d @pr.json \
  http://git-server:3000/api/v1/repos/$USER/srx-terraform/pulls | python3 -c 'import json,sys; print(json.load(sys.stdin)["html_url"])'
rm pr.json
```

Ask a neighbour or the facilitator to review. A good review reads the plan first: the counts, then the resource names, then the values.

Merge it in Forgejo, then update and apply from `main`:

```sh
git checkout main
git pull origin main
terraform plan
terraform apply
```

## 3. Check the result

```sh
dojo wan config halifax-01-gw
```

<!-- dojo-reveal: What to look for -->

```text
# site: halifax-01
set system host-name halifax-01-gw
set system name-server 192.0.2.53
set system ntp server 192.0.2.123
set interfaces ge-0/0/0 unit 0 family inet address 198.51.100.10/29
set interfaces ge-0/0/1 unit 10 family inet address 10.40.0.1/24
set routing-options static route 0.0.0.0/0 next-hop 198.51.100.9
```

The Halifax addresses come from the site variables, DNS and NTP from the template. Nothing is overridden on the box.

<!-- /dojo-reveal -->

```sh
terraform plan
dojo check 9
```

<!-- dojo-reveal: What it checks -->

Through the API: a `halifax-01` site using the template with its four variables; its gateway claimed, in that site, with no profile, and rendered with the Halifax WAN address and the template's DNS and NTP; and `terraform plan` clean.

<!-- /dojo-reveal -->

## Stretch

- Add the next ticket yourself: a fifth site with a local DNS server (`dns_servers = [...]` in its map entry). Where does that setting belong?
- Run `dojo wan events` and read your whole week: every create, update and delete, and who did it.
- Pretend `halifax-01` closes. What is the smallest change, and what would the plan say?

## What you built

A greenfield estate, from empty org to four branch offices and a hub: shared org objects, one gateway template, a hub profile for the data-centre gateway, sites with variables, gateways claimed and assigned from a delivery, state in a shared locked backend, and a change process with the plan in front of the reviewer. That is the real job.

## Common mistakes

| You see | Cause / fix |
| ------- | ----------- |
| `Invalid value for input variable` | A field is missing from the new map entry, or a comma or brace is misplaced. The error names the file and line. |
| The plan shows a destroy | You edited an existing entry. Revert and change only the new one. |
| `claim code ... already claimed` | You used a code from a site you already have. Take the second `SRX345` from `dojo wan delivery`. |
| `Error acquiring the state lock` | Another run holds it. Wait, or look for a Terraform you left open in another pane. |
| Merge conflict in `terraform.tfvars` | Someone else's entry landed first. Pull `main`, keep both entries. Conflicts in one shared map are normal. |
