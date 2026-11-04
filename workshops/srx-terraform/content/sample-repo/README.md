# srx-terraform

The Terraform for a greenfield Juniper SRX estate managed from Mist. In the lab it talks to Dojo WAN, a
simulator that answers as `api.mist.com`; the provider and the resource types are the real ones.

| Path | What it is |
| ---- | ---------- |
| `versions.tf` | Terraform and provider versions (`juniper/mist` 0.11.0) |
| `providers.tf` | The provider block. No host or token: `MIST_HOST` and `MIST_API_TOKEN` come from the environment |
| `variables.tf` | Inputs. `org_id` comes from `TF_VAR_org_id` |
| `main.tf` | Org objects. Empty until Lab 1 |
| `.terraform.lock.hcl` | The exact provider build and checksums (commit it) |
| `.gitignore` | Keeps `.terraform/` and state out of git |

Follow the labs in `~/lab` (start with `lab0.md`).

## Commit / don't commit

Commit: `*.tf`, `*.tfvars` (no secrets), `.terraform.lock.hcl`.
Never commit: `.terraform/`, `*.tfstate*`, or an API token.
