# Lab 0: The tour

**Goal:** get your own copy of the repo, meet your Mist org in the Dojo WAN portal, and run `terraform init` against the provider. Nothing you run here changes your org.

---

## 1. Fork the repo and clone your fork

The team repo is `netops/srx-terraform`. Each of you works in your own **fork**: a copy on the git server under your account that still knows where it came from. `--netrc` signs you in with the access token your terminal came with, so there is no password to type.

```sh
curl --netrc -H "Content-Type: application/json" -d '{}' \
  http://git-server:3000/api/v1/repos/netops/srx-terraform/forks
cd ~/lab
git clone http://git-server:3000/$USER/srx-terraform.git
cd srx-terraform
ls -a
```

A block of JSON means the fork worked. `repository is already forked` means you did it earlier: carry on.

<!-- dojo-reveal: What is in the repo? -->

- `versions.tf` pins Terraform (`>= 1.17`) and the `juniper/mist` provider (`0.11.0`).
- `providers.tf` is `provider "mist" {}`: empty on purpose. The address and the token live in your environment.
- `variables.tf` has one input, `org_id`.
- `main.tf` is empty. You fill it in from Lab 1.
- `.terraform.lock.hcl` pins the exact provider build. Commit it.

<!-- /dojo-reveal -->

## 2. Your login is already in your environment

Your terminal set four values for you. The token is a secret: look at the names, never paste the value anywhere.

| Variable | Meaning |
| -------- | ------- |
| `MIST_HOST` | where the API lives: `api.mist.com` |
| `MIST_API_TOKEN` | your own API token (a secret) |
| `MIST_ORG_ID` | your organization's id |
| `TF_VAR_org_id` | the same id, which Terraform turns into `var.org_id` |

**Your turn:** before you run this, predict why `providers.tf` has no `host` or `token` in it.

```sh
env | grep -E '^(MIST_|TF_VAR_)' | sed 's/\(TOKEN=\).*/\1.../'
dojo wan whoami
```

<!-- dojo-reveal: Results -->

```text
MIST_HOST=api.mist.com
MIST_API_TOKEN=...
MIST_ORG_ID=1f0b3a7e-5c1d-4e0e-9a55-7d1c2b3a4f66
TF_VAR_org_id=1f0b3a7e-5c1d-4e0e-9a55-7d1c2b3a4f66
org id: 1f0b3a7e-5c1d-4e0e-9a55-7d1c2b3a4f66
host:   api.mist.com
```

Your org id differs. Settings that differ per person or per environment, and secrets, stay out of the repo. That is what lets the same files run for everyone.

<!-- /dojo-reveal -->

> **No `MIST_` lines?** Dojo WAN may have started after your shell did. Open a new terminal tab.

## 3. Meet your org

Open the landing page and click the **Dojo WAN** card. This is a practice Mist cloud. It answers at `api.mist.com` inside the lab and nothing here can reach the real one. The provider and the resource types are the real ones.

In the portal find your organization, **Dojo Org studentNN**. It is empty: no networks, no sites, no templates. It has a **delivery**, the packing slip for five gateways that just arrived, still in their boxes:

```sh
dojo wan delivery
```

<!-- dojo-reveal: Results -->

```text
model   serial        mac           magic
SRX300  ...           ...           SRX300...
SRX300  ...           ...           SRX300...
SRX345  ...           ...           SRX345...
SRX345  ...           ...           SRX345...
```

`magic` is the claim code. Mist uses it to prove the box is yours. You claim these in Lab 4.

<!-- /dojo-reveal -->

You can ask the API the same thing the portal does. The token goes in a header:

```sh
curl -s -H "Authorization: Token $MIST_API_TOKEN" https://api.mist.com/api/v1/self | python3 -m json.tool | head -20
curl -s -H "Authorization: Token $MIST_API_TOKEN" https://api.mist.com/api/v1/orgs/$MIST_ORG_ID/networks
```

The second call prints `[]`: an empty collection, not an error.

## 4. `terraform init`

`init` installs the provider named in `versions.tf`. Normally it downloads from a registry. This lab has no internet, so it comes from a local copy; the commands and the output are the same.

```sh
terraform version
terraform init
```

<!-- dojo-reveal: Results -->

```text
Terraform v1.17.1
on linux_amd64

Initializing provider plugins...
- Reusing previous version of juniper/mist from the dependency lock file
- Installing juniper/mist v0.11.0...
- Installed juniper/mist v0.11.0
Terraform has been successfully initialized!
```

<!-- /dojo-reveal -->

Now `terraform plan`. There is nothing to build yet:

```sh
terraform plan
```

```text
No changes. Your infrastructure matches the configuration.
```

Even an empty plan asks the API who you are (`GET /api/v1/self`), so this also proves your token works.

## Check

```sh
dojo check 0
```

<!-- dojo-reveal: What it checks -->

The check calls the API with your own token. It confirms the token is valid, the org it names is the one in `MIST_ORG_ID`, the delivery lists five gateways, and `terraform init` has run in your clone.

<!-- /dojo-reveal -->

## Check yourself

1. Where does the provider get the API address and the token?
2. Why is it fine to commit `.terraform.lock.hcl` but never `terraform.tfstate`?

<!-- dojo-reveal: Show the answer -->

1. From the environment: `MIST_HOST` and `MIST_API_TOKEN`.
2. The lock file holds provider versions and checksums, nothing secret. State records every attribute of every resource, and can hold secrets in plain text.

<!-- /dojo-reveal -->

## Common mistakes

| You see | Cause / fix |
| ------- | ----------- |
| `Error: The configured Mist Host does not match the supported Clouds` | `MIST_HOST` is empty or wrong. Open a new terminal tab, then `echo $MIST_HOST` should print `api.mist.com`. |
| `curl: (60) SSL certificate problem` or `x509: certificate signed by unknown authority` | Your shell started before Dojo WAN's certificate was installed. Open a new terminal tab. |
| `Error: Failed to query available provider packages` | You are not in the repo folder. `cd ~/lab/srx-terraform`. |
| `No configuration files` | Same: wrong folder. |

**Next:** [lab1.md](lab1.md)
