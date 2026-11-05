# Lab 7: Team workflow

**Goal:** move state to a shared, locked home, keep the token out of the repo, and change the estate through a reviewed pull request with the plan attached. All commands run in `~/lab/srx-terraform`.

> **Starting here?** Run `dojo prep 7`.

---

## 1. Why your state can't stay on your laptop

Right now Terraform's memory of your estate is a file, `terraform.tfstate`, in your clone. That works for one person. For a team it breaks in three ways:

- a colleague who runs `plan` without your file sees an empty estate and wants to create everything again;
- two people who `apply` at the same time can overwrite each other's work;
- the file holds every attribute of every object, and can hold secrets, so it must not live in git.

The answer is a **backend**: state kept in one shared place, with a **lock** so only one run changes it at a time. Dojo WAN serves a Terraform `http` backend for this, at `https://api.mist.com/dojo-state/<name>`. A real team would use an object store or Terraform Cloud; the idea is the same.

```sh
ls -l terraform.tfstate
terraform state list | head -5
```

## 2. Where the secrets are (and aren't)

Two kinds of secret reach Terraform here: the Mist API token, and the backend login. Both are in your environment (`MIST_API_TOKEN`, `TF_HTTP_USERNAME`, `TF_HTTP_PASSWORD`), set by your terminal. Neither is in a file. Prove it:

```sh
git grep -n -i -E 'token|password' -- ':!*.md' || echo "no secrets in tracked files"
```

On the real estate the token would come from a secrets manager (a vault) at run time and from the CI system's own secret store, never from the repo. The rule you keep is the same: **the repo holds names, never values**.

## 3. Switch to the shared backend

Create `backend.tf`. The login comes from `TF_HTTP_USERNAME` and `TF_HTTP_PASSWORD`, so it isn't written here:

```hcl
# backend.tf
terraform {
  backend "http" {
    address        = "https://api.mist.com/dojo-state/srx-estate"
    lock_address   = "https://api.mist.com/dojo-state/srx-estate"
    unlock_address = "https://api.mist.com/dojo-state/srx-estate"
    lock_method    = "LOCK"
    unlock_method  = "UNLOCK"
  }
}
```

A backend change needs a new `init`, and Terraform offers to copy the state you have:

```sh
terraform init -migrate-state
```

<!-- dojo-reveal: Result -->

```text
Initializing the backend...
Do you want to copy existing state to the new backend?
  Pre-existing state was found while migrating the previous "local" backend to the
  newly configured "http" backend. ...

  Enter a value: yes

Successfully configured the backend "http"! Terraform will automatically
use this backend unless the backend configuration changes.
```

Answer `yes`.

<!-- /dojo-reveal -->

Check that nothing changed and that the state really is on the server:

```sh
terraform plan
terraform state list | wc -l
curl -s -u "$TF_HTTP_USERNAME:$TF_HTTP_PASSWORD" https://api.mist.com/dojo-state/srx-estate \
  | python3 -c 'import json,sys; s=json.load(sys.stdin); print("serial", s["serial"], "resources", len(s["resources"]))'
```

`plan` still says `No changes.` The local `terraform.tfstate` is now stale and git ignores it; the server holds the truth.

Commit `backend.tf`: it holds no secret, and a colleague who clones the repo needs it to find the same state.

```sh
git add backend.tf
git commit -m "Keep the estate's state in the shared, locked backend"
```

## 4. The lock

Open a second terminal pane (`Ctrl+b %`). In **pane 1**, start an `apply` and leave it at its confirmation question. `-replace` asks Terraform to destroy and recreate that one resource; you will answer `no`, so nothing changes. A run takes the state lock before it plans and holds it until it finishes, so while it waits for your answer the lock is held:

```sh
terraform apply -replace=mist_org_service.dns
```

Do **not** answer yet.

**Your turn:** in **pane 2**, predict what `terraform plan` does.

```sh
terraform plan
```

<!-- dojo-reveal: Result -->

```text
Error: Error acquiring the state lock

Error message: ... state locked
Lock Info:
  ID:        ...
  Operation: OperationTypeApply
  Who:       studentNN@...
  Created:   ...
```

That is the lock doing its job: a second run is refused while the first holds it. Now answer **`no`** in pane 1 (nothing is replaced), and pane 2's `plan` works again.

<!-- /dojo-reveal -->

If a run is killed and leaves a lock behind, `terraform force-unlock <ID>` removes it. Use it only after checking nobody is really running.

## 5. Change the estate through a pull request

The rule for the team: **nobody applies from a branch**. A change goes: branch, `plan`, pull request with the plan in it, review, merge, `apply` from `main`. (On the real estate a runner runs `plan` on every pull request. Here you paste the output.)

First make sure `main` has your work from the earlier labs:

```sh
git checkout main
git merge --ff-only estate     # nothing to do if dojo prep did it for you
git push origin main
```

Now the change: a new service so policies can allow NTP. Make a branch and add it to the end of `main.tf`:

```sh
git checkout -b add-ntp-service
```

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

resource "mist_org_service" "ntp" {
  org_id    = var.org_id
  name      = "ntp"
  type      = "custom"
  addresses = ["0.0.0.0/0"]
  specs     = [{ protocol = "udp", port_range = "123" }]
}
```

Save the plan to a file, so the reviewer reads exactly what you saw. Never `apply` yet:

```sh
terraform fmt -check
terraform validate
terraform plan -no-color | tee plan.txt
```

<!-- dojo-reveal: Result -->

```text
  # mist_org_service.ntp will be created
  + resource "mist_org_service" "ntp" {
      ...
    }

Plan: 1 to add, 0 to change, 0 to destroy.
```

<!-- /dojo-reveal -->

Commit, push, and open the pull request in your fork with the plan in its description. (`plan.txt` is git-ignored.)

```sh
git add main.tf
git commit -m "Add an ntp service"
git push -u origin add-ntp-service

python3 - <<'PY' > pr.json
import json
fence = chr(96) * 3
plan = open("plan.txt").read()
print(json.dumps({"head": "add-ntp-service", "base": "main",
  "title": "Add an ntp service",
  "body": "New org service so policies can allow NTP.\n\n" + fence + "text\n" + plan + "\n" + fence}))
PY
curl -s --netrc -H 'Content-Type: application/json' -d @pr.json \
  http://git-server:3000/api/v1/repos/$USER/srx-terraform/pulls | python3 -c 'import json,sys; print(json.load(sys.stdin)["html_url"])'
rm pr.json
```

Open the link in Forgejo. Swap with a neighbour (or ask the facilitator) and **review**: read the plan in the description. Is it what the title says? Is the destroy count zero? Leave a comment, then approve.

When it is reviewed, merge it in Forgejo (**Merge**), then apply **from `main`**:

```sh
git checkout main
git pull origin main
terraform plan
terraform apply
```

## Check

```sh
dojo check 7
```

<!-- dojo-reveal: What it checks -->

Through the API: the shared state for your org exists at `/dojo-state/srx-estate`, holds your sites, is not locked, and your org has the `ntp` service the pull request added.

<!-- /dojo-reveal -->

## Check yourself

1. Two people run `terraform apply` at the same moment. What stops them corrupting the state?
2. Why paste the plan into the pull request?

<!-- dojo-reveal: Show the answer -->

1. The backend's lock: the second run waits or fails with `Error acquiring the state lock`.
2. Reviewers can't see what Terraform will do from the code diff alone. The plan is the effect, and the destroy count is the line a reviewer must read.

<!-- /dojo-reveal -->

## Common mistakes

| You see | Cause / fix |
| ------- | ----------- |
| `Error: Failed to get existing workspaces` / `401` | Your shell has no `TF_HTTP_USERNAME` and `TF_HTTP_PASSWORD`. Open a new terminal tab. |
| `Backend configuration changed` | You edited `backend.tf` and didn't re-init. Run `terraform init -migrate-state`. |
| `Error acquiring the state lock` and nobody is running anything | A killed run left a lock. Confirm with the class, then `terraform force-unlock <ID>`. |
| `git push` rejected | You are on the wrong branch or cloned the team repo. Check `git remote -v`: `origin` should be your own fork. |
| The plan in the PR says `1 to add` but also `1 to destroy` | Something else changed. Read the whole plan before asking for review. |

**Next:** [lab8.md](lab8.md)
