# SRX with Terraform and Mist

Welcome! This is your personal workspace for the **SRX with Terraform and Mist** session. You will build a greenfield Juniper SRX estate the way a network team runs it for real: **HashiCorp Terraform** and the real **`Juniper/mist`** provider, with code review and shared state.

You are working in your own student account. Keep all lab work under this `~/lab` folder.

## What this is, and what it isn't

Nothing here touches a real Mist organization or a real SRX. Your terminal talks to **Dojo WAN**, a practice cloud inside the lab that answers at `api.mist.com`. The provider, the resource types and the API calls are the real ones; the Junos configuration the portal shows is a **preview** built from the parts you can confirm on a real SRX. The lab has no internet, so `terraform init` installs the provider from a local copy.

Your login is already in your environment (`MIST_HOST`, `MIST_API_TOKEN`, `MIST_ORG_ID`). Keep the token out of files and out of git.

## What you'll do

| Lab | Topic | Time |
| --- | ----- | ---- |
| [lab0.md](lab0.md) | Tour: fork, the portal, your org and its delivery, `init` | ~10 min |
| [lab1.md](lab1.md) | First objects: a network and services, plan, apply, idempotency | ~12 min |
| [lab2.md](lab2.md) | The gateway template: ports, networks, policies | ~12 min |
| [lab3.md](lab3.md) | Sites and variables: one template, three sites | ~12 min |
| [lab4.md](lab4.md) | Claim and assign the delivered gateways, read their Junos config | ~12 min |
| [lab5.md](lab5.md) | Layers: spoke template, hub profile, device override, and where settings go | ~12 min |
| [lab6.md](lab6.md) | Structure: modules, `for_each`, `moved` so nothing is destroyed | ~15 min |
| [lab7.md](lab7.md) | Team workflow: shared state, the lock, a reviewed pull request with the plan | ~15 min |
| [lab8.md](lab8.md) | Drift and import | ~15 min |
| [lab9.md](lab9.md) | Capstone: a new branch from a ticket | ~15 min |

**Do them in order.** Each lab builds on the one before; nothing is destroyed along the way. Open the portal from the landing page's **Dojo WAN** card and keep it in its own tab.

**Starting partway through?** Run `dojo prep <N>` (for example `dojo prep 5`). It sets up what the earlier labs would have left behind (your fork and clone, the files, `init` and the applied estate) so you can start Lab N right away.

**Checking your work.** `dojo check <N>` asks the API what your org looks like now and tells you what matches and what doesn't. It reads the result, not your files. A wrong answer costs nothing.

Keep [cheat-sheet.md](cheat-sheet.md) open in a split pane (`Ctrl+b %` in tmux) while you work.

## Commands for this workshop

| Command | What it does |
| ------- | ------------ |
| `dojo wan delivery` | the packing slip: your five gateways, their MACs and claim codes |
| `dojo wan config <device>` | the Junos config a gateway would get (name, MAC or serial) |
| `dojo wan events` | the latest changes in your org, and who made them |
| `dojo wan whoami` | your org id and the API host |
| `dojo check N` | check lab N |
| `dojo prep N` | catch your workspace up to where lab N starts |
| `dojo sensei ask "..."` | ask the support desk |

Open any lab file with:

```sh
glow lab0.md   # or: nano lab0.md, batcat lab0.md, etc.
```

## Check your shell

```sh
whoami
terraform version
git --version
dojo wan whoami
```

Your username looks like `student01`, `student02`, and so on. Your terminal is already signed in to the git server with your own access token, so forking the repo (Lab 0) and pushing (Labs 1, 7 and 9) ask for no password.
