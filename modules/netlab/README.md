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

## Demo bots (`--test`)

Bots are treated like students. With `./dojo netlab-ansible --test N [--fast]`, `testuserK` gets pod `STUDENT_COUNT + K`
(`generate.py` reads `BOT_COUNT`; `netlab-checker` and `netlab-view` map the same names to the same pods, and the
facilitator sees the bot pods like any other). Students and bots share the cap: `STUDENT_COUNT + BOT_COUNT` must stay at or
below `NETLAB_MAX_STUDENTS` (15), or the generator fails with a message saying so. The pack's default is 12 students, so
`--test 3` fits and `--test 4` needs `STUDENT_COUNT` lowered (`--env`/`dojo.local.toml`).

`account.d/57-netlab.sh` seeds a bot's `~/netlab` like a student's and also copies `solutions/` into the bot's own
`~/.netlab-solutions`. The folder is mounted read-only at `/opt/netlab-private/solutions`, a root-only directory, so no
student can read the solutions. The bot steps are in `workshops/netlab-ansible/content/bots/steps.sh`.
