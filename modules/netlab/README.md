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
| `netlab-view/` | The "My Network" page (`/netlab-view/`, identity gate; an `/admin` tab of the same id for the facilitator). Read-only: per node up/down, interfaces and addresses, switch VLANs per port, firewall `LAB` rules, the pc's ping/HTTP/HTTPS probe of web, and the latest `dojo netlab check` verdicts (kept in memory by `netlab-checker`, read through `GET /last/<pod>` with a token only the view derives). A student reads only their own pod; the facilitator reads every pod. It SSHes to the nodes with `netlab-checker/checker.py`, one collection per pod per 4 s. Tests: `python3 -B -m unittest discover -s modules/netlab/netlab-view`. |
