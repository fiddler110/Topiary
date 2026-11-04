# srx-terraform: SRX with Terraform and Mist

A ~2¾ hour technology-track session: build a greenfield Juniper SRX estate managed from Mist, with HashiCorp Terraform and the real `Juniper/mist` provider (0.11.0). Students work against **Dojo WAN**, a simulator that answers as `api.mist.com`. Design and decisions: [`docs/SRX-MIST-PLAN.md`](../../docs/SRX-MIST-PLAN.md).

```sh
./dojo srx-terraform
```

**Running it as the facilitator? Read [`FACILITATOR.md`](FACILITATOR.md).**

## What's in this folder

| Path | What it is |
| ---- | ---------- |
| `workshop.env` | Name, track `technology`, order 1, duration, Forgejo `netops/srx-terraform` (fork workflow), `MODULES="lab-prep wan-cloud sensei feedback"` |
| `content/lab/` | `README.md`, `lab0.md` to `lab9.md`, `cheat-sheet.md`, seeded into each `~/lab` |
| `content/slides/` | Marp deck: `presentation.md`, `labs.md`, `cheat-sheet.md`, `lab-index.md`, `index.md` |
| `content/sample-repo/` | The starter repo seeded into Forgejo: versions, provider, variables, empty `main.tf`, lock file for linux amd64 and arm64 |
| `content/stages/labN/` | The end-of-lab files, cut from the lab pages; `dojo prep` and the bots install them. Files ending `.tmpl` hold claim-code placeholders |
| `content/bots/steps.sh` | Demo-bot steps for Labs 0-9; each round ends by destroying what it built |
| `compose/terminal/` | A thin terminal layer: `lab-prep` (`dojo prep N`) and `srx-check` (`dojo check N`). Terraform, the provider mirror and the login come from the `wan-cloud` module |

## Labs

| Lab | Topic | Resources |
| --- | ----- | --------- |
| 0 | Tour | fork, login, `init` |
| 1 | First objects | `mist_org_network`, `mist_org_service` |
| 2 | Gateway template | `mist_org_servicepolicy`, `mist_org_gatewaytemplate` |
| 3 | Sites and variables | `mist_site`, `mist_site_setting` |
| 4 | Claim and assign | `mist_org_inventory` |
| 5 | Layers | `mist_org_deviceprofile_gateway`, `_assign`, `mist_device_gateway` |
| 6 | Structure | modules, `for_each`, `moved` |
| 7 | Team workflow | `http` backend with lock, pull request with the plan |
| 8 | Drift and import | `terraform import` of a network and a device |
| 9 | Capstone | a new branch from a ticket |

## Checks

`dojo check N` (`srx-check`) calls the Dojo WAN API with the student's own token (the same requests as `curl -H "Authorization: Token $MIST_API_TOKEN" https://api.mist.com/api/v1/...`) and asserts on the org and on the rendered config from `.../dojo/config`. Labs 6 to 9 also read Terraform (`state list`, `plan -detailed-exitcode`) and Lab 7 reads `/dojo-state/srx-estate`.

## Depends on the `wan-cloud` module

`dojo wan delivery|config|events|whoami`; `MIST_HOST`, `MIST_API_TOKEN`, `MIST_ORG_ID`, `TF_VAR_org_id`, `TF_HTTP_USERNAME`, `TF_HTTP_PASSWORD`; the endpoints in plan section 10.6; `/wan/` portal with a facilitator drift button.

## Not done yet

- **Achievements** (a catalog, challenges): skipped for now. `dojo check` here would need folding into the achievements module's `check` command.
- The token in a secrets manager (`openbao`) and `plan` on pull requests through `runner-pool`.
- Stretch lab: HA with `mist_device_gateway_cluster`. Use literal MACs from `dojo wan delivery` and `depends_on` the inventory resource (two unknown MACs fail with "Duplicate List Value"). Labs must not use the `mist_org_deviceprofiles_gateway` data source (provider 0.11.0 queries type=ap and finds nothing).
- Never run against the live simulator: only `terraform validate` was run.
