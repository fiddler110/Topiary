# netlab module

Per-student practice networks for learning Ansible: a pc, a VLAN switch, a Linux firewall and an nginx web node,
twice (one branch configured by hand, one by playbooks), all on internal-only networks.

Add it with `MODULES="netlab"` in a `workshop.env`, and keep `STUDENT_COUNT` at or below `NETLAB_MAX_STUDENTS` (15).
The design, spike results and the lab path are in `NETLAB-PLAN.md` at the repo root.

| Part | What it does |
|---|---|
| `node/` | One Alpine image for every node; `NODE_ROLE` (pc, sw, fw, web) picks the job. SSH as root with a per-pod password. |
| `generate.py` | Writes the pods as a Compose file at start (`.generated/modules/netlab.yml`); `test_generate.py` covers it. |
| `compose.yml` | Builds the node image, declares the internal `netlab_mgmt` network (10.80.0.0/22) and puts the terminal on it. |
| `terminal/netlab_fw.py`, `terminal/start.d/50-netlab.sh` | The per-uid firewall (below). `test_fw.py` covers the rule generation and checks it agrees with `generate.py`'s addressing. |
| `netlab-view/` | The "My Network" page (`/netlab-view/`, identity gate; an `/admin` tab of the same id for the facilitator). Read-only: per node up/down, interfaces and addresses, switch VLANs per port, firewall `LAB` rules, the pc's ping/HTTP/HTTPS probe of web, and the latest `dojo netlab check` verdicts (kept in memory by `netlab-checker`, read through `GET /last/<pod>` with a token only the view derives). A student reads only their own pod; the facilitator reads every pod. It SSHes to the nodes with `netlab-checker/checker.py`, one collection per pod per 4 s. Tests: `python3 -B -m unittest discover -s modules/netlab/netlab-view`. |

## Keeping students out of each other's pods

Every student shares one terminal container (one network namespace) and every pod's nodes sit on `netlab_mgmt`, so two
things stand between student N and pod M: the pod's derived root password, and a per-uid firewall.

- **Addresses.** Every node has a fixed management address (`generate.py` `mgmt_ip`): pod N owns the eight addresses
  `10.80.1.(8N)` to `10.80.1.(8N+7)`, a node's slot is `branch*4 + role`. The services (terminal, checker, view) take
  Docker's pick from `10.80.0.0/24` (`ip_range`), so nothing dynamic can land in a pod's block. Up to 32 pods fit.
- **Rules.** `start.d/50-netlab.sh` runs `netlab_fw.py` as root once every account exists. It loads a `NETLAB_ISOLATION`
  chain at the top of `OUTPUT` with `iptables-restore --noflush` (one step, so a re-run has no open window): uid 0 is
  left alone; the uid of studentN (and of demo bot testuserK, pod STUDENT_COUNT+K) may reach only its pod's block;
  everyone else is dropped for the rest of `netlab_mgmt`: the connection never opens and the sender sees a timeout (`REJECT` was measured not to reach the local socket in the terminal's namespace, in any variant).
  Nothing else is touched: the gateway, DNS, Forgejo and the checker (the terminal reaches `netlab-checker` on
  `workshop_lab`, never on `netlab_mgmt`) are different destinations. The facilitator is root, so keeps every pod, and the
  checker and view are separate containers that the terminal's rules never see.
- **Fails closed.** If the rules cannot be loaded or read back, the hook exits 1; the engine stops the container on a
  failing `start.d` hook, so the netlab labs refuse to start rather than run with every pod open. A class that does not
  start is noticed at once; a silent open pod would only be noticed after someone read another pod's nodes. It needs
  `NET_ADMIN` on `web-terminal`, which the engine already grants for `DOJO_ISOLATION`, so the module adds no capability.
  The chain lives in the container's network namespace and is rebuilt at every start.
- **What it does not cover.** Anyone with root on their own node (the student has that password) is on the same
  `netlab_mgmt` segment as the other pods' nodes and can reach their SSH from there; only the other pod's derived root
  password stops that. Closing it needs a management network per pod, with the terminal on all of them.

## Capstone proof for the achievements module

`netlab-checker` keeps its latest verdict per pod and lab in memory (`LAST`, only ever set after the checker has itself
SSHed into the nodes and run a lab's assertions). `POST /proof {user, labs}` answers `{passed, missing}` from that record,
and only to a caller sending `X-Netlab-Proof-Token`. The token is `NETLAB_PROOF_TOKEN`, derived in `module.env` from the
install's `GATEWAY_TOKEN` and handed to the checker and the `achievements` service only (never to the terminal, never the
check key a student holds or the view token), so a student cannot ask it or forge its answer. The achievements verb
`netlab_labs_passed` (`modules/achievements/plugins/netlab`) calls it with the checking student's own user name; the
pack's `capstone.json` lists labs 0-4, 6 and 8 (lab 8 includes the manual-versus-automated comparison). The record is lost
when the checker restarts, so students re-run the checks `dojo check capstone` names; a capstone already earned is kept.
No effect without the achievements module (the token is then unused). Tests: `netlab-checker/test_checker.py` (`Proof`).

## Demo bots (`--test`)

Bots are treated like students. With `./dojo netlab-ansible --test N [--fast]`, `testuserK` gets pod `STUDENT_COUNT + K`
(`generate.py` reads `BOT_COUNT`; `netlab-checker` and `netlab-view` map the same names to the same pods, and the
facilitator sees the bot pods like any other). Students and bots share the cap: `STUDENT_COUNT + BOT_COUNT` must stay at or
below `NETLAB_MAX_STUDENTS` (15), or the generator fails with a message saying so. The pack's default is 12 students, so
`--test 3` fits and `--test 4` needs `STUDENT_COUNT` lowered (`--env`/`dojo.local.toml`).

`account.d/57-netlab.sh` seeds a bot's `~/netlab` like a student's and also copies `solutions/` into the bot's own
`~/.netlab-solutions`. The folder is mounted read-only at `/opt/netlab-private/solutions`, a root-only directory, so no
student can read the solutions. The bot steps are in `workshops/netlab-ansible/content/bots/steps.sh`.
