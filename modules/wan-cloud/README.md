# wan-cloud module

Simulated Juniper Mist API ("Dojo WAN") plus Terraform and the Juniper/mist provider, offline, at /wan.

**Dojo WAN**: a simulated Mist cloud for gateway (SRX) labs. `wan-api` answers as `api.mist.com` on the lab
network, so students write the real `host = "api.mist.com"` and use HashiCorp Terraform with the `juniper/mist`
provider. Each student has one org. Nothing real is touched. Add it with `MODULES="wan-cloud"` in a
`workshop.env`. The design is in `docs/SRX-MIST-PLAN.md`.

| Part | What it does |
|---|---|
| `compose.yml` | `wan-api` (on `workshop_lab`, aliases `api.mist.com` and `wan-api`), volumes `wan_pki`, `wan_secrets`, `wan_data`, and the terminal's read-only CA and signing-key mounts. |
| `extensions.json` | Landing card **Dojo WAN**, the facilitator's `/admin` tab, the `/wan` route (identity gate), the reset hook and the status-strip check on `/readyz`. |
| `terminal/` | Terraform 1.17.1 (sha256-pinned per arch), the offline `juniper/mist` 0.11.0 mirror, root-owned `terraformrc`, the root credential broker (`wan-broker.py`), `wan-env` (sourced from zshenv), `start.d/50-wan-cloud.sh` (trusts the CA, runs the broker) and `dojo wan`. |
| `wan-api/` | The service source and its unit tests. |
| `test_parity.py` | Checks that the broker and `wan-api` derive identical tokens and org ids, and that files copied from `tofu-basics` have not drifted. |

**Student command**: `dojo wan delivery` (packing slip), `dojo wan config <device>` (rendered Junos config),
`dojo wan events`, `dojo wan whoami`.

**Settings** (set in `.env` or `workshop.env`): `WAN_API_MEM_LIMIT` (256m), `WAN_API_RATE_BURST` (200) and
`WAN_API_RATE_PER_SEC` (20; `0` = off, a 429 with `Retry-After` when exceeded). The gateway and reset tokens come
from the engine (`GATEWAY_TOKEN_WAN_API`, `RESET_TOKEN_WAN_API`, derived because `wan-api` is a routed upstream).

**Tests** (host Python, no containers):

```sh
cd modules/wan-cloud && python3 -B -m unittest test_parity
```

## Trust notes

- Student tokens are derived from `wan_secrets/signing.key`, which only root in the terminal can read. Students get
  their own values only from the root broker, which asks the kernel who is calling (`SO_PEERCRED`). A student cannot
  ask for another student's token. The facilitator's token sees every org.
- Port 443 (the Mist API, state backend and Dojo extras) needs a valid token on every call.
- Port 8080 is plain HTTP and meant only behind the gateway. `/wan/` and `/wan/api/` check `X-Gateway-Token`;
  `/_dojo/reset/{user}` checks `RESET_TOKEN`. `/readyz` answers without a token (it reveals only readiness). Students
  on `workshop_lab` can reach 8080 directly, so wan-api must check the token on every route except `/readyz`.
- The CA key stays in `wan-api`; the terminal mounts only `ca.crt`, which the start hook adds to the system trust
  store. The broker hands out nothing until that has happened (open a new terminal tab if Dojo WAN started late).
- The terminal has no internet: Terraform installs the provider only from the baked-in mirror.
- Copied from `tofu-basics`: `unpack-mirror.py`, `disable-tofu-ls.py` (and the pinned OpenTofu VS Code extension, for
  HCL highlighting). `test_parity.py` fails if they drift.

Used by: `srx-terraform`.
