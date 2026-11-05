# SRX with Terraform and Mist: Cheat Sheet

## The loop

```text
edit .tf files → fmt → validate → plan → (pull request) → apply → dojo check N
```

| Command | What it does | Changes anything? |
| ------- | ------------ | ----------------- |
| `terraform init` | Install the provider, prepare the folder (again after adding a module or a backend). | Only `.terraform/` |
| `terraform fmt -recursive` | Tidy formatting. | Your files (style only) |
| `terraform validate` | Check syntax and references. | No |
| `terraform plan` | Show what would change. | **No** |
| `terraform plan -no-color \| tee plan.txt` | Save a plan to paste in a pull request. | No |
| `terraform plan -detailed-exitcode` | Exit code 0 means no changes, 2 means changes. | No |
| `terraform apply` | Plan, ask, then do it. | **Yes** |
| `terraform state list` | What Terraform tracks. | No |
| `terraform state show ADDR` | One tracked object, with its id. | No |
| `terraform state rm ADDR` | Forget an object (the real one stays). | State only |
| `terraform import ADDR ID` | Start tracking an existing object. | State only |
| `terraform init -migrate-state` | Move state to a new backend. | Where state lives |
| `terraform force-unlock ID` | Remove a stuck state lock. | The lock |

Plan symbols: `+` create, `~` change in place, `-` destroy, `-/+` replace. **Read the destroy count.**

## Dojo commands

| Command | What it does |
| ------- | ------------ |
| `dojo wan delivery` | Your packing slip: model, serial, MAC, claim code (`magic`). |
| `dojo wan config <device>` | The Junos config a gateway would get (name, MAC or serial). |
| `dojo wan events` | The change log of your org, and who made each change. |
| `dojo wan whoami` | Your org id and the API host. |
| `dojo check N` | Check lab N against your org. |
| `dojo prep N` | Catch your workspace up to where lab N starts. |
| `dojo sensei ask "..."` | Ask the support desk when you are stuck. |

## Your environment

| Variable | Meaning |
| -------- | ------- |
| `MIST_HOST` | `api.mist.com` (the practice cloud answers to it) |
| `MIST_API_TOKEN` | your API token. A secret: never paste it, never commit it |
| `MIST_ORG_ID`, `TF_VAR_org_id` | your org id, for scripts and for `var.org_id` |
| `TF_HTTP_USERNAME`, `TF_HTTP_PASSWORD` | your login to the shared state backend (Lab 7) |

## Resources used

| Resource | What it is |
| -------- | ---------- |
| `mist_org_network` | a LAN segment: name, VLAN, subnet (may hold `{{variables}}`) |
| `mist_org_service` | something to allow: protocol and port |
| `mist_org_servicepolicy` | allow or deny services for tenants (networks) |
| `mist_org_gatewaytemplate` | the shared branch design: ports, networks, policies |
| `mist_org_deviceprofile_gateway` | a hub role: its own ports and DNS, on a site with no template |
| `mist_org_deviceprofile_assign` | which devices (by MAC) have a profile |
| `mist_site` | a branch: name, address, time zone, template |
| `mist_site_setting` | the site's `vars` |
| `mist_org_inventory` | claim devices by code and assign them to a site |
| `mist_device_gateway` | one gateway's own settings (an override) |

## Roles

```text
spoke (branch site):  gateway template     hub (no template):  hub profile     one box:  device override
site variables fill the blanks; a device's own vars win
DNS/NTP in a template or profile apply only with dns_override / ntp_override = true
```

House rule: same everywhere, org objects. Same for every branch, the template. Same for a hub, a hub profile. Differs per site, a site variable. One box only, an override (last resort). Never a template and a profile on one gateway.

## Import ids

| Resource | Id |
| -------- | -- |
| `mist_org_network` | `<org_id>.<network_id>` |
| `mist_device_gateway` | `<site_id>.<device_id>` |

## Useful API calls

```sh
H="Authorization: Token $MIST_API_TOKEN"
curl -s -H "$H" https://api.mist.com/api/v1/self
curl -s -H "$H" https://api.mist.com/api/v1/orgs/$MIST_ORG_ID/sites
curl -s -H "$H" https://api.mist.com/api/v1/orgs/$MIST_ORG_ID/networks
curl -s -H "$H" https://api.mist.com/api/v1/orgs/$MIST_ORG_ID/inventory
curl -s -H "$H" https://api.mist.com/api/v1/orgs/$MIST_ORG_ID/dojo/events
```

## Git

```sh
git checkout -b my-change     # branch
git add FILE && git commit -m "why"
git push -u origin my-change  # then open the pull request in Forgejo
git checkout main && git pull origin main && terraform apply   # apply from main only
```
