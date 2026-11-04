---
marp: true
theme: default
paginate: true
size: 16:9
html: true
style: |
  @import url('assets/themes/labs.css');
footer: '[&larr; Labs](lab-index.md) &nbsp;|&nbsp; SRX with Terraform and Mist | Lab Overview'
---

<!-- _class: lead -->
<!-- _paginate: false -->
<!-- _footer: "[&larr; Labs](lab-index.md)" -->

# Lab Overview

## What each lab covers, before you dive in

Ten short labs, about 130 minutes. **Do them in order:** each one builds on the last, and nothing is destroyed along the way.

<p class="nav">Keep <code>cheat-sheet.md</code> open in another tab while you work.</p>

---

## Before you start

```sh
whoami
terraform version
dojo wan whoami
```

Preinstalled: `terraform` with the `juniper/mist` provider, and `git`. Your login to **Dojo WAN** (a practice cloud that answers as `api.mist.com`) is already in your environment. The lab has no internet, so `init` installs the provider from a local copy.

> Full detail lives in `~/lab/README.md` once you're in the terminal. Each lab is a file next to it: `lab0.md` … `lab9.md`.

---

## The labs

| Lab | Topic | Time |
| --- | ----- | ---- |
| **0** | Tour: fork the repo, the portal, your org and delivery, `init` | ~10 min |
| **1** | First objects: a network and services, plan, apply, idempotency | ~12 min |
| **2** | The gateway template and a service policy | ~12 min |
| **3** | Sites and variables: one template, three sites | ~12 min |
| **4** | **Claim and assign** the delivered gateways, read their config | ~12 min |
| **5** | Layers: profile and device override, where settings go | ~12 min |
| **6** | Modules, `for_each` and `moved`: refactor, destroy nothing | ~15 min |
| **7** | Shared state, the lock, a pull request with the plan | ~15 min |
| **8** | Drift and import | ~15 min |
| **9** | Capstone: a new branch from a ticket | ~15 min |

---

## What you'll learn

- **Labs 1-3:** objects have references; the second `plan` is empty; one template, many sites, with variables
- **Lab 4:** a claim code, a site and a template turn a box into a configured gateway
- **Lab 5:** the last layer to speak wins. Put each setting as high as it fits
- **Lab 6:** read the destroy count before every `apply`; `moved` keeps objects alive
- **Lab 7:** state is shared and locked; changes go through a pull request with the plan
- **Lab 8:** `plan` finds drift; you revert or adopt; `import` takes on what was made by hand
- **Lab 9:** all of it, from a ticket

---

## Expect these

- Check your work with `dojo check N`. It reads your org, not your files
- `dojo wan config <device>` shows the Junos config a gateway would get. It is a **preview**
- An error in Lab 6 (a plan with seven destroys) is **the point**. Read it and do not apply
- **Never delete `terraform.tfstate`** before Lab 7, and never put the API token in a file
- `git checkout <file>` undoes an edit. It is your friend

---

<!-- _class: lead -->
<!-- _paginate: false -->
<!-- _footer: "[&larr; Labs](lab-index.md)" -->

# Ready?

## Open `~/lab/README.md` in your terminal and start with Lab 0

Stuck? Ask. Done early? Try the stretch ideas at the end of Lab 9.
