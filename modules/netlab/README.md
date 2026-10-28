# netlab module

Per-student practice networks for learning Ansible: a pc, a VLAN switch, a Linux firewall and an nginx web node,
twice (one branch configured by hand, one by playbooks), all on internal-only networks.

Add it with `MODULES="netlab"` in a `workshop.env`, and keep `STUDENT_COUNT` at or below `NETLAB_MAX_STUDENTS` (15).
The design, spike results and the lab path are in `NETLAB-PLAN.md` at the repo root.

| Part | What it does |
|---|---|
| `node/` | One Alpine image for every node; `NODE_ROLE` (pc, sw, fw, web) picks the job. SSH as root with a per-pod password. |
| `generate.py` | Writes the pods as a Compose file at start (`.generated/modules/netlab.yml`); `test_generate.py` covers it. |
| `compose.yml` | Builds the node image, declares the internal `netlab_mgmt` network and puts the terminal on it. |
