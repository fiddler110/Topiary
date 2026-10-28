# NETLAB-PLAN: per-student firewall pods for learning Ansible

Status: **in progress** on branch `feat/netlab-module`. This is the design for a new module, `modules/netlab`.
The first design (FRR routers) and the second (Juniper cSRX with containerlab) were dropped; see section 10 for why.

## 1. Goal

The lab teaches **Ansible**, and the firewall is only the thing being configured. The depth is in Ansible: inventory,
ad-hoc commands, playbooks, variables, templates, handlers, idempotency, check mode, secrets, error handling, roles.

Every student gets **two parallel networks that start identical**:

- **Branch M (manual)**: the student SSHes in and configures the firewall and web server **by hand**.
- **Branch A (automated)**: the student writes **playbooks** that must produce the same result.

Doing it by hand first shows what the playbook has to say, and makes the payoff of automating (repeat, undo, check, scale)
concrete. A seeded `compare.yml` and a **test bot** both check that the two branches ended up the same and that the
result is correct. See section 6 for the labs and section 7 for the bot.

## 2. Decisions

| Topic | Decision |
|---|---|
| Firewall | **Linux netfilter** (iptables/nftables) in a small Alpine container. No licence, no KVM, no containerlab, works offline |
| Parallelism | **One pod per student** with two branches: `client-NN` plus `fw-m-NN`/`web-m-NN` (manual) and `fw-a-NN`/`web-a-NN` (automated). With the switch that is 8 containers per student. **Capped at 15 students** (`NETLAB_MAX_STUDENTS=15`, the generator refuses more): 120 containers and 90 networks, under the rootless-podman key limit (section 9.1). `NETLAB_MANUAL_BRANCH=0` drops branch M (4 per student) |
| Reach | Ansible runs from the student's existing terminal and SSHes to every node of the pod. Traffic probes run **from `client` against a web node** as real Ansible tasks |
| Entry point | Existing gateway and per-student ttyd. No new Caddy and no `student-shell` |
| Web server | `web-m-NN` and `web-a-NN` run **nginx** (HTTP and HTTPS), configured by the student's playbooks |
| Fronting | A browser page, `/netlab-view/`, shows the student's own page *as the pod's client sees it*, so it appears only when the firewall allows it (same idea as the CTF range's `ctf-view`) |
| Checking | A **bot** service verifies each lab from outside the pod and returns a verdict (same idea as `ctf-checker`) |
| Switch | A **VLAN-aware Linux bridge** container (`sw`) per branch, **on by default** (`NETLAB_SWITCH=1`, section 6.2). It is configured very differently from the firewall, which is the point |
| Vendor firewalls | Out of scope. The pod shape allows a Juniper or Fortinet node later as an optional track |

## 3. Architecture

```text
 web-terminal (Ansible control node; one shared container, per-student accounts)
       |  netlab_mgmt (internal: true, fixed subnet): SSH :22 to every node
       |
       +--- client-07 ==cm==> fw-m-07 ==mw==> web-m-07     branch M: configured by hand
       |         \
       |          ==ca==> fw-a-07 ==aw==> web-a-07          branch A: configured by playbooks
       (cm, mw, ca, aw: one internal /29 network each; one pod per student NN; pod 00 for the facilitator)
```

- `netlab_mgmt` is declared in `modules/netlab/compose.yml` with `internal: true`. The terminal and every node join it.
  It carries Ansible's SSH only. No internet, no LAN, no published port.
- Each pod has four data networks, `netlab_NN_cm`, `_mw`, `_ca`, `_aw`: `internal: true`, a **/29** each (Docker keeps `.1`
  as the gateway, so a /30 cannot hold two nodes), two members each. The terminal is not on them. `client` has two data
  interfaces, one per branch, and the two branches use different subnets so a mistake in one cannot reach the other.
- One image, `topiary/netlab-node`, picks its job from `NODE_ROLE`:
  - `fw`: IP forwarding on; baseline `FORWARD` policy DROP with a jump to a student-owned chain `LAB`; SSH allowed only from the management network.
  - `web`: **nginx** serving a default page on 80, the thing to reach. The student adds HTTPS, content and hardening.
  - `client`: a normal host with `curl` and `nc`; the probe runs here, once per branch.
  - all: `sshd` with **root login by password** (no `sudo`, no `become`; see the spike results) and Python 3 so Ansible modules run.
- `client` and `web` add routes to each other's subnets via their branch's `fw` at start. Both branches start from the same baseline.
- Capabilities: `cap_drop: [ALL]` plus the measured minimum (section 9.1). No `SYS_ADMIN`,
  no `privileged`, no Docker socket. `mem_limit` about 32m per node, `pids_limit`, `no-new-privileges`, `init: true`.

### Keeping students out of each other's pods

All pods share `netlab_mgmt` and all students share one terminal container, so network separation alone is not enough.

1. **Per-pod credentials**: each pod's `root` password is `HMAC(STUDENT_PASSWORD_SEED, "netlab:<NN>")`, written only to that
   student's `~/.config/dojo/netlab-password` (`0600`), the same pattern as `modules/dns-gate/terminal/start.d/50-dns-key.sh`.
2. **Per-uid firewall in the terminal** (built, same shape as `modules/ctf-range/terminal/start.d/50-ctf-range.sh`): every node
   has a fixed management address (pod N: `10.80.1.(8N)`..`(8N+7)`; `netlab_mgmt` is `10.80.0.0/22`, services take
   dynamic addresses from `10.80.0.0/24`), and `terminal/start.d/50-netlab.sh` runs `netlab_fw.py` to load a
   `NETLAB_ISOLATION` chain on `OUTPUT`: root returns, studentN's uid (and demo bot K's, pod STUDENT_COUNT+K) returns for
   pod N's block only, everything else to `netlab_mgmt` is dropped (`REJECT` never reaches the local socket from `OUTPUT` here). It fails closed: if the rules cannot be
   loaded and read back the hook exits 1 and the engine stops the container, because starting with every pod open would
   only be noticed after someone read another pod's nodes. `NET_ADMIN` is already on `web-terminal` (engine, for
   `DOJO_ISOLATION`). **Residual:** root on one's own node shares the `netlab_mgmt` segment, so another pod's SSH is
   reachable from there (password only); closing it needs a management network per pod.

## 4. Engine change: a per-module generator

Compose cannot loop over students. `engine/dojo/start.py` `_plan` already writes generated files under `engine/.generated/`
and appends them to the compose file list, so a module can do the same:

- If `modules/<m>/generate.py` exists, `_plan` runs it with the resolved environment, writes `.generated/modules/<m>.yml`
  (`.generated/dry-run/...` on `--dry-run`) and appends it after that module's `compose.yml`.
- A module without `generate.py` is unchanged. Tests go next to the other engine tests; `docs/authoring.md` section 6 documents it.
- `generate.py` reads `STUDENT_COUNT`, `STUDENT_PREFIX`, `STUDENT_PASSWORD_SEED` and `NETLAB_*`, and emits the pod services and networks.

## 5. Files

```text
modules/netlab/
  README.md  module.env  compose.yml
  generate.py  test_generate.py
  node/Dockerfile  node/entrypoint.sh  node/probe-agent.py
  netlab-view/  netlab-checker/        (Python stdlib services, each with tests)
  extensions.json                      the /netlab-view route, card, status checks
  terminal/Dockerfile  terminal/account.d/57-netlab.sh
  terminal/seed/   ansible.cfg hosts.ini group_vars/all.yml probe.yml compare.yml verify_topology.yml reset_fw.yml labs/0..8 LAB-README.md
  terminal/cmd (the `dojo netlab check` command and key hook)
  solutions/       facilitator-only, never copied into homes
engine/dojo/start.py (+ tests)   the generator hook
docs/modules.md  docs/authoring.md
```

## 6. Seeded workspace (`~/netlab`)

- `ansible.cfg`: local inventory and log, `host_key_checking = False`, short timeouts, `ControlPersist`, `pipelining`.
- `hosts.ini`: groups by branch and by role (`[manual]`, `[auto]`, `[fw]`, `[web]`, `[client]`) holding the student's own nodes by Docker DNS name. **The playbooks the student writes target `[auto]`; branch M is the hands-on branch, reached with `ssh`.** Plain `ansible.builtin.*` modules, so no collections (`community.crypto` is deliberately avoided so labs run offline with nothing extra baked in).
- `group_vars/all.yml`: the student comes from `$USER`, the pod number from the account name. Topiary does **not** export `DOJO_USER` or `WORKSHOP_SLUG` to terminals.
- `probe.yml`: runs on `client`, tests a branch's web node, takes `-e branch=m|a -e expect=allowed|blocked`, prints PASS or FAIL.
- `compare.yml`: reads the normalised firewall rules and the web server's effective config from both branches and shows the difference (itself an Ansible lesson in facts, `delegate_to` and set arithmetic). Empty diff means the two routes agree.
- `verify_topology.yml`: reachability, facts, baseline asserts, and a node x check matrix that exits non-zero on any red cell.
- `reset_fw.yml`: returns the student's firewalls and web nodes to the baseline (both branches, or `-e branch=a`).
- `labs/`: one folder per lab with a `README.md`, starter files and TODO markers (section 6.1). Solutions stay in `solutions/`.

### 6.1 The lab path

Both branches start **closed**: each `fw` allows only ICMP echo from `client` to its `web` and drops everything else, and
each `web` serves nginx's default page. Every lab has the same four parts:

1. **By hand on M**: the lab README states the goal, not the commands. The student SSHes in and does it.
2. **By playbook on A**: they write the playbook that does the same, on the automated branch.
3. **Prove it**: `probe.yml` for the traffic, `compare.yml` for "both branches agree".
4. **The twist**: something that is easy to do once by hand and painful to repeat (run it again, undo it, change one value,
   do it on a second host), where the playbook wins. The bot (section 7) confirms the result.

| # | Lab | Ansible concepts | Hand-built on M, then automated on A |
|---|---|---|---|
| 0 | **Orientation** | inventory, groups, `ansible` ad-hoc, `setup` facts, `ping` module, `ansible-inventory`, `ansible-doc` | Find out what is on each node by hand (`ip a`, `iptables -L`), then gather the same with facts |
| 1 | **A first playbook: the web page** | plays and tasks, `copy`, `template` (Jinja2), handlers, `become` | Edit `index.html` by hand; then template it with the student's name. Ping works, HTTP still blocked |
| 2 | **Variables, loops, conditionals: open HTTP and HTTPS** | `vars`, `group_vars`/`host_vars`, precedence, `loop`, `when`, `ansible.builtin.iptables` | Type the `iptables` rules for 80 and 443; then drive them from one variable list |
| 3 | **Idempotency and check mode** | `--check --diff`, `changed_when`/`failed_when`, `command` with `creates:`, running twice | Make a self-signed certificate by hand; then make the playbook safe to rerun (`changed=0`). The twist: rerun both |
| 4 | **Templates, handlers, validate: open SSH safely** | `template` with `validate:`, `lineinfile`, handlers, `notify`, per-group vars | Harden `sshd_config` and nginx TLS by hand, with a typo that locks something out; then use `validate:` so the playbook cannot |
| 5 | **Secrets with Vault** *(stretch)* | `ansible-vault`, encrypted vars, `no_log`, `vars_prompt`, `--vault-id` | Put a password on `/admin` by hand with `htpasswd`; then keep it in Vault so it never appears in git or logs |
| 6 | **Errors, rollback and tests: lock it down** | `block/rescue/always`, `assert`, `retries`/`until`, `ignore_errors`, `serial`, run order | Lock the server down by hand, break the page, scramble to undo; then a playbook that tests after each step and rolls back |
| 7 | **Roles and structure** *(stretch)* | `roles/`, `defaults`, `tasks/main.yml`, `import_` vs `include_`, tags, `ansible-lint` | Refactor labs 1-6 into one role without changing behaviour (`compare.yml` stays empty) |
| 8 | **Capstone: from clean to done** | everything above; `reset_fw.yml`, then `site.yml` once, then again | Rebuild branch A from the baseline with one `site.yml` that matches the hand-built M; second run `changed=0` |

Core path for a half day: **0, 1, 2, 3, 4, 6, 8**. Labs 5 and 7 are stretch and are marked in each README.

Management traffic (the terminal's SSH to every node on `netlab_mgmt`) is allowed by an early baseline rule on the
management interface, so a lab cannot lock the student out of Ansible. Student rules live in the `LAB` chain and are
scoped to the data-plane interface. The "lock it out" twists in labs 4 and 6 therefore break the *data plane*, which
`reset_fw.yml` repairs.

### 6.2 The switch (on by default, `NETLAB_SWITCH=1`)

**The teaching arc is hand-holding first, then building.**

- **Firewall labs (1-4, 6, 8) are guided.** There is an Ansible module (`iptables`), the labs ship starter playbooks with `TODO` markers,
  and the student learns the Ansible concepts on well-trodden ground.
- **Switch labs (S1-S3) are build-it-yourself.** There is no core module for a switch, and the starter is a **blank file**. The
  README gives the target state and a short reference of the `bridge`/`ip` commands, and the student designs their own
  data model (a VLAN list in `group_vars`), their own **Jinja2 template**, and their own idempotency guard. The bot judges the
  resulting state, so any correct design passes. Hints are available (two per lab, like the CTF labs) and a reference solution is in `solutions/`.

Different Ansible problem, same skills: **configuring something with no module**, using `template` + `command` and making it idempotent.

Per branch the flat `client - fw - web` becomes **router-on-a-stick** with a switch in the middle:

```text
   pc (VLAN 10) --access--> [ sw ] <--access-- web (VLAN 20)
                              |
                            trunk (VLAN 10, 20)
                              |
                            [ fw ]  eth0.10  10.10.10.1/24
                                    eth0.20  10.10.20.1/24     the only path between VLANs, so the firewall rules apply
```

Verified by spike (2026-10-28, `cap_drop: ALL`, `NET_ADMIN` only): a `vlan_filtering` bridge with access and trunk ports
(`bridge vlan add ...`) passes tagged frames across Docker's internal networks; the firewall's 802.1Q subinterfaces route
between the VLANs; the switch learns MACs per VLAN (`bridge fdb show`). No extra capability beyond `NET_ADMIN`.

| # | Lab | Ansible concepts | What differs from the firewall |
|---|---|---|---|
| S1 | **VLANs and access ports** | design a data model, write a `template` from scratch, `command` with `changed_when`, guards (`bridge vlan show` first), `bridge -j vlan show` parsed with `from_json` | No module and no starter: the playbook must decide "already configured?" itself |
| S2 | **Trunk and router-on-a-stick** | write the subinterface `template` yourself, `loop` over a VLAN data structure, handlers, `serial: 1` | One data structure (VLAN list) drives the switch **and** the firewall |
| S3 | **Segmentation policy** | `assert`, `block/rescue`, cross-device ordering with `delegate_to`/`run_once` | Open VLAN 10 to VLAN 20's web only; everything else dropped; the bot proves it |

Cost: 4 nodes and 3 data networks per branch, so 8 nodes and 6 networks per student (120 containers and 90 networks for the 15-student cap).
**Scale risk to measure**: podman starts containers slowly at this size (section 9.1), so start time at 120 is recorded when the node image exists.
Mitigations: `NETLAB_SWITCH=0` (flat pod, section 3); `NETLAB_MANUAL_BRANCH=0` (automated branch only). Because the switch is now standard, the pod topology (section 3) is the switch topology by default, and the flat pod is the fallback.

## 7. Fronting and the test bot

Both reuse patterns from `modules/ctf-range/`.

- **Probe agent** (a small stdlib Python service on the management network). On `client-NN` it runs the tests *from the pod's
  own client*, per branch: ICMP, a TCP connect, an HTTP or HTTPS fetch, a port scan of that branch's `web`. On every `fw` and
  `web` node it reports **normalised state** (`iptables-save` without counters and comments, the effective nginx config and
  `sshd -T`). It answers only with a per-pod token that the bot and the view know and students do not.
- **`netlab-view`** (route `/netlab-view`, `gate: identity`, like `ctf-view`): shows the caller's own branch-A and branch-M pages (two tabs) by
  asking that pod's probe agent to fetch each. If the firewall blocks HTTP, the browser shows "blocked". Uses
  `modules/_shared/dojo_http.py` to read the gateway identity.
- **`netlab-checker`** (like `ctf-checker`): `POST /check {user, key, lab}`. The key is the account's own, derived
  `HMAC(seed, "netlab-check:<user>")` and stored in `~/.config/dojo/netlab-check-key`, so a caller can only name itself.
  It runs the lab's assertions through the pod's probe agent and returns a verdict per assertion, so the student sees
  what failed. Rate-limited per user. Terminal command: `dojo netlab check <lab>` (follows the existing `dojo check` style).
- **The bot as an attacker view**: the checker scans each `web` for open ports and tries disallowed paths (SSH from a
  non-client source, a high port), so lock-down labs are judged on what is exposed, not on which rules the student wrote.
- **"Two routes, one result"**: for every lab the checker also compares branch M with branch A (normalised state), so the
  verdict says *the manual and the automated branches match* or lists exactly what differs. A correct playbook that does
  something different from the hand-built branch fails, and so does a manual branch that does not meet the goal.
- Student-side `probe.yml` stays: the student proves each change with Ansible (the learning), and the bot confirms it independently (the grade).
- Later, optional: report results to the `achievements` module with signed adapter events.

## 8. Lifecycle and persistence

- `~/netlab` is on the `terminal_home` volume: kept by `./dojo restart`, wiped by `./dojo stop`. The seed hook never overwrites. There is no `/workspace`.
- Firewall state is not persisted. `./dojo restart` recreates pods at the baseline. A per-student reset is `ansible-playbook reset_fw.yml`.
- The generator is deterministic, so a restart reproduces the same pods and passwords.

## 9. Spike, build order and verification

**Spike (done, results in 9.1):** hand-build one pod **with both branches**; confirm routing through each `fw`, the DROP baseline, `interface_name`
support and the minimum capabilities (nginx, sshd, iptables, `ping` without `NET_RAW` via `net.ipv4.ping_group_range`); run Ansible against branch A
(blocked, allowed, blocked); measure memory and start time for one pod and for 15.

The `sw` node role and the VLAN-aware pod topology are built together with the flat one (step 2-3), not after; the **S1-S3 labs and their bot checks** are built after the firewall labs run end to end.

**Build order:** 1 spike, 2 node image (nginx, sshd, probe agent), 3 generator and tests, 4 engine hook and tests, 5 `compose.yml` and `module.env`,
6 terminal image and seed hook, 7 labs 0-8 run end to end with `probe.yml` and `compare.yml` (core path first: 0-4, 6, 8), **8 `netlab-checker` and the probe agent, 9 `netlab-view`**, 10 README, docs, lint and `--dry-run`.
Steps 1-7 are a usable release on their own (self-checked labs); 8-9 add the bot and the browser page.

**Verification:** unit tests (generator, hook); `lint-repo.sh`; `./dojo <workshop> --dry-run`; every `netlab_*` network
`Internal: true` and only the gateway publishes a port; five accounts run the core labs at the same time; the bot gives a pass on a correct solution and a specific fail on each wrong one (open too much, open too little, break the page); one account
cannot log in to another pod; `./dojo stop` leaves no `netlab_*` containers or networks; a 15-student start with the switch (120 containers, 90 networks) with start time and idle memory recorded, and the same with `NETLAB_MANUAL_BRANCH=0` (60); the generator rejects 16 students.

### 9.1 Spike results (2026-10-28, this host, Docker 29.8.1, Compose 5.5.1)

All run with `cap_drop: [ALL]`, `no-new-privileges`, and one network namespace per container. Everything was removed afterwards.

| Check | Result |
|---|---|
| Node image | Alpine 3.24 (digest already pinned elsewhere in the repo) with `openssh python3 sudo iptables iproute2 nginx curl libcap openssl busybox-extras`: **76 MB**. `iptables` is the nf_tables build; nginx 1.30.6, Python 3.14 |
| Routing | `client` and `web` each add one route via `fw`; `fw` needs `net.ipv4.ip_forward=1` (a compose `sysctls` entry) and `NET_ADMIN` |
| Baseline | `FORWARD` DROP plus ICMP echo/reply accept: ping client to web works, HTTP is blocked (`curl` returns `000`); after an allow rule HTTP is served |
| Ping without `NET_RAW` | Works with `sysctls: net.ipv4.ping_group_range: "0 2147483647"` on `client` |
| Capabilities (`sshd`) | `NET_ADMIN SETUID SETGID SYS_CHROOT CHOWN DAC_OVERRIDE NET_BIND_SERVICE` is enough. No `SYS_ADMIN`, no `NET_RAW`, no `KILL` |
| Capabilities (nginx) | `CHOWN SETUID SETGID DAC_OVERRIDE NET_BIND_SERVICE` started nginx and served HTTP |
| **`no-new-privileges` breaks `sudo`** | `sudo: The "no new privileges" flag is set, which prevents sudo from running as root.` So nodes use **root over SSH** with the derived password and `ansible_become: false`. This keeps `no-new-privileges` (a repo convention) and costs nothing in the lab |
| Ansible against a node | `ansible-core` from a separate container over SSH as root: `ping` pong; a playbook that creates the `LAB` chain and loops `ansible.builtin.iptables` over ports 80 and 443 gives `changed=2` on run 1 and **`changed=0` on run 2** |
| Isolation | A container on an `internal: true` network could not reach the Alpine mirrors, as intended |
| VLAN switch | `vlan_filtering` bridge with access and trunk ports, 802.1Q subinterfaces on `fw`, inter-VLAN ping through `fw`, MAC learning per VLAN: all work with `NET_ADMIN` only (section 6.2) |
| Memory | Idle `sshd`-only node about **1.4 MiB**; an nginx web node about **11 MiB**. A full pod (6 plain + 2 web nodes) is about **31 MiB**, so 30 pods is about **1 GB** before Docker's own overhead. A per-node `mem_limit` of 32m is generous; 64m was used in the spike |
| Networks at scale | Creating **180** `internal: true` /29 networks (a 30-student class with the switch) took **7 s**. Not yet measured: starting 240 containers together, and the host's iptables rule count with them |
| Addressing | A /29 holds 5 usable addresses after Docker takes `.1`, enough for two nodes. Subnets can be carved from one range (e.g. `10.81.x.y/29`) |
| `interface_name` (re-checked 2026-10-28, rootless podman 5.7.0 + podman-compose 1.5.0) | **Not honoured.** The key is accepted and ignored: a node asked for `lan0`/`wan0` got `eth0`/`eth1`. `./dojo` runs on podman here, not Docker. The entrypoint must find interfaces by IP, not by name |
| Engine caveat | Docker is **not installed on this machine** (podman + podman-compose only, as `CLAUDE.md` says). The rows above dated 2026-10-28 were measured on Docker 29.8.1 / Compose 5.5.1, so capability, `sysctls` and `no-new-privileges` results still need a re-run under rootless podman when the node image exists |
| **240-container class (podman)** | **Does not fit this host as is.** `podman-compose up -d` of 240 `sleep` nodes on 180 internal /29 networks took **1845 s (about 31 min)** and stopped at **196 containers** with `crun: create keyring ...: Disk quota exceeded`. Cause: `kernel.keys.maxkeys` is 200 per uid and each rootless container uses one key (uid 1000 showed 200/200). Teardown took several more minutes. A class of 30 with the switch is out of reach here; 30 without the switch (150) fits under the key limit. Raising `kernel.keys.maxkeys` needs root and was not done |
| Idle memory at 196 containers (podman) | Host used memory 945 to 1313 MiB, **about 1.9 MiB per container**, mostly `conmon` (about 2.2 MiB each). Container cgroup usage is about 0.25 MiB for an idle `sleep`. Add the nginx and `sshd` footprint from the Docker spike for the real figure |
| **Built and run on podman (2026-10-28)** | `./dojo netlab-ansible` (then named `netlab-dev`) with 3 students (4 pods, 32 nodes) came up healthy. Verified from a student's terminal: Ansible reaches all 8 nodes of its pod as root with the derived password; the same password is refused by another pod; ping crosses switch and firewall, HTTP is blocked until a rule is added to `LAB`, and the other branch stays closed; `probe.yml`, `compare.yml` (it flagged a hand-added rule) and `reset_fw.yml` behave. Interfaces are found by address, so `interface_name` is not needed |
| Rootless podman: `ping_group_range` | `"0 2147483647"` is rejected (`crun: write to /proc/sys/net/ipv4/ping_group_range: Invalid argument`: that gid is not mapped). `"0 0"` works because the nodes ping as root |
| Addressing as built | Docker-level `/29`s are unique per pod and branch (from `10.81.0.0/16`). The lab addresses (`10.10.10.0/24`, `10.10.20.0/24`) are the same in every pod and both branches, since each branch is its own isolated L2 segment. This replaces the "different subnets per branch" idea in section 3 |
| Still not measured | Start time and idle memory of the 15-student class (128 nodes with the facilitator's pod); host iptables/nft rule count; nginx and `sshd` together under load |

## 10. How the design got here

- **FRR routers** worked (OSPF reached `Full` over an internal bridge on `quay.io/frrouting/frr:10.7.1`; Docker Hub's image stops at 8.4.1).
  LLDP did not cross a default Docker bridge, and FRR needed `SYS_ADMIN`. The lab is about Ansible, so routing was more than it needed.
- **Juniper cSRX with containerlab** needs a licence-bound tarball, about 4 GB of RAM per firewall, and containerlab on the host
  (which has no hook in `dojo` today). Per-student firewalls would not fit a class.
- **Linux netfilter** keeps the block/allow labs, costs almost nothing per student, and needs nothing outside the repo.
- **Two branches** (manual and automated) came from the goal that the labs are about Ansible: building the same thing by hand first
  makes each playbook's purpose obvious and gives the bot an objective comparison.

## 11. Out of scope

Vendor firewalls (cSRX, FortiGate), routing labs, containerlab, a standalone non-Topiary compose, and a full workshop pack
(slides, achievements, `FACILITATOR.md`) was a follow-up and is now `workshops/netlab-ansible` (2026-10-28).
