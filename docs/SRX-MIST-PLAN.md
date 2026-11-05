# SRX-MIST-PLAN: SRX firewalls with Terraform and the Mist provider, simulated

Status: **built and run live once** (2026-11-04, branch `feat/srx-terraform`). The spike (section 9) showed the real provider running a full SRX build against a simulated API; the module, simulator and pack followed, and a `--test 1 --fast` bot has since followed the lab pages for Labs 0 to 9 with every `dojo check` passing (section 6). Open: a person reading the pages in a browser, a read of the Junos preview by someone who knows SRX, the `/admin` Drift button, and a many-student run (ROADMAP T4, T5). The first pack of the **technology** track
(`WORKSHOP_TRACK=technology`). Working names: workshop `srx-terraform`, module `wan-cloud` (section 2).

## 1. Goal

The education track teaches concepts (git, IaC, secrets, policy). This pack trains the team for one real job: a
**greenfield Juniper SRX estate managed from Mist with Terraform**. It is product-focused on purpose: the real provider
(`Juniper/mist`), the real resource types, the real inheritance model, and the habits the team will keep on the real
estate (layout, state, review, drift, secrets).

Students never touch a real Mist org or a real SRX. Like `tofu-basics` and Dojo Cloud, the provider talks to a
**simulated Mist API inside the stack**. Student terminals keep no internet (CLAUDE.md), and the class is free to
break things.

By the end a student can:

- lay out a Mist-managed SRX estate in Terraform: org objects, a gateway template, a gateway device profile, sites,
  site variables, claimed devices, per-device overrides;
- explain which layer a setting belongs in (org, template, profile, site, device) and why;
- run the change workflow the team will use: branch, `terraform plan` on a pull request, review, apply;
- find and fix drift made outside Terraform, and bring existing objects under Terraform with `import`;
- keep the API token out of the repo (openbao) and the state somewhere shared and locked.

## 2. Decisions

| Topic | Decision |
|---|---|
| Track | `technology`: the first pack in it |
| Tool | **HashiCorp Terraform** (user's choice, 2026-11-04), not OpenTofu: it is what the team will run for real. Pinned and sha256-verified per architecture in the module's terminal image. `tofu-basics` symlinks `terraform` to `tofu`; this pack's image must not include that layer |
| Provider | **`Juniper/mist`**, pinned (0.11.0 at writing; 96 MB binary), served from an offline filesystem mirror like `tofu-basics`. Terraform pinned at 1.17.1 |
| Host | The provider **only accepts the real Mist cloud hostnames** (spike Q1). So `wan-api` answers as **`api.mist.com`** inside the lab: a network alias on `workshop_lab` (to verify under podman's aardvark-dns; fallback `extra_hosts` on `web-terminal`) and a stack-CA certificate for that name. Students write the real `host = "api.mist.com"`. Nothing in the lab can reach the real one anyway (no egress) |
| Backend | **Simulated only** (user's choice, 2026-11-04): no real Mist org, no real SRX, no egress. A module service implements the subset of the Mist REST API the provider calls |
| Shape | Same pattern as `dojo-cloud`: an API service, a portal, a per-student credential broker in the terminal, a status check, an `/admin` tab |
| Fidelity | The provider is built on `mistapi-go` (v0.4.109 for provider 0.11.0), which is generated from the public Mist OpenAPI spec (`mistsys/mist_openapi`, MIT). The simulator validates request bodies against that spec, pinned to the SDK's version, and contract tests replay a recorded `apply`/`plan`/`destroy` per provider version |
| SRX realism | Phase 1: the simulator **renders the Junos `set` config** each gateway would receive (template or hub profile, then device; site variables, then device variables, substituted; DNS/NTP override flags honoured) and shows it in the portal and over a read-only CLI. Phase 2 (optional): back each gateway with a Linux netfilter container so zones and policies can be tested with real traffic, reusing `netlab`'s node image |
| Layers | Checked against Mist's documentation and OpenAPI spec (2026-11-04). Documented: a **WAN edge template** is assigned to spoke sites, a **gateway device profile** ("hub profile") to each hub device; device settings beat the template (WAN guided setup); a device's `vars` override site `vars`; a template's or profile's `dns_servers`/`ntp_servers` apply only with `dns_override`/`ntp_override = true` (`dnsOverride`/`ntpOverride` on the wire), otherwise the site's values are inherited. **Not documented** for gateways: a template and a profile on the same device, so lab 5 teaches them as roles (spoke template, hub profile on a fifth, hub gateway) and the renderer, which still layers both, prints a note when it happens. Sources: juniper.net WAN guided setup, SRX hub profile, WAN edge template and WAN configuration overview pages; `mistsys/mist_openapi` (`gateway_template`, `deviceprofile_gateway`, `device_gateway`) |
| Branding | Mist-*inspired*, no Juniper or Mist logos or trademarks in the portal (same rule as Dojo Cloud). Working name **Dojo WAN** for the portal; the module id `wan-cloud`. Provider and resource names stay real: they are the point of the pack |
| Tenancy | **One simulated org per student** (the facilitator gets org 00). A student's token sees only their org; the facilitator's token sees every org (CLAUDE.md: the facilitator reaches every part) |
| Secrets | The API token comes from the broker as `MIST_API_TOKEN`; a later lab moves it to openbao (`MODULES="wan-cloud openbao"`) |
| State | Local state in lab 1; a later lab moves it to a shared backend. Candidate: the HTTP backend served by the simulator (Dojo Cloud already serves one, `tfstate.py`), with locking |

## 3. Architecture

```text
 web-terminal (terraform + mirrored Juniper/mist provider; MIST_HOST, MIST_API_TOKEN per student from the broker)
       |  workshop_lab, HTTPS with the stack CA
       v
 wan-api  (simulated Mist REST API: /api/v1/self, /orgs/{org}/..., /sites/{site}/...)
       |  per-org JSON store (volume), spec validation, config renderer, event log
       +--> portal  (/wan, identity gate: orgs, sites, gateways, rendered Junos config, events)
       +--> admin tab (/admin: every org)
       +--> drift bot (facilitator- or lab-triggered "portal edits" that Terraform must notice)
```

- `wan-api` is one Python service, standard library plus a pinned JSON-schema validator, written like Dojo Cloud's
  `cloud-api` (token check, `X-Gateway-Token` for portal calls, rate-limit tripwire, `/readyz`).
- The terminal reaches it as `MIST_HOST=api.mist.com` on port 443, over TLS signed by the stack CA, trusted through
  `SSL_CERT_FILE` (or the system bundle the terminal's start hook writes, as Dojo Cloud does).
- Device inventory: each org is seeded with a few **unclaimed SRX serials and claim codes** (SRX300/SRX345 models), so
  `mist_org_inventory` has something to claim, as on a real greenfield delivery. The provider checks claim codes before
  any call: exactly 15 characters of `[0-9A-Z]` (e.g. `SRX300DOJO00001`); MACs are 12 lowercase hex digits.
- Nothing here runs Junos. Phase 1 needs no KVM, no licence and no vendor image.

## 4. Resource scope

Phase 1 covers what a greenfield SRX build uses. Each needs create, read, update, delete and import in the simulator.

| Layer | Resources |
|---|---|
| Org | `mist_org_network`, `mist_org_service`, `mist_org_servicepolicy`, `mist_org_vpn`, `mist_org_idpprofile`, `mist_org_avprofile` (if the labs reach security services) |
| Template and profile | `mist_org_gatewaytemplate`, `mist_org_deviceprofile_gateway`, `mist_org_deviceprofile_assign` |
| Site | `mist_site`, `mist_site_setting` (site variables), `mist_org_sitegroup` |
| Device | `mist_org_inventory` (claim, assign to site), `mist_device_gateway` (per-device overrides), `mist_device_gateway_cluster` (HA, a stretch lab) |
| Data sources | the matching `mist_org_*` / `mist_device_*` data sources the labs use |

Out of scope: Wi-Fi, switching, NAC, Marvis, firmware upgrades (`mist_upgrade_device`).

## 5. Labs (draft)

| # | Lab | Teaches |
|---|---|---|
| 0 | Tour | The Dojo WAN portal, an org, unclaimed inventory; the provider block, `MIST_HOST`/`MIST_API_TOKEN`; `terraform init` from the mirror |
| 1 | First objects | `mist_org_network` and `mist_org_service`; plan, apply, read back in the portal; idempotency (a second plan is empty) |
| 2 | The gateway template | Ports, WAN/LAN interfaces, networks, service policies on one `mist_org_gatewaytemplate`; the rendered Junos config |
| 3 | Sites and variables | `mist_site`, `mist_site_setting` vars (`{{wan_ip}}`, `{{site_subnet}}`); one template, three sites, three configs |
| 4 | Claim and assign | `mist_org_inventory` claims the delivered serials and assigns them to sites; the gateway picks up the template |
| 5 | Roles | Spoke template versus hub profile (a fifth gateway at a hub site), `dns_override`/`ntp_override`, device `vars` and a per-device override (`mist_device_gateway`): which value wins, and the house rule for where settings go |
| 6 | Structure | Refactor into modules (`site`, `gateway`), `for_each` over a sites map, `moved` blocks so nothing is destroyed |
| 7 | Team workflow | Shared state with locking (the lock is shown by holding an `apply` at its question; `terraform console` takes no lock against this backend), a reviewed pull request with the plan pasted in. As built, the token is explained but not moved to openbao, and the runner pool is not used: both are future work |
| 8 | Drift and import | A "portal edit" by the drift bot; `plan` shows it; decide to revert or adopt; `import` an object made by hand |
| 9 | Capstone | A new branch office from a ticket: one map entry, reviewed plan, apply, rendered config checked by `dojo check` |

Checks (`dojo check cN`) read the simulator's store and the rendered config, not the student's files, so they test the
result.

## 6. Bots

`--test --fast` bots run the labs end to end with the same Terraform and provider and write `~/.dojo-bot-done`.
As built (2026-11-04) the bot **follows the lab text**: `content/bots/labtext.py` turns each page's `hcl` blocks into
pastes and its `sh` blocks into commands, in page order, so a page that drifts from the provider, the simulator or
`dojo check` fails the bot (`LABTEXT FAIL` in its log, `~/.dojo-bot-labfails`). It answers only what a person would: the
`yes` to `apply`, the lock demo's first pane, and merging the pull request in the bot's own fork. The round-1
mistakes are a typo in a reference (Lab 1), a 14-character claim code (Lab 4) and a hub profile without `dns_override`
(Lab 5), placed with the page's own file blocks; the destroy-and-recreate refactor (Lab 6) and the refused second run
(Lab 7) are in the pages. First run: 18 failed blocks, which were five lab bugs (an apply before the hub's inventory
entry, a prose-only `profile.tf` edit, a lock demo that held no lock, a Lab 8 branch never merged so Lab 9 destroyed
`guest`, and two wrong plan counts), all fixed; the rerun has no failures. Not covered: the `/admin` Drift button, a
person reading the pages, and a run with many bots.

## 7. Phases

| Phase | Work | Effort |
|---|---|---|
| 0 | Spike (section 9) | S |
| 1 | `wan-api`: store, auth, the section 4 endpoints, spec validation, recorded contract tests | L |
| 2 | Terminal layer: Terraform, provider mirror, broker, CA trust; `wan-cloud` module wiring, manifest, `/admin` tab | M |
| 3 | Config renderer (template, profile, device, variables, to Junos `set` lines) and the portal | M |
| 4 | Workshop pack `srx-terraform`: slides, labs 0 to 9, checks, sample repo, facilitator guide. **Built**; open: a student rehearsal in a browser, the Junos preview read by an SRX person | L |
| 5 | Bots, drift bot, live checks with `--test --fast`. **Bots built and live-run once** (one bot, no failing block); open: the Drift button, 10+ bots, `capacity` numbers | M |
| 6 | Optional: netfilter-backed gateways for traffic tests | L |

## 8. Risks

| Risk | Mitigation |
|---|---|
| Simulator drifts from the real API as the provider moves | Pin the provider; validate against the spec version the provider was built from; contract tests replay recorded traffic; upgrades are a deliberate task with a re-record |
| The provider insists on a known Mist cloud host | Confirmed (Q1). Resolved by answering as `api.mist.com` inside the lab; both a hosts entry and a `MIST_PROXY` tunnel were proven |
| The provider crashes or reports "inconsistent result" on answers the real API would not give | Seen in the spike (a nil-pointer panic on a site setting without `site_id`). The rules in section 9.1 fix every case found; contract tests keep them fixed |
| The rendered Junos config is invented, so it may teach wrong details | Keep it to the parts the team can confirm on a real SRX (interfaces, zones, policies, NAT); label it a preview; have someone check it against a real device before the first class |
| Layer behaviour Mist doesn't document (template plus profile on one gateway; whether a device's own `dns_servers` needs a flag; inheritance from org-level settings) | The labs avoid the undocumented cases; the renderer notes them. Verify on a real org before the first class |
| Terraform licence (BSL) | Internal training use; record the decision in the module README |

## 9. Spike

Questions, answered on this machine (it has internet; the stack does not).

| # | Question | Result |
|---|---|---|
| Q1 | Does the provider accept an arbitrary `host` (name and port)? | **No.** Any host not on its list of Mist clouds is refused at configure time (`The configured Mist Host does not match the supported Clouds`). Both workarounds work: a CONNECT proxy via `MIST_PROXY`, and (cleaner, used in the plan) a hosts entry mapping `api.mist.com` to the simulator, tested with `--network none` |
| Q2 | Does it trust a private CA from `SSL_CERT_FILE`, or need the system store? | **Yes.** A private CA in `SSL_CERT_FILE` is trusted; TLS is still verified against `api.mist.com` |
| Q3 | Which HTTP calls do `init`/`plan`/`apply`/second `plan`/`destroy` make for a minimal SRX config (site, network, service, service policy, gateway template, device profile, claim, device override)? | `plan` calls only `GET /self`. Full list in 9.2. Order on destroy: unassign profile, clear device config and site setting (`PUT` with `-field` keys), delete profile, unclaim (`PUT inventory op=delete` by MAC), delete site, template, policy, service, network |
| Q4 | Does a generic store that echoes the request body (plus `id`, `org_id`, timestamps) satisfy the provider, or which fields must the server compute? | **A generic store works** once it follows the rules in 9.1. Result: 10 resources applied, an empty second plan, destroy back to an empty org |
| Q5 | Does `import` work against the same store? | **Yes.** `state rm` then `import` of `mist_org_network` (`<org_id>.<id>`) and `mist_device_gateway` (`<site_id>.<device_id>`) gave an empty plan. Drift (a direct API edit of a VLAN) showed in `plan` and `apply` reverted it |
| Q6 | Sizes: provider binary, Terraform binary, memory of a `plan` | Provider 96 MB; Terraform a 37 MB zip, 124 MB unpacked (about 220 MB added to the terminal image). A full apply of the spike config: 0.9 s, about 100 MB peak RSS (Terraform plus provider), so 15 students applying at once is about 1.5 GB in the terminal |

Spike files (throwaway, not in the repo): the fake API, CONNECT proxy and config lived in the session scratchpad.
Tested locally on WSL2: Terraform 1.17.1, provider 0.11.0, the fake API on the host (proxy route) and in a podman
container with no network (hosts route).

### 9.1 Rules the simulator must follow

Each was found by a provider error or crash in the spike.

1. **Chunked request bodies.** The provider sends `Transfer-Encoding: chunked`, no `Content-Length`.
2. **Return scope ids.** Every object carries `org_id`; site-scoped answers (`/sites/{id}/setting`, devices) carry
   `site_id`. Without it the provider panics.
3. **Paging headers on every list**: `X-Page-Limit`, `X-Page-Page`, `X-Page-Total`. Without them inventory refresh fails.
4. **`PUT` semantics**: a key `-name` deletes `name`; other keys replace. Server-owned fields (`id`, `org_id`,
   `site_id`, `type`, `mac`, `serial`, `model`, `created_time`) are never taken from the request (the provider sends
   `type: ""` on a device).
5. **Echo what was sent, in the same shape.** Dropping or reshaping a field (e.g. `type`, `addresses` on a service) is
   reported as "inconsistent result after apply".
6. **Inventory**: `POST` claims by code list and returns `added`/`duplicated`/`error`/`inventory_added`; `PUT` with
   `op` `assign` (to a site), `unassign` or `delete` (by MAC or serial). Profile `assign`/`unassign` must set
   `deviceprofile_id` on the device, because the assign resource refreshes from the inventory list.
7. **An empty collection is `[]`, not 404.** A missing object is 404.
8. **`POST` (create) bodies carry `-name` keys too** (e.g. `"-gateway": ""` on a network): strip them, do not store them.
9. **Inventory errors**: on a 400/404 the provider indexes `reason[i]` for every `error[i]`, so the two lists must be the
   same length (a mismatch panics). Deleting a device that is already gone is answered 200, so a destroy never fails on it.
10. **Cluster create** (`POST .../devices/{id}/ha`): the provider recognises "already formed" by the text
    `already belong to a ha cluster` in the 400 `detail`; keep that wording. Both nodes must already be assigned to the site.
11. **`GET /sites/{site}/setting` never 404s** for a site that exists (an empty setting with `site_id`/`org_id`).
12. **`deviceprofiles?type=`**: the list filters on `type`. Provider 0.11.0's `mist_org_deviceprofiles_gateway` data source
    asks for `type=ap` (a provider bug), so it lists nothing for gateway profiles; labs should not use it.
13. **Read every request body**, even on a refused or unknown path: Terraform keeps connections alive and an unread body
    is parsed as the next request line.

### 9.2 Endpoints a basic SRX build uses

```text
GET    /api/v1/self
POST   /api/v1/orgs/{org}/{networks|services|servicepolicies|gatewaytemplates|deviceprofiles|sites}
GET    /api/v1/orgs/{org}/{networks|services|servicepolicies|gatewaytemplates|deviceprofiles}/{id}
PUT    /api/v1/orgs/{org}/{...}/{id}
DELETE /api/v1/orgs/{org}/{...}/{id}
POST   /api/v1/orgs/{org}/deviceprofiles/{id}/{assign|unassign}
GET    /api/v1/orgs/{org}/inventory          (query: page, limit, serial, mac, model, type, vc, unassigned, ...)
POST   /api/v1/orgs/{org}/inventory          (claim)
PUT    /api/v1/orgs/{org}/inventory          (op: assign, unassign, delete)
GET    /api/v1/sites/{site}                  DELETE /api/v1/sites/{site}
GET    /api/v1/sites/{site}/setting          PUT    /api/v1/sites/{site}/setting
GET    /api/v1/sites/{site}/devices/{id}     PUT    /api/v1/sites/{site}/devices/{id}
```

Also exercised in Phase 1 by `modules/wan-cloud/wan-api/test_contract.py` (the real provider, apply/plan/update/drift/import/
destroy): `PUT` on a gateway template, service policy, site group, VPN, site and device; `mist_org_vpn`,
`mist_org_sitegroup`, `mist_device_gateway_cluster` (`POST`/`GET`/`DELETE /sites/{site}/devices/{id}/ha`, the cluster id
is node 0's device id) and the data sources `mist_org_networks`, `services`, `servicepolicies`, `gatewaytemplates`,
`deviceprofiles_gateway`, `sitegroups`, `vpns`, `mist_sites`, `mist_org_inventory` (all plain paged `GET` lists).
`GET /sites/{site}/devices` (the site's claimed devices) is served for the terminal's `dojo wan`; the provider's
`mist_device_gateway_stats` data source and everything under "Out of scope" are not.

## 10. Build contract

The interfaces the parts share, fixed before the build so they can be written in parallel. Change them here first.

### 10.1 Names

| Thing | Name |
|---|---|
| Module | `modules/wan-cloud/` (`wan-api/` service, `terminal/` layer, `compose.yml`, `module.env`, `extensions.json`, `README.md`) |
| Service | `wan-api`, container `workshop_wan_api`, image `topiary/wan-api:${WORKSHOP_SLUG:-local}` |
| Workshop | `workshops/srx-terraform/`, `WORKSHOP_TRACK=technology`, `WORKSHOP_ORDER=1`, Forgejo `netops/srx-terraform` with `FORGEJO_FORK_WORKFLOW=1` |
| Volumes | `wan_pki` (CA and server cert), `wan_secrets` (signing key), `wan_data` (org stores, state) |
| Portal | Dojo WAN at `/wan/` (identity gate), card and `/admin` tab id `wan` |

### 10.2 Network and TLS

- `wan-api` joins `workshop_lab` with aliases `api.mist.com` and `wan-api` (Dojo Cloud already uses dotted aliases).
- Port **443**: TLS, the Mist API (`/api/v1/...`), the state backend (`/dojo-state/...`) and the Dojo extras
  (`.../dojo/...`). Every call needs a valid token. `cap_add: NET_BIND_SERVICE` as `cloud-api` does.
- Port **8080**: plain HTTP behind Caddy only: `/wan/` portal and `/wan/api/...` (needs `X-Gateway-Token`, identity from
  `X-Auth-User`), `/readyz`, `/_dojo/reset/{user}` (`RESET_TOKEN`).
- At first start `wan-api` creates the CA and a server cert for `api.mist.com`, `wan-api`. The keys stay in
  `/data/pki` (`wan_data`, never mounted by the terminal); only `ca.crt` goes to `/pki`. The terminal mounts `wan_pki` at `/run/wan-pki:ro` and its start hook adds `ca.crt` to the system trust store, so
  Terraform needs no `SSL_CERT_FILE`.

### 10.3 Identity, tokens, orgs

- `wan-api` writes `/secrets/signing.key` (32 random bytes, hex, 0600) at first start. The terminal mounts `wan_secrets`
  at `/run/wan-secrets:ro`, readable by root only; a root broker on a Unix socket hands each user their values (the
  `dojo-cloud` broker pattern, `SO_PEERCRED`).
- `wan_ids.py` (in `wan-api/`, copied into the terminal image; a `test_parity.py` checks both copies agree):
  - `api_token(key, user) = hmac_sha256(key, "wan/apitoken:" + user).hexdigest()[:40]`
  - `org_id(key, user) = str(uuid.UUID(bytes=hmac_sha256(key, "wan/org:" + user).digest()[:16]))`
  - `claim_code(key, user, n)`: 15 characters `[0-9A-Z]`: model prefix (`SRX300` or `SRX345`) plus 9 from the HMAC of
    `"wan/claim:" + user + ":" + n`, uppercased base32 restricted to `[0-9A-Z]`.
- Known users: `STUDENT_PREFIX` 1..`STUDENT_COUNT` (two digits), `BOT_PREFIX` 1..`BOT_COUNT`, and `FACILITATOR_USERNAME`.
  Each has one org, created with its seed at start-up. The facilitator's token lists every org in `/self` privileges and
  may read and write any of them.
- The broker exports: `MIST_HOST=api.mist.com`, `MIST_API_TOKEN`, `MIST_ORG_ID`, `TF_VAR_org_id` (same value),
  `TF_HTTP_USERNAME=<user>`, `TF_HTTP_PASSWORD=<token>` (state backend).

### 10.4 Seed per org

Org name `Dojo Org <user>`. A **delivery** of five unclaimed gateways: two `SRX300`, two `SRX345`, one `SRX1500`, serials and MACs
derived from the user (MAC 12 lowercase hex, locally administered), claim codes from `claim_code`. Unclaimed devices are
not in the inventory until claimed (as in Mist). `GET /api/v1/orgs/{org}/dojo/delivery` (token auth) returns the packing
slip; the portal shows it too.

### 10.5 Store

One JSON file per org in `/data/orgs/<org_id>.json`, written atomically, guarded by a per-org lock (never held across
anything slow):

```json
{"org": {...}, "networks": {"<id>": {}}, "services": {}, "servicepolicies": {}, "gatewaytemplates": {},
 "deviceprofiles": {}, "sitegroups": {}, "vpns": {}, "sites": {"<id>": {}}, "site_settings": {"<site_id>": {}},
 "delivery": [{"serial": "", "mac": "", "model": "", "magic": ""}],
 "inventory": [{"id": "", "serial": "", "mac": "", "model": "", "type": "gateway", "site_id": null,
                "deviceprofile_id": null, "magic": ""}],
 "devices": {"<device_id>": {}}, "events": [{"ts": 0, "actor": "", "action": "", "path": ""}]}
```

Device id: `00000000-0000-0000-1000-<mac>`. Every object follows the rules of 9.1.

### 10.6 Dojo extras (token auth, on 443)

- `GET /api/v1/orgs/{org}/dojo/delivery`: the packing slip.
- `GET /api/v1/sites/{site}/devices/{id}/dojo/config`: the rendered Junos `set` config (text/plain), from
  `renderer.render(store, device_id) -> str`. Order of precedence: gateway template, then device profile, then device;
  `{{var}}` replaced from the site setting `vars` (an unknown variable stays and is reported in a comment line).
- `GET /api/v1/orgs/{org}/dojo/events`: the event log (who changed what, so drift is visible).
- `/dojo-state/{name}`: Terraform HTTP backend, Basic auth `<user>:<token>`, state per org and name, `LOCK`/`UNLOCK`
  supported (port of `dojo-cloud/cloud-api/tfstate.py`).
- `POST /_dojo/drift/{user}` on 8080, facilitator only via the portal: makes a canned out-of-band change and logs it with
  actor `portal:facilitator`.

### 10.7 Checks

Lab checks run in the terminal as the student and read the org through the API with the student's own token (`curl`
to `https://api.mist.com`), so they test the result, not the files. Bots use the same Terraform and provider.
