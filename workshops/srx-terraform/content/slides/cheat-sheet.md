---
marp: true
theme: default
paginate: true
size: 16:9
html: true
style: |
    @import url('assets/themes/cheat-sheet.css');
footer: "[&larr; Hub](index.md) &nbsp;|&nbsp; SRX with Terraform and Mist | Cheat Sheet"
---

<!-- _class: lead -->
<!-- _paginate: false -->
<!-- _footer: "[&larr; Hub](index.md)" -->

# Cheat Sheet

## Every command from Labs 0-9, in one place

Keep this open in a split pane or another tab while you work. You don't need to memorize any of it.

<p class="nav">Full detail: <code>~/lab/cheat-sheet.md</code> in your terminal.</p>

---

## The loop

```text
edit .tf files → fmt → validate → plan → (pull request) → apply → dojo check N
```

| Step    | Command                                          | Changes anything?          |
| ------- | ------------------------------------------------ | -------------------------- |
| Prepare | <span class="command">terraform init</span>      | Only `.terraform/`         |
| Tidy    | <span class="command">terraform fmt -recursive</span> | Your files (style)    |
| Check   | <span class="command">terraform validate</span>  | No                         |
| Preview | <span class="command">terraform plan</span>      | **No**                     |
| Do it   | <span class="command">terraform apply</span>     | **Yes**, after you type `yes` |

Plan symbols: `+` create, `~` change in place, `-` destroy, `-/+` replace. **Read the destroy count.**

---

## Dojo commands

| Command                                                  | What it does                                      |
| -------------------------------------------------------- | ------------------------------------------------- |
| <span class="command">dojo wan delivery</span>           | Your packing slip: model, serial, MAC, claim code |
| <span class="command">dojo wan config DEVICE</span>      | The Junos config a gateway would get              |
| <span class="command">dojo wan events</span>             | The change log of your org, and who made each one |
| <span class="command">dojo wan whoami</span>             | Your org id and the API host                      |
| <span class="command">dojo check N</span>                | Check lab N against your org                      |
| <span class="command">dojo prep N</span>                 | Catch up to where lab N starts                    |

---

## State, import and the backend

| Command                                                         | What it does                              |
| --------------------------------------------------------------- | ----------------------------------------- |
| <span class="command">terraform state list</span>               | What Terraform tracks                     |
| <span class="command">terraform state show ADDR</span>          | One object, with its id                   |
| <span class="command">terraform state rm ADDR</span>            | Forget it (the real one stays)            |
| <span class="command">terraform import ADDR ID</span>           | Start tracking an existing object         |
| <span class="command">terraform init -migrate-state</span>      | Move state to a new backend               |
| <span class="command">terraform force-unlock ID</span>          | Remove a stuck lock                       |

Import ids: network `ORG_ID.NETWORK_ID`, gateway `SITE_ID.DEVICE_ID`.

---

## Roles

```text
spoke   branch site   gateway template on the site
hub     hub/DC        hub profile on the device (site has no template)
one box               device override (last resort)
```

Never a template and a profile on one gateway.

| The setting is... | Put it in |
| ----------------- | --------- |
| the same everywhere | org objects |
| the same for every branch | the template |
| the same for a hub | a hub profile |
| different per site | a site variable |
| true for exactly one box | a device override |

---

## Your environment

| Variable                               | Meaning                                    |
| -------------------------------------- | ------------------------------------------ |
| `MIST_HOST`                            | `api.mist.com` (the practice cloud)        |
| `MIST_API_TOKEN`                       | your token: never paste it or commit it    |
| `MIST_ORG_ID`, `TF_VAR_org_id`         | your org id                                |
| `TF_HTTP_USERNAME`, `TF_HTTP_PASSWORD` | your login to the shared state (Lab 7)     |

```sh
curl -s -H "Authorization: Token $MIST_API_TOKEN" https://api.mist.com/api/v1/orgs/$MIST_ORG_ID/sites
```

---

## Git for a change

```sh
git checkout -b my-change
git add FILE && git commit -m "why"
git push -u origin my-change     # open the pull request, paste the plan
git checkout main && git pull origin main
terraform apply                  # apply from main only
```

- Nobody applies from a branch
- Read the destroy count in the plan
- No secrets in git: `.terraform/`, `*.tfstate*` and tokens stay out
